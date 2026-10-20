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

import { lsGet, lsSet } from './utils.js';
import { fillLine, lineState } from './viewer-render.js?v=20261020-readings';
import { markUnclear } from './readings.js';
import { READINGS } from './strings.js';

const REVIEWER_KEY = 'docta-review-reviewer';
const LEGACY_STATUS = new Set(['gesichtet', 'abgenommen']);
// Persisted reasons that justify a correction claim; the text status reads them too.
export const CORRECTION_REASONS = new Set(['text-corrected', 'review-reopened-after-text-change']);
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
 *   saveBtn: HTMLElement
 * }} els
 * @param {{
 *   getContext: () => { docId: number|null, pageNr: number|null, viewMode: string },
 *   rerenderPage: (pageNr: number) => void
 * }} opts
 */
export function createReviewView(els, { getContext, rerenderPage, local, onSaved, onDraftChange }) {
  let reviewMode = false;
  let saving = false;
  let visibleDocId = null;
  let activeEdit = null;
  const drafts = new Map();
  // The state attribute lets tests and styles tell outcomes apart without reading the wording.
  const setHint = (text, state = '') => {
    els.hint.textContent = text;
    els.hint.dataset.state = state;
  };

  function saveReview(store) {
    drafts.set(store.docId, store);
    if (!lsSet(reviewKey(store.docId), JSON.stringify(store))) {
      setHint('The browser draft could not be stored. Keep this tab open and save the changes locally or export them now.');
    } else {
      setHint('Changes kept as a browser draft. Not yet saved locally.');
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
    setHint('Enter two to four initials before correcting.');
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
    setHint('Draft exported. The file can now be taken into the pipeline.');
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
      setHint(draft(docId) ? 'Browser draft restored. Not yet saved locally.' : '');
      if (local.enabled && draft(docId) && draft(docId).baseRevision !== getContext().revision) {
        setHint('The restored draft is based on an older version. Export it before discarding and check the current text again.');
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
      setHint('Click a line to correct its transcription.');
    }
    applyReviewMode();
  }

  function setReviewMode(on) {
    reviewMode = on;
    setHint('');
    syncReviewUI();
    if (on && !els.bar.hidden && initialsValue().length < 2) els.initials.focus();
  }

  /**
   * Record a line's reading and, where given, whether it is deleted. Only this
   * line is redrawn: a full re-render would detach the element whose blur
   * committed the edit, and the click that caused the blur would land in a
   * dropped subtree instead of opening the next line. A draft equal to the
   * saved line is withdrawn; the excluded flag is written only where it
   * differs from the saved state, which the save then carries over.
   */
  function commitCorrection(lineEl, rawValue, excludedChoice) {
    const id = lineEl.dataset.lineId;
    const { pageNr } = getContext();
    if (!id || pageNr == null) return;
    const original = lineEl.dataset.original ?? '';
    const savedExcluded = lineEl.dataset.excluded === 'true';
    const value = rawValue.trim();
    const store = reviewStore();
    const page = ensurePage(store, pageNr);
    const idx = page.lines.findIndex(l => l && l.id === id);
    const drafted = idx >= 0 && typeof page.lines[idx].excluded === 'boolean'
      ? page.lines[idx].excluded : savedExcluded;
    const excluded = typeof excludedChoice === 'boolean' ? excludedChoice : drafted;
    // Empty text deliberately removes a hallucinated reading without removing its anchor.
    const withdrawn = value === original && excluded === savedExcluded;
    const record = { id, original, corrected: value,
      ...(excluded === savedExcluded ? {} : { excluded }) };
    if (withdrawn) {
      if (idx < 0) return;
      page.lines.splice(idx, 1);
    } else if (idx >= 0) {
      page.lines[idx] = record;
    } else {
      page.lines.push(record);
    }
    page.date = today();
    page.status = null;
    if (initialsValue().length >= 2) store.reviewer = initialsValue();
    prunePage(store, pageNr);
    saveReview(store);
    fillLine(lineEl, lineState(lineEl, withdrawn ? null : record));
    syncReviewUI();
    lineEl.focus({ preventScroll: true });
  }

  /** Return a deleted line to the edition text with the reading it shows. */
  function restoreLine(lineEl) {
    if (saving || !reviewMode || !lineEl || !requireInitials()) return;
    const record = reviewCorrections(getContext().pageNr).get(lineEl.dataset.lineId);
    commitCorrection(lineEl, lineState(lineEl, record).text, false);
  }

  function lineAction(label, title) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'review-btn';
    button.textContent = label;
    button.title = title;
    // Pressing keeps the caret and the selection in the input.
    button.addEventListener('mousedown', event => event.preventDefault());
    return button;
  }

  function beginEdit(lineEl) {
    if (saving) return;
    if (!reviewMode || getContext().viewMode !== 'synopsis') return;
    if (!lineEl || lineEl.classList.contains('transcription__line--folio')) return;
    // A deleted line is restored first; its Restore control is the way back.
    if (lineEl.classList.contains('transcription__line--excluded')) return;
    if (!requireInitials()) return;
    const span = lineEl.querySelector('.transcription__line-text');
    if (!span || lineEl.querySelector('.transcription__line-edit')) return;

    const editor = document.createElement('div');
    editor.className = 'transcription__line-editor';
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'transcription__line-edit';
    input.value = span.textContent;
    const initialValue = input.value;
    input.setAttribute('aria-label', 'Correct transcription line');
    const unclear = lineAction(READINGS.markUnclear, READINGS.markUnclearTitle);
    const remove = lineAction(READINGS.deleteLine, READINGS.deleteLineTitle);
    editor.append(input, unclear, remove);
    let settled = false;
    const finish = (commit, excluded) => {
      if (settled) return;
      settled = true;
      activeEdit = null;
      const value = input.value;
      editor.remove();
      span.hidden = false;
      if (commit) commitCorrection(lineEl, value, excluded);
      else lineEl.focus({ preventScroll: true });
    };
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); finish(true); }
      else if (e.key === 'Escape') { e.preventDefault(); finish(false); }
    });
    unclear.addEventListener('click', () => {
      const next = markUnclear(input.value, input.selectionStart ?? input.value.length,
        input.selectionEnd ?? input.value.length);
      input.value = next.value;
      input.focus();
      input.setSelectionRange(next.caret, next.caret);
    });
    remove.addEventListener('click', () => finish(true, true));
    // The edit ends when focus leaves the line editor, not when it moves to
    // one of its actions, so a keyboard user can reach them with Tab.
    editor.addEventListener('focusout', (e) => {
      if (!editor.contains(e.relatedTarget)) finish(true);
    });
    activeEdit = { input, initialValue, finish };
    span.hidden = true;
    span.after(editor);
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
      setHint('This draft belongs to an older version. Export it before discarding and check the current text again.');
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
        setHint('Changes saved locally.', 'saved');
      }
    } catch (error) {
      setHint(`Not saved: ${error.message}. The browser draft is kept.`);
    } finally {
      saving = false;
      syncReviewUI();
    }
  });
  window.addEventListener('beforeunload', (event) => {
    // Reload and tab close need not blur the focused correction first.
    if (activeEdit && activeEdit.input.value !== activeEdit.initialValue) activeEdit.finish(true);
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
    restoreLine,
    applyMode: applyReviewMode,
    sync: syncReviewUI,
  };
}
