/**
 * DoCTA viewer - the curation view.
 *
 * Decisions are made in the browser and live in localStorage per document.
 * They leave through an explicit JSON export that the pipeline ingests; the
 * site itself is static and writes nothing back. The shape of that export is a
 * contract with pipeline/apply_review.py and is not changed here alone.
 *
 * The module holds no page state. Which document, which page and which view the
 * reader is in comes from the getContext callback the page supplies.
 */

import { escapeHTML, lsGet, lsSet } from './utils.js';

const REVIEWER_KEY = 'docta-review-reviewer';
// The two human review states of the register vocabulary, in the German
// wording the data specification uses. pipeline/apply_review.py accepts
// exactly these two values plus null (REVIEW_STATUS there); the machine
// states of the register are not reachable from the viewer. Any change here
// is a change of the export contract and belongs in both places.
const STATUS_LABEL = { gesichtet: 'Reviewed', abgenommen: 'Approved' };
// Shape version of the stored draft. Raise it when the store no longer
// satisfies what loadReview() keeps, so a stale draft is dropped instead of
// being exported against the contract.
const REVIEW_VERSION = 1;
const REVIEW_DATE = /^\d{4}-\d{2}-\d{2}$/;

const reviewKey = (docId) => `docta-review-${docId}`;
const today = () => new Date().toISOString().slice(0, 10);

/**
 * A stored draft is read back entry by entry: a page that still satisfies the
 * export contract (a known status or none, an ISO date, a line list) is kept,
 * anything else is dropped rather than carried into an export.
 * @param {number} docId
 */
function loadReview(docId) {
  const raw = lsGet(reviewKey(docId));
  if (!raw) return null;
  let data;
  try { data = JSON.parse(raw); } catch { return null; }
  if (!data || typeof data !== 'object' || typeof data.pages !== 'object' || !data.pages) return null;
  const pages = {};
  for (const [key, page] of Object.entries(data.pages)) {
    if (!page || typeof page !== 'object') continue;
    const status = page.status ?? null;
    if (status !== null && !(status in STATUS_LABEL)) continue;
    if (typeof page.date !== 'string' || !REVIEW_DATE.test(page.date)) continue;
    if (!Array.isArray(page.lines)) continue;
    pages[key] = { ...page, status };
  }
  return { ...data, version: REVIEW_VERSION, pages };
}

function saveReview(store) {
  lsSet(reviewKey(store.docId), JSON.stringify(store));
}

function ensurePage(store, pageNr) {
  const key = String(pageNr);
  const page = store.pages[key];
  if (page && typeof page === 'object') {
    if (!Array.isArray(page.lines)) page.lines = [];
    if (!('status' in page)) page.status = null;
    return page;
  }
  store.pages[key] = { status: null, date: today(), lines: [] };
  return store.pages[key];
}

/** A page entry without a decision and without corrections carries nothing */
function prunePage(store, pageNr) {
  const key = String(pageNr);
  const page = store.pages[key];
  if (page && !page.status && (!page.lines || !page.lines.length)) delete store.pages[key];
}

/**
 * The vocabulary is ordered: "abgenommen" implies "gesichtet" and is stored
 * alone. Approved therefore toggles between itself and no decision, while
 * Reviewed only ever toggles the lower state; on an approved page it leaves
 * the decision alone, because a press on a button that reads as pressed must
 * not silently downgrade an approval into the export.
 * @param {string|null} current
 * @param {'gesichtet'|'abgenommen'} pressed
 */
export function nextStatus(current, pressed) {
  if (pressed === 'abgenommen') return current === 'abgenommen' ? null : 'abgenommen';
  if (current === 'abgenommen') return current;
  return current === 'gesichtet' ? null : 'gesichtet';
}

/**
 * Build the curation view over the elements of the review bar.
 * @param {{
 *   bar: HTMLElement, toggle: HTMLElement, initials: HTMLInputElement,
 *   hint: HTMLElement, statusReviewed: HTMLElement, statusApproved: HTMLElement,
 *   exportBtn: HTMLElement, clearBtn: HTMLElement, meta: HTMLElement
 * }} els
 * @param {{
 *   getContext: () => { docId: number|null, pageNr: number|null, viewMode: string },
 *   markText: (escaped: string) => string,
 *   rerenderPage: (pageNr: number) => void
 * }} opts
 */
