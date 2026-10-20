import { initNav, initBanner } from './app.js';
import { loadJSON } from './data-loader.js';
import { escapeHTML as esc, escapeAttr as attr, formatDate, formatCount as number, catLabel, vocabLabel } from './utils.js';
import { searchKeys } from './viewer-registry-display.js';
import { imageDocument } from './source-images.js';
import { PROVENANCE, PROGRESS } from './strings.js';

initNav('dashboard');
initBanner();

const search = document.getElementById('search-input');
const sort = document.getElementById('sort-select');
const availability = document.getElementById('filter-availability');
const list = document.getElementById('sources-list');
const count = document.getElementById('result-count');
let sources = [];
let category = '';

function extentMarkup(source) {
  const parts = [];
  const images = source.digital_images || 0;
  if (images) parts.push(`<span>${number(images)} ${images === 1 ? 'digitised image' : 'digitised images'}</span>`);
  const extent = source.catalogue_extent;
  if (extent?.value != null) {
    const unit = vocabLabel('extentUnit', extent.unit || 'unbekannt');
    parts.push(`<span>Catalogue extent ${number(extent.value)} ${esc(unit)}</span>`);
  }
  return parts.join('');
}

function provenanceMarkup(item) {
  const parts = [];
  const inventariaDocuments = item.documents.filter(doc => doc.summary?.transcription_by === 'Inventaria');
  const inventaria = inventariaDocuments[0];
  if (inventaria) {
    let url = 'https://www.inventaria.at/';
    try {
      const candidate = new URL(inventaria.summary.edition_url);
      if (['https:', 'http:'].includes(candidate.protocol)) url = candidate.href;
    } catch { /* Missing edition links use the project's public homepage. */ }
    const corrected = inventariaDocuments.every(doc => doc.summary.pages_total > 0 && doc.summary.done_pages >= doc.summary.pages_total);
    const partlyCorrected = inventariaDocuments.some(doc => doc.summary.done_pages > 0);
    const correction = corrected ? ', corrected' : partlyCorrected ? ', partly corrected' : '';
    const state = corrected ? 'full' : partlyCorrected ? 'partial' : 'none';
    parts.push(`<a href="${attr(url)}" target="_blank" rel="noopener" data-correction="${state}">Transcription by Inventaria${correction}</a>`);
  }
  if (item.documents.some(doc => doc.summary?.transcription_source === 'vlm')) {
    parts.push(`<span data-provenance="machine-unrevised">${esc(PROVENANCE.sourceListVlm)}</span>`);
  } else if (item.hasText && !inventaria) {
    parts.push('<span>Transcription from Transkribus</span>');
  }
  const corrected = item.documents.reduce((sum, doc) =>
    sum + (doc.summary?.verification?.gesichtet || 0) + (doc.summary?.verification?.abgenommen || 0), 0);
  if (corrected) parts.push(`<span data-progress="corrected">${esc(PROGRESS.overview(corrected))}</span>`);
  if (!item.hasText) {
    const firstImage = item.documents.find(doc => doc.image);
    const text = firstImage
      ? firstImage.collection.nrOfPages > 1 ? 'First image available' : 'Digitised image'
      : item.hasImages ? 'Digitised' : 'Catalogue record';
    parts.push(`<span>${text}</span>`);
  }
  return parts.join('');
}

function rowMarkup(item) {
  const source = item.source;
  const target = item.documents.find(doc => doc.hasText) || item.documents.find(doc => doc.image);
  const title = target
    ? `<a class="src-title" href="viewer.html?doc=${encodeURIComponent(target.id)}">${esc(source.titel)}</a>`
    : `<span class="src-title">${esc(source.titel)}</span>`;
  const thumbnail = item.documents.map(doc => doc.summary?.thumb || doc.image?.pages[0]?.iiif).find(Boolean);
  const image = thumbnail
    ? `<img class="src-thumb" src="${attr(thumbnail.replace('/full/max/', '/full/,120/'))}" alt="" loading="lazy" decoding="async">`
    : '<span class="src-thumb src-thumb--empty" aria-hidden="true"></span>';
  return `<li class="src-row" data-availability="${item.availability}">
    ${image}
    <div class="src-main">
      ${title}
      <div class="src-meta"><span class="src-sig">${esc(source.signatur)}</span><span class="src-date">${esc(formatDate(source.datierung))}</span>${extentMarkup(source)}</div>
      <div class="src-provenance">${provenanceMarkup(item)}</div>
    </div>
    <span class="src-cat">${esc(catLabel(source.kategorie))}</span>
  </li>`;
}

