# TECH: Architecture, Libraries, Project Structure

## Constraint

The site is static and served by GitHub Pages from `docs/` on `main`. It uses vanilla JavaScript with ES6 modules, no build process and no package manager at runtime. External dependencies are vendored in `docs/lib/`.

### Vendored versions (from the file headers in `docs/lib/`)

| Library | Vendored | File |
|---------|----------|------|
| Bootstrap | 5.3.3 | `lib/bootstrap.min.css`, `lib/bootstrap.bundle.min.js` |
| Cytoscape.js | 3.30.4 | `lib/cytoscape.esm.min.mjs` |
| OpenSeadragon | 4.1.1 | `lib/openseadragon.min.js` |
| marked | 15.0.12 | `lib/marked.min.js` |

The pins lag behind upstream. That is deliberate. The versions are frozen since they worked, and without a package manager an upgrade means editing files by hand and retesting every page.

## Site pages

| Page | Purpose |
|------|---------|
| `index.html` | Home. The source catalogue with search, filters and a per-source stage indicator for facsimile, HTR text, TEI and edited state |
| `viewer.html` | Source explorer. OpenSeadragon facsimile beside the transcription, with the extracted entities of the demo source, plus a reading mode over the whole document text |
| `exploration.html` | The relation network extracted by an LLM from a Transkribus working transcription |
| `benchmark.html` | Results of the versioned prompt benchmark, read from `data/benchmark/` |
| `knowledge.html` | Knowledge vault, rendering these Markdown documents |
| `about.html` | About the project, data sources, imprint |

Navigation is generated centrally in `js/app.js`, so a page added to the site is registered in one place.

## Network visualisation: Cytoscape.js

### Why Cytoscape.js

| Library | Renderer | Node ceiling | ESM support | Graph algorithms |
|---------|----------|--------------|-------------|------------------|
| **Cytoscape.js** | Canvas, WebGL from 3.31 | High, with WebGL | Yes, ESM build | Yes (BFS, PageRank, betweenness, communities) |
| Sigma.js v3 | WebGL native | High | Problematic without npm | Through graphology |
| vis.js | Canvas | Low | UMD build | No |
| D3.js | SVG or Canvas | Low with SVG | Yes | No |

Loading it:

```html
<script type="module">
  import cytoscape from './lib/cytoscape.esm.min.mjs';
</script>
```

### Scale and the two graph problems

The current graph on `exploration.html` is the extracted relation network of a single source. It is small, so `cose` over the whole set renders immediately and no progressive disclosure is needed.

The SiCProD court network is a different problem, with several thousand persons and tens of thousands of relations. The prototype-era network page solved it by progressive disclosure, an ego network around Sigmund as the entry point with a bounded full view behind a toggle. That page was removed in the August 2026 consolidation; the design reasoning is preserved in DESIGN.md and applies again when the court network returns as a view over edited text.

Two performance measures were planned in the prototype phase and never became necessary. Labels shown only on hover and above a zoom threshold stayed unnecessary at the node counts actually displayed. Layout pre-computation exists as `scripts/compute_layout.py`, which writes `data/network.json`; no page loads that file, because Cytoscape computes a layout for these node counts fast enough in the browser and a live layout allows switching between layout algorithms. The WebGL renderer is unavailable to the vendored 3.30.4 in any case, and Canvas suffices.

## Document viewer: OpenSeadragon

Zero dependencies, IIIF support, deep zoom.

```html
<script src="lib/openseadragon.min.js"></script>
```

Images come from Transkribus IIIF URLs, loaded as a plain image source (`viewer.open({ type: 'image', url })`) rather than as a tiled IIIF service. That is enough for single pages and saves a request round trip per tile.

The transcription panel is separate HTML beside the viewer. A synchronisation over viewport events, so that a line in the text highlights its line box in the image, was planned and is not implemented; image and text sit side by side without pointing at each other. The line coordinates from the PAGE XML are ready in `data/transcriptions/`, the overlay is missing.

## Search: custom vanilla JavaScript

No library is needed. `Array.filter()` with `Map` and `Set` handles the data volumes involved. The logic sits inline in the page that uses it, as plain functions over a small filter-state object, rather than as a class.

The source search on the home page filters over category, availability tier and free text. A faceted search across the SiCProD entities ran in the prototype phase with facets for entity type, gender, function and place type. Institution was never usable as a facet, because almost all institution records carry no type (see DATA.md), and a period slider fails on the heterogeneous and often missing datings.

## Data loading

Every page loads only the JSON files it needs. `js/data-loader.js` exports `loadJSON(path)` and `loadAll(pathMap)`, caching per file in IndexedDB and versioning the cache through the constant `DATA_VERSION`.

