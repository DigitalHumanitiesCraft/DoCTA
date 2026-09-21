import { initNav, initBanner } from './app.js';
import { createLocalEditor } from './viewer-local.js';
import { escapeHTML as esc, escapeAttr as attr } from './utils.js';
import { searchKeys, describeEntry, historyMarkup } from './viewer-registry-display.js';

initNav('register');
initBanner();

const local = createLocalEditor();
const kinds = { person: 'Person', place: 'Ort', term: 'Begriff' };
const status = document.getElementById('register-status');
const search = document.getElementById('register-search');
const kind = document.getElementById('register-kind');
const results = document.getElementById('register-results');
const detail = document.getElementById('register-detail');
let registry = null;
let indexed = [];
let selectedId = null;
let documents = new Map();

function entryUrl(id, resetFilters = false) {
  const url = new URL(location.href);
  url.searchParams.set('entry', id);
  if (resetFilters) {
    url.searchParams.delete('q');
    url.searchParams.delete('kind');
  }
  return url.pathname + url.search;
}

function attestationMarkup(mention) {
  const source = documents.get(String(mention.docId));
  const label = [mention.quote, source?.title || `Dokument ${mention.docId}`, source?.shelfmark, `Seite ${mention.pageNr}`].filter(Boolean).join(', ');
  const url = `viewer.html?doc=${encodeURIComponent(mention.docId)}&page=${encodeURIComponent(mention.pageNr)}&mention=${encodeURIComponent(mention.id)}`;
  return `<li><a href="${attr(url)}">${esc(label)}</a>${mention.stale ? '<span class="register-stale">Quellentext geändert, Fundstelle prüfen.</span>' : ''}</li>`;
}

function renderDetail(entry) {
  detail.hidden = !entry;
  if (!entry) {
    detail.replaceChildren();
    return;
  }
  const parent = registry.entries.find(value => value.id === entry.broaderId);
  const mentions = registry.mentions.filter(value => value.entryId === entry.id);
  const mentionIds = new Set(mentions.map(value => value.id));
  const events = registry.history.filter(event => [event.before, event.after].some(record =>
    record && (record.id === entry.id || record.entryId === entry.id || mentionIds.has(record.id))));
  const fields = [
    entry.aliases.length ? `<div><dt>Weitere Schreibweisen</dt><dd>${esc(entry.aliases.join(', '))}</dd></div>` : '',
    entry.note ? `<div><dt>Notiz</dt><dd>${esc(entry.note)}</dd></div>` : '',
    parent ? `<div><dt>Oberbegriff</dt><dd><a href="${attr(entryUrl(parent.id, true))}" data-entry-id="${attr(parent.id)}">${esc(parent.label)}</a></dd></div>` : '',
  ].join('');
  detail.innerHTML = `
    <h2 id="register-entry-title" tabindex="-1">${esc(entry.label)}</h2>
    <p class="register-kind">${kinds[entry.kind]}</p>
    ${fields ? `<dl>${fields}</dl>` : ''}
    <h3>Fundstellen</h3>
    ${mentions.length ? `<ul class="register-attestations" role="list">${mentions.map(attestationMarkup).join('')}</ul>` : '<p>Keine Fundstellen zugeordnet.</p>'}
    <details><summary>Kennung</summary><code>${esc(entry.id)}</code></details>
    ${events.length ? `<details id="register-history"><summary>Änderungsverlauf</summary>${historyMarkup(events)}</details>` : ''}`;
}

function updateUrl({ push = false } = {}) {
  const url = new URL(location.href);
  for (const [name, value] of [['q', search.value], ['kind', kind.value], ['entry', selectedId]]) {
    if (value) url.searchParams.set(name, value);
    else url.searchParams.delete(name);
  }
  window.history[push ? 'pushState' : 'replaceState'](null, '', url);
}

function render({ preferredId = selectedId, writeUrl = true } = {}) {
  const keys = searchKeys(search.value.trim());
  const matches = indexed.filter(item => (!kind.value || item.entry.kind === kind.value)
    && keys.some(query => item.keys.some(value => value.includes(query))));
  const selected = matches.find(item => item.entry.id === preferredId)?.entry || matches[0]?.entry;
  selectedId = selected?.id || null;
  if (writeUrl) updateUrl();
  results.innerHTML = matches.map(({ entry }) => `<li>
    <a href="${attr(entryUrl(entry.id))}" data-entry-id="${attr(entry.id)}"${entry.id === selectedId ? ' aria-current="true"' : ''}>
      ${esc(describeEntry(entry, registry.entries))}<span class="register-kind">${kinds[entry.kind]}</span>
    </a></li>`).join('');
  status.textContent = matches.length ? '' : registry.entries.length ? 'Keine passenden Einträge.' : 'Noch keine Registereinträge angelegt.';
  renderDetail(selected);
}

function readUrl() {
  const params = new URLSearchParams(location.search);
  search.value = params.get('q') || '';
  kind.value = Object.hasOwn(kinds, params.get('kind')) ? params.get('kind') : '';
  selectedId = params.get('entry');
}

document.getElementById('register-filters').addEventListener('submit', event => event.preventDefault());
search.addEventListener('input', () => render());
kind.addEventListener('change', () => render());
document.getElementById('register-browser').addEventListener('click', event => {
  const link = event.target.closest('[data-entry-id]');
  if (!link || event.button || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
  event.preventDefault();
  selectedId = link.dataset.entryId;
  if (!results.contains(link)) {
    search.value = '';
    kind.value = '';
  }
  updateUrl({ push: true });
  render();
  document.getElementById('register-entry-title')?.focus();
});
window.addEventListener('popstate', () => {
  if (!registry) return;
  readUrl();
  render({ writeUrl: false });
});
document.getElementById('register-export').addEventListener('click', () => {
  if (!registry) return;
  const url = URL.createObjectURL(new Blob([JSON.stringify(registry, null, 2)], { type: 'application/json' }));
  const link = document.createElement('a');
  link.href = url;
  link.download = 'docta-editorial-registry.json';
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});

async function initialize() {
  await local.init();
  if (!local.enabled) {
    status.textContent = 'Der editorische Index ist im lokalen Arbeitseditor verfügbar.';
    return;
  }
  try {
    const [state, summary] = await Promise.allSettled([
      local.registry(),
      fetch('data/pipeline/register_summary.json').then(response => response.ok ? response.json() : null),
    ]);
    if (state.status === 'rejected') throw state.reason;
    registry = state.value;
    if (summary.status === 'fulfilled') documents = new Map((summary.value?.documents || []).map(value => [String(value.docId), value]));
    indexed = registry.entries.filter(entry => Object.hasOwn(kinds, entry.kind))
      .map(entry => ({ entry, keys: searchKeys([entry.label, ...entry.aliases, entry.note].join(' ')) }))
      .sort((a, b) => a.entry.label.localeCompare(b.entry.label, 'de') || a.entry.id.localeCompare(b.entry.id));
    const unresolved = registry.mentions.filter(mention => !mention.entryId && Object.hasOwn(kinds, mention.kind));
    const unassigned = document.getElementById('register-unassigned');
    unassigned.hidden = !unresolved.length;
    unassigned.querySelector('ul').innerHTML = unresolved.map(attestationMarkup).join('');
    document.getElementById('register-browser').hidden = false;
    document.getElementById('register-export').hidden = false;
    readUrl();
    render();
  } catch (error) {
    status.textContent = `Index nicht geladen. ${error.message}`;
  }
}

initialize();
