/**
 * DoCTA viewer - the transcription panel.
 *
 * Everything here builds markup from loaded data into a container element: the
 * page synopsis, the reading text over the whole document, the TEI source and
 * the entity marks laid over the line text. The facsimile, the line overlay,
 * the pager and the URL state stay with the page that owns them.
 */

import { escapeHTML, escapeAttr, ICON_AI, ICON_UNVERIFIED } from './utils.js';

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

// === Entity marks in the transcription ===

const ENTITY_TYPE_LABELS = { person: 'Person', place: 'Ort',
                             object: 'Gegenstand', time: 'Zeitangabe' };

/**
 * Objects are left unmarked, they are the bulk of an inventory and marking them
 * would colour whole pages.

 * @param {any} data - the loaded extraction, or null
 * @returns {{ byId: Map<string, any> }|null}
 */
export function buildEntityIndex(data) {
  if (!data?.entities?.length) return null;
  const byId = new Map(data.entities.filter(ent => ent.type !== 'object' && ent.text.trim()).map(ent => [ent.id, ent]));
  return byId.size ? { byId } : null;
}
function entityTipText(ent, model) {
  const head = ent.normalized || ent.text;
  const date = ent.date ? ` (${ent.date})` : '';
  const type = ENTITY_TYPE_LABELS[ent.type] || ent.type;
  return `${head}${date}, ${type}. Automatischer Vorschlag von ${model}, fachlich ungeprüft.`;
}

// Anchors belong to a document's current page and line, never to a spelling globally.
export function markEntities(escapedText, index, model, context, editable = false) {
  if (!context) return escapedText;
  const { pageNr, lineId, text } = context;
  const spans = [];
  for (const ent of index.byId.values()) {
    if (ent.pageNr !== pageNr || ent.lineId !== lineId) continue;
    const start = text.indexOf(ent.text);
    // Ambiguous repeated readings require an explicit manual span.
    if (start < 0 || text.indexOf(ent.text, start + 1) !== -1) continue;
    spans.push({ start, end: start + ent.text.length, ent });
  }
  spans.sort((a, b) => a.start - b.start || b.end - a.end);
  let cursor = 0;
  let html = '';
  for (const { start, end, ent } of spans) {
    if (start < cursor) continue;
    html += escapeHTML(text.slice(cursor, start));
    html += `<span class="entity entity--${escapeAttr(ent.type)}" role="${editable ? 'button' : 'mark'}" tabindex="0" data-ent-key="${escapeAttr(ent.id)}" aria-label="${escapeAttr(entityTipText(ent, model))}">${escapeHTML(text.slice(start, end))}</span>`;
    cursor = end;
  }
  return html + escapeHTML(text.slice(cursor));
}
/**
 * Entity key for the doc-meta strip: one colour dot per type present, then the
 * provenance with the model named. Sits beside the category and provenance
 * chips, apart from the running text it explains.
 */
function entityLegend(index, model) {
  const present = new Set([...index.byId.values()].map(e => e.type));
  const chips = Object.keys(ENTITY_TYPE_LABELS)
    .filter(t => present.has(t))
    .map(t => `<span class="ent-key">` +
              `<span class="ent-key__dot ent-key__dot--${escapeAttr(t)}"></span>` +
              `${escapeHTML(ENTITY_TYPE_LABELS[t])}</span>`)
    .join('');
  // The leading label binds model and verification state to the entity
  // layer; without it they read as statements about the text layer, whose
  // own provenance chip sits in the doc-meta strip below.
  return `<span class="ent-key-group" title="Entity marks:` +
         ` ${escapeAttr(model)} extraction, not verified by a` +
         ` scholar"><span class="ent-key">Automatische Vorschläge</span>${chips}` +
         `<span class="ent-prov">${ICON_AI} ${escapeHTML(model)}</span>` +
         `<span class="ent-prov">${ICON_UNVERIFIED} Fachlich ungeprüft</span></span>`;
}

