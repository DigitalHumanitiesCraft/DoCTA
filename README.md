# DoCTA — Doing Court in the Tyrolean Alps

A functional web prototype demonstrating Digital Humanities methods for analyzing 15th-century Tyrolean court records from the reign of Archduke Sigmund (1427--1496).

**Live:** [dhcraft.org/DoCTA](https://dhcraft.org/DoCTA/)

## What This Is

DoCTA is a methodological proof-of-concept for an FWF research grant resubmission (APART-GSK). It shows that a computational pipeline — from digitized manuscript to structured knowledge network — works on real Early New High German source material.

The prototype processes 6,288 historical persons, 42,893 relations, 312 archival sources, and 57 fully transcribed inventories from the Tyrolean State Archives. It is not a finished research tool but a demonstration that the proposed methods are viable.

## Pages

| Page | Purpose |
|------|---------|
| **Dashboard** | Project overview, key metrics, entry points |
| **Pipeline Demo** | Step-by-step: Source → HTR → NER → Relations → Network |
| **Quellenübersicht** | 312 archival sources, filterable by category and availability |
| **Facettierte Suche** | Search across SiCProD persons, places, functions, institutions |
| **Quellen-Explorer** | Side-by-side: IIIF manuscript image + transcription |
| **Netzwerk-Explorer** | Interactive graph of the Sigmund court network |
| **Knowledge Vault** | Promptotyping documentation (6 research documents) |
| **Hilfe** | User guide and project context |

## Data Sources

- **[SiCProD](https://sicprod.acdh-dev.oeaw.ac.at/)** — Prosopographic database of Sigmund's court (ACDH-CH, Austrian Academy of Sciences)
- **[Transkribus](https://app.transkribus.org/collection/2197991)** — Collection 2197991: 115 documents, 12,236 pages from the Tyrolean State Archives
- **[Inventaria](https://www.inventaria.at)** — Castle inventory transcriptions (University of Salzburg/Innsbruck)

## Technology

- Vanilla JavaScript (ES6 Modules), no build process
- Static site on GitHub Pages
- Vendored dependencies: Bootstrap 5.3.3, Cytoscape.js, OpenSeadragon, marked.js
- Pre-fetched data via Python scripts (see `scripts/`)
- IndexedDB caching for large JSON datasets

## Methodology: Promptotyping

This prototype was built using [Promptotyping](https://lisa.gerda-henkel-stiftung.de/digitale_geschichte_pollin), a four-phase context engineering methodology for LLM-assisted research artifact development:

1. **Preparation** — Gathering source documents and domain expertise
2. **Exploration** — Testing APIs, analyzing data quality, mapping research questions to data structures
3. **Distillation** — Compressing findings into optimized knowledge documents
4. **Implementation** — Iterative code generation with continuous expert validation

The six documents in the Knowledge Vault (`knowledge/`) are the distilled output of this process. They serve as both human-readable documentation and structured context for LLM-assisted development.

Core principle: *Documents as Source of Truth, Code as Disposable Artifact.*

## Project

| | |
|---|---|
| **Project** | DoCTA (Doing Court in the Tyrolean Alps) |
| **PI** | Dr. Barbara Denicolò, University of Salzburg |
| **DH Component** | [Digital Humanities Craft OG](https://dhcraft.org) (Christopher Pollin, Christian Steiner) |
| **Related** | [coOCR/HTR](https://dhcraft.org/co-ocr-htr) — Sister project for OCR/HTR quality assessment |
| **Funding context** | FWF APART-GSK resubmission, ÖAW application (2026) |

## Repository Structure

```
DoCTA/
├── *.html              8 pages (index, pipeline, sources, search, viewer, network, knowledge, help)
├── css/styles.css      Design system (CSS custom properties, entity/confidence colors)
├── js/                 ES6 modules (app.js, data-loader.js, utils.js)
├── lib/                Vendored dependencies
├── data/               Pre-fetched JSON (SiCProD, Transkribus, computed layouts)
│   ├── demo/           Pipeline demo data (Thaur A 49.1 entities, relations, network)
│   └── transcriptions/ 57 inventory transcriptions from Transkribus
├── knowledge/          Promptotyping documents (6 Markdown files)
└── scripts/            Python build-time scripts (data fetching, transformation)
```

## License

Source code: MIT. Research data and knowledge documents: CC BY 4.0.

Historical source material is property of the Tyrolean State Archives (Tiroler Landesarchiv). IIIF images are served by Transkribus (READ-COOP).