```javascript
export async function loadJSON(path) {
  const cached = await getFromCache(path);
  if (cached) return cached;
  const resp = await fetch(path);
  if (!resp.ok) throw new Error(`Failed to load ${path}: ${resp.status}`);
  const data = await resp.json();
  putToCache(path, data);
  return data;
}
```

IndexedDB is optional. If the database does not open within one and a half seconds, or fails outright, the module falls back silently to plain `fetch()`.

## Project structure

```
DoCTA/
├── docs/                   Published site, GitHub Pages serves this folder on main
│   ├── *.html              index, viewer, exploration, benchmark, knowledge, about
│   ├── css/styles.css      Design tokens as CSS custom properties
│   ├── js/                 ES6 modules shared by several pages
│   │   ├── app.js          Navigation, banner, footer
│   │   ├── benchmark.js    Benchmark tables from data/benchmark/summary.json
│   │   ├── data-loader.js  Fetch JSON, IndexedDB cache
│   │   └── utils.js        Formatting, sorting, escaping
│   ├── data/               Pre-processed JSON, git-tracked
│   │   ├── benchmark/      Published export of the prompt benchmark
│   │   ├── demo/           Entity and relation extraction on Thaur A 49.1
│   │   └── transcriptions/ Inventory transcriptions from Transkribus PAGE XML
│   ├── lib/                Vendored dependencies
│   └── knowledge/          This knowledge base
├── evaluation/
│   ├── benchmark/          Versioned prompt benchmark: pages, prompts, runs, metrics
│   └── pilot/              The benchmark prompts on continuous, uncurated material
├── experiments/
│   └── transcription-test/ The frozen first VLM transcription test of 26.08.2026
├── pipeline/               Page register: per-page content class, empty evidence,
│                           verification status, provenance-tagged transcription runs
├── scripts/                Python build-time scripts
└── tests/                  Smoke and interaction tests against the published site
```

The module layout departs from the original plan. One module per page was planned (`network-view.js`, `search-engine.js`, `source-table.js`, `document-viewer.js`, `pipeline-demo.js`). What was built is different. Page-specific JavaScript sits as `<script type="module">` directly in its HTML file, and `js/` holds only what several pages share. Without a build process each module costs an additional HTTP request, and the code of one page is used by no other. Reading one file is enough to understand one page.

The planned folder `images/` for sample facsimiles does not exist either. Facsimiles load at runtime from the Transkribus IIIF URLs, and no image material lives in the repository.

## Design system

Consistent with coOCR/HTR, an external reference project developed by DHCraft.

| Aspect | Implementation |
|--------|----------------|
| Colour scheme | Warm, light |
| Review status | Green for secure, amber for worth checking, red for problematic, bound to rules or to a scholarly decision |
| HTML | Semantic, with ARIA labels |
| Layout | Desktop first, responsive, without a mobile focus |
| Typography | Monospace for source text, sans-serif for the interface |

## Build-time scripts (Python)

| Script | Input | Output |
|--------|-------|--------|
| `fetch_sicprod.py` | SiCProD API | `data/persons.json`, `data/places.json`, `data/institutions.json`, `data/functions.json`, `data/relations.json` |
| `transform_sources.py` | Source catalogue CSV plus `data/source_mapping.json` | `data/sources.json` |
| `fetch_transcriptions.py` | Transkribus API over OAuth2 | `data/transcriptions/{id}.json` |
| `map_sources.py` | Transkribus titles plus catalogue shelfmarks | `data/source_mapping.json` |
| `build_stats.py` | The exported JSON files | `data/stats.json`, the single source of truth for the figures the site shows |

Exploration and helper scripts whose output no page loads: `compute_layout.py` writing `data/network.json`, `explore_transkribus.py`, `explore_transkribus_deep.py`, `transkribus_status.py` writing `data/transkribus_collection.json` and `data/transkribus_status.json`, and `fetch_remaining.py`. They document how the data situation was established and stay in the repository for that reason.

## Tests

`tests/` holds a smoke test and an interaction test driven by Playwright. Both start a local server that deliberately serves the repository under the subpath `/DoCTA/`, exactly as GitHub Pages does, so that path errors invisible at a domain root become visible. The smoke test loads every page and reports console errors, uncaught exceptions, failed network requests, HTTP status codes from 400 upwards and internal links that resolve to no file. The interaction test exercises the central controls of each page. Playwright is not a project dependency; the site itself has no Node dependencies. Their README states how to install and run them.

## coOCR/HTR as a reference

A browser-based VLM transcription workbench. It is an **external project** and no part of DoCTA.

| | |
|---|---|
| Demo | https://dhcraft.org/co-ocr-htr |
| Repository | https://github.com/DigitalHumanitiesCraft/co-ocr-htr |
| Stack | Vanilla JavaScript with ES6 modules, OpenSeadragon, no build process |

DoCTA adopts the visual design language of coOCR/HTR. Its earlier categorical confidence display is carried on here as a rule-bound review status. The code is not adopted.
