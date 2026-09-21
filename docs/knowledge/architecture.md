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
updated: 2026-09-21
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

### Local editing service

`pipeline/local_editor.py` serves the same `docs/` tree on loopback and exposes a same-origin API. `viewer-local.js` discovers this service through its response header and session capability. GitHub Pages and ordinary static preview servers retain the export workflow. Local transcription requests bypass IndexedDB and read the effective register text. Drafts carry the loaded revision, and a save against a changed revision fails visibly.

The browser keeps pending corrections until an explicit save succeeds. The backend records the review under `pipeline/reviews/` and updates `pipeline/pages/`. The event stores the server UTC timestamp in `exported`, its `reviewId`, the document and page identities, the reviewer and each line's `original` and `corrected` text. The page register appends a human run with the complete effective line list and keeps the previous runs. The saved event and register are filesystem state until committed to Git. A later review uses the newest effective text as its base. Original Transkribus files and recognition runs remain unchanged. `viewer-review.js` records text corrections without time tracking or page approval controls. Existing review statuses and historical effort fields remain readable for compatibility. A new correction sends a null decision; the ingest layer retains its legacy `gesichtet` state with reason `text-corrected`, while the interface labels the factual change as `Lokal korrigiert`. Earlier curation sidecars under `pipeline/annotations/` remain keyed by extraction identity and source-line digest. The current viewer does not load their editing interface.

The explicit local build takes an edition date and a document selection to check. It rebuilds the complete connected TEI set, including the shared entity register, because document references and the common date must remain consistent. It applies annotation decisions to TEI and graph, rejects stale source digests, validates generated TEI and updates the static text projections. Failed file replacement restores the preceding output set. Saved work, generated files, a local commit and publication remain separate operations. The loopback server neither commits nor pushes. `--root` selects an isolated repository copy for end-to-end tests.

Accepted annotation normalization enters the local TEI register and graph. Rejected occurrences are excluded, and undecided proposals retain machine provenance. Authority URIs enter the graph. The closed inventory TEI schema does not permit them on register entries, so no external authority pointer is claimed in that TEI representation. Introducing one requires a deliberate encoding change. Source extraction files remain available to the viewer as machine proposals, with saved decisions shown in the curation form.

Hersch's direct file writing provided a comparison for canonical data and their site mirrors. Its sequential writes do not supply the conflict check required here. The [SZD HTR pipeline save handler](https://github.com/chpollin/szd-htr-ocr-pipeline/blob/1caf45127071ea8adf849922cb169c519a88e77b/pipeline/serve.py) preserves the first machine text in `transcription_llm` and appends previous readings with reviewer provenance to `edit_history`. Its [browser save flow](https://github.com/chpollin/szd-htr-ocr-pipeline/blob/1caf45127071ea8adf849922cb169c519a88e77b/docs/app.js) does not await the write response. The server writes the result JSON directly after replacing one backup, without a revision precondition or shared lock, and an edit defaults to approved. Site projections require a separate rebuild. This comparison was inspected on 2026-09-21 and informs provenance design, but supplies no verified persistence implementation to reuse unchanged.

DoCTA retains immutable recognition runs and explicit review records. It checks the loaded revision and original readings, serializes writes, replaces files atomically and reopens review after a correction. The validated edition build keeps the connected projections consistent. These checks address the observed failure cases without claiming a crash-safe transaction across every output file.

### Manual research tags

`viewer-tags.js` exposes the local page or line tagging form independently of the extraction layer. `local_tags.py` stores working annotations under `pipeline/tags/<docId>.json`. The API checks both sidecar and source revisions under the shared review lock, creates identifiers and timestamps on the server and replaces the sidecar atomically. Each annotation retains its source text and digest. A recheck explicitly replaces the snapshot and records its reviewer and update time. This sidecar is current working state, with Git providing version history after commits.

The browser preserves form drafts across page changes and reloads. Unsaved transcription corrections block new tags and rechecks. A draft attached to an older source revision requires explicit reassociation after the current source is loaded. The API independently rejects stale writes. Saved tags are searchable on the current page and exportable as document JSON. They are not part of the TEI or graph build, so working terms cannot silently become formal entity or event assertions.

### Vendored versions (from the file headers in `docs/lib/`)

| Library | Vendored | File |
|---------|----------|------|
| Bootstrap | 5.3.3 | `lib/bootstrap.min.css`, `lib/bootstrap.bundle.min.js` |
| D3 | 7.9.0 | `lib/d3.v7.min.js` |
| OpenSeadragon | 4.1.1 | `lib/openseadragon.min.js` |

