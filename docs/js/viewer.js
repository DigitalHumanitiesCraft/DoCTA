import { initNav, initBanner } from './app.js?v=20261020-en';
import { loadJSON } from './data-loader.js';
import { getParams, setParams, escapeHTML, escapeAttr,
         lsGet, lsSet, catLabel, vocabLabel, formatDate } from './utils.js';
import { createTeiView, renderReading,
         renderTranscription } from './viewer-render.js?v=20261020-readings';
import { createReviewView } from './viewer-review.js?v=20261020-readings';
import { createLocalEditor } from './viewer-local.js';
import { createRegistryEditor } from './viewer-registry.js?v=20261020-segments';
import { createAnnotationWorkspace } from './viewer-annotation-workspace.js';
import { createTextStatus, editionUrl, pageProgress } from './viewer-status.js?v=20261020-progress';
import { STATUS_DETAILS, PROGRESS } from './strings.js';
import { imageDocument } from './source-images.js';

initNav('viewer');
initBanner();
const local = createLocalEditor();
const annotationWorkspace = createAnnotationWorkspace();

let viewer = null;
let imageKey = null;
let imageUrl = null;
let currentDoc = null;
let currentPage = 0;
let viewMode = 'synopsis';
let rotation = 0;
let sourceByDocId = new Map();
let registerByDocId = new Map();
let imageDocuments = new Map();

const transcriptionContainer = document.getElementById('transcription-container');

const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

const textStatus = createTextStatus({
  group: document.getElementById('text-status'),
  pill: document.getElementById('doc-provenance'),
  credit: document.getElementById('doc-edition-link'),
  details: document.getElementById('text-status-details'),
});

// The pill states the document's attribution and the current page's state in
// one place; an unsaved draft takes it over until it is saved or discarded.
function updateTextStatus() {
  textStatus.update({
    doc: currentDoc,
    reg: currentDoc ? registerByDocId.get(Number(currentDoc.docId)) : null,
    pageNr: currentPageNr(),
    scope: viewMode === 'synopsis' ? 'page' : 'document',
    dirty: Boolean(currentDoc) && review.hasDraft,
  });
}

function renderDocMeta(docId) {
  const source = sourceByDocId.get(Number(docId));
  const reg = registerByDocId.get(Number(docId));
  const title = source?.titel || currentDoc?.title || 'Source';
  document.getElementById('source-title').textContent = title;
  document.getElementById('source-shelfmark').textContent = source?.signatur || 'Not recorded';
  const date = source?.datierung ? formatDate(source.datierung) : '';
  document.getElementById('source-date').textContent = date || 'Not recorded';
  const field = (label, value) => value
    ? '<div><dt>' + escapeHTML(label) + '</dt><dd>' + escapeHTML(String(value)) + '</dd></div>' : '';
  let details = field('Title', title) + field('Shelfmark', source?.signatur) +
    field('Date', date) + field('Archive', 'Tyrolean State Archives') +
    field('Source type', source?.kategorie && catLabel(source.kategorie)) +
    field('Archival unit', source?.art && vocabLabel('archivalUnit', source.art)) +
    field('Transcription project', reg?.transcription_by || source?.transkribiert) +
    field('Transkribus document', docId);
  const url = editionUrl(reg);
  if (url) {
    details += '<div><dt>Original edition</dt><dd><a class="doc-meta__edition" href="' +
      escapeAttr(url) + '" target="_blank" rel="noopener">' +
      escapeHTML(STATUS_DETAILS.editionLink) + '</a></dd></div>';
  }
  document.getElementById('source-details').innerHTML = details;
}

function initOSD() {
  const placeholder = document.getElementById('osd-placeholder');
  if (placeholder) placeholder.remove();
  viewer = OpenSeadragon({
    id: 'osd-viewer',
    showNavigator: false,
    showNavigationControl: false,
    maxZoomLevel: 5,
    defaultZoomLevel: 0,
    animationTime: reduceMotion ? 0 : 1.2,
    gestureSettingsMouse: { clickToZoom: false, dblClickToZoom: true },
  });
  viewer.addHandler('open', buildLineOverlay);
  viewer.addHandler('close', clearLineOverlay);
}

// === Line regions ===
// Each page of the export carries polygon coords per line in full-image pixel
// space. They become one SVG overlay: a type:image world item is 1 unit wide,
// so the overlay rect is 1 x aspect and the SVG viewBox does the scaling.
const SVG_NS = 'http://www.w3.org/2000/svg';
let lineOverlayEl = null;
let showLineRegions = false;
let activeLineId = null;   // line hovered in the transcription, zone highlighted
let linkedLineId = null;   // zone hovered in the image, line highlighted

