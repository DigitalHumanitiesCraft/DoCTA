---
title: INDEX
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
  name: Vorlage Index
  version: 0.4
  url: https://dhcraft.org/Promptotyping/promptotyping-document/index
  alias: https://dhcraft.org/Promptotyping/#promptotyping-document-index
related: [project, specification, data, htr-evaluation, domain-knowledge, editorial-model, accounting-encoding, architecture, design, journal, handoff]
---

# INDEX

Navigation and glossary of the DoCTA knowledge base. These documents hold the distilled project context, written to be read both by people and by agents, and they are the source of truth for how the project understands its sources, its methods and its own decisions; the code is the disposable artifact. What the project is and where it stands is `project.md`.

## Document register

File names follow the Promptotyping naming contract, lowercase canonical function names with `INDEX.md` and the repo-root `CLAUDE.md` as the registered uppercase exceptions, and specializations as `<subject>-<function>.md`.

| Path | Function | Routing question | Update trigger |
|---|---|---|---|
| `INDEX.md` | Navigation | What exists, where does it belong, and how is it read? | path, function, or constitutive term changes |
| [project.md](project.md) | Charter | What is this project, for whom, and on what material basis? | project identity or scope changes |
| [specification.md](specification.md) | Specification | What must the pipeline and site deliver, against which criticism and constraints? | requirement or decision changes |
| [data.md](data.md) | Material | Which data exist, what can each source carry, where does it break, and which rights rules bind third-party material? | data source, quality finding, or rights rule changes |
| [htr-evaluation.md](htr-evaluation.md) | Evaluation methodology | How are transcriptions produced, compared, and released for scholarly use? | reference class, protocol, metric, or release rule changes |
| [domain-knowledge.md](domain-knowledge.md) | Domain Knowledge | Which scholarly framework governs interpretation (SiCPAS, praxeology, BeNASch, epistemology)? | domain model or method changes |
| [editorial-model.md](editorial-model.md) | Domain Knowledge, account-book specialization | Which editorial objects, evidence relations and decisions structure the account-book pilot? | editorial vocabulary changes |
| [accounting-encoding.md](accounting-encoding.md) | Encoding specification | How do those objects become JSON, TEI and RDF, and which validator checks which rule? | representation or validation rule changes |
| [architecture.md](architecture.md) | Architecture | How are site and pipeline technically realised? | implementation architecture changes |
| [design.md](design.md) | Design | How does it look and behave, and what was rejected, with reasons? | design-system or interaction changes |
| [journal.md](journal.md) | Provenance | How did we get here? | a substantive decision or finding closes |
| [handoff.md](handoff.md) | Handoff | Which received deltas still require integration or rejection? | a handoff point arrives or is resolved |

## Reading order for agent context

1. **INDEX.md** (this document), orientation
2. **handoff.md**, open handoff points
3. **project.md**, what the project is
4. **data.md**, which data exist and where they break
5. **htr-evaluation.md**, how transcriptions are produced, compared and approved
6. **domain-knowledge.md**, the scholarly framework needed for correct interpretation
7. **specification.md**, what the work has to deliver and against which criticism
8. **architecture.md**, how site and pipeline are built
9. **design.md**, why it looks and behaves as it does
10. **editorial-model.md** and **accounting-encoding.md**, read together before any work on the account-book pilot
11. **journal.md**, decision history, read on demand

## Source documents (`sources/`)

The knowledge files distil the source documents listed below. **These files are project-internal and are not part of the public repository**, because they contain unpublished proposal text and personal correspondence. The table stays here so that the provenance of the knowledge files remains traceable; the paths lead nowhere in the public clone.

| File (project-internal) | Function | Captured in knowledge? |
|-------|----------|----------------------|
| `sources/strategische-planung.md` | Master planning document | Yes, distributed across all files |
| `sources/requirements-projektleitung.md` | Requirements of the project lead | Yes, in specification.md |
| `sources/raitbuch-2-analyse.md` | Source analysis of account book 2 | Yes, in data.md |
| `sources/coocr-htr-epistemologie.md` | Epistemological argument | Yes, core concepts in domain-knowledge.md |
| `sources/fwf-proposal-2025.md` | Rejected first submission. The file name comes from an earlier filing and is misleading. | Partly. Bibliography and work-package detail are not captured. |
| `sources/gutachten-ersteinreichung.pdf` | Review of the first submission | Yes, in specification.md |
| `sources/quellen-katalog.csv` | Source catalogue | Yes, analysis in data.md |
| `sources/sicpas-modell.svg` | SiCPAS diagram | As text in domain-knowledge.md |

## Exported data (`docs/data/`)

Unlike `sources/`, this folder is fully contained in the public repository. The site computes every figure it shows from the files below; the table names what each file holds rather than how much.

### Used by the site

