import { initNav, initBanner } from './app.js?v=20260921-ui';
import { loadJSON, loadEntities } from './data-loader.js';
import { getParams, setParams, escapeHTML, escapeAttr,
         lsGet, lsSet } from './utils.js';
import { createEntityLayer, createTeiView, renderReading,
         renderTranscription } from './viewer-render.js?v=20260921-ui';
import { createReviewView } from './viewer-review.js?v=20260921-corrections';
import { createLocalEditor } from './viewer-local.js';
import { createAnnotationEditor } from './viewer-annotations.js?v=20260921-ui';
import { createTagEditor } from './viewer-tags.js?v=20260921-ui';
import { createRegistryEditor } from './viewer-registry.js';

initNav('viewer');
initBanner();
const local = createLocalEditor();
const annotations = createAnnotationEditor(document.getElementById('annotation-editor'), local, { hasDraft: () => review.hasDraft });

let viewer = null;
let imageKey = null;
let currentDoc = null;
let currentPage = 0;
let viewMode = 'synopsis';
let rotation = 0;
let sourceByDocId = new Map();
let registerByDocId = new Map();

// Entities of the loaded document: the index the marks are matched against
// and the markup that states which model produced them.
const entities = createEntityLayer();
const transcriptionContainer = document.getElementById('transcription-container');

const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

// Which text layer the reader is looking at: human-corrected pages are the
// ones marked DONE in Transkribus, everything else is the unrevised HTR layer.
function provenanceState(docId) {
  const reg = registerByDocId.get(Number(docId));
  if (!reg || typeof reg.pages_total !== 'number' || !reg.pages_total) return null;
  const done = typeof reg.done_pages === 'number' ? reg.done_pages : 0;
  const total = reg.pages_total;
  // Name who corrected: for the attributed documents that work is the
  // Inventaria project's, and "human-corrected" must not leave it open.
  const by = reg.transcription_by === 'Inventaria' ? ' by the Inventaria project' : '';
  // A document Transkribus holds no text for was transcribed by DoCTA
  // itself; naming the Transkribus HTR layer here would be wrong.
  if (reg.transcription_source === 'vlm') {
    return {
      state: 'machine',
      label: 'Maschinentranskription von DoCTA',
      title: 'Unrevised transcription produced by the DoCTA pipeline with a ' +
             'vision-language model. Transkribus holds no transcription of this ' +
             'source, and no page has been read against the scan by a scholar',
    };
  }
  if (done >= total) {
    return {
      state: 'human',
      label: `Textquelle ${by ? 'Inventaria, korrigiert' : 'Transkribus, korrigiert'}`,
      title: `All ${total} pages corrected${by} and marked done in Transkribus`,
    };
  }
  if (done > 0) {
    return {
      state: 'partial',
      label: `Textquelle teilweise korrigiert (${done}/${total} Seiten)`,
      title: `${done} of ${total} pages corrected${by} and marked done in Transkribus, ` +
             'the remaining pages are the unrevised Transkribus HTR layer',
    };
  }
  // Absence of the done status documents nothing about actual correction
  // work; the chip states the origin and what the status does not record.
  return {
    state: 'machine',
    label: 'Transkribus HTR, Korrektur nicht verzeichnet',
    title: 'Text layer exported from Transkribus. No page of this document ' +
           'is marked done there, so no human correction is documented; the ' +
           'text may have been worked on without the status being set',
  };
}

function provenanceChip(docId) {
  const prov = provenanceState(docId);
  if (!prov) return '';
  const reg = registerByDocId.get(Number(docId));
  const url = reg?.edition_url || 'https://www.inventaria.at/';
  if (reg?.transcription_by === 'Inventaria' && /^https?:\/\//i.test(url)) {
    return `<a class="prov-chip prov-chip--${prov.state}" id="doc-provenance"` +
      ` href="${escapeAttr(url)}" target="_blank" rel="noopener"` +
      ` title="${escapeAttr(prov.title)}. Originaledition öffnen">${escapeHTML(prov.label)}</a>`;
  }
  return `<span class="prov-chip prov-chip--${prov.state}" id="doc-provenance"` +
         ` title="${escapeAttr(prov.title)}">${escapeHTML(prov.label)}</span>`;
}

