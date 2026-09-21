---
title: Specification
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
  name: Vorlage Specification
  version: 0.3
  url: https://dhcraft.org/Promptotyping/promptotyping-document/specification
  alias: https://dhcraft.org/Promptotyping/#promptotyping-document-specification
related: [INDEX, project, data, htr-evaluation]
---

# Specification

## Project frame

| | |
|---|---|
| Project | DoCTA (Doing Court in the Tyrolean Alps) |
| Project lead | The project lead, University of Salzburg |
| Digital humanities component | Digital Humanities Craft OG |
| Phases | 1: Promptotyping, 2: workflow, 3: web application, 4: training |
| Funding context | Planned resubmission of the research proposal |

## What the work has to deliver

The present goal is an agentic edition pipeline. The Transkribus facsimiles of the Tyrolean State Archives, covering account books (Raitbücher), inventories, copybooks and court ordinances, are turned into research data and a simple digital edition. Every stage is versioned and verifiable. Machine output remains marked as unrevised until it has been checked against the facsimile and editorially accepted. An accepted page becomes evaluation data only when it is assigned to a named evaluation corpus.

This is a reframing of the earlier goal rather than a replacement of it. The prototype of February 2026 had to convince a reviewer that the methods work; the pipeline has to actually produce the data. The requirements of the project lead below are unchanged by that shift, and the ten points of review criticism remain the checklist the eventual resubmission has to satisfy.

## Requirements of the project lead

Recorded in her own words and rendered here in English.

**Audience.** In the first instance herself, in order to answer her own research questions. The proposal names no further audience.

**Design.** Functional to the point of being irrelevant.

**Core wish.** To be able to see who does what with which objects and where.

**Features.**

- A web application with network, time and space visualisations
- A network of persons and objects
- Faceted search and analytical functions
- Links to authority data (GND, Wikidata)

**Source priorities.**

1. Account books (Raitbücher)
2. Court ordinances, including Hs. 2466 to 2469, the wedding documents of 1484
3. Inventories
4. Copybooks

**Wish list.**

- Advice on the semantic model and ontology (CIDOC-CRM, ACE guidelines)
- A workflow pipeline from source through HTR and TEI to annotation, RDF and visualisation
- **Training for herself.** The project lead wants to learn the methods, not only receive their results.
- A prototype
- Annotation guidelines following a praxeological, verb-centred approach
- Data integration with SiCProD, Inventaria, Wikidata and the Getty AAT
- A glossary that could be built and integrated to improve recognition accuracy

