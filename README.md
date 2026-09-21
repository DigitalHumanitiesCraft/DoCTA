# DoCTA: Doing Court in the Tyrolean Alps

An agentic edition pipeline for the court records of Sigismund of Tyrol (1427–1496), held by the Tyrolean State Archives.

[Public site](https://dhcraft.org/DoCTA/) and [project knowledge](docs/knowledge/INDEX.md).

## What this is

DoCTA supports source-based research into court practices, possession and object movement, and the use of space. The research conversation starts with the historical question, then the material, the information to annotate and its intended analysis. The [project plan](docs/knowledge/plan.md#joint-walkthrough) connects those decisions to a bounded editorial pilot.

The local working edition displays facsimile and transcription together. It saves line corrections with their previous reading, reviewer and timestamp, supports page or line tags, and lets the editor curate existing machine annotation proposals. It has no time tracking or page approval controls. Saved corrections are distinct from scholarly acceptance of a complete source. [Current results and remaining work](docs/knowledge/handoff.md) identify the evidence for each implemented part.

Account books (Raitbücher), castle and personal inventories, copybooks and court ordinances form the source programme. Account books are the leading research source. Inventories currently supply the working-editor demonstration. The account-book edition still requires accepted reference text and research annotations.

## Local editing

On Windows, prepare the repository clone with `uv sync --locked`, then run `./start-editor.ps1`. The launcher uses uv or the existing `.venv`. Open [the Thaur inventory](http://127.0.0.1:8742/viewer.html?doc=11328300&page=1). The local URL works only on the computer running the editor, and externally hosted images may require network access.

1. Open Bearbeiten, enter initials and correct a line against the image.
2. Select Änderungen speichern and wait for confirmation. Reload to inspect the saved reading. Enter alone retains a browser draft.
3. Open Schlagwörter to attach a working term and note to a page or line. Changed source text requires a recheck. Tags support page-local filtering and document JSON export.
4. Open Automatische Annotationen to curate existing proposals. The source text, a machine proposal and a human annotation decision have separate provenance.
5. Use Weitere Funktionen to derive and validate edition output from saved work when needed. Saved data, generated output, Git commits and publication are separate steps.

Inventaria attribution identifies the transcription source. The colored annotation proposals are a separate DoCTA extraction layer whose stored metadata names the model and prompt. Opening the viewer performs no model API call. Direct editing from a highlighted mention remains a proposed improvement. The [annotation contract](docs/knowledge/specification.md#annotation-curation-in-the-viewer) defines the implemented scope.

The public GitHub Pages viewer supports browser drafts and JSON export. Writing corrections into repository files requires the local editor. Source exports and prior transcription runs remain available. [The persistence model](docs/knowledge/architecture.md#local-editing-service) describes revision checks and output generation.

## Repository layout

```
DoCTA/
├── docs/                   Published site, GitHub Pages serves this folder on main
│   ├── *.html              index, viewer, exploration, benchmark, about
│   ├── css/, js/, lib/     Design tokens, shared ES6 modules, vendored dependencies
│   ├── data/               Pre-processed JSON read by the site
│   └── knowledge/          The Promptotyping knowledge base, Markdown read in the repository
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
│   ├── reviews/            Saved correction events
│   ├── annotations/        Decisions on machine entity proposals
│   ├── tags/               Page and line research tags
│   ├── prompts/            Prompts used by the pipeline's extraction scripts
│   └── schema/             Vendored TEI P5 grammar and the project schema docta.rng
├── scripts/                Python build-time scripts for data fetching and transformation
└── tests/                  Playwright smoke and interaction tests against the published site
```

The site is static: vanilla JavaScript with ES6 modules, no build process, dependencies vendored in `docs/lib/`. Details are in `docs/knowledge/architecture.md`.

The figures the site shows are computed in the browser from the source catalogue in `docs/data/sources.json` and the register projection in `docs/data/pipeline/register_summary.json`, so no count is hard-coded in a page. Benchmark results live in `evaluation/benchmark/summary.json`, with the published export under `docs/data/benchmark/`.

## Knowledge base

The [document register](docs/knowledge/INDEX.md) lists the knowledge documents and their maintenance roles. Start with [the project charter](docs/knowledge/project.md) for research scope, [the joint walkthrough](docs/knowledge/plan.md#joint-walkthrough) for the meeting, or [the handoff](docs/knowledge/handoff.md) for current evidence and open work.

[Pipeline documentation](pipeline/README.md) defines stored data and processing commands. [Test instructions](tests/README.md) describe the executable checks. Agents enter through [CLAUDE.md](CLAUDE.md).

## Data sources

- [SiCProD](https://sicprod.acdh-dev.oeaw.ac.at/), the prosopographic database of Sigismund's court, supplying persons, places, court offices and relations through a public API
- [Transkribus](https://app.transkribus.org/collection/2197991), collection 2197991, holding the facsimiles and the inventory working transcriptions, with facsimiles served over IIIF
- [Inventaria](https://www.inventaria.at), an edition of castle inventories on Transkribus Sites (FWF project P 35988, led from the University of Salzburg with the University of Innsbruck). DoCTA uses only material Inventaria has published, and cites it with attribution wherever a transcription is displayed or evaluated.

## Method

The project is built with [Promptotyping](https://dhcraft.org/Promptotyping/). Maintained knowledge guides the versioned implementation through preparation, exploration, distillation and implementation. Formal validation checks the data structures. Scholarly acceptance requires source-based judgement under an agreed convention.

## Project

DoCTA is a collaboration between the historical project lead at the University of Salzburg and [Digital Humanities Craft OG](https://dhcraft.org), which builds the digital component. [coOCR/HTR](https://dhcraft.org/co-ocr-htr) is a sister project on transcription quality assessment and serves as the design and method reference.

## License

Source code is licensed under the MIT License. Research data and the documents in `docs/knowledge/` are licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

Historical source material is the property of the Tyrolean State Archives. IIIF facsimiles are served by Transkribus (READ-COOP). Published Inventaria transcriptions carry the terms of that project.
