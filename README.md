# DoCTA: Doing Court in the Tyrolean Alps

An agentic edition pipeline for the court records of Sigismund of Tyrol (1427–1496), held by the Tyrolean State Archives.

[Public site](https://dhcraft.org/DoCTA/) and [project knowledge](docs/knowledge/INDEX.md).

## What this is

DoCTA supports source-based research into court practices, possession and object movement, and the use of space. The research conversation starts with the historical question, then the material, the information to annotate and its intended analysis. The [project plan](docs/knowledge/plan.md#joint-walkthrough) connects those decisions to a bounded editorial pilot.

The local working edition displays facsimile and transcription together. It saves line corrections with their previous reading, reviewer and timestamp, supports page or line tags, and lets the editor curate existing machine annotation proposals. It has no time tracking or page approval controls. Saved corrections are distinct from scholarly acceptance of a complete source. [Current results and remaining work](docs/knowledge/handoff.md) identify the evidence for each implemented part.

Account books (Raitbücher), castle and personal inventories, copybooks and court ordinances form the source programme. Account books are the leading research source. Inventories currently supply the working-editor demonstration. The account-book edition still requires accepted reference text and research annotations.

## Local editing

### First start

Use a project copy containing `start-editor.ps1` and `pipeline/local_editor.py`. Check that both files exist before following these instructions. The editor and the public website can be at different revisions. If either file is missing, obtain the working-editor version from the project maintainer.

GitHub Desktop can clone a supplied repository URL into a local folder. Editing requires Python 3.11 or later and uv, the dependency manager. In a terminal opened in the project folder, prepare the environment once:

```powershell
uv sync --locked
```

On Windows and macOS, start the editor from that folder with the same command:

```powershell
uv run python pipeline/local_editor.py
```

Windows also provides `.\start-editor.ps1`, which uses uv or an existing project environment. The shared command also applies on Linux. The macOS entry point has been inspected in code but has not been tested on a Mac. Installation on the editor's own computer requires a first save-and-reload check.

Keep the terminal open while working. Open [the silver inventory used in the joint reading](http://127.0.0.1:8742/viewer.html?doc=12647153&page=1) or [the Thaur inventory](http://127.0.0.1:8742/viewer.html?doc=11328300&page=1) in a browser. The local URL works only on the computer running the editor. Source images may require network access. Reading, correcting and tagging existing material requires no model API key.

### Correct, save and resume

1. Open Bearbeiten, enter initials and correct a line against the image.
2. Select Änderungen speichern and wait for confirmation. Reload to inspect the saved reading. Enter alone retains a browser draft.
3. Open Schlagwörter to attach a working term and note to a page or line. Changed source text requires a recheck. Tags support page-local filtering and document JSON export.
4. Open Automatische Annotationen to curate existing proposals. The source text, a machine proposal and a human annotation decision have separate provenance.
5. Use Weitere Funktionen to derive and validate edition output from saved work when needed. Saved data, generated output, Git commits and publication are separate steps.

For the first exercise, correct one existing line, save and reload before continuing. Änderungen verwerfen discards the current page draft and preserves saved text. Leave an uncertain reading unchanged and attach a note through Schlagwörter. Whole-line corrections and page or line tags are supported. Selecting a new word span to create a person annotation is still a planned extension.

Before finishing, save text changes and any tag or annotation form separately. Stop the server with Ctrl+C in its terminal after saving. For the next session, run the start command again and reopen the local link. Saved corrections reside in the project folder. Clearing browser storage can remove unsaved drafts.

### Keep a local version and report feedback

After saving, GitHub Desktop shows the changed project files. Select only the intended research changes, enter a short description and commit them to the local branch. A commit records a local version and does not send it elsewhere. Push origin uploads commits. Publication and sharing of the internal working material require a separate decision. Text events live under `pipeline/reviews/` and effective readings under `pipeline/pages/`. Tags and annotation decisions have their own files. The service saves these files without committing them.

If a save reports a conflict, retain the unsaved wording, reload the current saved state and reconcile the readings before saving again. If the browser cannot connect, inspect the terminal for a startup error and confirm that the editor is still running. Do not discard a draft to resolve an unexplained error.

Feedback should include the document and page, the action attempted, the expected result and the observed result. A screenshot can help identify an interface problem. Use the agreed internal feedback channel while source rights remain unresolved.

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