function clearLineOverlay() {
  if (!lineOverlayEl) return;
  if (viewer) {
    try { viewer.removeOverlay(lineOverlayEl); } catch { /* overlay already dropped */ }
  }
  lineOverlayEl.remove();
  lineOverlayEl = null;
  activeLineId = null;
}

function zoneFor(lineId) {
  return lineOverlayEl
    ? lineOverlayEl.querySelector(`[data-line-id="${CSS.escape(lineId)}"]`)
    : null;
}

function lineElFor(lineId) {
  return document.querySelector(
    `.transcription__line[data-line-id="${CSS.escape(lineId)}"]`);
}

// "x,y x,y ..." to an SVG points string, dropping malformed pairs
function parseCoords(coords) {
  if (typeof coords !== 'string') return null;
  const pts = coords.trim().split(/\s+/)
    .map(p => p.split(','))
    .filter(p => p.length === 2 && p.every(v => v !== '' && Number.isFinite(Number(v))));
  return pts.length >= 3 ? pts.map(p => p.join(',')).join(' ') : null;
}

function highlightZone(lineId) {
  if (activeLineId === lineId) return;
  if (activeLineId) zoneFor(activeLineId)?.classList.remove('line-zone--active');
  activeLineId = lineId;
  if (lineId) zoneFor(lineId)?.classList.add('line-zone--active');
}

function highlightLine(lineId) {
  if (linkedLineId === lineId) return;
  if (linkedLineId) lineElFor(linkedLineId)?.classList.remove('transcription__line--linked');
  linkedLineId = lineId;
  if (lineId) lineElFor(lineId)?.classList.add('transcription__line--linked');
}

function revealLine(lineId) {
  const el = lineElFor(lineId);
  if (!el) return;
  el.scrollIntoView({ block: 'center', behavior: reduceMotion ? 'auto' : 'smooth' });
  el.focus({ preventScroll: true });
}

function onZoneOver(e) {
  const id = e.target instanceof Element ? e.target.getAttribute('data-line-id') : null;
  if (id) highlightLine(id);
}

function onZoneOut(e) {
  const id = e.target instanceof Element ? e.target.getAttribute('data-line-id') : null;
  if (id && id === linkedLineId) highlightLine(null);
}

// OpenSeadragon captures the pointer on the canvas, so a click event never
// reaches the polygon. The zone press is completed on the document instead,
// and a drag of more than a few pixels stays a pan.
let pendingZone = null;

function onZonePointerDown(e) {
  const id = e.target instanceof Element ? e.target.getAttribute('data-line-id') : null;
  pendingZone = id ? { id, x: e.clientX, y: e.clientY } : null;
}

document.addEventListener('pointerup', (e) => {
  const pending = pendingZone;
  pendingZone = null;
  if (!pending) return;
  if (Math.abs(e.clientX - pending.x) > 4 || Math.abs(e.clientY - pending.y) > 4) return;
  revealLine(pending.id);
});
document.addEventListener('pointercancel', () => { pendingZone = null; });

// Transkribus scales full/max down to its maximum area, while PAGE coordinates
// address the original scan; info.json names the original size. Until it
// arrives, or where it fails, the loaded size stands in, which is exact for
// every image under that limit.
const originalSizes = new Map();
function originalSize(url) {
  const info = url.replace(/\/full\/[^/]+\/[^/]+\/default\.\w+$/, '/info.json');
  if (info === url) return null;
  if (!originalSizes.has(info)) {
    originalSizes.set(info, null);
    fetch(info).then(response => (response.ok ? response.json() : null)).then(data => {
      if (!(Number.isFinite(data?.width) && Number.isFinite(data?.height) &&
        data.width > 0 && data.height > 0)) return;
      originalSizes.set(info, { x: data.width, y: data.height });
      if (imageUrl === url) buildLineOverlay();
    }).catch(() => {});
  }
  return originalSizes.get(info);
}