| File | Content |
|------|---------|
| `data/sources.json` | The source catalogue, cleaned from the CSV |
| `data/source_mapping.json` | Mapping from Transkribus document titles to catalogue shelfmarks |
| `data/pipeline/register_summary.json` | Compact projection of the page register, per document the identity fields, the page counts by state, attribution and edition links, and whether a TEI file exists |
| `data/pipeline/transcriptions/*.json` | Text of the documents the pipeline transcribed itself, read by the viewer for documents without a Transkribus transcription |
| `data/tei/*.xml` | Generated TEI P5, one file per document that carries text, plus `register.xml`, the corpus-wide entity register |
| `data/transcriptions/*.json` | Inventory transcriptions exported from Transkribus PAGE XML |
| `data/entities/*.json` | Line-anchored entity extraction per document, read by the viewer's entity layer and encoded into the TEI |
| `data/graph.jsonld` | Aggregated entity graph (JSON-LD) over every document with an extraction, read by the network view on `exploration.html` |
| `data/benchmark/summary.json` | Published export of the prompt benchmark, read by `benchmark.html`. The runs themselves stay in `evaluation/benchmark/runs/`, which remains their source of truth |
| `data/demo/*.json` | Entity and relation extraction demo on the inventory Thaur A 49.1, kept as fallback |

### Pipeline inputs kept under `data/`

`data/edition_pages.json` is the page list with IIIF references for the documents the pipeline transcribes itself, read by the register build and the edition runner. `data/inventaria_mapping.json` is the harvested mapping from Transkribus documents to their published Inventaria edition; `build_register.py --project` folds both into the register projection.

### Generated by the pipeline

`data/pipeline/register_summary.json`, `data/pipeline/transcriptions/`, `data/tei/` (including `register.xml`), `data/entities/` and `data/graph.jsonld` are written by the pipeline scripts and are never edited by hand; `check_pipeline.py` checks them against the register and against one shared entity id space.

### Exploration artifacts, loaded by no page

They stay in the repository because they document how the data situation was established.

| File | Content |
|------|---------|
| `data/stats.json` | Aggregate counts written by `scripts/build_stats.py` in the prototype phase. The site computes its figures from `data/sources.json` and the register projection instead, so no page loads this file |
| `data/persons.json`, `data/relations.json` | Persons and relations from SiCProD. They drove the prototype's network and faceted search; no current page loads them |
| `data/places.json`, `data/institutions.json`, `data/functions.json` | Places, institutions and court offices from SiCProD, likewise from the prototype phase |
| `data/transkribus_collection.json` | The full collection with document metadata |
| `data/transkribus_status.json` | Transcription status of every document in the collection |
| `data/raitbuch2_pages.json` | Page list of account book 2 with IIIF keys |

## Evaluation (`evaluation/`) and experiments (`experiments/`)

| Folder | Purpose |
|--------|---------|
| `evaluation/benchmark/` | The versioned prompt benchmark, fixed page set, versioned prompts, repeated runs with full provenance, stratified metrics. Its published export drives `benchmark.html`. |
| `evaluation/pilot/` | The benchmark prompts run on continuous, uncurated material, one full inventory document and a run of consecutive account-book openings. |
| `evaluation/pilot2/` | The same frozen prompt configuration on a wider slice of unseen material, three further inventory documents and a later section of account book 2, which tests whether the observed behaviour holds across hands and castles. |
| `evaluation/checks/` | Reference-free checks over the transcription runs. The arithmetic probe compares the item amounts of an account-book block against its Summa line and names the pages worth reading at the image. |
| `evaluation/edition/` | The pipeline's own transcriptions for edition use, one run per page, append-only, without summary or metrics because nothing is repeated or measured. Source of the text of documents without a Transkribus transcription; that text stays unrevised machine output until review. |
| `experiments/transcription-test/` | The first VLM transcription test of 26.08.2026 with its raw outputs and synopsis viewer. Frozen; it is the origin of benchmark iteration it01 and the only remaining experiment. |

Every folder under `evaluation/` carries its own README with protocol and re-entry instructions; `experiments/transcription-test/` documents itself through its viewer and its runner script alone. The methodological reading of the results is in `htr-evaluation.md`. All transcriptions produced in these folders are unrevised machine output until they have been checked at the facsimile and editorially accepted.

## Glossary

Terms constitutive for this knowledge base; the long forms live in the linked documents.

**HTR.** Umbrella term for machine transcription here. A vision-language model processes a whole page image; Transkribus recognises text on a layout and line structure. Both produce candidate text, and neither produces an edition (`htr-evaluation.md`).

**Raitbuch.** Account book of the Tyrolean court chamber. Account book 2 is the working volume (`data.md`).

**SiCPAS.** The data model connecting sources, persons, court structures and practices that guides interpretation (`domain-knowledge.md`).

**Run.** One immutable transcription of one page with full provenance. A better transcription is a new run, never an edit; run ids encode their origin cohort (`pipeline/README.md`).

**Edition cohort.** The run cohort of the pipeline's own transcriptions intended for edition use, one run per page and no metrics, as opposed to the measuring cohorts benchmark, pilot and pilot2.

**Naming contract.** The Promptotyping convention that file names are the primary routing signal; see the document register above.
