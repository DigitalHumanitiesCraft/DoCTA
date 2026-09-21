/**
 * DoCTA viewer - the curation view.
 *
 * Browser drafts can be exported or explicitly saved through the loopback API.
 * The public site remains export-only. The review shape is a contract with
 * pipeline/apply_review.py and is not changed here alone.
 *
 * The module holds no page state. Which document, which page and which view the
 * reader is in comes from the getContext callback the page supplies.
 */

import { escapeHTML, lsGet, lsSet } from './utils.js';

const REVIEWER_KEY = 'docta-review-reviewer';
const LEGACY_STATUS = new Set(['gesichtet', 'abgenommen']);
const CORRECTION_REASONS = new Set(['text-corrected', 'review-reopened-after-text-change']);
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
    if (status !== null && !LEGACY_STATUS.has(status)) continue;
    if (typeof page.date !== 'string' || !REVIEW_DATE.test(page.date)) continue;
    if (!Array.isArray(page.lines)) continue;
    pages[key] = { ...page, status };
  }
  return { ...data, version: REVIEW_VERSION, pages };
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
 * Build the curation view over the elements of the review bar.
 * @param {{
 *   bar: HTMLElement, toggle: HTMLElement, initials: HTMLInputElement,
 *   hint: HTMLElement, exportBtn: HTMLElement, clearBtn: HTMLElement,
 *   saveBtn: HTMLElement, meta: HTMLElement
 * }} els
 * @param {{
 *   getContext: () => { docId: number|null, pageNr: number|null, viewMode: string },
 *   markText: (escaped: string) => string,
 *   rerenderPage: (pageNr: number) => void
 * }} opts
 */