export function createReviewView(els, { getContext, markText, rerenderPage }) {
  let reviewMode = false;

  const initialsValue = () => els.initials.value.trim();

  function requireInitials() {
    if (initialsValue().length >= 2) return true;
    els.initials.classList.add('is-missing');
    els.initials.focus();
    els.hint.textContent = 'Enter two to four initials before recording a decision.';
    return false;
  }

  function reviewStore() {
    const { docId } = getContext();
    const stored = loadReview(docId);
    if (stored) return stored;
    return { version: REVIEW_VERSION, docId, reviewer: initialsValue(), pages: {} };
  }

  function reviewPage(pageNr) {
    const { docId } = getContext();
    if (docId == null || pageNr == null) return null;
    const store = loadReview(docId);
    const page = store?.pages?.[String(pageNr)];
    return page && typeof page === 'object' ? page : null;
  }

  /** lineId to correction record, for the lines of one page */
  function reviewCorrections(pageNr) {
    const map = new Map();
    const page = reviewPage(pageNr);
    if (!page || !Array.isArray(page.lines)) return map;
    for (const line of page.lines) {
      if (line && typeof line.id === 'string' && typeof line.corrected === 'string') {
        map.set(line.id, line);
      }
    }
    return map;
  }

  function setStatus(pressed) {
    const { docId, pageNr, viewMode } = getContext();
    if (docId == null || viewMode !== 'synopsis') return;
    if (!requireInitials()) return;
    if (pageNr == null) return;
    const store = reviewStore();
    const page = ensurePage(store, pageNr);
    const next = nextStatus(page.status, pressed);
    if (next === page.status && pressed === 'gesichtet') {
      els.hint.textContent = 'Approved already implies reviewed. Clear the approval to change it.';
      return;
    }
    page.status = next;
    page.date = today();
    store.reviewer = initialsValue();
    prunePage(store, pageNr);
    saveReview(store);
    syncReviewUI();
  }

  function clearReviewPage() {
    const { docId, pageNr } = getContext();
    if (docId == null || pageNr == null) return;
    const store = loadReview(docId);
    if (!store) return;
    delete store.pages[String(pageNr)];
    saveReview(store);
    rerenderPage(pageNr);
    syncReviewUI();
  }

  function exportReview() {
    const { docId } = getContext();
    if (docId == null) return;
    const store = loadReview(docId) ||
      { version: REVIEW_VERSION, docId, reviewer: initialsValue(), pages: {} };
    const payload = { ...store, exported: new Date().toISOString(), source: 'docta-viewer' };
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = `review-${docId}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    els.hint.textContent = 'Exported. Hand the file to the pipeline to ingest it.';
  }

  /** The chip states a local decision, so it names its own reach in the tooltip */
  function updateReviewChip() {
    const { docId, pageNr, viewMode } = getContext();
    els.meta.querySelector('#review-chip')?.remove();
    const page = viewMode === 'synopsis' ? reviewPage(pageNr) : null;
    if (!page || !page.status) return;
    const store = loadReview(docId);
    const who = (store && typeof store.reviewer === 'string' && store.reviewer) || '??';
    const chip = document.createElement('span');
    chip.id = 'review-chip';
    chip.className = 'prov-chip prov-chip--review';
    chip.textContent = `${STATUS_LABEL[page.status] || 'Reviewed'} · ${who}`;
    chip.title = `Decision by ${who} on ${page.date}, held in this browser only. ` +
                 'It is local until it is exported and ingested by the pipeline.';
    els.meta.appendChild(chip);
    els.meta.hidden = false;
  }

  /** Editable lines get a tab stop only while review mode is on */
  function applyReviewMode() {
    const editable = reviewMode && getContext().viewMode === 'synopsis';
    document.body.dataset.review = editable ? 'on' : 'off';
    for (const el of document.querySelectorAll(
      '.transcription__line[data-line-id]:not(.transcription__line--folio)')) {
      el.tabIndex = editable ? 0 : -1;
    }
  }

  function syncReviewUI() {
    const { pageNr, viewMode } = getContext();
    const isSynopsis = viewMode === 'synopsis';
    els.toggle.setAttribute('aria-pressed', String(reviewMode));
    els.toggle.disabled = !isSynopsis;
    els.bar.hidden = !(reviewMode && isSynopsis);
    const page = isSynopsis ? reviewPage(pageNr) : null;
    const status = page?.status || null;
    els.statusReviewed.setAttribute('aria-pressed',
      String(status === 'gesichtet' || status === 'abgenommen'));
    els.statusApproved.setAttribute('aria-pressed', String(status === 'abgenommen'));
    if (!els.bar.hidden && !els.hint.textContent) {
      els.hint.textContent = 'Click a line to correct it.';
    }
    applyReviewMode();
    updateReviewChip();
  }

  function setReviewMode(on) {
    reviewMode = on;
    els.hint.textContent = '';
    syncReviewUI();
    if (on && !els.bar.hidden && initialsValue().length < 2) els.initials.focus();
  }

  /**
   * One line after a correction, in the same shape renderTranscription gives
   * it. Only this line is touched: a full re-render would detach the element
   * whose blur committed the edit, and the click that caused the blur would
   * land in a dropped subtree instead of opening the next line.
   */
  function updateLineEl(lineEl, original, corrected) {
    const span = lineEl.querySelector('.transcription__line-text');
    if (!span) return;
    let text = escapeHTML(corrected ?? original);
    if (corrected == null) text = markText(text);
    span.innerHTML = text;
    lineEl.classList.toggle('transcription__line--corrected', corrected != null);
    if (corrected == null) lineEl.removeAttribute('title');
    else lineEl.title = `Original: ${original}`;
  }

  function commitCorrection(lineEl, rawValue) {
    const id = lineEl.dataset.lineId;
    const { pageNr } = getContext();
    if (!id || pageNr == null) return;
    const original = lineEl.dataset.original ?? '';
    const value = rawValue.trim();
    const store = reviewStore();
    const page = ensurePage(store, pageNr);
    const idx = page.lines.findIndex(l => l && l.id === id);
    // An emptied line is treated as a withdrawn correction; a blank reading is
    // not expressible here and would be indistinguishable from a mis-click
    const withdrawn = value === original || value === '';
    if (withdrawn) {
      if (idx < 0) return;
      page.lines.splice(idx, 1);
    } else if (idx >= 0) {
      page.lines[idx].corrected = value;
    } else {
      page.lines.push({ id, original, corrected: value });
    }
    page.date = today();
    if (initialsValue().length >= 2) store.reviewer = initialsValue();
    prunePage(store, pageNr);
    saveReview(store);
    updateLineEl(lineEl, original, withdrawn ? null : value);
    syncReviewUI();
    lineEl.focus({ preventScroll: true });
  }

  function beginEdit(lineEl) {
    if (!reviewMode || getContext().viewMode !== 'synopsis') return;
    if (!lineEl || lineEl.classList.contains('transcription__line--folio')) return;
    if (!requireInitials()) return;
    const span = lineEl.querySelector('.transcription__line-text');
    if (!span || lineEl.querySelector('.transcription__line-edit')) return;

    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'transcription__line-edit';
    input.value = span.textContent;
    input.setAttribute('aria-label', 'Correct this transcription line');
    let settled = false;
    const finish = (commit) => {
      if (settled) return;
      settled = true;
      const value = input.value;
      input.remove();
      span.hidden = false;
      if (commit) commitCorrection(lineEl, value);
      else lineEl.focus({ preventScroll: true });
    };
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); finish(true); }
      else if (e.key === 'Escape') { e.preventDefault(); finish(false); }
    });
    input.addEventListener('blur', () => finish(true));
    span.hidden = true;
    span.after(input);
    input.focus();
    input.select();
  }

  els.toggle.addEventListener('click', () => setReviewMode(!reviewMode));
  els.statusReviewed.addEventListener('click', () => setStatus('gesichtet'));
  els.statusApproved.addEventListener('click', () => setStatus('abgenommen'));
  els.exportBtn.addEventListener('click', exportReview);
  els.clearBtn.addEventListener('click', clearReviewPage);

  els.initials.value = lsGet(REVIEWER_KEY) || '';
  els.initials.addEventListener('input', () => {
    els.initials.classList.remove('is-missing');
    lsSet(REVIEWER_KEY, initialsValue());
  });

  return {
    /** Whether review mode is on; the page reads it before routing a click. */
    get on() { return reviewMode; },
    corrections: reviewCorrections,
    beginEdit,
    applyMode: applyReviewMode,
    sync: syncReviewUI,
  };
}