function buildLineOverlay() {
  clearLineOverlay();
  if (!viewer || viewMode !== 'synopsis' || !currentDoc) return;
  const item = viewer.world.getItemAt(0);
  const page = currentDoc.pages[currentPage];
  if (!item || !page) return;
  const size = item.getContentSize();
  if (!size.x || !size.y) return;
  // A page of the export can arrive without layout analysis; there is then
  // no polygon to draw and the overlay stays away.
  if (!Array.isArray(page.regions)) return;

  const svg = document.createElementNS(SVG_NS, 'svg');
  svg.setAttribute('class', 'line-overlay');
  const coords = originalSize(imageUrl) || size;
  svg.setAttribute('viewBox', `0 0 ${coords.x} ${coords.y}`);
  svg.setAttribute('preserveAspectRatio', 'none');
  svg.setAttribute('aria-hidden', 'true');
  let count = 0;
  for (const region of page.regions) {
    for (const line of region.lines || []) {
      const points = parseCoords(line.coords);
      if (!points) continue;
      const poly = document.createElementNS(SVG_NS, 'polygon');
      poly.setAttribute('points', points);
      poly.setAttribute('class', 'line-zone');
      poly.setAttribute('data-line-id', line.id);
      svg.appendChild(poly);
      count++;
    }
  }
  if (!count) return;
  svg.classList.toggle('line-overlay--visible', showLineRegions);
  // Handlers live on the overlay element and go with it when it is removed
  svg.addEventListener('mouseover', onZoneOver);
  svg.addEventListener('mouseout', onZoneOut);
  svg.addEventListener('pointerdown', onZonePointerDown);
  viewer.addOverlay({
    element: svg,
    location: new OpenSeadragon.Rect(0, 0, 1, size.y / size.x),
  });
  lineOverlayEl = svg;
}

// The tooltip names what the next press does; the accessible name stays
// constant and aria-pressed carries the state.
function setLineRegions(on) {
  showLineRegions = on;
  const button = document.getElementById('btn-line-regions');
  button.setAttribute('aria-pressed', String(on));
  button.title = `${on ? 'Hide' : 'Show'} line regions (L)`;
  lineOverlayEl?.classList.toggle('line-overlay--visible', on);
}

function loadImage(iiifUrl) {
  if (!viewer) initOSD();
  const key = `${currentDoc.docId}/${currentPageNr()}/${iiifUrl}`;
  // Saving a reading re-renders the text, but keeps the inspected image area.
  if (imageKey === key && viewer.world.getItemCount()) {
    buildLineOverlay();
    return;
  }
  imageKey = key;
  imageUrl = iiifUrl;
  clearLineOverlay();
  document.getElementById('image-focus').value = 'spread';
  viewer.addOnceHandler('open', () => fitView(true));
  viewer.open({ type: 'image', url: iiifUrl });
  document.getElementById('osd-viewer').classList.add('osd-active');
  // A new page starts upright; rotation is a per-page inspection aid
  rotation = 0;
  viewer.viewport.setRotation(0, true);
}

function zoomBy(factor) {
  if (!viewer) return;
  viewer.viewport.zoomBy(factor);
  viewer.viewport.applyConstraints();
}

function rotateBy(delta) {
  if (!viewer) return;
  rotation = (rotation + delta + 360) % 360;
  viewer.viewport.setRotation(rotation, reduceMotion);
}

function fitView(immediately = false) {
  if (!viewer) return;
  const side = document.getElementById('image-focus').value;
  const item = viewer.world.getItemAt(0);
  if (!item || side === 'spread') { viewer.viewport.goHome(immediately || reduceMotion); return; }
  const size = item.getContentSize();
  const area = document.getElementById('osd-viewer').getBoundingClientRect();
  const height = Math.min(size.y, size.x / 2 * area.height / area.width);
  const rect = item.imageToViewportRectangle(
    side === 'right' ? size.x / 2 : 0, (size.y - height) / 2, size.x / 2, height);
  viewer.viewport.fitBounds(rect, immediately || reduceMotion);
}

document.getElementById('image-focus').addEventListener('change', () => fitView());

const panel = document.getElementById('facsimile-panel');
const btnFullscreen = document.getElementById('btn-fullscreen');

function toggleFullscreen() {
  if (document.fullscreenElement) {
    document.exitFullscreen();
  } else if (panel.requestFullscreen) {
    panel.requestFullscreen().catch(() => { if (viewer) viewer.setFullScreen(true); });
  } else if (viewer) {
    viewer.setFullScreen(true);
  }
}

document.addEventListener('fullscreenchange', () => {
  const on = document.fullscreenElement === panel;
  btnFullscreen.setAttribute('aria-pressed', String(on));
  btnFullscreen.title = on ? 'Leave full screen' : 'Show the facsimile in full screen';
});

