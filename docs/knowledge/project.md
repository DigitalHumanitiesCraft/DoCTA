---
title: Project
project:
  name: DoCTA
  repository: https://github.com/DigitalHumanitiesCraft/DoCTA
method:
  name: Promptotyping
  url: https://dhcraft.org/Promptotyping/
status: complete
language: en
version: "1.0"
created: 2026-08-28
updated: 2026-08-28
authors: [Christopher Pollin]
generated-with: Claude Code (Claude Fable 5)
template:
  name: Vorlage Projekt-Wissensdokument
  version: 0.3
  url: https://dhcraft.org/Promptotyping/promptotyping-document/project
  alias: https://dhcraft.org/Promptotyping/#promptotyping-document-project
knowledge-sources:
  institutions:
    Digital Humanities Craft OG: https://dhcraft.org
  datasets:
    SiCProD: https://sicprod.acdh-dev.oeaw.ac.at/
    Transkribus collection 2197991: https://app.transkribus.org/collection/2197991
    Inventaria edition: https://www.inventaria.at/
related: [INDEX, specification, data, domain-knowledge, journal, handoff]
---

# Project

DoCTA (Doing Court in the Tyrolean Alps) studies court practice at the court of Sigismund of Tyrol (1427–1496). This document is the charter, what the project is, for whom it works and on what material basis.

## What the project is

The digital component is an agentic edition pipeline. It turns facsimiles of fifteenth-century court records held by the Tyrolean State Archives into research data and a digital edition. Its stages are vision-language-model transcription, a versioned prompt benchmark, scholarly review at the facsimile, TEI encoding with a corpus-wide entity register, and a static site that publishes the state of the work. The digital instruments are heuristic tools in service of historical research questions about court practice; the tools themselves are never the object of the project.

Two commitments hold everywhere. All model output remains unrevised machine transcription until a scholar approves it, and is marked as such wherever it is displayed. Every derived artifact carries its provenance, down to the model, prompt iteration and work step that produced it.

## Proposed next form: a working edition

Proposed to the project lead on 28.08.2026 and not yet confirmed: DoCTA develops into a working edition, a shared working environment tailored to the project lead's research and material, in which account books, inventories, court ordinances, copybooks and further court sources are brought together for indexing and comparative analysis. In a resubmission this takes the form of a service arrangement, Digital Humanities Craft supporting the work with the already developed environment, while the centre of gravity stays with the historical research. The transcription review in the viewer is the model for the next step, an editor-in-the-loop for the annotations, specified in `specification.md`.

## Who it is for

The historical project lead at the University of Salzburg reads, reviews and accepts transcriptions and sets the scholarly requirements. Digital Humanities Craft OG builds and maintains the digital component. Reviewers of a planned FWF resubmission are the third audience; for them the prototype makes the proposed methods checkable on the real material. The public About page carries the reviewer-facing framing, and `specification.md` holds the requirements together with the review criticism of the first submission and how it was answered.

## Material basis

Transkribus collection 2197991 holds the facsimiles, account books (Raitbücher), castle and personal inventories, copybooks and court ordinances, treated as one connected corpus. Account book 2 is the working volume. The archival source catalogue maps the collection against the holdings. SiCProD supplies persons, places, court offices and relations of Sigismund's court through a public API. A subset of the castle inventories was edited and published by the Inventaria project and is used with attribution under the rights rule in `data.md`. The detailed data description, including where each source breaks, is `data.md`.

## State

The reviewer-facing prototype went public in February 2026 and answered the review critique of the first submission. Since August 2026 the site is organised around the pipeline stages, and the edition pipeline runs end to end, from the pipeline's own transcription of a source through entity extraction to validated TEI. The qualitative gaps that remain, an editorially accepted account-book reference and the comparison with specialised HTR, are named in `htr-evaluation.md`; decisions and their reasons are in `journal.md`.

## Method

The project is built with Promptotyping. The knowledge base in this folder is the source of truth for how the project understands its sources, methods and decisions, and the code is the disposable artifact. [coOCR/HTR](https://dhcraft.org/co-ocr-htr) is the sister project on transcription quality assessment and serves as design and method reference.