function compareSources(left, right) {
  const a = left.source;
  const b = right.source;
  let order = 0;
  if (sort.value === 'datierung') order = (a.datierung?.start ?? Infinity) - (b.datierung?.start ?? Infinity);
  else if (sort.value === 'images') order = (b.digital_images || 0) - (a.digital_images || 0);
  else order = a[sort.value].localeCompare(b[sort.value], 'de', { numeric: true });
  return order || a.signatur.localeCompare(b.signatur, 'de', { numeric: true });
}

function update() {
  const query = searchKeys(search.value.trim());
  const filtered = sources.filter(item => (!category || item.source.kategorie === category)
    && (!availability.value || item.availability === availability.value)
    && query.some(key => item.search.some(value => value.includes(key)))).sort(compareSources);
  const active = search.value.trim() || category || availability.value;
  count.textContent = active ? `${number(filtered.length)} ${filtered.length === 1 ? 'source found' : 'sources found'}` : '';
  list.innerHTML = filtered.map(rowMarkup).join('') || '<li class="src-empty">No sources found.</li>';
  const url = new URL(location.href);
  for (const [name, value] of [['q', search.value], ['category', category], ['availability', availability.value], ['sort', sort.value === 'signatur' ? '' : sort.value]]) {
    if (value) url.searchParams.set(name, value);
    else url.searchParams.delete(name);
  }
  window.history.replaceState(null, '', url);
}

function renderCategories() {
  const categories = [...new Set(sources.map(item => item.source.kategorie))].sort((a, b) => catLabel(a).localeCompare(catLabel(b), 'en'));
  const choices = [{ value: '', label: 'All source types' }, ...categories.map(value => ({ value, label: catLabel(value) }))];
  document.getElementById('category-chips').innerHTML = choices.map(choice =>
    `<button type="button" class="chip" data-kat="${attr(choice.value)}" aria-pressed="${choice.value === category}">${esc(choice.label)}</button>`).join('');
}

document.querySelector('.sources-filters').addEventListener('submit', event => event.preventDefault());
search.addEventListener('input', update);
sort.addEventListener('change', update);
availability.addEventListener('change', update);
document.getElementById('category-chips').addEventListener('click', event => {
  const button = event.target.closest('[data-kat]');
  if (!button) return;
  category = button.dataset.kat;
  for (const control of document.querySelectorAll('#category-chips button')) {
    control.setAttribute('aria-pressed', String(control.dataset.kat === category));
  }
  update();
});

async function initialize() {
  try {
    const [catalogue, register, collection] = await Promise.all([
      loadJSON('data/sources.json'),
      loadJSON('data/pipeline/register_summary.json').catch(() => ({ documents: [] })),
      loadJSON('data/transkribus_collection.json').catch(() => []),
    ]);
    const summaries = new Map(register.documents.map(doc => [Number(doc.docId), doc]));
    const images = new Map(collection.map(doc => [Number(doc.docId), doc]));
    sources = catalogue.map(source => {
      const documents = (source.transkribus_docs || []).map(doc => {
        const id = Number(doc.doc_id);
        const summary = summaries.get(id);
        const collection = images.get(id);
        return {
          id, summary, collection,
          image: collection ? imageDocument(collection) : null,
          // VLM projections carry text even when the legacy summary count is zero.
          hasText: !!(doc.has_text || summary?.pages_with_text || summary?.transcription_source === 'vlm' || summary?.effective_transcription),
        };
      });
      const hasText = documents.some(doc => doc.hasText);
      const hasImages = !!source.digital_images || documents.some(doc => doc.image || doc.summary?.thumb);
      return {
        source, documents, hasText, hasImages,
        availability: hasText ? 'text' : hasImages ? 'images' : 'catalogue',
        search: searchKeys([source.signatur, source.titel, source.datierung?.raw].join(' ')),
      };
    });
    const params = new URLSearchParams(location.search);
    search.value = params.get('q') || '';
    category = sources.some(item => item.source.kategorie === params.get('category')) ? params.get('category') : '';
    availability.value = ['', 'text', 'images', 'catalogue'].includes(params.get('availability')) ? params.get('availability') : '';
    sort.value = ['signatur', 'titel', 'datierung', 'images'].includes(params.get('sort')) ? params.get('sort') : 'signatur';
    renderCategories();
    update();
  } catch (error) {
    list.replaceChildren();
    const message = document.createElement('li');
    message.className = 'src-empty';
    message.textContent = `Sources could not be loaded. ${error.message}`;
    list.append(message);
  }
}

initialize();