// === Transcription text size ===
// Steps around the 1rem default; the choice is a per-browser convenience
// and survives via localStorage where that is available.
const FONT_KEY = 'docta-viewer-textsize';
const FONT_STEPS = ['0.8125rem', '0.875rem', '0.9375rem', '1rem',
                    '1.0625rem', '1.125rem', '1.25rem', '1.375rem'];
const FONT_DEFAULT = 3;
let fontIdx = (() => {
  const stored = Number.parseInt(lsGet(FONT_KEY) ?? '', 10);
  return Number.isInteger(stored) && stored >= 0 && stored < FONT_STEPS.length
    ? stored : FONT_DEFAULT;
})();

const btnFontDec = document.getElementById('btn-font-dec');
const btnFontInc = document.getElementById('btn-font-inc');

function applyFontSize() {
  document.documentElement.style.setProperty(
    '--transcription-size', FONT_STEPS[fontIdx]);
  btnFontDec.disabled = fontIdx === 0;
  btnFontInc.disabled = fontIdx === FONT_STEPS.length - 1;
  lsSet(FONT_KEY, String(fontIdx));
}

btnFontDec.addEventListener('click', () => {
  if (fontIdx > 0) { fontIdx--; applyFontSize(); }
});
btnFontInc.addEventListener('click', () => {
  if (fontIdx < FONT_STEPS.length - 1) { fontIdx++; applyFontSize(); }
});
applyFontSize();

function currentPageNr() {
  return currentDoc ? currentDoc.pages[currentPage]?.pageNr : null;
}

// === Curation view ===
// The review module owns the stored decisions and the line editor; the page
// hands it the review bar, where the reader currently stands, and the way
// back to a freshly rendered page.
const review = createReviewView({
  bar: document.getElementById('review-bar'),
  toggle: document.getElementById('btn-review'),
  initials: document.getElementById('review-initials'),
  hint: document.getElementById('review-hint'),
  exportBtn: document.getElementById('btn-review-export'),
  clearBtn: document.getElementById('btn-review-clear'),
  saveBtn: document.getElementById('btn-review-save'),
}, {
  getContext: () => ({
    docId: currentDoc ? Number(currentDoc.docId) : null,
    pageNr: currentPageNr(),
    viewMode: currentDoc?.imageOnly ? 'image' : viewMode,
    revision: currentDoc?.revision,
    reviewState: currentDoc?.reviewState,
  }),
  rerenderPage: renderPage,
  local,
  onDraftChange: updateTextStatus,
  onSaved: (doc) => {
    currentDoc = doc;
    registry.load();
    renderDocMeta(doc.docId);
    renderCurrentView();
  },
});

const registry = createRegistryEditor(local, {
  context: () => ({ doc: currentDoc, pageNr: currentPageNr(), hasDraft: review.hasDraft, viewMode }),
  rerender: () => { if (currentDoc) renderCurrentView(); },
  workspace: annotationWorkspace,
});

document.getElementById('btn-review').addEventListener('click', event => {
  if (!canNavigate()) { event.preventDefault(); event.stopImmediatePropagation(); }
}, { capture: true });

// A document DoCTA transcribed itself carries the model's brackets, which are
// not editorial notation until a reviewer saves the line.
function isMachineText() {
  return currentDoc != null &&
    registerByDocId.get(Number(currentDoc.docId))?.transcription_source === 'vlm';
}

// One page of the synopsis. The coupling with the image overlay is keyed on
// the rendered lines, so a fresh page starts with no line held on either side.
function renderPage(pageNr) {
  activeLineId = null;
  linkedLineId = null;
  renderTranscription(transcriptionContainer, currentDoc, pageNr, {
    corrections: review.corrections(pageNr),
    machine: isMachineText(),
  });
  review.applyMode();
  registry.render();
  if (currentDoc.imageOnly) {
    const note = document.createElement('p');
    note.className = 'loading';
    note.dataset.testid = 'no-transcription';
    note.textContent = 'No transcription is available for this digitised image.';
    transcriptionContainer.replaceChildren(note);
  }
  updateTextStatus();
}

const tei = createTeiView(transcriptionContainer, {
  getViewMode: () => viewMode,
  onRendered: updateTeiDownload,
});

// The link offers what the TEI view has actually shown; before the fetch and
// for a document without TEI the cache holds no text and the link stays away.
function updateTeiDownload() {
  const dl = document.getElementById('tei-download');
  const xml = currentDoc ? tei.cached(currentDoc.docId) : undefined;
  dl.hidden = viewMode !== 'tei' || xml == null;
  if (currentDoc && (xml != null || registerByDocId.get(Number(currentDoc.docId))?.has_tei)) {
    dl.href = `data/tei/${currentDoc.docId}.xml`;
    dl.setAttribute('download', `${currentDoc.docId}.xml`);
  } else {
    dl.removeAttribute('href');
    dl.removeAttribute('download');
  }
}

