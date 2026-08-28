/**
 * DoCTA - Shared Utilities
 */

/**
 * Get URL search parameters as an object.
 * @returns {Object<string, string>}
 */
export function getParams() {
  const params = {};
  new URLSearchParams(window.location.search).forEach((v, k) => {
    params[k] = v;
  });
  return params;
}

/**
 * Update URL search parameters without reloading.
 * @param {Object<string, string>} params
 */
export function setParams(params) {
  const url = new URL(window.location);
  Object.entries(params).forEach(([k, v]) => {
    if (v == null || v === '') {
      url.searchParams.delete(k);
    } else {
      url.searchParams.set(k, v);
    }
  });
  history.replaceState(null, '', url);
}

/**
 * Debounce a function.
 * @param {Function} fn
 * @param {number} ms
 * @returns {Function}
 */
export function debounce(fn, ms = 250) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}

/**
 * Simple HTML escaping.
 * @param {string} str
 * @returns {string}
 */
export function escapeHTML(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

/**
 * Escape a string for use inside a double-quoted HTML attribute.
 * escapeHTML alone leaves quotes intact and would break out of the attribute.
 * @param {string} str
 * @returns {string}
 */
export function escapeAttr(str) {
  return escapeHTML(str).replace(/"/g, '&quot;');
}

/**
 * Format a date object from sources.json.
 * @param {{ raw: string, start: number|null, end: number|null, circa: boolean }} date
 * @returns {string}
 */
export function formatDate(date) {
  if (!date || (!date.raw && date.start == null)) return '–';
  const circa = date.circa ? 'c. ' : '';
  // A span of years reads as a range with an en dash; a single date keeps the
  // archival day-level form of the finding aid (e.g. 1471.09.25).
  if (date.start != null && date.end != null && date.start !== date.end) {
    return `${circa}${date.start}–${date.end}`;
  }
  return circa + (date.raw || String(date.start));
}

/**
 * Archival titles and shelfmarks stay in their original German; the closed
 * category vocabulary of sources.json gets an English display label.
 */
const CATEGORY_EN = {
  'Anderes': 'Other',
  'Burgeninventar': 'Castle inventory',
  'Hof- und Speiseordnungen': 'Court and table ordinances',
  'Kircheninventar': 'Church inventory',
  'Kopialbuch': 'Copybook',
  'Landtagsakten': 'Diet records',
  'Literatur': 'Literature',
  'Personeninventar': 'Personal inventory',
  'Rechnungen': 'Accounts',
  'Repertorium': 'Repertory',
};

/**
 * English label for a source category, the source term where none is known.
 * @param {string} kategorie
 * @returns {string}
 */
export function catLabel(kategorie) {
  return CATEGORY_EN[kategorie] || kategorie;
}

/**
 * Counts in the interface read in the page language, not the reader's locale.
 * @param {number|null|undefined} n
 * @returns {string}
 */
export function formatCount(n) {
  return n == null ? '–' : n.toLocaleString('en-GB');
}

/**
 * localStorage may be unavailable (private mode, blocked site data) or full; a
 * view that uses it stays functional and simply carries no stored state.
 * @param {string} key
 * @returns {string|null}
 */
export function lsGet(key) {
  try { return window.localStorage.getItem(key); } catch { return null; }
}

/**
 * @param {string} key
 * @param {string} value
 * @returns {boolean} false when the value could not be stored
 */
export function lsSet(key, value) {
  try { window.localStorage.setItem(key, value); return true; } catch { return false; }
}

/* Shared provenance icons: a sparkle for a model product, a dashed circle for
   missing scholarly verification. One definition, and the badge that pairs them
   is assembled once in entity-view.js, so neither the iconography nor its
   markup can drift between the pages that state machine provenance. */
export const ICON_AI =
  '<svg class="meta-ico" viewBox="0 0 16 16" fill="currentColor"' +
  ' aria-hidden="true"><path d="M8 1.8 9.3 5.2 12.7 6.5 9.3 7.8 8 11.2' +
  ' 6.7 7.8 3.3 6.5 6.7 5.2z"/><path d="m12.9 10.2.7 1.9 1.9.7-1.9.7' +
  '-.7 1.9-.7-1.9-1.9-.7 1.9-.7z"/></svg>';
export const ICON_UNVERIFIED =
  '<svg class="meta-ico" viewBox="0 0 16 16" fill="none"' +
  ' stroke="currentColor" stroke-width="1.5" aria-hidden="true">' +
  '<circle cx="8" cy="8" r="6.2" stroke-dasharray="2.6 2.1"/></svg>';