// The badge carries the machine-output marking in every view, including the
// synopsis: the provenance chip beside it can be absent (no source row, no
// register entry), and losing the chip must never mean losing the marking.
// A document the register does not know counts as unrevised machine text.
function updateDraftBadge() {
  const badge = document.getElementById('draft-badge');
  const corrected = currentDoc && provenanceState(currentDoc.docId)?.state === 'human';
  const states = Object.values(currentDoc?.reviewState || {});
  const approved = states.length && states.every(page => page.status === 'abgenommen');
  const reviewed = states.some(page => ['gesichtet', 'abgenommen'].includes(page.status));
  const pending = currentDoc && review.hasDraft;
  badge.hidden = !currentDoc || (!pending && (corrected || approved));
  badge.textContent = pending ? 'Ungespeicherte Änderungen' : reviewed ? 'Teilweise geprüft' : 'Ungeprüfter Text';
  // Reading mode shows the exported text only; local review corrections live
  // in the synopsis, and the badge says so instead of implying they are here.
  badge.title = local.enabled
    ? 'Saved corrections appear in Synopsis and Reading. Page approval is recorded separately. Unsaved drafts appear in Synopsis only.'
    : 'Machine source text. Browser drafts appear in Synopsis until saved through the local editor or ingested from an export.';
}

function renderDocMeta(docId) {
  const source = sourceByDocId.get(Number(docId));
  const reg = registerByDocId.get(Number(docId));
  const title = source?.titel || currentDoc?.title || 'Quelle';
  document.getElementById('source-title').textContent = title;
  document.getElementById('source-shelfmark').textContent = source?.signatur || 'Nicht verzeichnet';
  const rawDate = source?.datierung?.raw || '';
  const date = /^\d{4}\.\d{2}\.\d{2}$/.test(rawDate)
    ? rawDate.split('.').reverse().join('.') : rawDate;
  document.getElementById('source-date').textContent = date || 'Nicht verzeichnet';
  const field = (label, value) => value
    ? '<div><dt>' + escapeHTML(label) + '</dt><dd>' + escapeHTML(String(value)) + '</dd></div>' : '';
  let details = field('Titel', title) + field('Signatur', source?.signatur) +
    field('Datierung', date) + field('Archiv', 'Tiroler Landesarchiv') +
    field('Quellentyp', source?.kategorie) + field('Archivalische Einheit', source?.art) +
    field('Transkriptionsprojekt', reg?.transcription_by || source?.transkribiert) +
    field('Transkribus-Dokument', docId);
  let attribution = '';
  if (reg?.transcription_by === 'Inventaria') {
    const url = reg.edition_url || 'https://www.inventaria.at/';
    // Only web links from the source register may become navigable metadata.
    if (/^https?:\/\//i.test(url)) {
      attribution = '<a class="doc-meta__edition" href="' + escapeAttr(url) +
        '" target="_blank" rel="noopener">Edition von Inventaria</a>';
      details += '<div><dt>Originaledition</dt><dd>' + attribution + '</dd></div>';
    }
  }
  document.getElementById('source-details').innerHTML = details;
  const provenance = currentDoc?.provenance;
  const coverage = provenance && provenance.pagesTranscribed < provenance.pagesInDocument
    ? '<span>' + escapeHTML(String(provenance.pagesTranscribed)) + ' von ' +
      escapeHTML(String(provenance.pagesInDocument)) + ' Seiten transkribiert</span>' : '';
  const meta = document.getElementById('doc-meta');
  meta.innerHTML = provenanceChip(docId) + coverage;
  meta.hidden = false;
  document.getElementById('entity-tools').hidden = !entities.active;
  document.getElementById('btn-tags').hidden = !local.enabled;
  document.getElementById('btn-entities').hidden = !entities.active;
  document.getElementById('entity-legend').innerHTML = entities.legendHTML();
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
  svg.setAttribute('viewBox', `0 0 ${size.x} ${size.y}`);
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

function setLineRegions(on) {
  showLineRegions = on;
  document.getElementById('btn-line-regions').setAttribute('aria-pressed', String(on));
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
  btnFullscreen.setAttribute('aria-pressed', String(document.fullscreenElement === panel));
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
  meta: document.getElementById('doc-meta'),
}, {
  getContext: () => ({
    docId: currentDoc ? Number(currentDoc.docId) : null,
    pageNr: currentPageNr(),
    viewMode,
    revision: currentDoc?.revision,
    reviewState: currentDoc?.reviewState,
  }),
  markText: entities.markText,
  rerenderPage: renderPage,
  local,
  onDraftChange: () => { updateDraftBadge(); tags.sync(); },
  onSaved: (doc) => {
    currentDoc = doc;
    annotations.update(doc);
    registry.load();
    tags.load(doc);
    renderDocMeta(doc.docId);
    renderCurrentView();
  },
});