function clampPage(n) {
  return Math.max(0, Math.min(currentDoc.pages.length - 1, n));
}

// The page unit of the interface and of the URL is the page number of the
// document, which a document with a gap in its numbering does not share with
// the index in pages[]. Everything the reader sees or links is a pageNr, and
// this is the one place where it becomes an index.
function pageIndexOf(nr) {
  return currentDoc ? currentDoc.pages.findIndex(p => p.pageNr === nr) : -1;
}

const currentPageNrOr = (fallback) =>
  currentDoc?.pages[currentPage]?.pageNr ?? fallback;

function updatePager() {
  const pageInput = document.getElementById('page-input');
  pageInput.value = String(currentPageNrOr(currentPage + 1));
  pageInput.max = String(currentDoc.pages[currentDoc.pages.length - 1]?.pageNr ??
                         currentDoc.pages.length);
  // pages[] can be shorter than the document: a DoCTA transcription holds the
  // pages a model run transcribed, an image-only source its first image.
  const total = currentDoc.provenance?.pagesInDocument || currentDoc.pages.length;
  const held = currentDoc.pages.length;
  const what = currentDoc.imageOnly ? (held === 1 ? 'image available' : 'images available') : 'transcribed';
  document.getElementById('page-total').textContent = total === held
    ? `/ ${total}` : `/ ${total}, ${held} ${what}`;
  document.getElementById('btn-prev-page').disabled = currentPage === 0;
  document.getElementById('btn-next-page').disabled = currentPage === currentDoc.pages.length - 1;
  renderProgress();
}

// Above this many pages the dots no longer read as pages; the count stays.
const PROGRESS_DOTS_MAX = 80;

/** Work progress: the count in the source header and one dot per held page. */
function renderProgress() {
  const progress = pageProgress(currentDoc, registerByDocId.get(Number(currentDoc.docId)));
  const count = document.getElementById('doc-progress');
  count.hidden = !progress.transcribed;
  document.getElementById('doc-progress-count').textContent =
    PROGRESS.count(progress.corrected, progress.transcribed);
  const strip = document.getElementById('page-progress');
  strip.hidden = !progress.transcribed || progress.states.length < 2 ||
    progress.states.length > PROGRESS_DOTS_MAX;
  if (strip.hidden) { strip.replaceChildren(); return; }
  // The pager stays the keyboard route; the dots add a pointer shortcut and
  // a visible overview, so they take no tab stop of their own.
  strip.replaceChildren(...progress.states.map((page, idx) => {
    const dot = document.createElement('button');
    dot.type = 'button';
    dot.tabIndex = -1;
    dot.className = 'page-progress__dot';
    dot.dataset.state = page.state;
    dot.dataset.index = String(idx);
    dot.title = page.label;
    dot.setAttribute('aria-label', page.label);
    if (idx === currentPage) dot.setAttribute('aria-current', 'page');
    return dot;
  }));
}

document.getElementById('page-progress').addEventListener('click', (e) => {
  const dot = e.target.closest('.page-progress__dot');
  if (dot) setPage(Number(dot.dataset.index));
});

function syncParams() {
  setParams({
    doc: String(currentDoc.docId),
    page: String(currentPageNrOr(currentPage + 1)),
    view: viewMode === 'synopsis' ? '' : viewMode,
  });
}

// idx: index in pages[], not a page number
function setPage(idx) {
  if (!currentDoc) return;
  if (clampPage(idx) !== currentPage && !canNavigate()) { updatePager(); return; }
  currentPage = clampPage(idx);
  updatePager();
  syncParams();
  if (viewMode !== 'synopsis') { review.sync(); return; }

  const page = currentDoc.pages[currentPage];
  loadImage(page.iiif);
  renderPage(page.pageNr);
  document.querySelector('.transcription-workspace').scrollTop = 0;
  review.sync();
  syncImageOnly();
}

function syncImageOnly() {
  const imageOnly = Boolean(currentDoc?.imageOnly);
  document.getElementById('btn-review').hidden = imageOnly || viewMode !== 'synopsis';
  if (imageOnly) document.getElementById('review-bar').hidden = true;
  document.getElementById('btn-more').hidden = imageOnly;
  syncReadOnlyHint();
}

