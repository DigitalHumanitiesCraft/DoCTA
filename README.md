# DoCTA: Doing Court in the Tyrolean Alps

An agentic edition pipeline for the court records of Sigismund of Tyrol (1427–1496), held by the Tyrolean State Archives.

[Public site](https://dhcraft.org/DoCTA/) and [project knowledge](docs/knowledge/INDEX.md).

## What this is

DoCTA supports source-based research into court practices, possession and object movement, and the use of space. The research conversation starts with the historical question, then the material, the information to annotate and its intended analysis. The [project plan](docs/knowledge/plan.md#joint-walkthrough) connects those decisions to a bounded editorial pilot.

The local working edition displays facsimile and transcription together. It saves line corrections with their previous reading, reviewer and timestamp, and lets the editor build a person index and controlled vocabulary through source-bound assignments. It has no time tracking or page approval controls. Saved corrections are distinct from scholarly acceptance of a complete source. [Current results and remaining work](docs/knowledge/handoff.md) identify the evidence for each implemented part.

Account books (Raitbücher), castle and personal inventories, copybooks and court ordinances form the source programme. Account books are the leading research source. Inventories currently supply the working-editor demonstration. The account-book edition still requires accepted reference text and research annotations.

## Local editing

### First start

The working edition is version 0.2.0. It is an internal research version. Public availability and scholarly acceptance are separate from this software version.

Use a project copy containing `start-editor.cmd`, `start-editor.command` and `pipeline/local_editor.py`. GitHub Desktop can clone a supplied repository URL into a local folder. Obtain the agreed working version before starting, since the public website and the local editor can be at different revisions.

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) once. It prepares the project Python environment and locked dependencies on the first launch. That first setup requires network access. Then open the project folder and start the matching launcher:

| System | Start |
|---|---|
| Windows | Double-click `start-editor.cmd` |
| macOS | Open `start-editor.command` |

The starter opens the local viewer in the browser. Keep its terminal window open while working. If a downloaded macOS copy has lost executable permissions, open a terminal in the project folder and run `bash start-editor.command`. The equivalent command on both systems is `uv run --locked python pipeline/local_editor.py --open-browser`. Windows also retains `start-editor.ps1` for PowerShell use. Existing prepared environments can run without uv through the launchers.

Open [the silver inventory used in the joint reading](http://127.0.0.1:8742/viewer.html?doc=12647153&page=1) or [the Thaur inventory](http://127.0.0.1:8742/viewer.html?doc=11328300&page=1). The local URL addresses your own computer. Source images may require network access. Reading, correcting and annotating existing material requires no LLM API key.

If the port is occupied, the starter leaves the running service intact. Stop your old editor before starting the new version, or use `--port 8744` and open the URL printed by the new server. The macOS launcher requires native verification on the recipient computer. The CI configuration covers Windows, macOS and Linux when it runs on the remote repository.

### Correct, save and resume

1. Open Bearbeiten, enter initials and correct a line against the image.
2. Select Änderungen speichern and wait for confirmation. Reload to inspect the saved reading. Enter alone retains a browser draft.
3. Select a passage in a saved line and choose Begriff to assign a controlled term, or Person, Ort or Datumsangabe for the corresponding annotation. The annotation field holds the optional note and register assignment.
4. Open Index to find saved entries and return to their source occurrences.
5. Use Weitere Funktionen to derive and validate edition output from saved work when needed. Saved data, generated output, Git commits and publication are separate steps. Editorial register assignments currently export separately as JSON.

For the first exercise, correct one existing line, save and reload before continuing. Änderungen verwerfen discards the current page draft and preserves saved text. Leave an uncertain reading unchanged and attach a note to the selected passage. Source spelling stays in the transcription even when a register entry uses a normalized name.

Before finishing, save text changes and any tag or annotation form separately. Stop the server with Ctrl+C in its terminal after saving. For the next session, run the start command again and reopen the local link. Saved corrections reside in the project folder. Clearing browser storage can remove unsaved drafts.

### Keep a local version and report feedback

After saving, GitHub Desktop shows the changed project files. Select only the intended research changes, enter a short description and commit them to the local branch. A commit records a local version and does not send it elsewhere. Push origin uploads commits. Publication and sharing of the internal working material require a separate decision. Text events live under `pipeline/reviews/` and effective readings under `pipeline/pages/`. Tags and annotation decisions have their own files. The service saves these files without committing them.

If a save reports a conflict, retain the unsaved wording, reload the current saved state and reconcile the readings before saving again. If the browser cannot connect, inspect the terminal for a startup error and confirm that the editor is still running. Do not discard a draft to resolve an unexplained error.

Feedback should include the document and page, the action attempted, the expected result and the observed result. A screenshot can help identify an interface problem. Use the agreed internal feedback channel while source rights remain unresolved.

### Build a person index and vocabulary

1. Select text within one saved transcription line. A small toolbar offers Person, Begriff, Ort and Datumsangabe. Right-clicking the selection also opens the toolbar. Auswahl annotieren and Alt+A provide an explicit alternative.
2. Choose a category. The same field beside the passage contains the assignment and its history. For persons, places and terms, search for an existing register entry or choose Neuer Registereintrag. Create or edit the entry in that field, save it, then explicitly save the occurrence. Noch nicht zugeordnet retains an unresolved occurrence with a note.
3. For a date, retain the source wording and optionally enter a normalized year, month or day using `YYYY`, `YYYY-MM` or `YYYY-MM-DD`. A Zeitraum can have an earliest and/or latest bound. Unsichere Datierung records uncertainty. The editor decides the historical interpretation and any calendar conversion. Validation uses the proleptic Gregorian calendar, without automatic conversion.
4. Save the occurrence with your initials. Click its editorial mark to edit or remove it later. Removing an annotation preserves the source text and retains the previous value in history. Closing the inline field retains unsaved input, available through Annotation fortsetzen. Explicit discard removes that draft.
5. Open Register to search persons, places and terms in a collapsible sidebar. Entries hold a preferred label, spelling variants and notes. Terms may have a broader term. Fundstellen link back to source passages, and equal names remain independent identities. Register als JSON exportieren downloads the saved entries, occurrences and history.

If source text changes, affected occurrences require checking. Their retained quotations remain inspectable. Select the new wording to create a replacement occurrence, and remove the superseded occurrence when appropriate. The first version anchors selections within a single existing line. It does not split or merge transcription lines.

The editorial register identifies persons and classifies source occurrences. Assigning the term Polster does not establish that two sources describe the same physical cushion. These explicit assignments remain independent of the automatically generated extraction index. They are saved with their history in `pipeline/registry/index.json` and exported as JSON. The existing TEI and graph build continues to use machine-proposal curation and does not yet incorporate the new editorial register.

### Select sources

Quellen opens the searchable source overview. Availability filters distinguish sources with transcription, sources with a stored image address and archival records. Image-only sources open the first image whose address is recorded. The viewer names the documented total separately and does not invent missing pages. Transcription attribution is shown on the source row and in the viewer. Research preview links to the project explanation.

The separate Schlagwörter dialog is retired. Earlier tag files and browser drafts remain preserved; new controlled terms are assigned through the common annotation field. Historical tags are not automatically converted into register entries.

### Browse the index and check text provenance

Index beside Viewer opens the editor-owned person and place index and controlled vocabulary. Search preferred names, spelling variants and notes, or filter by category. A selected entry shows its description, broader term where recorded, and source occurrences. Follow a Fundstelle to reopen that exact assignment in the viewer. Equal names remain independent entries. The page reads saved entries and does not merge or import the generated machine index.

The annotation field in the viewer contains only editorial assignments. Selecting source text performs no LLM call and displays no automatic proposal. The historical editor builds the index and vocabulary through explicit assignments. Earlier extraction files and annotation decisions remain in the project data, available to their existing processing workflows.

Transcription provenance remains visible independently of editorial annotation. It identifies the recorded transcription LLM and saved human corrections. Details provide the recorded source run and prompt metadata. Missing model information in imported text remains explicitly unknown. The [annotation contract](docs/knowledge/specification.md#annotation-curation-in-the-viewer) defines the implemented scope.

The public GitHub Pages viewer supports browser transcription drafts and JSON export. Writing corrections and register assignments into project files requires the local editor. Source exports and prior transcription runs remain available. [The persistence model](docs/knowledge/architecture.md#local-editing-service) describes revision checks and output generation.

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
