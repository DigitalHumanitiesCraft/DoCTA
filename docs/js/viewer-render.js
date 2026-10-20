/**
 * DoCTA viewer - the transcription panel.
 *
 * Everything here builds markup from loaded data into a container element: the
 * page synopsis, the reading text over the whole document and the TEI source.
 * The facsimile, the line overlay,
 * the pager and the URL state stay with the page that owns them.
 */

import { escapeHTML, escapeAttr } from './utils.js';
import { readingsHTML } from './readings.js';
import { READINGS } from './strings.js';

// Lines like "[fol.2r]", "[fol. 12v]" or bare "[1r]" are structure; the
// endpaper marks "[us_vorne_r]" etc. count as structure as well.
const FOLIO_RE = /^\[(?:fol\.\s*)?(\d+[rv]?|us_[a-z]+_[rv])\]$/i;

/**
 * The folio label of a structural line, or null for a line of source text.
 * @param {string} text
 * @returns {string|null}
 */
export function folioLabel(text) {
  const m = FOLIO_RE.exec(text.trim());
  if (!m) return null;
  const n = m[1].trim();
  return n.startsWith('us_') ? n : `fol. ${n}`;
}

/**
 * The text and state of one synopsis line, shared by the full render and the
 * single-line update after an edit. A deleted line keeps its text, struck
 * through, with a Restore control that only the edit mode shows.
 * @param {HTMLElement} lineEl
 * @param {{ text: string, machine: boolean, corrected: boolean, excluded: boolean, original: string }} state
 */
export function fillLine(lineEl, { text, machine, corrected, excluded, original }) {
  const span = lineEl.querySelector('.transcription__line-text');
  span.innerHTML = readingsHTML(text, machine);
  lineEl.classList.toggle('transcription__line--corrected', corrected);
  lineEl.classList.toggle('transcription__line--excluded', excluded);
  lineEl.querySelector('.transcription__line-restore')?.remove();
  if (excluded) {
    const restore = document.createElement('button');
    restore.type = 'button';
    restore.className = 'transcription__line-restore review-btn';
    restore.textContent = READINGS.restoreLine;
    restore.title = READINGS.restoreLineTitle;
    lineEl.append(restore);
  }
  if (excluded) lineEl.title = READINGS.excluded;
  else if (corrected) lineEl.title = `Original reading: ${original}`;
  else lineEl.removeAttribute('title');
}

/**
 * The synopsis of one page: line number and line text with its unclear marks.
 * The container is replaced wholesale and scrolled back to the top.
 * @param {HTMLElement} container
 * @param {any} doc
 * @param {number} pageNr
 * @param {{ corrections: Map<string, any>, machine: boolean }} opts
 */
export function renderTranscription(container, doc, pageNr, { corrections, machine }) {
  const page = doc.pages.find(p => p.pageNr === pageNr);
  if (!page) {
    container.innerHTML = '<div class="loading text-body-secondary">No transcription for this page</div>';
    container.scrollTop = 0;
    return;
  }

  let lineNr = 0;
  for (const p of doc.pages) {
    if (p.pageNr < pageNr) {
      for (const r of p.regions || []) lineNr += (r.lines || []).length;
    }
  }

  let html = '<div class="transcription">';
  // A layout region boundary becomes a paragraph gap: heading, preamble
  // and list blocks of the source read as blocks, straight from the
  // Transkribus segmentation, with no interpretation added here.
  for (const [ri, region] of (page.regions || []).entries()) {
    let firstInRegion = true;
    for (const line of region.lines || []) {
      lineNr++;
      const regionStart = ri > 0 && firstInRegion ? ' transcription__line--region-start' : '';
      firstInRegion = false;
      // The line id keys the coupling with the image overlay; tabindex -1 lets
      // a zone click move focus to the line without adding a tab stop per line
      const lineAttr = line.id ? ` data-line-id="${escapeAttr(line.id)}" tabindex="-1"` : '';
      const fol = folioLabel(line.text);
      if (fol) {
        html += `<div class="transcription__line transcription__line--folio${regionStart}"${lineAttr}>` +
                `<span class="transcription__line-nr">${lineNr}</span>` +
                `<span class="transcription__line-text">${escapeHTML(line.text)}</span></div>`;
        continue;
      }
      // A saved line states whether a reviewer changed or deleted it; only an
      // unchanged line of a machine transcription keeps the model's marks.
      const saved = ` data-original="${escapeAttr(line.text)}"` +
        (line.excluded ? ' data-excluded="true"' : '') +
        (machine && !line.corrected ? ' data-machine="true"' : '');
      html += `<div class="transcription__line${regionStart}"${lineAttr}${saved}>` +
              `<span class="transcription__line-nr">${lineNr}</span>` +
              '<span class="transcription__line-text"></span></div>';
    }
  }
  html += '</div>';
  container.innerHTML = html;
  for (const lineEl of container.querySelectorAll('.transcription__line[data-original]')) {
    fillLine(lineEl, lineState(lineEl, corrections.get(lineEl.dataset.lineId)));
  }
  container.scrollTop = 0;
}