export function createReviewView(els, { getContext, markText, rerenderPage, local, onSaved, onDraftChange }) {
  let reviewMode = false;
  let saving = false;
  let visibleDocId = null;
  const drafts = new Map();

  function saveReview(store) {
    drafts.set(store.docId, store);
    if (!lsSet(reviewKey(store.docId), JSON.stringify(store))) {
      els.hint.textContent = 'Der Browserentwurf konnte nicht gespeichert werden. Diesen Tab offen lassen und die Änderungen lokal speichern oder jetzt exportieren.';
    } else {
      els.hint.textContent = 'Änderungen als Browserentwurf gesichert. Noch nicht lokal gespeichert.';
    }
    onDraftChange();
  }

  function draft(docId) {
    if (!drafts.has(docId)) drafts.set(docId, loadReview(docId));
    return drafts.get(docId);
  }

  const initialsValue = () => els.initials.value.trim();

  function requireInitials() {
    if (initialsValue().length >= 2) return true;
    els.initials.classList.add('is-missing');
    els.initials.focus();
    els.hint.textContent = 'Vor einer Korrektur zwei bis vier Initialen eingeben.';
    return false;
  }

  function reviewStore() {
    const { docId, revision } = getContext();
    const stored = draft(docId);
    if (stored) return stored;
    return { version: REVIEW_VERSION, docId, baseRevision: revision,
      reviewer: initialsValue(), pages: {} };
  }

  function reviewPage(pageNr) {
    const { docId } = getContext();
    if (docId == null || pageNr == null) return null;
    const store = draft(docId);
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

  function clearReviewPage() {
    if (saving) return;
    const { docId, pageNr } = getContext();
    if (docId == null || pageNr == null) return;
    const store = draft(docId);
    if (!store) return;
    delete store.pages[String(pageNr)];
    if (!Object.keys(store.pages).length) store.baseRevision = getContext().revision;
    saveReview(store);
    rerenderPage(pageNr);
    syncReviewUI();
  }

  function exportReview() {
    const { docId } = getContext();
    if (docId == null) return;
    const store = draft(docId) ||
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
    els.hint.textContent = 'Review exportiert. Die Datei kann nun in die Pipeline übernommen werden.';
  }

  /** Only a persisted correction reason justifies a correction claim. */
  function updateReviewChip() {
    const { pageNr, viewMode } = getContext();
    els.meta.querySelector('#review-chip')?.remove();
    if (viewMode !== 'synopsis' || pageNr == null) return;
    const savedPage = getContext().reviewState?.[String(pageNr)];
    if (!CORRECTION_REASONS.has(savedPage?.reason)) return;
    const who = savedPage.reviewer || '';
    const date = savedPage.date || '';
    const chip = document.createElement('span');
    chip.id = 'review-chip';
    chip.className = 'prov-chip prov-chip--review';
    chip.textContent = 'Lokal korrigiert';
    chip.title = `Textkorrektur lokal gespeichert${who ? ` von ${who}` : ''}${date ? ` am ${date}` : ''}.`;
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
    const { docId, viewMode } = getContext();
    if (visibleDocId !== docId) {
      visibleDocId = docId;
      els.hint.textContent = draft(docId) ? 'Browserentwurf wiederhergestellt. Noch nicht lokal gespeichert.' : '';
      if (local.enabled && draft(docId) && draft(docId).baseRevision !== getContext().revision) {
        els.hint.textContent = 'Der wiederhergestellte Entwurf beruht auf einer älteren Fassung. Vor dem Verwerfen exportieren und den aktuellen Text erneut prüfen.';
      }
    }
    const isSynopsis = viewMode === 'synopsis';
    els.toggle.setAttribute('aria-pressed', String(reviewMode));
    els.toggle.disabled = !isSynopsis;
    els.saveBtn.hidden = !local.enabled;
    els.saveBtn.disabled = saving || !Object.keys(draft(docId)?.pages || {}).length;
    for (const control of [els.initials, els.clearBtn]) control.disabled = saving;
    els.bar.hidden = !(reviewMode && isSynopsis);
    if (!els.bar.hidden && !els.hint.textContent) {
      els.hint.textContent = 'Eine Zeile anklicken, um ihre Transkription zu korrigieren.';
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
    if (corrected == null) text = markText(text, { pageNr: getContext().pageNr, lineId: lineEl.dataset.lineId, text: original });
    span.innerHTML = text;
    lineEl.classList.toggle('transcription__line--corrected', corrected != null);
    if (corrected == null) lineEl.removeAttribute('title');
    else lineEl.title = `Ursprüngliche Lesung: ${original}`;
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
    // Empty text deliberately removes a hallucinated reading without removing its anchor.
    const withdrawn = value === original;
    if (withdrawn) {
      if (idx < 0) return;
      page.lines.splice(idx, 1);
    } else if (idx >= 0) {
      page.lines[idx].corrected = value;
    } else {
      page.lines.push({ id, original, corrected: value });
    }
    page.date = today();
    page.status = null;
    if (initialsValue().length >= 2) store.reviewer = initialsValue();
    prunePage(store, pageNr);
    saveReview(store);
    updateLineEl(lineEl, original, withdrawn ? null : value);
    syncReviewUI();
    lineEl.focus({ preventScroll: true });
  }

  function beginEdit(lineEl) {
    if (saving) return;
    if (!reviewMode || getContext().viewMode !== 'synopsis') return;
    if (!lineEl || lineEl.classList.contains('transcription__line--folio')) return;
    if (!requireInitials()) return;
    const span = lineEl.querySelector('.transcription__line-text');
    if (!span || lineEl.querySelector('.transcription__line-edit')) return;

    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'transcription__line-edit';
    input.value = span.textContent;
    input.setAttribute('aria-label', 'Transkriptionszeile korrigieren');
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
  els.exportBtn.addEventListener('click', exportReview);
  els.clearBtn.addEventListener('click', clearReviewPage);
  els.saveBtn.addEventListener('click', async () => {
    if (saving) return;
    const { docId, revision } = getContext();
    if (!Object.keys(draft(docId)?.pages || {}).length) return;
    if (!requireInitials()) return;
    const store = reviewStore();
    if (store.baseRevision !== revision) {
      els.hint.textContent = 'Dieser Entwurf gehört zu einer älteren Fassung. Vor dem Verwerfen exportieren und den aktuellen Text erneut prüfen.';
      return;
    }
    store.reviewer = initialsValue();
    saveReview(store);
    saving = true;
    syncReviewUI();
    try {
      const result = await local.save(store);
      drafts.set(docId, null);
      try { window.localStorage.removeItem(reviewKey(docId)); } catch {
        // A stale stored draft is still rejected by its saved base revision on reload.
      }
      if (getContext().docId === docId) {
        onSaved(result.document);
        els.hint.textContent = 'Änderungen lokal gespeichert.';
      }
    } catch (error) {
      els.hint.textContent = `Nicht gespeichert: ${error.message}. Der Browserentwurf bleibt erhalten.`;
    } finally {
      saving = false;
      syncReviewUI();
    }
  });
  window.addEventListener('beforeunload', (event) => {
    if ([...drafts.values()].some(store => store && Object.keys(store.pages).length)) {
      event.preventDefault();
      event.returnValue = '';
    }
  });

  els.initials.value = lsGet(REVIEWER_KEY) || '';
  els.initials.addEventListener('input', () => {
    els.initials.classList.remove('is-missing');
    lsSet(REVIEWER_KEY, initialsValue());
  });

  return {
    /** Whether review mode is on; the page reads it before routing a click. */
    get on() { return reviewMode; },
    get hasDraft() { return Object.keys(draft(getContext().docId)?.pages || {}).length > 0; },
    corrections: reviewCorrections,
    beginEdit,
    applyMode: applyReviewMode,
    sync: syncReviewUI,
  };
}