D3 comes from `https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js`, the single-file UMD dist build of the release, vendored on 2026-08-28 and licensed ISC. Cytoscape.js 3.30.4 was vendored until the same day, when the network view moved to D3 and `lib/cytoscape.esm.min.mjs` was deleted. `lib/marked.min.js` (marked 15.0.12) is still in the folder as a remnant of the knowledge page removed on 28.08.2026, and no page loads it.

The pins lag behind upstream. That is deliberate. The versions are frozen since they worked, and without a package manager an upgrade means editing files by hand and retesting every page.

## Site pages

| Page | Purpose |
|------|---------|
| `index.html` | Home. The source catalogue with search, filters and a per-source stage indicator for facsimile, HTR text, TEI and edited state |
| `viewer.html` | Source explorer. OpenSeadragon facsimile beside the transcription, with a line overlay coupling image and text, line corrections, working tags and editor-owned source annotations, plus a reading mode over the whole document text |
| `register.html` | Editor-owned Index with persons, places, controlled terms and links to source occurrences |
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

The current graph is small, a few hundred nodes at most with objects switched on, so a live force layout over the whole set is fast enough and needs no progressive disclosure. The cost that is already noticeable is the filter change: every toggle rebuilds the node and edge DOM, runs a fresh simulation and finishes with the label-separation pass, which is why switching the objects on takes a moment (operator observation, 2026-08-28). The head-room in this architecture, in the order to use it: seed the simulation with the previous positions instead of starting cold, cache settled positions per filter state, cap the label pass by iteration budget, and only then a Canvas renderer when node counts grow past what SVG carries.

The SiCProD court network is a different problem, with several thousand persons and tens of thousands of relations. The prototype-era network page solved it by progressive disclosure, an ego network around Sigmund as the entry point with a bounded full view behind a toggle. That page was removed in the August 2026 consolidation; the design reasoning is preserved in design.md and applies again when the court network returns as a view over edited text. At that size SVG marks become the bottleneck and a Canvas renderer is the upgrade path.

Layout pre-computation was tried once, as a script writing a `data/network.json` with fixed node positions. It was removed in August 2026 together with its output, because the layout runs fast enough in the browser and a live simulation lets a filter change re-lay the graph, which a frozen layout cannot.

## Document viewer: OpenSeadragon

Zero dependencies, IIIF support, deep zoom.

```html
<script src="lib/openseadragon.min.js"></script>
```

Images come from Transkribus IIIF URLs, loaded as a plain image source (`viewer.open({ type: 'image', url })`) rather than as a tiled IIIF service. That is enough for single pages and saves a request round trip per tile.

