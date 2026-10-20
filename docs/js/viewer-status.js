/**
 * DoCTA viewer - the text status pill and its details surface.
 *
 * One statement beside the transcription title: the document's text
 * attribution, qualified by the state of the current page. The details surface
 * holds what the pill abbreviates. The module derives everything from the
 * loaded document and the register summary; it holds no review state of its
 * own.
 */

import { escapeHTML, escapeAttr } from './utils.js';
import { PROVENANCE, STATUS_DETAILS as D, DRAFT_BADGE } from './strings.js';
import { CORRECTION_REASONS } from './viewer-review.js?v=20261020-en';
import { createAnchoredPopover } from './viewer-annotation-popover.js';

const WEB_URL = /^https?:\/\//i;

function displayDate(value) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return value;
  // Written out like the archival dates in the source header.
  const day = new Intl.DateTimeFormat('en-GB', { dateStyle: 'long' }).format(date);
  if (!String(value).includes('T')) return day;
  return `${day}, ${new Intl.DateTimeFormat('en-GB', { timeStyle: 'short' }).format(date)}`;
}

/**
 * Who produced the text layer of a document, from the register summary.
 * Absence of the Transkribus done status documents no correction work, so it
 * is named as unrecorded rather than as unrevised.
 */
function attribution(reg) {
  if (!reg || typeof reg.pages_total !== 'number' || !reg.pages_total) return null;
  const done = typeof reg.done_pages === 'number' ? reg.done_pages : 0;
  const total = reg.pages_total;
  const inventaria = reg.transcription_by === 'Inventaria';
  const url = reg.edition_url || 'https://www.inventaria.at/';
  const edition = inventaria && WEB_URL.test(url) ? url : null;
  const by = inventaria ? 'the Inventaria project' : '';
  if (reg.transcription_source === 'vlm') {
    return { kind: 'vlm', provenance: 'machine-unrevised', tone: 'machine', edition, description: D.vlmNote };
  }
  if (done >= total) {
    return { kind: 'corrected', provenance: 'corrected', tone: 'human', edition,
      base: inventaria ? PROVENANCE.inventariaCorrected : PROVENANCE.transkribusCorrected,
      description: D.corrected(by, total) };
  }
  if (done > 0) {
    return { kind: 'partial', provenance: 'partly-corrected', tone: 'partial', edition,
      base: PROVENANCE.partlyCorrected(done, total), description: D.partlyCorrected(by, done, total) };
  }
  return { kind: 'unrecorded', provenance: 'correction-unrecorded', tone: 'machine', edition,
    description: D.unrecordedNote };
}

function newestCorrection(page, saved) {
  const runs = page?.provenance?.humanCorrections || [];
  const newest = runs.reduce((best, run) =>
    (!best || String(run.timestamp || '') > String(best.timestamp || '') ? run : best), null);
  return {
    who: newest?.reviewer || saved?.reviewer || '',
    when: displayDate(newest?.timestamp || saved?.date || ''),
  };
}

/**
 * The correction state of the current page, or of the whole document outside
 * the synopsis. state: none | counted | uncounted | unlocated.
 */
function correctionState({ doc, reg, pageNr, scope }) {
  const local = doc.reviewState && typeof doc.reviewState === 'object';
  const savedFor = nr => {
    const saved = doc.reviewState?.[String(nr)];
    const page = doc.pages.find(item => item.pageNr === nr);
    return CORRECTION_REASONS.has(saved?.reason) || Boolean(page?.provenance?.humanCorrections?.length);
  };
  if (scope === 'document') {
    const corrected = local ? doc.pages.some(page => savedFor(page.pageNr)) : Boolean(reg?.effective_transcription);
    return { state: corrected ? 'unlocated' : 'none' };
  }
  if (local && !savedFor(pageNr)) return { state: 'none' };
  if (!local && !reg?.effective_transcription) return { state: 'none' };
  const page = doc.pages.find(item => item.pageNr === pageNr);
  const who = local ? newestCorrection(page, doc.reviewState?.[String(pageNr)]) : { who: '', when: '' };
  // The served page counts its lines that differ from the machine or export
  // reading (build_register.effective_transcription_from_pages); the base
  // lines themselves are not served. A page without the count is not
  // reviewed in the static projection, and of unknown extent locally.
  const count = page?.changedLines;
  if (!Number.isInteger(count)) return { state: local ? 'uncounted' : 'none', ...who };
  if (!local && !count) return { state: 'none' };
  return { state: 'counted', count, ...who };
}

