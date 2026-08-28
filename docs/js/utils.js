/**
 * DoCTA Prototype - Shared Utilities
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
  if (!date || !date.raw) return '–';
  return date.raw;
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