const tags = createTagEditor(document.getElementById('tag-editor'), local, {
  hasReviewDraft: () => review.hasDraft,
  refreshSource: async () => {
    const docId = currentDoc.docId;
    const doc = await local.load(docId);
    if (currentDoc.docId !== docId) return;
    currentDoc = doc;
    annotations.update(doc);
    await tags.load(doc);
    renderDocMeta(doc.docId);
    renderCurrentView();
  },
});

const registry = createRegistryEditor(local, {
  context: () => ({ doc: currentDoc, pageNr: currentPageNr(), hasDraft: review.hasDraft, viewMode }),
  rerender: () => { if (currentDoc) renderCurrentView(); },
});

// One page of the synopsis. The coupling with the image overlay is keyed on
// the rendered lines, so a fresh page starts with no line held on either side.
function renderPage(pageNr) {
  activeLineId = null;
  linkedLineId = null;
  renderTranscription(transcriptionContainer, currentDoc, pageNr, {
    corrections: review.corrections(pageNr),
    markText: entities.markText,
  });
  review.applyMode();
  registry.render();
  const provenance = currentDoc.pages.find(page => page.pageNr === pageNr)?.provenance;
  const provenanceElement = document.getElementById('page-provenance');
  const displayDate = value => {
    const date = new Date(value);
    if (Number.isNaN(date.valueOf())) return value;
    return new Intl.DateTimeFormat('de-AT', { dateStyle: 'short', ...(value.includes('T') ? { timeStyle: 'short' } : {}) }).format(date);
  };
  const origins = provenance?.originalRuns.filter(run => run.id === provenance.originalRunId) || [];
  const summary = provenance ? [
    ...origins.map(run => `Transkription ${run.model || (run.source === 'transkribus' ? 'Transkribus, Modell nicht dokumentiert' : 'Modell nicht dokumentiert')}${run.date ? ' (' + displayDate(run.date) + ')' : ''}`),
    ...provenance.humanCorrections.map(run => `Textkorrektur ${run.reviewer || 'Kürzel nicht dokumentiert'}${run.timestamp ? ' (' + displayDate(run.timestamp) + ')' : ''}`),
  ].join('. ') : '';
  provenanceElement.innerHTML = provenance ? `<details><summary>${escapeHTML(summary)}</summary><dl>` +
    origins.map(run => `<dt>Transkriptionslauf</dt><dd>${escapeHTML([run.id, run.date, run.prompt, run.prompt_hash].filter(Boolean).join(', '))}</dd>`).join('') +
    provenance.humanCorrections.map(run => `<dt>Textkorrektur ${escapeHTML(run.reviewer || '')}</dt><dd><time datetime="${escapeAttr(run.timestamp || '')}">${escapeHTML(run.timestamp || 'Zeitpunkt nicht dokumentiert')}</time></dd>`).join('') + '</dl></details>' : '';
}

// === Entity marks in the transcription ===
// One shared tooltip element; screen readers use the span's aria-label
const entTip = document.createElement('div');
entTip.className = 'ent-tip';
entTip.hidden = true;
entTip.setAttribute('aria-hidden', 'true');
document.body.appendChild(entTip);

function showEntityTip(target) {
  const html = entities.tipHTML(target.dataset.entKey);
  if (html === null) return;
  entTip.innerHTML = html;
  entTip.hidden = false;
  const rect = target.getBoundingClientRect();
  entTip.style.left = `${Math.max(8, Math.min(rect.left,
    window.innerWidth - entTip.offsetWidth - 8))}px`;
  entTip.style.top = `${rect.bottom + 6}px`;
}