// Pages and a plain static preview cannot write; the hint names that state
// instead of leaving the missing annotation controls unexplained.
function syncReadOnlyHint() {
  document.getElementById('readonly-hint').hidden = local.enabled || Boolean(currentDoc?.imageOnly);
}

// Renders whatever the current mode shows, from the page the mode still holds
function renderCurrentView() {
  if (!currentDoc) return;
  updateTextStatus();
  updateTeiDownload();
  if (viewMode === 'synopsis') { setPage(currentPage); return; }
  updatePager();
  syncParams();
  if (viewMode === 'reading') renderReading(transcriptionContainer, currentDoc, isMachineText());
  else tei.render(currentDoc.docId);
  registry.render();
  review.sync();
}

const VIEWS = ['synopsis', 'reading', 'tei'];

// pageIdx: optional index in pages[] to land on when returning to the synopsis
function setView(mode, pageIdx) {
  if (mode !== viewMode && !canNavigate()) return;
  viewMode = VIEWS.includes(mode) ? mode : 'synopsis';
  const isSynopsis = viewMode === 'synopsis';
  document.getElementById('btn-view-synopsis').hidden = isSynopsis;
  document.getElementById('btn-review').hidden = !isSynopsis;
  document.getElementById('text-view-title').textContent = isSynopsis ? 'Transcription' : viewMode === 'tei' ? 'TEI' : 'Reading text';
  document.body.dataset.view = viewMode;
  document.getElementById('facsimile-panel').setAttribute('aria-hidden', String(!isSynopsis));
  for (const v of VIEWS) {
    document.getElementById(`btn-view-${v}`).setAttribute('aria-pressed', String(v === viewMode));
  }
  // Reading and TEI have no facsimile; the overlay is rebuilt on the way back
  if (!isSynopsis) clearLineOverlay();
  updateTextStatus();
  updateTeiDownload();

  if (!currentDoc) {
    setParams({ view: isSynopsis ? '' : viewMode });
    review.sync();
    return;
  }
  if (pageIdx !== undefined) currentPage = clampPage(pageIdx);
  renderCurrentView();
}

let docRequest = 0;

// pageNr: page number of the document to start on. Omit to take it from the
// URL (deep link into a page); an unknown number falls back to the first page.
async function loadDocument(docId, pageNr) {
  if (currentDoc && Number(docId) !== Number(currentDoc.docId) && !canNavigate()) {
    document.getElementById('doc-selector').value = String(currentDoc.docId);
    return;
  }
  const token = ++docRequest;
  try {
    // Deep links arrive copy-pasted; a stray trailing dot or space in the
    // doc parameter must not turn into a nonexistent file path.
    docId = String(parseInt(docId, 10));
    // Where the text of this document lives: the Transkribus export, or the
    // projection of DoCTA's own transcription for a source without one.
    const source = registerByDocId.get(Number(docId))?.transcription_source;
    const path = source === 'vlm' || registerByDocId.get(Number(docId))?.effective_transcription
      ? `data/pipeline/transcriptions/${docId}.json`
      : `data/transcriptions/${docId}.json`;
    const doc = imageDocuments.get(Number(docId)) ||
      await (local.enabled ? local.load(docId) : loadJSON(path));
    // A later document switch wins over a slow response
    if (token !== docRequest) return;
    if (!Array.isArray(doc.pages) || !doc.pages.length) {
      throw new Error('the transcription holds no page');
    }
    currentDoc = doc;
    if (doc.imageOnly) viewMode = 'synopsis';
    registry.load();
    const wanted = pageNr !== undefined
      ? Number(pageNr)
      : parseInt(getParams().page || '', 10);
    const idx = Number.isFinite(wanted) ? pageIndexOf(wanted) : -1;
    renderDocMeta(docId);
    // A document switch keeps the current view
    currentPage = clampPage(idx >= 0 ? idx : 0);
    setView(viewMode);
  } catch (err) {
    if (token !== docRequest) return;
    const errEl = document.createElement('div');
    errEl.className = 'loading text-body-secondary';
    errEl.textContent = `Document ${docId} could not be loaded: ${err.message}`;
    transcriptionContainer.replaceChildren(errEl);
  }
}

