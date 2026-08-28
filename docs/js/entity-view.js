/**
 * DoCTA - shared building blocks of the entity views.
 *
 * The viewer, the network and the register state the same three things about an
 * entity record: which document a form was read in, how to get back to that
 * page, and that a model produced the record with no scholarly verification
 * behind it. The markup for those lives here once, so the views cannot drift.
 */

import { escapeHTML, escapeAttr, ICON_AI, ICON_UNVERIFIED } from './utils.js';

/** Short name of a document, the part in front of the shelfmark. */
export function shortDoc(label) {
  return String(label || '').split(',')[0].trim();
}

/**
 * Index over the document records of the aggregated graph. The label is what a
 * card, a list or a select shows; an id the graph does not carry keeps a name.
 * @param {Array<any>} docs - the `docta:Document` records
 * @returns {{ byId: Map<number, any>, label: (id: number|string) => string }}
 */
export function documentIndex(docs) {
  const byId = new Map(docs.map(d => [Number(d.transkribusDocId), d]));
  return { byId, label: id => byId.get(Number(id))?.label || `Document ${id}` };
}

/** Deep link into the viewer, addressed by document and page number. */
export function viewerHref(docId, page) {
  return `viewer.html?doc=${encodeURIComponent(docId)}&page=${encodeURIComponent(page)}`;
}

/**
 * One link into the viewer. The label is markup, because the callers bind the
 * page number to the "p." with a non-breaking space.
 * @param {string} href
 * @param {string} title
 * @param {string} labelHTML - already escaped
 */
export function attestationLink(href, title, labelHTML) {
  return `<a class="exp-attest__link" href="${escapeAttr(href)}" ` +
    `title="${escapeAttr(title)}">${labelHTML}</a>`;
}

/**
 * The attestations of one entity, each a link into the viewer at the page the
 * form was read on. The line and the attested spelling are named once per
 * entry: as visible meta text where the list has room for it, in the link title
 * where it has not.
 * @param {Array<{docId: number|string, page: number|string, line?: string, form?: string}>} atts
 * @param {(id: number|string) => string} docLabel
 * @param {{ className: string, detail: 'meta'|'title' }} opts
 */
export function attestationList(atts, docLabel, { className, detail }) {
  return `<ul class="${className}">` + atts.map(a => {
    const extra = detail === 'title'
      ? (a.line ? `, line ${a.line}` : '') + (a.form ? `, “${a.form}”` : '')
      : '';
    const link = attestationLink(
      viewerHref(a.docId, a.page),
      `Open ${docLabel(a.docId)}, page ${a.page} in the viewer${extra}`,
      `${escapeHTML(shortDoc(docLabel(a.docId)))} p.&nbsp;${escapeHTML(String(a.page))}`);
    const meta = detail === 'meta'
      ? [a.line ? `line ${a.line}` : '', a.form ? `“${a.form}”` : ''].filter(Boolean).join(' · ')
      : '';
    return `<li>${link}` +
      (meta ? ` <span class="net-att__meta">${escapeHTML(meta)}</span>` : '') + '</li>';
  }).join('') + '</ul>';
}

/**
 * Provenance of an entity layer as two quiet chips, the model that produced it
 * and the missing scholarly verification. A layer whose model is not recorded
 * carries the verification chip alone.
 * @param {string} model - empty where the extraction records no model
 */
export function provenanceBadges(model) {
  return (model
    ? `<span class="ent-key ent-key--prov">${ICON_AI}${escapeHTML(model)}</span>`
    : '') +
    `<span class="ent-key ent-key--prov">${ICON_UNVERIFIED}not verified</span>`;
}
