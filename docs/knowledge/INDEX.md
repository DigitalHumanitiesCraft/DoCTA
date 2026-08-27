# DoCTA Knowledge: Map of Content

This knowledge base holds the distilled project context of DoCTA (Doing Court in the Tyrolean Alps), a study of court practices at the court of Sigismund of Tyrol (1427–1496). It is written to be read both by people and by agents, and it is the source of truth for how the project understands its sources, its methods and its own decisions. The code is the disposable artifact; these documents are not.

## Current state

The project runs an agentic edition pipeline. Facsimiles of the Tyrolean State Archives, held in a Transkribus collection, are turned into research data and a simple digital edition. Account books (Raitbücher), inventories, copybooks and court ordinances are treated as one connected corpus. Vision-language models produce first transcriptions, a versioned prompt benchmark measures the quality of each prompt iteration, and scholarly review by the project team produces ground truth that serves at once as evaluation base and as edition progress. The digital tools are heuristic instruments in service of historical research questions; they are not the object of the project.

The reviewer-facing prototype of February 2026 is documented history. It demonstrated that the proposed methods work on this material and answered the review critique of the first submission; its eight pages have since been reorganised around the pipeline stages: home with the source catalogue and its per-source stage indicator, source explorer, edition, exploration, benchmark, knowledge vault and about. Where a document below still describes prototype features, it describes the earlier state and says so.

| Phase | State |
|-------|-------|
| 1. Preparation | Complete. Source documents in `sources/` (project-internal) |
| 2. Exploration | Complete. SiCProD API, source catalogue CSV and the Transkribus collection mapped |
| 3. Distillation | Complete. Eight knowledge files covering data state and the transcription review contract |
| 4. Prototype implementation | Complete. Public since 19.02.2026, reorganised around the pipeline stages in August 2026 |
| 5. Edition pipeline | Running. Versioned prompt benchmark and pilot in operation; specialised HTR comparison and an approved account-book reference are still open |

## Files by purpose

| File | Purpose | Content |
|------|---------|---------|
| **DATA.md** | Data sources and quality | SiCProD API (structure, real examples, gaps), source catalogue CSV (quality problems, availability pyramid), Transkribus (auth, collection, IIIF, pre-fetch), account book 2 (structure, open questions) |
| **HTR-EVALUATION.md** | Transcription and review contract | Reference classes, observed findings, generation procedure, metrics, release rule |
| **REQUIREMENTS.md** | Goals and constraints | Requirements of the project lead in her own words, the ten points of review criticism and how they were answered, technical constraints, success criteria |
| **CONTEXT.md** | Domain knowledge and methods | SiCPAS data model, praxeology and verb classes, BeNASch scheme, research questions, case studies, partners, epistemic asymmetry |
| **TECH.md** | Architecture and implementation | Libraries, performance strategies, project structure, design system, build-time scripts |
| **DESIGN.md** | Design and interaction | Rejected architectural patterns with reasons, network explorer design, rule-bound review status, rejected views, colour system |
| **JOURNAL.md** | Decisions and findings | Chronological decisions with reasons, exploration results, dead ends, open questions |

## Reading order for agent context

1. **INDEX.md** (this document): orientation
2. **DATA.md**: which data exist and where they break
3. **HTR-EVALUATION.md**: how transcriptions are produced, compared and approved
4. **CONTEXT.md**: domain knowledge needed for correct interpretation
5. **REQUIREMENTS.md**: what the work has to deliver and against which criticism
6. **TECH.md**: how the site is built
7. **DESIGN.md**: why it looks and behaves as it does, and what was rejected
8. **JOURNAL.md**: decision history, read on demand

## Source documents (`sources/`)

The knowledge files distil the source documents listed below. **These files are project-internal and are not part of the public repository**, because they contain unpublished proposal text and personal correspondence. The table stays here so that the provenance of the knowledge files remains traceable; the paths lead nowhere in the public clone.

| File (project-internal) | Function | Captured in knowledge? |
|-------|----------|----------------------|
| `sources/strategische-planung.md` | Master planning document | Yes, distributed across all files |
| `sources/requirements-projektleitung.md` | Requirements of the project lead | Yes, in REQUIREMENTS.md |
| `sources/raitbuch-2-analyse.md` | Source analysis of account book 2 | Yes, in DATA.md |
| `sources/coocr-htr-epistemologie.md` | Epistemological argument | Yes, core concepts in CONTEXT.md |
| `sources/fwf-proposal-2025.md` | Rejected first submission. The file name comes from an earlier filing and is misleading. | Partly. Bibliography and work-package detail are not captured. |
| `sources/gutachten-ersteinreichung.pdf` | Review of the first submission | Yes, in REQUIREMENTS.md |
| `sources/quellen-katalog.csv` | Source catalogue | Yes, analysis in DATA.md |
| `sources/sicpas-modell.svg` | SiCPAS diagram | As text in CONTEXT.md |

## Exported data (`data/`)

Unlike `sources/`, this folder is fully contained in the public repository. Current counts live in `data/stats.json`, which the site reads; the table below names what each file holds rather than how much.

### Used by the site

| File | Content |
|------|---------|
| `data/stats.json` | Aggregate counts of the exported data, single source of truth for all figures shown |
| `data/sources.json` | The source catalogue, cleaned from the CSV |
| `data/source_mapping.json` | Mapping from Transkribus document titles to catalogue shelfmarks |
| `data/transcriptions/*.json` | Inventory transcriptions exported from Transkribus PAGE XML |
| `data/benchmark/` | Published export of the prompt benchmark (summary and runs), read by `benchmark.html` |
| `data/demo/*.json` | Entity and relation extraction demo on the inventory Thaur A 49.1 |

### Exploration artifacts, loaded by no page

They stay in the repository because they document how the data situation was established.

| File | Content |
|------|---------|
| `data/persons.json`, `data/relations.json` | Persons and relations from SiCProD. They drove the prototype's network and faceted search; no current page loads them |
| `data/places.json`, `data/institutions.json`, `data/functions.json` | Places, institutions and court offices from SiCProD, likewise from the prototype phase |
| `data/transkribus_collection.json` | The full collection with document metadata |
| `data/transkribus_status.json` | Transcription status of every document in the collection |
| `data/raitbuch2_pages.json` | Page list of account book 2 with IIIF keys |
| `data/network.json` | Pre-computed network layout from the prototype phase (see TECH.md) |

## Evaluation (`evaluation/`) and experiments (`experiments/`)

| Folder | Purpose |
|--------|---------|
| `evaluation/benchmark/` | The versioned prompt benchmark: fixed page set, versioned prompts, repeated runs with full provenance, stratified metrics. Its published export drives `benchmark.html`. |
| `evaluation/pilot/` | The benchmark prompts run on continuous, uncurated material: one full inventory document and a run of consecutive account-book openings. |
| `experiments/transcription-test/` | The first VLM transcription test of 26.08.2026 with its raw outputs and synopsis viewer. Frozen; it is the origin of benchmark iteration it01 and the only remaining experiment. |

Each folder carries its own README with protocol and re-entry instructions. The methodological reading of the results is in `HTR-EVALUATION.md`. All transcriptions produced in these folders are unrevised machine output until a scholar has approved them.