const entityAt = (node) =>
  (node && node.closest) ? node.closest('.entity[data-ent-key]') : null;

function editEntity(target) {
  if (!local.enabled || target.closest('[data-mention-id]')) return;
  const dialog = document.getElementById('entities-dialog');
  annotations.select(target.dataset.entKey);
  if (!dialog.open) dialog.showModal();
  dialog.addEventListener('close', () => target.focus(), { once: true });
}
document.addEventListener('click', event => { const target = entityAt(event.target); if (target && !event.target.closest('[data-mention-id]')) editEntity(target); });
document.addEventListener('keydown', event => {
  const target = entityAt(event.target);
  if (target && !event.target.closest('[data-mention-id]') && ['Enter', ' '].includes(event.key)) { event.preventDefault(); editEntity(target); }
});

// Pointer and keyboard reach the tip alike: the marks are focusable, so
// focus opens it and Escape closes it without leaving the line.
document.addEventListener('mouseover', (e) => {
  const target = entityAt(e.target);
  if (target) showEntityTip(target);
  else if (!entTip.hidden) entTip.hidden = true;
});
document.addEventListener('focusin', (e) => {
  const target = entityAt(e.target);
  if (target) showEntityTip(target);
  else if (!entTip.hidden) entTip.hidden = true;
});
document.addEventListener('focusout', (e) => {
  if (entityAt(e.target)) entTip.hidden = true;
});
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && !entTip.hidden) entTip.hidden = true;
});
document.addEventListener('scroll', () => { entTip.hidden = true; }, true);

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
  if (currentDoc) {
    dl.href = `data/tei/${currentDoc.docId}.xml`;
    dl.setAttribute('download', `${currentDoc.docId}.xml`);
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
  const total = currentDoc.provenance?.pagesInDocument || currentDoc.pages.length;
  document.getElementById('page-total').textContent = total === currentDoc.pages.length
    ? `/ ${total}` : `/ ${total} (${currentDoc.pages.length} available)`;
  document.getElementById('btn-prev-page').disabled = currentPage === 0;
  document.getElementById('btn-next-page').disabled = currentPage === currentDoc.pages.length - 1;
}

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
  currentPage = clampPage(idx);
  updatePager();
  syncParams();
  if (viewMode !== 'synopsis') { review.sync(); return; }

  const page = currentDoc.pages[currentPage];
  annotations.page(page.pageNr);
  tags.page(page.pageNr);
  loadImage(page.iiif);
  renderPage(page.pageNr);
  document.querySelector('.transcription-workspace').scrollTop = 0;
  review.sync();
}

// Renders whatever the current mode shows, from the page the mode still holds
function renderCurrentView() {
  if (!currentDoc) return;
  updateDraftBadge();
  updateTeiDownload();
  if (viewMode === 'synopsis') { setPage(currentPage); return; }
  updatePager();
  syncParams();
  if (viewMode === 'reading') renderReading(transcriptionContainer, currentDoc);
  else tei.render(currentDoc.docId);
  registry.render();
  review.sync();
}

const VIEWS = ['synopsis', 'reading', 'tei'];

