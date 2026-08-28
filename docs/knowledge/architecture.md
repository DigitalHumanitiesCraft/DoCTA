---
title: Architecture
project:
  name: DoCTA
  repository: https://github.com/DigitalHumanitiesCraft/DoCTA
method:
  name: Promptotyping
  url: https://dhcraft.org/Promptotyping/
status: complete
language: en
version: "1.0"
created: 2026-02-18
updated: 2026-08-28
authors: [Christopher Pollin]
generated-with: Claude Code (Claude Fable 5)
template:
  name: Vorlage Architecture
  version: 0.4
  url: https://dhcraft.org/Promptotyping/promptotyping-document/architecture
  alias: https://dhcraft.org/Promptotyping/#promptotyping-document-architecture
related: [INDEX, specification, design, data]
---

# Architecture

## Constraint

The site is static and served by GitHub Pages from `docs/` on `main`. It uses vanilla JavaScript with ES6 modules, no build process and no package manager at runtime. External dependencies are vendored in `docs/lib/`.

### Vendored versions (from the file headers in `docs/lib/`)

| Library | Vendored | File |
|---------|----------|------|
| Bootstrap | 5.3.3 | `lib/bootstrap.min.css`, `lib/bootstrap.bundle.min.js` |
| D3 | 7.9.0 | `lib/d3.v7.min.js` |
| OpenSeadragon | 4.1.1 | `lib/openseadragon.min.js` |
| marked | 15.0.12 | `lib/marked.min.js` |

D3 comes from `https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js`, the single-file UMD dist build of the release, vendored on 2026-08-28 and licensed ISC. Cytoscape.js 3.30.4 was vendored until the same day, when the network view moved to D3 and `lib/cytoscape.esm.min.mjs` was deleted; no page loads it any more.

The pins lag behind upstream. That is deliberate. The versions are frozen since they worked, and without a package manager an upgrade means editing files by hand and retesting every page.

## Site pages

| Page | Purpose |
|------|---------|
| `index.html` | Home. The source catalogue with search, filters and a per-source stage indicator for facsimile, HTR text, TEI and edited state |
| `viewer.html` | Source explorer. OpenSeadragon facsimile beside the transcription, with the extracted entities of the demo source, plus a reading mode over the whole document text |
| `exploration.html` | Workbench over the extracted content layer, a D3 network over `data/graph.jsonld` and a sortable entity table per source |
| `benchmark.html` | Results of the versioned prompt benchmark, read from `data/benchmark/` |
| `about.html` | About the project, data sources, imprint |

Navigation is generated centrally in `js/app.js`, so a page added to the site is registered in one place. The knowledge base itself has no page on the site since 28.08.2026; it lives as Markdown under `docs/knowledge/` and addresses agents and repository readers, while the About page links to it on GitHub.

## Network visualisation: D3

### Why D3

The network view on `exploration.html` reads `data/graph.jsonld`, the aggregated graph over every document that carries an entity extraction. It draws entity and document nodes with two kinds of edge, attestation of an entity in a document and co-occurrence of two entities in one transcription line.

Cytoscape.js held this view until August 2026 and was replaced. The demo file it read was hand-made, and its default styling put a label on every edge, which made the canvas unreadable at a few dozen nodes. The requirement that replaced it is readability under a filter, so what the layout needs is direct control over force parameters, node shapes, label rules and hit areas. D3 gives that control in one force simulation with an SVG scene graph; the built-in graph algorithms of Cytoscape were never used.

| Library | Renderer | Node ceiling | Control over layout and marks | Graph algorithms |
|---------|----------|--------------|-------------------------------|------------------|
| **D3 7** | SVG (Canvas possible) | Some thousands with SVG | Full, forces and marks are written out | None built in |
| Cytoscape.js | Canvas, WebGL from 3.31 | High, with WebGL | Through a style sheet and layout presets | Yes (BFS, PageRank, betweenness, communities) |
| Sigma.js v3 | WebGL native | High | Through graphology | Through graphology |
| vis.js | Canvas | Low | Low | No |

Loading it as a classic script keeps the runtime free of a bundler, because the pinned single-file dist build is UMD:

```html
<script src="lib/d3.v7.min.js"></script>
```

The view code lives in `js/network.js` as an ES module and reads the global `d3`.

### What keeps the view readable

Object entities outnumber persons and places by an order of magnitude, so they start hidden and are switched on through the type filter. Edges carry no labels at all; the pair, the count and the loci of an edge live in the detail card that a click opens. Labels stand permanently on persons, places and documents and on objects attested more than once, with the remaining object labels appearing on hover. The collision force reserves extra radius for a labelled node, which spreads labels apart without a label-placement pass. Under `prefers-reduced-motion` the simulation is stepped to convergence synchronously and the settled layout is painted once.

### Scale and the two graph problems

The current graph is small, a few hundred nodes at most with objects switched on, so a live force layout over the whole set is fast enough and needs no progressive disclosure. The cost that is already noticeable is the filter change: every toggle rebuilds the node and edge DOM, runs a fresh simulation and finishes with the label-separation pass, which is why switching the 212 objects on takes a moment (operator observation, 2026-08-28). The head-room in this architecture, in the order to use it: seed the simulation with the previous positions instead of starting cold, cache settled positions per filter state, cap the label pass by iteration budget, and only then a Canvas renderer when node counts grow past what SVG carries.

The SiCProD court network is a different problem, with several thousand persons and tens of thousands of relations. The prototype-era network page solved it by progressive disclosure, an ego network around Sigmund as the entry point with a bounded full view behind a toggle. That page was removed in the August 2026 consolidation; the design reasoning is preserved in design.md and applies again when the court network returns as a view over edited text. At that size SVG marks become the bottleneck and a Canvas renderer is the upgrade path.

