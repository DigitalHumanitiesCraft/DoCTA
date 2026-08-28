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
updated: 2026-08-28
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

The training request is a design constraint rather than a courtesy. A pipeline the project lead cannot operate or inspect herself fails the requirement even if its output is correct.

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
| 9 | Evaluation of technical procedures missing | The versioned prompt benchmark measures each prompt iteration with repetitions, stratified metrics and full provenance. `htr-evaluation.md` defines reference classes, task-specific metrics and the release rule. | Code and method |
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

## Planned: annotation curation in the viewer

Announced in the feedback response of 28.08.2026 and next in line after the transcription review: the editor-in-the-loop of the review mode extends to the entity annotations. Machine entity proposals are already anchored to the source line; the viewer gains their direct correction and confirmation, with source line, model provenance, review status and the reasoned correction preserved for every assignment. Reconciliation targets are SiCProD for persons and functions, Wikidata and the GND additionally for persons and for places, and the Inventaria terminology together with the Getty Art & Architecture Thesaurus for object names and controlled object categories. Confirmed corrections may feed later extraction runs. Two decisions are open and belong to the project lead: the priority object categories, and the order in which the reconciliation sources are consulted.

## Open questions

- Whether bilingual presentation in German and English is needed is unresolved. The site is currently English; the source material and the working documents are German.
- Which case study the resubmission builds on is not decided (see domain-knowledge.md).