/**
 * What a line shows: the saved reading, or a browser draft made against it. A
 * draft is bound to the original it was made against, so a changed export
 * drops it silently. A draft without the excluded flag keeps the saved state.
 * @param {HTMLElement} lineEl
 * @param {any} stored the draft record of the line, if any
 */
export function lineState(lineEl, stored) {
  const original = lineEl.dataset.original ?? '';
  const savedExcluded = lineEl.dataset.excluded === 'true';
  const corr = stored && stored.original === original ? stored : null;
  return {
    original,
    text: corr ? corr.corrected : original,
    machine: !corr && lineEl.dataset.machine === 'true',
    corrected: Boolean(corr),
    excluded: corr && typeof corr.excluded === 'boolean' ? corr.excluded : savedExcluded,
  };
}

/**
 * Reading mode: the whole document as one text, without line numbers and
 * without the lines a reviewer deleted.
 * @param {HTMLElement} container
 * @param {any} doc
 * @param {boolean} machine the document is a machine transcription
 */
export function renderReading(container, doc, machine = false) {
  const out = [];
  doc.pages.forEach((page, idx) => {
    const regions = (page.regions || []).filter(r => (r.lines || []).length);
    if (!regions.length) return;
    out.push('<section class="reading-page">');
    out.push(`<button type="button" class="reading-page__mark" data-index="${idx}"` +
             ` title="Open page ${page.pageNr} beside the facsimile">p. ${page.pageNr}</button>`);
    // Region boundaries from the layout give the paragraph gaps; a line
    // opening with "Item" additionally starts a small entry gap. Both are
    // display segmentation only and never enter the data.
    regions.forEach((region, ri) => {
      region.lines.forEach((l, li) => {
        if (l.excluded) return;
        const fol = folioLabel(l.text);
        if (fol) {
          out.push(`<div class="folio-mark">${escapeHTML(fol)}</div>`);
          return;
        }
        const cls = ['reading-line'];
        if (ri > 0 && li === 0) cls.push('reading-line--region-start');
        else if (/^item\b/i.test(l.text)) cls.push('reading-line--entry');
        out.push(`<div class="${cls.join(' ')}">${readingsHTML(l.text, machine && !l.corrected)}</div>`);
      });
    });
    out.push('</section>');
  });
  container.innerHTML = out.length
    ? `<div class="reading-text">${out.join('')}</div>`
    : '<div class="loading text-body-secondary">No transcription text for this document</div>';
  container.scrollTop = 0;
}

/**
 * TEI mode: the encoded document as source text. Escape first, then colour
 * only inside the escaped tag spans, so no source content can become markup.
 * @param {string} xml
 */
export function highlightTEI(xml) {
  return escapeHTML(xml).replace(/&lt;[\s\S]*?&gt;/g, (tag) => {
    if (tag.startsWith('&lt;?') || tag.startsWith('&lt;!')) {
      return `<span class="tei-decl">${tag}</span>`;
    }
    return tag
      .replace(/([\w:.-]+)=("[^"]*")/g,
               '<span class="tei-attr">$1</span>=<span class="tei-val">$2</span>')
      .replace(/^(&lt;\/?)([\w:.-]+)/, '$1<span class="tei-tag">$2</span>');
  });
}

/**
 * The TEI source view. The fetched text is cached per document, a document
 * without TEI is cached as absent, and `cached` reports what the view has
 * actually shown, which is what the download link may offer.
 * @param {HTMLElement} container
 * @param {{ getViewMode: () => string, onRendered: () => void }} opts
 */
export function createTeiView(container, { getViewMode, onRendered }) {
  const cache = new Map();
  let request = 0;
  let generation = 0;

  return {
    /** @returns {string|null|undefined} undefined while nothing has been fetched */
    cached: (docId) => cache.get(String(docId)),
    invalidate: () => { request += 1; generation += 1; cache.clear(); },

    async render(docId) {
      const token = ++request;
      const startedGeneration = generation;
      const cachedXML = cache.get(String(docId));
      if (cachedXML === undefined) {
        container.innerHTML = '<div class="loading"><div class="loading__spinner"></div>Loading TEI</div>';
      }
      let xml = cachedXML;
      if (xml === undefined) {
        try {
          const res = await fetch(`data/tei/${docId}.xml`, { cache: 'no-store' });
          if (!res.ok) throw new Error(String(res.status));
          xml = await res.text();
        } catch {
          xml = null;
        }
        // A response started before a rebuild cannot refill its cleared cache.
        if (startedGeneration === generation) cache.set(String(docId), xml);
      }
      // A later document or view switch wins over a slow response
      if (token !== request || getViewMode() !== 'tei') return;
      container.innerHTML = xml === null
        ? '<div class="loading text-body-secondary">No TEI for this document.</div>'
        : `<pre class="tei-source">${highlightTEI(xml)}</pre>`;
      container.scrollTop = 0;
      onRendered();
    },
  };
}
