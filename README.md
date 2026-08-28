# DoCTA: Doing Court in the Tyrolean Alps

An agentic edition pipeline for the court records of Sigismund of Tyrol (1427–1496), held by the Tyrolean State Archives.

**Live site:** https://dhcraft.org/DoCTA/

## What this is

DoCTA turns facsimiles of fifteenth-century Tyrolean court records into research data and a digital edition. Account books (Raitbücher), castle and personal inventories, copybooks and court ordinances are treated as one connected corpus. The pipeline runs in five stages:

1. **Sources.** Facsimiles and metadata from a Transkribus collection, mapped against an archival source catalogue.
2. **VLM transcription.** Vision-language models produce candidate text from the page image. All such output is unrevised machine transcription and is marked as such wherever it is displayed.
3. **Validation and ground truth.** A versioned prompt benchmark measures each prompt iteration on a fixed page set. Scholarly review at the facsimile produces approved reference text, which serves at once as the evaluation base and as edition progress.
4. **TEI and research data.** Approved text is encoded and published as reusable research data.
5. **Edition.** The edition view over the sources that have passed validation.

The digital instruments are heuristic tools in service of historical research questions about court practice. The knowledge base in `docs/knowledge/` is the source of truth for how the project understands its sources, its methods and its own decisions; the code is the disposable artifact.

## Repository layout

```
DoCTA/
├── docs/                   Published site, GitHub Pages serves this folder on main
│   ├── *.html              index, viewer, exploration, benchmark, knowledge, about
│   ├── css/, js/, lib/     Design tokens, shared ES6 modules, vendored dependencies
│   ├── data/               Pre-processed JSON read by the site
│   └── knowledge/          The Promptotyping knowledge base, rendered by knowledge.html
├── evaluation/
│   ├── benchmark/          Versioned prompt benchmark: page set, prompts, runs, metrics
│   ├── pilot/              The benchmark prompts on continuous, uncurated material
│   ├── pilot2/             The same frozen configuration on a wider slice of unseen material
│   ├── checks/             Reference-free checks over transcription runs, currently the
│   │                       arithmetic probe of the account-book amounts
│   └── edition/            The pipeline's own per-page VLM transcriptions for edition use
├── experiments/
│   └── transcription-test/ The frozen first VLM transcription test of 26.08.2026
├── pipeline/               Page register (one entry per page with content class, empty
│   │                       evidence, verification status and provenance-tagged runs),
│   │                       TEI generation, validation and the cross-artifact healthcheck
│   ├── accounts/           Executable part of the account-book encoding specification
│   ├── prompts/            Prompts used by the pipeline's extraction scripts
│   └── schema/             Vendored TEI P5 grammar and the project schema docta.rng
├── scripts/                Python build-time scripts for data fetching and transformation
└── tests/                  Playwright smoke and interaction tests against the published site
```

The site is static: vanilla JavaScript with ES6 modules, no build process, dependencies vendored in `docs/lib/`. Details are in `docs/knowledge/architecture.md`.

The figures the site shows are computed in the browser from the source catalogue in `docs/data/sources.json` and the register projection in `docs/data/pipeline/register_summary.json`, so no count is hard-coded in a page. Benchmark results live in `evaluation/benchmark/summary.json`, with the published export under `docs/data/benchmark/`.

## Knowledge base

`docs/knowledge/` holds the distilled project context, readable by people and by agents.

| Document | Content |
|----------|---------|
| `INDEX.md` | Map of content and reading order |
| `data.md` | Data sources, structure and quality |
| `htr-evaluation.md` | Reference classes, benchmark protocol, metrics, release rule |
| `specification.md` | Goals, constraints, review criticism and how it was answered |
| `domain-knowledge.md` | Domain knowledge, the SiCPAS model, methods, epistemology |
| `editorial-model.md` | Editorial objects, evidence relations and responsible decisions of the account-book pilot |
| `accounting-encoding.md` | How those objects are represented as JSON, TEI and RDF, and which rule is checked by which validator |
| `architecture.md` | Architecture and implementation |
| `design.md` | Design and interaction decisions, including what was rejected |
| `journal.md` | Dated log of decisions, exploration results and open questions |

## Data sources

- [SiCProD](https://sicprod.acdh-dev.oeaw.ac.at/), the prosopographic database of Sigismund's court, supplying persons, places, court offices and relations through a public API
- [Transkribus](https://app.transkribus.org/collection/2197991), collection 2197991, holding the facsimiles and the inventory working transcriptions, with facsimiles served over IIIF
- [Inventaria](https://www.inventaria.at), an edition of castle inventories on Transkribus Sites (FWF project P 35988, led from the University of Salzburg with the University of Innsbruck). DoCTA uses only material Inventaria has published, and cites it with attribution wherever a transcription is displayed or evaluated.

## Method

The project is built with [Promptotyping](https://dhcraft.org/Promptotyping/), a context-engineering method for LLM-assisted development of research artifacts. It runs in four phases, preparation, exploration, distillation and implementation, and keeps maintained knowledge documents as the durable layer that guides each implementation round. Its core principle is that documents are the source of truth and code is a disposable artifact.

## Project

DoCTA is a collaboration between the historical project lead at the University of Salzburg and [Digital Humanities Craft OG](https://dhcraft.org), which builds the digital component. [coOCR/HTR](https://dhcraft.org/co-ocr-htr) is a sister project on transcription quality assessment and serves as the design and method reference.

## License

Source code is licensed under the MIT License. Research data and the documents in `docs/knowledge/` are licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

Historical source material is the property of the Tyrolean State Archives. IIIF facsimiles are served by Transkribus (READ-COOP). Published Inventaria transcriptions carry the terms of that project.