document.getElementById('btn-prev-page').addEventListener('click', () => setPage(currentPage - 1));
document.getElementById('btn-edition-build').addEventListener('click', async (event) => {
  if (!currentDoc) return;
  const button = event.currentTarget;
  const status = document.getElementById('local-edition-status');
  const date = document.getElementById('edition-date');
  if (review.hasDraft) {
    status.textContent = 'Please save or discard the text changes first.';
    return;
  }
  if (!date.reportValidity()) return;
  button.disabled = true;
  try {
    await local.build(date.value, [Number(currentDoc.docId)]);
    tei.invalidate();
    status.textContent = 'Edition output updated from the saved text and validated.';
    if (viewMode === 'tei') renderCurrentView();
  } catch (error) {
    status.textContent = `Output not updated: ${error.message}`;
  } finally { button.disabled = false; }
});
document.getElementById('btn-next-page').addEventListener('click', () => setPage(currentPage + 1));
document.getElementById('btn-zoom-in').addEventListener('click', () => zoomBy(1.4));
document.getElementById('btn-zoom-out').addEventListener('click', () => zoomBy(1 / 1.4));
function showWholePage() {
  document.getElementById('image-focus').value = 'spread';
  fitView();
}
document.getElementById('btn-zoom-fit').addEventListener('click', showWholePage);
document.getElementById('btn-rotate-left').addEventListener('click', () => rotateBy(-90));
document.getElementById('btn-rotate-right').addEventListener('click', () => rotateBy(90));
btnFullscreen.addEventListener('click', toggleFullscreen);
document.getElementById('btn-view-synopsis').addEventListener('click', () => setView('synopsis'));
document.getElementById('btn-view-reading').addEventListener('click', () => {
  document.getElementById('viewer-more').close();
  setView('reading');
});
document.getElementById('btn-view-tei').addEventListener('click', () => {
  document.getElementById('viewer-more').close();
  setView('tei');
});

// The page mark in the reading text is the way back to the facsimile
transcriptionContainer.addEventListener('click', (e) => {
  const mark = e.target.closest('.reading-page__mark');
  if (mark) { setView('synopsis', Number(mark.dataset.index)); return; }
  if (!review.on || e.target.closest('.transcription__line-editor')) return;
  const line = e.target.closest('.transcription__line[data-line-id]');
  if (e.target.closest('.transcription__line-restore')) { review.restoreLine(line); return; }
  review.beginEdit(line);
});

// Enter opens the line under the caret for correction; the input handles the rest
transcriptionContainer.addEventListener('keydown', (e) => {
  if (e.key !== 'Enter' || !review.on) return;
  if (e.target.closest('.transcription__line-editor, .transcription__line-restore')) return;
  const line = e.target.closest('.transcription__line[data-line-id]');
  if (!line) return;
  e.preventDefault();
  review.beginEdit(line);
});

// Transcription to image: hover or focus on a line lights up its zone
const lineIdOf = (target) => {
  const el = target instanceof Element
    ? target.closest('.transcription__line[data-line-id]') : null;
  return el ? el.getAttribute('data-line-id') : null;
};
transcriptionContainer.addEventListener('mouseover', (e) => highlightZone(lineIdOf(e.target)));
transcriptionContainer.addEventListener('mouseleave', () => highlightZone(null));
transcriptionContainer.addEventListener('focusin', (e) => highlightZone(lineIdOf(e.target)));
transcriptionContainer.addEventListener('focusout', () => highlightZone(null));

document.getElementById('btn-line-regions')
  .addEventListener('click', () => setLineRegions(!showLineRegions));

const pageInput = document.getElementById('page-input');
function canNavigate() {
  return registry.beforeNavigate();
}
// The field takes a page number of the document; a number the document does
// not carry leaves the current page in place.
function commitPageInput() {
  if (!currentDoc) return;
  const n = parseInt(pageInput.value, 10);
  const idx = Number.isFinite(n) ? pageIndexOf(n) : -1;
  if (idx >= 0) setPage(idx);
  else updatePager();
}
pageInput.addEventListener('change', commitPageInput);
pageInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') { e.preventDefault(); commitPageInput(); }
});

// Shortcuts are documented in the button tooltips; a change here changes
// the title attributes in viewer.html and setLineRegions with it.
document.addEventListener('keydown', (e) => {
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  if (e.shiftKey && ['ArrowLeft', 'ArrowRight'].includes(e.key)) return;
  const t = e.target;
  if (t instanceof HTMLElement &&
      (t.isContentEditable || ['INPUT', 'SELECT', 'TEXTAREA'].includes(t.tagName))) return;
  // Reading and TEI have no facsimile and no page unit, so the arrow keys are
  // left to the focused transcription container, which scrolls with them
  if (viewMode !== 'synopsis') return;
  switch (e.key) {
    case 'ArrowLeft': setPage(currentPage - 1); break;
    case 'ArrowRight': setPage(currentPage + 1); break;
    case '+': case '=': zoomBy(1.4); break;
    case '-': zoomBy(1 / 1.4); break;
    case '0': showWholePage(); break;
    // Shift selects the direction rather than the letter case, so Caps Lock
    // does not reverse the rotation.
    case 'r': case 'R': rotateBy(e.shiftKey ? -90 : 90); break;
    case 'l': case 'L': setLineRegions(!showLineRegions); break;
    default: return;
  }
  e.preventDefault();
});

