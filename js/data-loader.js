/**
 * DoCTA Prototype - Data Loading Module
 * Fetches JSON data with IndexedDB caching.
 */

const DB_NAME = 'docta-cache';
const DB_VERSION = 1;
const STORE_NAME = 'data';
const DATA_VERSION = '2026-02-18'; // Bump when data files change

let dbPromise = null;

function openDB() {
  if (dbPromise) return dbPromise;
  dbPromise = new Promise((resolve) => {
    try {
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      // Timeout: fall back to fetch-only if IndexedDB doesn't respond
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
 * @param {string} path - Relative path to JSON file (e.g., 'data/persons.json')
 * @returns {Promise<any>}
 */
export async function loadJSON(path) {
  // Try cache first
  const cached = await getFromCache(path);
  if (cached) return cached;

  // Fetch
  const resp = await fetch(path);
  if (!resp.ok) throw new Error(`Failed to load ${path}: ${resp.status}`);
  const data = await resp.json();

  // Cache for next time
  putToCache(path, data);

  return data;
}

/**
 * Load multiple JSON files in parallel.
 * @param {Object<string, string>} pathMap - { key: path } pairs
 * @returns {Promise<Object<string, any>>}
 */
export async function loadAll(pathMap) {
  const entries = Object.entries(pathMap);
  const results = await Promise.all(
    entries.map(([, path]) => loadJSON(path))
  );
  const out = {};
  entries.forEach(([key], i) => {
    out[key] = results[i];
  });
  return out;
}

/**
 * Clear the data cache (useful for development).
 */
export async function clearCache() {
  const db = await openDB();
  if (!db) return;
  const tx = db.transaction(STORE_NAME, 'readwrite');
  tx.objectStore(STORE_NAME).clear();
}