function pillLabel(attr, corr) {
  const n = corr.count;
  if (attr.kind === 'vlm') {
    if (corr.state === 'counted' && n) return PROVENANCE.vlmCorrected(n);
    if (corr.state === 'uncounted') return PROVENANCE.vlmCorrectedUncounted;
    if (corr.state === 'unlocated') return PROVENANCE.vlmPartlyCorrected;
    return PROVENANCE.vlm;
  }
  if (attr.kind === 'unrecorded') {
    if (corr.state === 'counted' && n) return PROVENANCE.transkribusUnrecordedCorrected(n);
    if (corr.state === 'uncounted' || corr.state === 'unlocated') return PROVENANCE.transkribusUnrecordedCorrectedUncounted;
    return PROVENANCE.transkribusUnrecorded;
  }
  if (corr.state === 'counted' && n) return PROVENANCE.changedInDocta(attr.base, n);
  return attr.base;
}

function detailFields(ctx, attr, corr) {
  const { doc, pageNr, scope } = ctx;
  const F = D.fields;
  const fields = [[F.layer, escapeHTML(D.layer[attr.kind] || attr.base)]];
  const page = doc.pages.find(item => item.pageNr === pageNr);
  const prov = page?.provenance;
  const runs = (prov?.originalRuns || []).filter(run => run.id === prov.originalRunId);
  if (scope === 'page' && runs.length) {
    for (const run of runs) {
      fields.push([F.model, escapeHTML(run.model || (run.source === 'transkribus' ? D.transkribusExport : D.modelUndocumented))]);
      if (run.date) fields.push([F.transcribed, escapeHTML(displayDate(run.date))]);
    }
  } else if (attr.kind === 'vlm') {
    const prompt = doc.provenance?.prompt ? `, prompt ${doc.provenance.prompt}` : '';
    fields.push([F.model, escapeHTML((doc.provenance?.model || D.modelUndocumented) + prompt)]);
  } else {
    fields.push([F.model, escapeHTML(D.transkribusExport)]);
  }
  if (attr.edition) {
    fields.push([F.edition, `<a href="${escapeAttr(attr.edition)}" target="_blank" rel="noopener">` +
      `${escapeHTML(D.editionLink)}</a>`]);
  }
  const state = { none: D.noCorrection, counted: D.correctionCount(corr.count),
    uncounted: D.correctionUncounted, unlocated: D.correctionUnlocated }[corr.state];
  if (state) fields.push([scope === 'page' ? F.page : F.document, escapeHTML(state)]);
  if (corr.who || corr.when) fields.push([F.correctedBy, escapeHTML([corr.who, corr.when].filter(Boolean).join(', '))]);
  const coverage = doc.provenance;
  if (coverage && coverage.pagesTranscribed < coverage.pagesInDocument) {
    fields.push([F.coverage, escapeHTML(D.coverage(coverage.pagesTranscribed, coverage.pagesInDocument))]);
  }
  return fields;
}

/** The notes under the fields: what the layer is, and what a correction is not. */
function detailNotes(attr, corr) {
  const notes = [attr.description];
  if (corr.state !== 'none') notes.push(D.notApproval);
  return notes;
}

/**
 * @param {{ group: HTMLElement, pill: HTMLButtonElement, credit: HTMLAnchorElement,
 *           details: HTMLElement }} els
 */
export function createTextStatus(els) {
  const label = els.pill.querySelector('.status-pill__label');
  const creditLabel = els.credit.querySelector('.action-label');
  const body = els.details.querySelector('.text-status__body');
  const popover = createAnchoredPopover(els.details, {
    onHide: () => els.pill.setAttribute('aria-expanded', 'false'),
  });

  function update(ctx) {
    const attr = ctx.doc && !ctx.doc.imageOnly ? attribution(ctx.reg) : null;
    els.group.hidden = !attr;
    if (!attr) { popover.hide({ restoreFocus: false }); return; }
    const corr = correctionState(ctx);
    const text = ctx.dirty ? DRAFT_BADGE : pillLabel(attr, corr);
    label.textContent = text;
    els.pill.dataset.provenance = attr.provenance;
    els.pill.dataset.pageState = corr.state;
    els.pill.dataset.state = ctx.dirty ? 'dirty'
      : corr.state === 'none' ? attr.tone : 'corrected';
    els.pill.title = 'Show text status details';
    els.credit.hidden = !attr.edition;
    if (attr.edition) {
      els.credit.href = attr.edition;
      creditLabel.textContent = D.editionLink;
      els.credit.title = D.editionLinkName;
    }
    body.innerHTML = (ctx.dirty ? `<p class="text-status__draft">${escapeHTML(D.draft)}</p>` : '') +
      '<dl class="text-status__fields">' +
      detailFields(ctx, attr, corr).map(([key, value]) => `<div><dt>${escapeHTML(key)}</dt><dd>${value}</dd></div>`).join('') +
      '</dl>' + detailNotes(attr, corr).map(note => `<p class="text-status__note">${escapeHTML(note)}</p>`).join('');
    popover.reposition();
  }

  els.pill.addEventListener('click', () => {
    if (popover.isOpen) { popover.hide(); return; }
    els.pill.setAttribute('aria-expanded', 'true');
    popover.open(els.pill, els.pill);
  });

  return { update, hide: () => popover.hide({ restoreFocus: false }) };
}