The project lead must be able to operate and inspect the working edition herself. Requirements elicitation starts with her research question, then the source material, the information to annotate and the intended analysis. The interface demonstration follows that sequence, as specified in [plan.md](plan.md#joint-walkthrough). Recorded feature wishes guide discussion but do not establish an accepted scope.

## Locally run editing tool, decided 2026-09-20

DoCTA becomes a locally run editing tool, which is the answer to the constraint above. The editor clones the repository, edits the research data in an edit mode of the locally running application, and commits her changes herself with GitHub Desktop.

The local editor serves the same viewer through `pipeline/local_editor.py` on loopback. Browser drafts are explicitly saved to the page register with an append-only review record. The server rejects a draft whose base revision no longer matches the stored document. The source transcription remains unchanged. Empty corrected text removes a reading while retaining its line anchor. The working interface has one editor and documents saved corrections with actor, timestamp and before/after text. It provides no elapsed-time tracking, interaction counters or page approval workflow. A separate build produces validated TEI and the static text projection from saved corrections.

GitHub Pages keeps the browser draft and review JSON export. It has no repository write service. The editor starts the local service with `start-editor.cmd` on Windows or `start-editor.command` on macOS, reviews saved changes in GitHub Desktop and commits them. Publication remains a separate push. Native macOS execution still requires observation on the recipient system. The concrete pilot and acceptance sequence are in [plan.md](plan.md).

Which interfaces and functions the editor needs is worked out together with her.

### Controlled terms and retained tags

The editor assigns Begriffe to selected passages through the shared annotation field and builds the controlled vocabulary in the editorial register. Index exposes these terms and their source occurrences. The former separate Schlagwörter dialog is removed. Existing page and line tags remain in their original storage and are not silently promoted into register entries. Their optional migration requires a defined mapping of source scope and vocabulary identity.

## Technical constraints

| Constraint | Reason |
|-----------|--------|
| GitHub Pages, static | No backend, no server |
| Vanilla JavaScript, ES6 modules | No framework, no build process, no npm at runtime |
| Vendored dependencies | External libraries in `/lib/`, no CDN dependency |
| Public, no authentication | The site has to be reachable by reviewers and by the project team alike |

## Answering the review of the first submission

The first submission was rejected in its then form, and the review addressed primarily the digital humanities part. The ten points below are paraphrased. The column "answered by" records how the prototype phase responded to each; that response is history, and the resubmission has to carry it forward.

| # | Criticism | Answered by | Level |
|---|-----------|-------------|-------|
| 1 | Computational methods are standard, no evidence of innovation | Showing that standard methods work on these particular sources. The innovation is the application to Early New High German material. | Code |
| 2 | "Digital X" not original enough, question of relevance | Framing digital methods as instruments in service of court studies rather than as the founding of a field. | Text |
| 3 | LLM approaches not discussed | The pipeline demonstrates model integration end to end. Epistemic asymmetry is the conceptual frame. | Code |
| 4 | Linguistic challenges not addressed | The source explorer shows Early New High German in Kurrentschrift with abbreviations and regional variants. | Code |
| 5 | Historical linguistics missing | Not addressable in a prototype. Requires reference to Early New High German scholarship in the proposal text. | Text |
| 6 | Sources not sufficiently characterised | The source catalogue is categorised, filterable and sortable, with an availability tier per source. | Code |
| 7 | No exemplary source excerpts | Real inventory pages with working transcription, entities and a source link. Reference status is now stated explicitly. | Code |
| 8 | Project plan too generic | A working pipeline is the specific plan. Each stage is shown on concrete material. | Code |
| 9 | Evaluation of technical procedures missing | The versioned prompt benchmark measures each prompt iteration with repetitions, metrics reported per page and full provenance. `htr-evaluation.md` defines reference classes, task-specific metrics and the release rule. | Code and method |
| 10 | No fulfilment criteria for the hypotheses | Raw counts on the home page evidence data availability. Fulfilment criteria for historical hypotheses must be formulated per research question in the proposal, as observable evidence together with a refutation criterion. | Text and method |

Seven points are addressed directly in code. Point 9 has moved from a first test to a running measuring instrument. Points 2, 5 and 10 need explicit work in the proposal text and cannot be answered by building anything.

### Current evaluation boundary

| Object | State |
|--------|-------|
| CER on inventories | Measured against the small set of pages carrying formal `DONE` status. The convention assignment of the wider stock is unresolved. |
| CER and WER on account book 2 | No editorially accepted ground-truth transcription exists. Only variant stability, structural observation and scholarly spot checks are available. |
| Derived rates (relation coverage, source coverage, network metrics) | Only raw counts are shown. A rate needs a defined denominator, that is, an answer to what counts as fully covered, and that has not been fixed methodologically. |

The full review specification is in `htr-evaluation.md`.

## Success criteria

1. A reader opens the site and understands within minutes what the project does methodologically and where it stands.
2. The project lead can explore her research questions on real data.
3. The pipeline visibly runs from facsimile through machine transcription and measurement to an editorially accepted edition page.
4. Quality statements comprise evidence and decision status per mention and assertion, the availability tiers of the sources, and clearly marked experimental transcription metrics with their reference class.
5. The seven directly code-addressable points of review criticism are answered.

## Annotation curation in the viewer

The working viewer shows editor-owned annotations only. Selecting text within one saved line opens Person, Begriff, Ort and Datumsangabe. Right-click is an additional entry point, while a toolbar button and Alt+A keep the action accessible without it. Persons, places and terms link to the editorial register. Dates preserve their quotation with optional exact or bounded normalization and uncertainty. Opening the viewer or selecting text performs no model API call and does not display stored machine proposals.

Index beside Viewer provides a dedicated view of the saved persons, places and controlled vocabulary. Search covers names, spelling variants and notes. Category filters narrow the entries, and source links return to the exact assignment. Names never establish identity on their own. Entry creation and correction remain attached to source passages in the viewer. The persistence and publication boundaries are defined in [architecture.md](architecture.md#editorial-register-persistence).

Earlier machine extractions and curation sidecars remain available to the existing pipeline. Their provenance distinguishes DoCTA extraction from Inventaria transcription. The build still applies recorded accepted normalizations and rejected occurrences to generated TEI and graph and rejects stale decisions. This compatibility does not import those proposals into the working annotation interface. Editorial register assignments do not yet enter that generated output.

SiCProD, Wikidata, GND and the Getty Art & Architecture Thesaurus remain possible future reconciliation resources. External identity enrichment requires a separate editorial decision and is not part of the initial index-building workflow.

## Decisions that lie with the project lead

### Editor-owned registers and source-bound annotation

The working edition requires an editor-owned person index and controlled vocabulary. Identity and vocabulary decisions always belong to the historical editor. Exact source selection, access and reuse terms remain scholarly and institutional decisions. Current implementation work uses the available internal material.

The local editor uses new, name-independent person IDs, preferred names, spelling variants, optional notes and explicit links to source occurrences. Local name search suggests existing entries without merging identities. Equal names remain separate entries, distinguished in the interface by variants, notes or an ID fragment. External authority enrichment remains future work. The existing generated entity index groups by type and normalized label and must not be treated as evidence of historical identity.

Vocabulary entries carry preferred terms, variants, notes and an optional broader term. Source occurrences link to these entries. The editor supplies this vocabulary. Verbs may be recorded as terms, and no dedicated verb category exists in the initial interface. Classifying an occurrence as a cushion does not identify it with a particular physical object mentioned elsewhere. Individual-object identity and historical relations require a separate evidence contract.

Selection-based annotations retain quotation, line identity, UTF-16 positions and a saved-line digest. Changed text requires rechecking the anchor. Registry and assignment changes retain actor, timestamp and before/after values in the atomic registry file. Machine-proposal decisions retain an event history as well. Older sidecars remain readable without inventing past events. Editorial assignments are available in the viewer and JSON export, but do not yet enter generated TEI or the graph. Multi-line spans remain unsupported. Category labels describe the initial working vocabulary and do not resolve the wider research distinction between place, space, object identity and events.

The transcription source is displayed independently of annotation provenance. The current page names its recorded transcription model and human correction information, retaining the original producer after corrections. Missing imported model metadata is explicit. Provenance details expose the recorded prompt, hash and run date. Human corrections do not imply a complete scholarly review.

Windows and macOS launchers use the same Python service and locked dependencies, with first-use setup documented in the README. The server opens the browser after binding successfully. Windows execution and shell syntax are checked locally, while native macOS execution still needs verification on that platform. The CI configuration covers Linux, Windows and macOS without establishing that an unpushed change has run there.

These decisions remain with the historical project lead.

- The transcription convention with the permitted normalisations. `htr-evaluation.md` names it under the scholarly review points.
- The editor-owned vocabulary, including its preferred terms, variants, broader-term relations and any verbs useful to the research question. The wider distinctions between place and space, object identity, practice and event remain scholarly modelling decisions (`domain-knowledge.md`).
- The concrete scope and scholarly acceptance of the working edition (`project.md`).

## Open questions

- Structural line insertion, split and merge require an explicit identity, region and annotation-migration contract before they can safely change source anchors.

- Whether bilingual presentation in German and English is needed is unresolved. The site is currently English; the source material and the working documents are German.
- Which case study the resubmission builds on is not decided (see domain-knowledge.md).