The transcription panel is separate HTML beside the viewer. `buildLineOverlay` in `viewer.html` draws the line polygons of the PAGE XML, held in `data/transcriptions/` under `regions[].lines[].coords`, as an SVG overlay on the image. Hovering or focusing a line in the text marks its polygon, hovering a polygon marks its line, and a click on a polygon scrolls to the line. A document the pipeline transcribed itself has no layout analysis and therefore no overlay.

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
│   ├── *.html              index, viewer, register, exploration, benchmark, about
│   ├── css/styles.css      Shared design tokens and site styles
│   ├── css/viewer.css      Working editor layout and disclosures
│   ├── js/                 ES6 modules shared by several pages
│   │   ├── app.js          Navigation, banner, footer
│   │   ├── benchmark.js    Benchmark tables from data/benchmark/summary.json
│   │   ├── data-loader.js  Fetch JSON, IndexedDB cache
│   │   ├── entity-view.js  Attestation links and provenance badges, shared by
│   │   │                   exploration views
│   │   ├── network.js      D3 force network over data/graph.jsonld
│   │   ├── utils.js        Formatting, sorting, escaping, localStorage
│   │   ├── viewer-render.js  Transcription, reading text, TEI
│   │   ├── viewer.js       Viewer page controller and image navigation
│   │   ├── viewer-review.js  Correction drafts, explicit save/discard and export
│   │   ├── viewer-local.js   Local editor capability and API requests
│   │   ├── register.js       Editor-owned Index view and source links
│   │   └── viewer-tags.js    Page and line working annotations
│   ├── data/               Pre-processed JSON, git-tracked
│   │   ├── benchmark/      Published export of the prompt benchmark, the summary
│   │   ├── demo/           Entity and relation extraction on Thaur A 49.1
│   │   ├── entities/       Line-anchored entities per document, input to the TEI build
│   │   ├── graph.jsonld    Aggregated entity graph over all extracted documents
│   │   ├── pipeline/       register_summary.json, the site projection of the register,
│   │   │                   and transcriptions/ for the documents DoCTA transcribed itself
│   │   ├── tei/            Generated TEI P5, one file per document
│   │   └── transcriptions/ Inventory transcriptions from Transkribus PAGE XML
│   ├── lib/                Vendored dependencies
│   └── knowledge/          This knowledge base
├── evaluation/
│   ├── benchmark/          Versioned prompt benchmark: pages, prompts, runs, metrics
│   ├── pilot/              The benchmark prompts on continuous, uncurated material
│   ├── pilot2/             The same configuration on a wider slice of unseen material
│   ├── checks/             Reference-free checks over the runs, currently the
│   │                       arithmetic probe of the account-book amounts
│   └── edition/            The pipeline's own per-page transcriptions for edition use
├── experiments/
│   └── transcription-test/ The frozen first VLM transcription test of 26.08.2026
├── pipeline/               Page register (per-page content class, empty evidence,
│   │                       verification status, provenance-tagged transcription runs),
│   │                       TEI generation, validation, healthcheck
│   ├── accounts/           Executable part of the account-book encoding specification
│   ├── reviews/            Saved correction events
│   ├── annotations/        Human decisions on machine proposals
│   ├── tags/               Current page and line working annotations
│   ├── prompts/            Prompts of the pipeline's extraction scripts
│   └── schema/             Vendored tei_all.rng and the project schema docta.rng
├── scripts/                Python build-time scripts
└── tests/                  Smoke and interaction tests against the published site
```

The module layout departs from the original plan, and it has moved twice. One module per page was planned (`network-view.js`, `search-engine.js`, `source-table.js`, `document-viewer.js`, `pipeline-demo.js`). What was built first was the opposite rule, page-specific JavaScript as `<script type="module">` directly in its HTML file, with `js/` holding only what several pages share. The reason was the missing build step, since each module costs an additional HTTP request while the code of one page is used by no other.

That reason stopped deciding on 28.08.2026. The viewer's inline script had become the largest body of front-end code in the repository, past the point where reading one file explains one page, and inline code is code that no linter reads and no test can import. The rule since then splits by weight. Small page wiring stays inline, meaning the collection of DOM handles, the listeners of a page's own controls, and the orchestration that holds the page state. Substantial view logic lives in a module under `js/`, meaning whatever builds markup from data, carries a contract with the pipeline, or is worth a test of its own. `js/viewer.js` now keeps the OpenSeadragon wiring, the line overlay, the pager and the URL state, while its transcription rendering sits in `js/viewer-render.js` and its curation view in `js/viewer-review.js`; that module takes the DOM handles of the review bar and a context callback from the page and holds no page state itself. `js/entity-view.js` holds what the exploration views say about an extracted entity record, its attestation links and its machine provenance. The handful of additional requests is accepted for this.

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
| `harvest_inventaria_mapping.py` | Public Transkribus Sites API of the Inventaria edition plus the IIIF keys of the page register | `data/inventaria_mapping.json` |
| `build_stats.py` | The exported JSON files | `data/stats.json`, currently read by no page |

The site computes the figures it shows in the browser, from the source catalogue in `data/sources.json` and the register projection in `data/pipeline/register_summary.json`, both of which it loads anyway. `build_stats.py` and its `data/stats.json` are left over from the prototype phase and have no consumer; the file stays as an exploration artifact. The pipeline scripts that write `data/pipeline/`, `data/tei/` and `data/entities/` live in `pipeline/` and are documented in `pipeline/README.md`.

Two of the collection scripts write files that are still in use. `explore_transkribus.py` writes `data/transkribus_collection.json`, which `index.html` loads for the first-page thumbnails of documents the register does not know, and which `transform_sources.py` reads for the page counts. `transkribus_status.py` writes `data/transkribus_status.json`, which no page loads but which `build_register.py` and `build_tei.py` read as the source of the Transkribus workflow status, and `fetch_transcriptions.py` and `map_sources.py` read as their document list.

One exploration script has no consumer for its output: `explore_transkribus_deep.py`. It documents how the data situation was established and stays in the repository for that reason.

## Editorial register persistence

The local API serves the editor-owned register at `GET /api/registry`. Mutations at `POST /api/registry` require the existing same-origin write token, the loaded registry revision and an editor identifier. `save-entry`, `save-mention` and `remove-mention` replace one validated state atomically under the shared review lock. `pipeline/registry/index.json` stores the current entries and mentions together with append-only before/after events, server timestamps and actors.

Entries use UUIDs independent of their names. Persons, places and terms have preferred labels, aliases and notes. Terms may have one broader term, with cycles rejected. Mentions carry document, page, line, UTF-16 start/end offsets, an exact quotation, the SHA-256 digest of the full saved line and an optional entry ID. IDs and kinds must agree. Empty assignment is an unresolved occurrence. A changed source digest marks the retained occurrence stale and rejects an attempted save against the obsolete reading. A corrected reading can receive a new explicitly selected occurrence.

Date mentions have kind `date` and no entry ID. Optional `when`, `notBefore` and `notAfter` retain ISO strings at year, month or day precision. `when` excludes interval bounds. Validation uses the proleptic Gregorian calendar in years 0001–9999 and compares the first possible lower day with the last possible upper day. `uncertain` records the editor's uncertainty separately from precision. The service never converts a historical calendar or infers a normalized date. Other mention kinds reject these fields. Existing entries and historical events retain their original shapes under schema version 1.

The frontend searches precomputed name and alias forms locally, including umlaut variants. It never merges identities. Fundstelle links preserve document, page and mention identity. Manual mentions and exact machine occurrences use different identifiers. The generated extraction index remains a separate name-based aggregation. The TEI/graph build does not consume the editorial register in this version. JSON export preserves the new research data and audit events.

Machine-proposal decisions retain their existing sidecar contract and now append actor, timestamp and previous/new decision values in the same atomic write. Historical files load with an empty history until a new decision is saved. Document API responses expose the selected original transcription run separately from human corrections. Source timestamps are read from saved events where available and otherwise remain as recorded in the run.

The frontend separates registry interaction and form markup into `viewer-registry.js` and `viewer-registry-markup.js`. `viewer-annotation-workspace.js` owns the single source context and popover for category selection, assignment and inline register-entry editing. `viewer-annotation-popover.js` positions the surface and provides a fixed-position fallback. Source-range rendering lives in `viewer-registry-anchors.js`, while search labels, fundstelle links and history presentation live in `viewer-registry-display.js`. Drafts survive surface dismissal, and source navigation requires saving or explicit discard. A registry response started before a subsequent save cannot replace that save's returned state.

`register.html` and `register.js` read the same local registry API for a dedicated Index view. The page searches and filters saved entries, resolves broader terms by ID and links occurrences to document, page and mention identity. It provides JSON export without write operations. The viewer no longer requests entity extractions or annotation sidecars and has no machine annotation layer. Earlier pipeline decisions and extraction data retain their existing storage and generation contracts.

## Working-version delivery

The application version comes from `pyproject.toml` and is returned by the local session API. The Windows and macOS launchers invoke the same Python server with automatic browser opening. They use locked uv dependencies or an existing local environment. A used port causes an explicit failure without stopping the service already listening. The CI platform matrix covers Windows, macOS and Linux, while native platform acceptance is only reported after an observed run.

## Tests

`tests/` holds a smoke test and an interaction test driven by Playwright. Both start a local server that deliberately serves the repository under the subpath `/DoCTA/`, exactly as GitHub Pages does, so that path errors invisible at a domain root become visible. Both derive their page list from the `*.html` files in `docs/`, so a new page is covered without an edit to the tests, and both exit nonzero when they report any finding, which makes them usable as a gate rather than as a report to read. The smoke test loads every page and reports console errors, uncaught exceptions, failed network requests, HTTP status codes from 400 upwards and internal links that resolve to no file. The interaction test exercises the central controls of each page. Playwright is not a project dependency; the site itself has no Node dependencies. Their README states how to install and run them.

## coOCR/HTR as a reference

A browser-based VLM transcription workbench. It is an **external project** and no part of DoCTA.

| | |
|---|---|
| Demo | https://dhcraft.org/co-ocr-htr |
| Repository | https://github.com/DigitalHumanitiesCraft/co-ocr-htr |
| Stack | Vanilla JavaScript with ES6 modules, OpenSeadragon, no build process |

DoCTA adopts the visual design language of coOCR/HTR. Its earlier categorical confidence display is carried on here as a rule-bound review status. The code is not adopted.