/** Inner markup of the floating tooltip of one entity mark. */
function entityTipHTML(ent, model) {
  const date = ent.date ? `, ${escapeHTML(ent.date)}` : '';
  const type = ENTITY_TYPE_LABELS[ent.type] || ent.type;
  return `<span class="ent-tip__head">${escapeHTML(ent.normalized || ent.text)}` +
    `${date}</span> <span>${escapeHTML(type)}</span>` +
    `<span class="ent-tip__prov">${ICON_AI} ${escapeHTML(model)}` +
    ` ${ICON_UNVERIFIED} Fachlich ungeprüfter Vorschlag</span>`;
}

/**
 * The entity layer of the loaded document: the index the line text is matched
 * against, the model that produced it, and the markup that states both. A
 * document without an extraction leaves the layer inactive, and every method
 * then renders as if no entity were known.
 */
export function createEntityLayer() {
  let index = null;
  let model = 'LLM';
  let editable = false;
  return {
    /** @param {any} data - the loaded extraction, or null */
    set(data, canEdit = false) {
      index = buildEntityIndex(data); editable = canEdit;
      model = (data && data.model) || 'LLM';
    },
    get active() { return index !== null; },
    /** Marks entities in already escaped line text. */
    markText: (escapedText, context) => (index ? markEntities(escapedText, index, model, context, editable) : escapedText),
    legendHTML: () => (index ? entityLegend(index, model) : ''),
    /** Tooltip markup for one entity key, or null where the key is unknown. */
    tipHTML(key) {
      const ent = index && index.byId.get(key);
      return ent ? entityTipHTML(ent, model) : null;
    },
  };
}

/**
 * The synopsis of one page: line number, line text, and the entity marks over
 * it. The container is replaced wholesale and scrolled back to the top.
 * @param {HTMLElement} container
 * @param {any} doc
 * @param {number} pageNr
 * @param {{ corrections: Map<string, any>, markText: (s: string) => string }} opts
 */
export function renderTranscription(container, doc, pageNr, { corrections, markText }) {
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
      // A stored correction replaces the text of its line; it is bound to the
      // original it was made against, so a changed export drops it silently
      const stored = line.id ? corrections.get(line.id) : null;
      const corr = stored && stored.original === line.text ? stored : null;
      let text = escapeHTML(corr ? corr.corrected : line.text);
      if (!corr) text = markText(text, { pageNr, lineId: line.id, text: line.text });
      const mark = corr ? ' transcription__line--corrected' : '';
      const title = corr ? ` title="${escapeAttr(`Original: ${line.text}`)}"` : '';
      html += `<div class="transcription__line${mark}${regionStart}"${lineAttr}${title}` +
              ` data-original="${escapeAttr(line.text)}">` +
              `<span class="transcription__line-nr">${lineNr}</span>` +
              `<span class="transcription__line-text">${text}</span></div>`;
    }
  }
  html += '</div>';
  container.innerHTML = html;
  container.scrollTop = 0;
}

/**
 * Reading mode: the whole document as one text, without line numbers.
 * @param {HTMLElement} container
 * @param {any} doc
 */
export function renderReading(container, doc) {
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
        const fol = folioLabel(l.text);
        if (fol) {
          out.push(`<div class="folio-mark">${escapeHTML(fol)}</div>`);
          return;
        }
        const cls = ['reading-line'];
        if (ri > 0 && li === 0) cls.push('reading-line--region-start');
        else if (/^item\b/i.test(l.text)) cls.push('reading-line--entry');
        out.push(`<div class="${cls.join(' ')}">${escapeHTML(l.text)}</div>`);
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

  return {
    /** @returns {string|null|undefined} undefined while nothing has been fetched */
    cached: (docId) => cache.get(String(docId)),
    invalidate: () => { request += 1; cache.clear(); },

    async render(docId) {
      const token = ++request;
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
          cache.set(String(docId), xml);
        } catch {
          xml = null;
          cache.set(String(docId), null);
        }
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
