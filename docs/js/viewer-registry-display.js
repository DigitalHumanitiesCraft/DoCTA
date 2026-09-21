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
  const source = sameDoc ? currentDoc.csvTitel || currentDoc.title : `Dokument ${item.docId}`;
  const label = [item.quote, source, `Seite ${item.pageNr}`, ordinal ? `Zeile ${ordinal}` : ''].filter(Boolean).join(', ');
  const edit = samePage ? `<button type="button" class="review-btn" data-edit-mention="${attr(item.id)}">Bearbeiten</button>` : '';
  return `<div><a href="${attr(url)}">${esc(label)}</a>${item.stale ? ', Text geändert, prüfen' : ''} ${edit}</div>`;
}

function formatTimestamp(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('de-AT', { dateStyle: 'short', timeStyle: 'short' });
}

function historyReading(record) {
  if (!record) return 'Nicht vorhanden';
  return [
    record.label || record.quote,
    ...(record.aliases || []),
    record.when,
    record.notBefore ? `frühestens ${record.notBefore}` : '',
    record.notAfter ? `spätestens ${record.notAfter}` : '',
    record.uncertain ? 'unsichere Datierung' : '',
    record.note,
  ].filter(Boolean).join(', ');
}

export function historyMarkup(events) {
  const actions = {
    'save-entry': 'Eintrag gespeichert',
    'save-mention': 'Fundstelle gespeichert',
    'remove-mention': 'Fundstelle entfernt',
  };
  return events.map(event => `<details>
    <summary>${esc(actions[event.action] || 'Änderung')}, ${esc(event.reviewer || event.actor || '')}, ${esc(formatTimestamp(event.timestamp || event.date || ''))}</summary>
    <dl><dt>Vorher</dt><dd>${esc(historyReading(event.before))}</dd>
    <dt>Nachher</dt><dd>${esc(historyReading(event.after))}</dd></dl>
  </details>`).join('') || '<p>Noch keine Änderungen.</p>';
}