document.getElementById('doc-selector').addEventListener('change', (e) => {
  // Switching documents always starts at page 1, never at the previous document's page
  if (e.target.value) loadDocument(e.target.value, 1);
});

async function init() {
  try {
    await local.init();
    if (local.enabled && local.version) {
      const version = document.createElement('p');
      version.textContent = `Working edition ${local.version}`;
      document.getElementById('viewer-more').append(version);
    }
    document.getElementById('local-edition-bar').hidden = !local.enabled;
    syncReadOnlyHint();
    document.getElementById('edition-date').value = new Date().toISOString().slice(0, 10);
    const [mapping, sources, register, collection] = await Promise.all([
      loadJSON('data/source_mapping.json'),
      loadJSON('data/sources.json').catch(() => []),
      loadJSON('data/pipeline/register_summary.json').catch(() => ({ documents: [] })),
      loadJSON('data/transkribus_collection.json').catch(() => []),
    ]);
    // A shelfmark can pair two Transkribus documents, so every one of them
    // resolves to its source row rather than only the first.
    sourceByDocId = new Map(sources
      .flatMap(s => (s.transkribus_docs || []).map(d => [Number(d.doc_id), s])));
    registerByDocId = new Map((register.documents || [])
      .map(d => [Number(d.docId), d]));
    const mappedText = new Set(mapping.matched.filter(m => m.has_text).map(m => Number(m.transkribus_id)));
    imageDocuments = new Map(collection.flatMap(entry => {
      const reg = registerByDocId.get(entry.docId);
      if (mappedText.has(entry.docId) || reg?.pages_with_text > 0 ||
          reg?.transcription_source === 'vlm' || reg?.effective_transcription) return [];
      const doc = imageDocument(entry);
      return doc ? [[entry.docId, doc]] : [];
    }));
    const selector = document.getElementById('doc-selector');

    // Text-bearing documents lead the selector; image-only sources remain accessible.
    const accessibleDocs = mapping.matched
      .filter(m => m.has_text ||
        imageDocuments.has(Number(m.transkribus_id)) ||
        registerByDocId.get(Number(m.transkribus_id))?.transcription_source === 'vlm')
      .sort((a, b) => Number(imageDocuments.has(Number(a.transkribus_id))) -
        Number(imageDocuments.has(Number(b.transkribus_id))) || a.csv_signatur.localeCompare(b.csv_signatur));

    for (const doc of accessibleDocs) {
      const opt = document.createElement('option');
      opt.value = doc.transkribus_id;
      opt.textContent = `${doc.csv_signatur} - ${doc.csv_titel}`;
      selector.appendChild(opt);
    }

    const params = getParams();
    setView(params.view);
    if (params.doc) {
      selector.value = params.doc;
      loadDocument(params.doc);
    } else if (accessibleDocs.length) {
      // No deep link: open the first document right away instead of an empty pane
      const first = String(accessibleDocs[0].transkribus_id);
      selector.value = first;
      loadDocument(first, 1);
    }
  } catch (err) {
    console.error('Failed to load source mapping:', err);
    const selector = document.getElementById('doc-selector');
    const opt = document.createElement('option');
    opt.value = '';
    opt.textContent = `Document list could not be loaded: ${err.message}`;
    selector.replaceChildren(opt);
    selector.disabled = true;
  }
}

init();

for (const [buttonId, dialogId] of [
  ['btn-source-details', 'source-dialog'], ['btn-more', 'viewer-more'],
]) {
  const button = document.getElementById(buttonId);
  const dialog = document.getElementById(dialogId);
  button.addEventListener('click', () => {
    dialog.showModal();
  });
  dialog.querySelector('[data-close-dialog]').addEventListener('click', () => dialog.close());
  // The browser restores focus on close itself; the close event arrives later,
  // so refocus only when focus was left nowhere, never pull it back from a
  // control the user has moved to meanwhile.
  dialog.addEventListener('close', () => {
    const active = document.activeElement;
    if (!active || active === document.body || dialog.contains(active)) button.focus();
  });
}