// pageIdx: optional index in pages[] to land on when returning to the synopsis
function setView(mode, pageIdx) {
  viewMode = VIEWS.includes(mode) ? mode : 'synopsis';
  const isSynopsis = viewMode === 'synopsis';
  document.getElementById('btn-view-synopsis').hidden = isSynopsis;
  document.getElementById('btn-review').hidden = !isSynopsis;
  document.getElementById('text-view-title').textContent = isSynopsis ? 'Transkription' : viewMode === 'tei' ? 'TEI' : 'Lesetext';
  document.body.dataset.view = viewMode;
  document.getElementById('facsimile-panel').setAttribute('aria-hidden', String(!isSynopsis));
  for (const v of VIEWS) {
    document.getElementById(`btn-view-${v}`).setAttribute('aria-pressed', String(v === viewMode));
  }
  // Reading and TEI have no facsimile; the overlay is rebuilt on the way back
  if (!isSynopsis) clearLineOverlay();
  updateDraftBadge();
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
    // Entities are optional per document and are awaited with the text, so
    // the first render already carries the marks instead of racing them in.
    const [doc, extraction] = await Promise.all([
      local.enabled ? local.load(docId) : loadJSON(path),
      loadEntities(docId),
    ]);
    // A later document switch wins over a slow response
    if (token !== docRequest) return;
    if (!Array.isArray(doc.pages) || !doc.pages.length) {
      throw new Error('the transcription holds no page');
    }
    currentDoc = doc;
    entities.set(extraction, local.enabled);
    annotations.load(doc, extraction);
    registry.load();
    tags.load(doc);
    const wanted = pageNr !== undefined
      ? Number(pageNr)
      : parseInt(getParams().page || '', 10);
    const idx = Number.isFinite(wanted) ? pageIndexOf(wanted) : -1;
    renderDocMeta(docId);
    // A document switch keeps the current view
    currentPage = clampPage(idx >= 0 ? idx : 0);
    renderCurrentView();
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
    status.textContent = 'Bitte die Textänderungen zuerst speichern oder verwerfen.';
    return;
  }
  if (!date.reportValidity()) return;
  button.disabled = true;
  try {
    await local.build(date.value, [Number(currentDoc.docId)]);
    tei.invalidate();
    status.textContent = 'Editionsausgabe aus dem gespeicherten Text aktualisiert und geprüft.';
    if (viewMode === 'tei') renderCurrentView();
  } catch (error) {
    status.textContent = `Ausgabe nicht aktualisiert: ${error.message}`;
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
  if (!review.on || e.target.closest('.transcription__line-edit')) return;
  review.beginEdit(e.target.closest('.transcription__line[data-line-id]'));
});

// Enter opens the line under the caret for correction; the input handles the rest
transcriptionContainer.addEventListener('keydown', (e) => {
  if (e.key !== 'Enter' || !review.on) return;
  if (e.target.closest('.transcription__line-edit')) return;
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

// Shortcuts are documented on the buttons via title/aria-label
document.addEventListener('keydown', (e) => {
  if (e.ctrlKey || e.metaKey || e.altKey) return;
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
    case 'r': case 'R': rotateBy(90); break;
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
      version.textContent = `Arbeitsedition ${local.version}`;
      document.getElementById('viewer-more').append(version);
    }
    document.getElementById('local-edition-bar').hidden = !local.enabled;
    document.getElementById('edition-date').value = new Date().toISOString().slice(0, 10);
    const [mapping, sources, register] = await Promise.all([
      loadJSON('data/source_mapping.json'),
      loadJSON('data/sources.json').catch(() => []),
      loadJSON('data/pipeline/register_summary.json').catch(() => ({ documents: [] })),
    ]);
    // A shelfmark can pair two Transkribus documents, so every one of them
    // resolves to its source row rather than only the first.
    sourceByDocId = new Map(sources
      .flatMap(s => (s.transkribus_docs || []).map(d => [Number(d.doc_id), s])));
    registerByDocId = new Map((register.documents || [])
      .map(d => [Number(d.docId), d]));
    const selector = document.getElementById('doc-selector');

    // Every document that carries a text, whether Transkribus exported it
    // or DoCTA transcribed it itself; the register says which.
    const docsWithText = mapping.matched
      .filter(m => m.has_text ||
        registerByDocId.get(Number(m.transkribus_id))?.transcription_source === 'vlm')
      .sort((a, b) => a.csv_signatur.localeCompare(b.csv_signatur));

    for (const doc of docsWithText) {
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
    } else if (docsWithText.length) {
      // No deep link: open the first document right away instead of an empty pane
      const first = String(docsWithText[0].transkribus_id);
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
  ['btn-tags', 'tags-dialog'], ['btn-entities', 'entities-dialog'],
]) {
  const button = document.getElementById(buttonId);
  const dialog = document.getElementById(dialogId);
  button.addEventListener('click', () => {
    const details = dialog.querySelector('#tag-editor > details');
    if (details) details.open = true;
    dialog.showModal();
  });
  dialog.querySelector('[data-close-dialog]').addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => button.focus());
}