Layout pre-computation exists as `scripts/compute_layout.py`, which writes `data/network.json`; no page loads that file, because the layout runs fast enough in the browser and a live simulation lets a filter change re-lay the graph.

## Document viewer: OpenSeadragon

Zero dependencies, IIIF support, deep zoom.

```html
<script src="lib/openseadragon.min.js"></script>
```

Images come from Transkribus IIIF URLs, loaded as a plain image source (`viewer.open({ type: 'image', url })`) rather than as a tiled IIIF service. That is enough for single pages and saves a request round trip per tile.

The transcription panel is separate HTML beside the viewer. A synchronisation over viewport events, so that a line in the text highlights its line box in the image, was planned and is not implemented; image and text sit side by side without pointing at each other. The line coordinates from the PAGE XML are ready in `data/transcriptions/`, the overlay is missing.

## Search: custom vanilla JavaScript

No library is needed. `Array.filter()` with `Map` and `Set` handles the data volumes involved. The logic sits inline in the page that uses it, as plain functions over a small filter-state object, rather than as a class.

The source search on the home page filters over category, availability tier and free text. A faceted search across the SiCProD entities ran in the prototype phase with facets for entity type, gender, function and place type. Institution was never usable as a facet, because almost all institution records carry no type (see data.md), and a period slider fails on the heterogeneous and often missing datings.

## Data loading

Every page loads only the JSON files it needs. `js/data-loader.js` exports `loadJSON(path)`, caching per file in IndexedDB and versioning the cache through the constant `DATA_VERSION`.

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
│   │   ├── network.js      D3 force network over data/graph.jsonld
│   │   └── utils.js        Formatting, sorting, escaping
│   ├── data/               Pre-processed JSON, git-tracked
│   │   ├── benchmark/      Published export of the prompt benchmark, the summary
│   │   ├── demo/           Entity and relation extraction on Thaur A 49.1
│   │   ├── entities/       Line-anchored entities per document, input to the TEI build
│   │   ├── graph.jsonld    Aggregated entity graph over all extracted documents
│   │   ├── pipeline/       register_summary.json, the site projection of the register
│   │   ├── tei/            Generated TEI P5, one file per document
│   │   └── transcriptions/ Inventory transcriptions from Transkribus PAGE XML
│   ├── lib/                Vendored dependencies
│   └── knowledge/          This knowledge base
├── evaluation/
│   ├── benchmark/          Versioned prompt benchmark: pages, prompts, runs, metrics
│   ├── pilot/              The benchmark prompts on continuous, uncurated material
│   ├── pilot2/             The same configuration on a wider slice of unseen material
│   └── checks/             Reference-free checks over the runs, currently the
│                           arithmetic probe of the account-book amounts
├── experiments/
│   └── transcription-test/ The frozen first VLM transcription test of 26.08.2026
├── pipeline/               Page register (per-page content class, empty evidence,
│   │                       verification status, provenance-tagged transcription runs),
│   │                       TEI generation, validation, healthcheck
│   ├── accounts/           Executable part of the account-book encoding specification
│   ├── prompts/            Prompts of the pipeline's extraction scripts
│   └── schema/             Vendored tei_all.rng and the project schema docta.rng
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
| `build_stats.py` | The exported JSON files | `data/stats.json`, currently read by no page |

The site computes the figures it shows in the browser, from the source catalogue in `data/sources.json` and the register projection in `data/pipeline/register_summary.json`, both of which it loads anyway. `build_stats.py` and its `data/stats.json` are left over from the prototype phase and have no consumer; the file stays as an exploration artifact. The pipeline scripts that write `data/pipeline/`, `data/tei/` and `data/entities/` live in `pipeline/` and are documented in `pipeline/README.md`.

Two of the collection scripts write files that are still in use. `explore_transkribus.py` writes `data/transkribus_collection.json`, which `index.html` loads for the first-page thumbnails of documents the register does not know, and which `transform_sources.py` reads for the page counts. `transkribus_status.py` writes `data/transkribus_status.json`, which no page loads but which `build_register.py` and `build_tei.py` read as the source of the Transkribus workflow status, and `fetch_transcriptions.py` and `map_sources.py` read as their document list.

Exploration and helper scripts whose output nothing consumes: `compute_layout.py` writing `data/network.json`, `explore_transkribus_deep.py` and `fetch_remaining.py`. They document how the data situation was established and stay in the repository for that reason.

## Tests

`tests/` holds a smoke test and an interaction test driven by Playwright. Both start a local server that deliberately serves the repository under the subpath `/DoCTA/`, exactly as GitHub Pages does, so that path errors invisible at a domain root become visible. Both derive their page list from the `*.html` files in `docs/`, so a new page is covered without an edit to the tests, and both exit nonzero on the first finding, which makes them usable as a gate rather than as a report to read. The smoke test loads every page and reports console errors, uncaught exceptions, failed network requests, HTTP status codes from 400 upwards and internal links that resolve to no file. The interaction test exercises the central controls of each page. Playwright is not a project dependency; the site itself has no Node dependencies. Their README states how to install and run them.

## coOCR/HTR as a reference

A browser-based VLM transcription workbench. It is an **external project** and no part of DoCTA.

| | |
|---|---|
| Demo | https://dhcraft.org/co-ocr-htr |
| Repository | https://github.com/DigitalHumanitiesCraft/co-ocr-htr |
| Stack | Vanilla JavaScript with ES6 modules, OpenSeadragon, no build process |

DoCTA adopts the visual design language of coOCR/HTR. Its earlier categorical confidence display is carried on here as a rule-bound review status. The code is not adopted.
