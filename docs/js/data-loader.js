/**
 * DoCTA Prototype - Data Loading Module
 * Fetches JSON data with IndexedDB caching.
 */

const DB_NAME = 'docta-cache';
const DB_VERSION = 1;
const STORE_NAME = 'data';
// Cache key of the shipped data. Raise it whenever the shape of a file under
// data/ changes, otherwise a returning browser keeps serving the old shape from
// IndexedDB and the page renders against a contract that no longer holds.
const DATA_VERSION = '2026-08-28c';

let dbPromise = null;

function openDB() {
  if (dbPromise) return dbPromise;
  dbPromise = new Promise((resolve) => {
    try {
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      const timer = setTimeout(() => {
        console.warn('IndexedDB timeout, falling back to fetch-only');
        resolve(null);
      }, 1500);
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          db.createObjectStore(STORE_NAME);
        }
      };
      req.onsuccess = () => { clearTimeout(timer); resolve(req.result); };
      req.onerror = () => { clearTimeout(timer); resolve(null); };
      req.onblocked = () => { clearTimeout(timer); resolve(null); };
    } catch {
      resolve(null);
    }
  });
  return dbPromise;
}

async function getFromCache(key) {
  const db = await openDB();
  if (!db) return null;
  return new Promise((resolve) => {
    try {
      const tx = db.transaction(STORE_NAME, 'readonly');
      const store = tx.objectStore(STORE_NAME);
      const req = store.get(key);
      req.onsuccess = () => {
        const entry = req.result;
        if (entry && entry.version === DATA_VERSION) {
          resolve(entry.data);
        } else {
          resolve(null);
        }
      };
      req.onerror = () => resolve(null);
    } catch {
      resolve(null);
    }
  });
}

async function putToCache(key, data) {
  const db = await openDB();
  if (!db) return;
  try {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    store.put({ data, version: DATA_VERSION }, key);
  } catch {
    // Cache failure is not critical
  }
}

/**
 * Load a JSON data file with caching.
 * @param {string} path - Relative path to JSON file (e.g., 'data/sources.json')
 * @returns {Promise<any>}
 */
export async function loadJSON(path) {
  const cached = await getFromCache(path);
  if (cached) return cached;

  const resp = await fetch(path);
  if (!resp.ok) throw new Error(`Failed to load ${path}: ${resp.status}`);
  const data = await resp.json();

  putToCache(path, data);

  return data;
}

/** The one document that still has a hand-made demo extraction as a fallback. */
export const DEMO_DOC_ID = 11328300;

/**
 * @typedef {Object} EntityRecord
 * @property {string} text - form as read in the source
 * @property {string} normalized
 * @property {string} type - person, place, object, time
 * @property {number|null} pageNr
 * @property {string|null} lineId
 * @property {string} detail - role, category or ISO date, whichever the record carries
 * @property {string|null} date - ISO date where the extraction resolved one
 * @property {number|null} count
 * @property {Array<{pageNr: number, lineId: string|null}>} occurrences
 */

/**
 * Two extraction files coexist: the pipeline output under data/entities/ and the
 * older hand-made demo set. They differ in the provenance shape and in a few
 * per-record fields, so both are read into one form here. The demo file's
 * confidence self-assessment is dropped, it never enters the display.
 * @param {any} raw
 * @returns {{ docId: number, provenance: string, entities: EntityRecord[] }}
 */
function normalizeEntities(raw, docId) {
  const prov = raw.provenance;
  const provenance = (typeof prov === 'string' && prov) ||
    (prov && typeof prov.source === 'string' && prov.source) || 'llm';
  // The pipeline files name the extracting model; the demo file predates that
  // and stays null, which the display renders as a bare LLM label.
  const model = (prov && typeof prov === 'object' && prov.model) || null;
  const entities = (Array.isArray(raw.entities) ? raw.entities : []).map(e => ({
    text: e.text || '',
    normalized: e.normalized || '',
    type: e.type || '',
    pageNr: typeof e.pageNr === 'number' ? e.pageNr : null,
    lineId: e.lineId || null,
    detail: e.role || e.category || e.isoDate || '',
    date: e.isoDate || null,
    count: typeof e.count === 'number' ? e.count : null,
    // One record per occurrence in both files; the list shape carries a record
    // attested on several pages without a change here.
    occurrences: (Array.isArray(e.occurrences) ? e.occurrences : [e])
      .filter(o => o && typeof o.pageNr === 'number')
      .map(o => ({ pageNr: o.pageNr, lineId: o.lineId || null })),
  }));
  return { docId: Number(raw.docId ?? docId), provenance, model, entities };
}

/**
 * Entities of one document, or null when none were extracted for it.
 * A missing per-document file is the normal case, most documents have no
 * extraction yet; only the demo document falls back to the older demo file.
 * @param {number|string} docId
 * @returns {Promise<{ docId: number, provenance: string, entities: EntityRecord[] }|null>}
 */
export async function loadEntities(docId) {
  const id = Number(docId);
  // The register projection says which documents have an extraction, so the
  // normal case (none) costs no failing request; without the projection the
  // probe stays as a fallback.
  const summary = await loadJSON('data/pipeline/register_summary.json')
    .catch(() => null);
  const entry = summary?.documents?.find(d => d.docId === id);
  let raw = null;
  if (!entry || entry.has_entities) {
    raw = await loadJSON(`data/entities/${id}.json`).catch(() => null);
  }
  if (!raw && id === DEMO_DOC_ID) {
    raw = await loadJSON('data/demo/thaur_entities.json').catch(() => null);
  }
  return raw ? normalizeEntities(raw, id) : null;
}
