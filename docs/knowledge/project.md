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
updated: 2026-09-21
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

## Working edition

The project lead's reply supplied on 2026-09-21 expresses willingness to use the working edition proposed on 2026-08-28 and requests a walkthrough. It asks which parts are already usable and which belong to a funded project. This establishes general interest. The commissioned scope and scholarly acceptance remain to be agreed.

DoCTA brings account books, inventories, court ordinances and copybooks into a working environment for indexing and comparative analysis. The local editing decision of 2026-09-20 gives the editor direct control over versioned research data. A future service arrangement with Digital Humanities Craft remains a proposal whose scope must follow the historical pilot. [plan.md](plan.md) specifies the walkthrough, contributions and evidence needed to make that scope concrete. [specification.md](specification.md) separates the local editing functions from the public static site.

## Who it is for

The historical project lead at the University of Salzburg reads, reviews and accepts transcriptions and sets the scholarly requirements. Digital Humanities Craft OG builds and maintains the digital component. Reviewers of a planned FWF resubmission are the third audience; for them the prototype makes the proposed methods checkable on the real material. The public About page carries the reviewer-facing framing, and `specification.md` holds the requirements together with the review criticism of the first submission and how it was answered.

## Material basis

Transkribus collection 2197991 holds the facsimiles, account books (Raitbücher), castle and personal inventories, copybooks and court ordinances, treated as one connected corpus. Account book 2 is the working volume. The archival source catalogue maps the collection against the holdings. SiCProD supplies persons, places, court offices and relations of Sigismund's court through a public API. A subset of the castle inventories was edited and published by the Inventaria project and is used with attribution under the rights rule in `data.md`. The detailed data description, including where each source breaks, is `data.md`.

## State

The reviewer-facing prototype went public in February 2026 and answered the review critique of the first submission. Since August 2026 the site is organised around the pipeline stages. What the pipeline has produced so far and what it has not is stated in `handoff.md` under the current result. The qualitative gaps of the evaluation, an editorially accepted account-book reference and the comparison with specialised HTR, are named in `htr-evaluation.md`; decisions and their reasons are in `journal.md`.

## Method

The project is built with Promptotyping. Maintained project knowledge guides a versioned implementation whose behavior is checked against source evidence and the editor's requirements. Research goals, material selection and the intended use of annotations determine the working edition's scope. [coOCR/HTR](https://dhcraft.org/co-ocr-htr) is the sister project on transcription quality assessment and serves as design and method reference.
