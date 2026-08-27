# DoCTA - Doing Court in the Tyrolean Alps

A functional web prototype demonstrating Digital Humanities methods for analyzing 15th-century Tyrolean court records from the court of Archduke Sigmund of Tyrol (1427-1496).

**Live:** [dhcraft.org/DoCTA](https://dhcraft.org/DoCTA/)

## What This Is

DoCTA is a methodological proof-of-concept for a planned research grant resubmission to the ÖAW APART-GSK programme. It shows that a computational pipeline, from digitized manuscript to structured knowledge network, works on real Early New High German source material.

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
| **Knowledge Vault** | Promptotyping documentation (7 research documents) |
| **Hilfe** | User guide and project context |

## Data Sources

- **[SiCProD](https://sicprod.acdh-dev.oeaw.ac.at/)**: Prosopographic database of Sigmund's court (University of Innsbruck with the Tiroler Landesarchiv and the ACDH-CH of the Austrian Academy of Sciences)
- **[Transkribus](https://app.transkribus.org/collection/2197991)**: Collection 2197991 with 115 documents, 12,236 pages from the Tyrolean State Archives
- **[Inventaria](https://www.inventaria.at)**: Castle inventory transcriptions (FWF project P 35988, led by Christina Antenhofer at the University of Salzburg, with the University of Innsbruck and the IZMF)

## Technology

- Vanilla JavaScript (ES6 Modules), no build process
- Static site on GitHub Pages
- Vendored dependencies: Bootstrap 5.3.3, Cytoscape.js, OpenSeadragon, marked.js
- Pre-fetched data via Python scripts (see `scripts/`)
- IndexedDB caching for large JSON datasets

## Methodology: Promptotyping

This prototype was built using [Promptotyping](https://lisa.gerda-henkel-stiftung.de/digitale_geschichte_pollin), a four-phase context engineering methodology for LLM-assisted research artifact development:

1. **Preparation**: Gathering source documents and domain expertise
2. **Exploration**: Testing APIs, analyzing data quality, mapping research questions to data structures
3. **Distillation**: Compressing findings into optimized knowledge documents
4. **Implementation**: Iterative code generation with continuous expert validation

The documents in the Knowledge Vault (`docs/knowledge/`) are the distilled output of this process. They serve as both human-readable documentation and structured context for LLM-assisted development.

Core principle: *Documents as Source of Truth, Code as Disposable Artifact.*

## Project

| | |
|---|---|
| **Project** | DoCTA (Doing Court in the Tyrolean Alps) |
| **PI** | Dr. Barbara Denicolò, University of Salzburg |
| **DH Component** | [Digital Humanities Craft OG](https://dhcraft.org) (Christopher Pollin, Christian Steiner) |
| **Related** | [coOCR/HTR](https://dhcraft.org/co-ocr-htr): Sister project for OCR/HTR quality assessment |
| **Funding context** | ÖAW APART-GSK, planned resubmission |

## Repository Structure

```
DoCTA/
├── docs/               Published site (GitHub Pages serves this folder)
│   ├── *.html          5 pages (index with sources+search, viewer, benchmark, knowledge, about)
│   ├── css/styles.css  Design system (CSS custom properties, entity/confidence colors)
│   ├── js/             ES6 modules (app.js, data-loader.js, utils.js)
│   ├── lib/            Vendored dependencies
│   ├── data/           Pre-fetched JSON (SiCProD, Transkribus, computed layouts)
│   │   ├── demo/       Pipeline demo data (Thaur A 49.1 entities, relations, network)
│   │   └── transcriptions/ Inventory transcriptions from Transkribus
│   └── knowledge/      Promptotyping documents (Markdown)
├── experiments/        VLM transcription test case and versioned HTR prompt benchmark
├── scripts/            Python build-time scripts (data fetching, transformation)
└── tests/              Smoke and interaction tests against the published site
```

## License

Source code: MIT. Research data and knowledge documents: CC BY 4.0.

Historical source material is property of the Tyrolean State Archives (Tiroler Landesarchiv). IIIF images are served by Transkribus (READ-COOP).
