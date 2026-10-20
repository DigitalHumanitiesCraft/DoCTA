import { escapeHTML as esc, escapeAttr as attr } from './utils.js';

export function searchKeys(text) {
  const lower = text.toLocaleLowerCase('de').replace(/ß/g, 'ss');
  const folded = lower.replace(/ä/g, 'ae').replace(/ö/g, 'oe').replace(/ü/g, 'ue');
  return [lower, folded].map(value => value.normalize('NFD').replace(/[\u0300-\u036f]/g, ''));
}

export function describeEntry(entry, entries) {
  const describe = item => [
    item.label,
    item.aliases.join(', '),
    (item.note || '').slice(0, 90) + (item.note?.length > 90 ? '…' : ''),
  ].filter(Boolean).join(', ');
  const description = describe(entry);
  const same = entries.filter(item => item.kind === entry.kind && describe(item) === description);
  if (same.length < 2) return description;
  // Identical labels retain distinct identities until an editor disambiguates them.
  let length = 8;
  while (same.some(item => item.id !== entry.id && item.id.slice(0, length) === entry.id.slice(0, length))) length += 1;
  return `${description} (${entry.id.slice(0, length)})`;
}

export function mentionLink(item, currentDoc, currentPageNr) {
  const url = `viewer.html?doc=${encodeURIComponent(item.docId)}&page=${encodeURIComponent(item.pageNr)}&mention=${encodeURIComponent(item.id)}`;
  const sameDoc = Number(item.docId) === Number(currentDoc?.docId);
  const samePage = sameDoc && item.pageNr === currentPageNr;
  const page = sameDoc && currentDoc.pages.find(value => value.pageNr === item.pageNr);
  const lines = page ? page.regions.flatMap(region => region.lines || []) : [];
  const ordinal = lines.findIndex(line => line.id === item.lineId) + 1;
  const source = sameDoc ? currentDoc.csvTitel || currentDoc.title : `Document ${item.docId}`;
  const label = [mentionQuote(item), source, `Page ${item.pageNr}`, ordinal ? `Line ${ordinal}` : ''].filter(Boolean).join(', ');
  const edit = samePage ? `<button type="button" class="review-btn" data-edit-mention="${attr(item.id)}">Edit</button>` : '';
  return `<div><a href="${attr(url)}">${esc(label)}</a>${item.stale ? '<span data-stale="true">, text changed, check</span>' : ''} ${edit}</div>`;
}

function formatTimestamp(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('en-GB', { dateStyle: 'short', timeStyle: 'short' });
}

function historyReading(record) {
  if (!record) return 'None';
  return [
    record.label || (record.quote && mentionQuote(record)),
    ...(record.aliases || []),
    record.when,
    record.notBefore ? `not before ${record.notBefore}` : '',
    record.notAfter ? `not after ${record.notAfter}` : '',
    record.uncertain ? 'uncertain date' : '',
    record.note,
  ].filter(Boolean).join(', ');
}

export function historyMarkup(events) {
  const actions = {
    'save-entry': 'Entry saved',
    'save-mention': 'Occurrence saved',
    'remove-mention': 'Occurrence removed',
  };
  return events.map(event => `<details>
    <summary>${esc(actions[event.action] || 'Change')}, ${esc(event.reviewer || event.actor || '')}, ${esc(formatTimestamp(event.timestamp || event.date || ''))}</summary>
    <dl><dt>Before</dt><dd>${esc(historyReading(event.before))}</dd>
    <dt>After</dt><dd>${esc(historyReading(event.after))}</dd></dl>
  </details>`).join('') || '<p>No changes yet.</p>';
}

/**
 * The line-bound spans of a mention in reading order. A mention across a line
 * break continues in further segments; the anchor fields of the mention are
 * its first, so an older mention is one segment unchanged.
 * @param {any} mention
 */
export function mentionSegments(mention) {
  const { lineId, start, end, quote, textDigest } = mention;
  return [{ lineId, start, end, quote, textDigest }, ...(mention.continuation || [])];
}

/** The quotation of a mention, its line breaks shown as a slash. */
export function mentionQuote(mention) {
  return mentionSegments(mention).map(segment => segment.quote).join(' / ');
}
