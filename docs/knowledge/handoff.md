---
title: Handoff
project:
  name: DoCTA
  repository: https://github.com/DigitalHumanitiesCraft/DoCTA
method:
  name: Promptotyping
  url: https://dhcraft.org/Promptotyping/
status: active
created: 2026-08-28
updated: 2026-09-21
---

# Handoff

## Current result

State of 2026-09-21. The local implementation and the remaining scholarly inputs are distinguished below.

Internal working version 0.2.0 integrates source annotation into the reading interface. One nonmodal field beside the selected passage contains person, term, place and date categories, assignments, inline register-entry creation and editing, and occurrence history. Machine annotation proposals are excluded from the working interface. Index beside Viewer opens the saved person and place indexes and controlled vocabulary with search, category filters and exact source links. The register sidebar remains available during source work. Dates retain their source quotation with optional normalization, bounds and uncertainty. Saved changes retain actor, timestamp and previous values. Register assignments export as JSON and remain separate from generated TEI and graph entities. Windows and macOS starters share the locked Python environment. Native macOS execution and the editor's own acceptance of the new interaction remain unverified.

- The inventory path runs from the pipeline's own transcription through entity extraction to TEI that passes both validation stages, for the documents where it was run. `evaluation/edition/README.md` names those documents and the pages still without an image reference. All of that text is unrevised machine transcription.
- The viewer has a loopback write service, retained browser drafts, revision conflict checks and explicit edition rebuild. A correction was saved and read back after reload in an isolated copy of the real silver-inventory data. The operator also saved a test correction in the local Thaur inventory register. This demonstrates persistence and is not a scholarly reading. The simplified editor records corrections without page approval controls or time tracking. The remaining browser draft and the test addition need reconciliation before a clean demonstration.
- Account book 2 has measuring runs and no released TEI. `pipeline/accounts/build_edition.py` prepares a checksummed TranscriptionRevision and manifest from a selected run and text-identical PAGE. Genuine page anchors and accepted accounting annotations remain required for TEI/RDF generation (`accounting-encoding.md`).
- Inventaria import is executable and has been exercised on a complete public document with its PAGE annotations. The private output is ignored by Git. Reuse permission remains pending. Missing silver-inventory image keys require authorized Transkribus metadata, for which a file-based import is available.
- [plan.md](plan.md) specifies the conversation examples, historical pilot, correction provenance, meeting answers, contributions and acceptance criteria. The German meeting guide was requested before the joint walkthrough was complete. General willingness to use the working edition has been received. Its concrete scope and scholarly acceptance remain to be agreed.

## Open work after the reviewed sample exists

The scholarly review of the pilot 2 transcriptions under `evaluation/pilot2/review/` ended in process lessons. None of them is implemented in a prompt iteration, in the runner or in the evaluation. They are open work for a new prompt iteration and a runner change once the reviewed reference sample exists.

- Forbid the transcription of show-through also where it reads in the normal direction, define the empty page positively and make the `empty` field mandatory. Iteration 02 covers only mirror-inverted show-through.
- Split an opening at the detected gutter with a small overlap. The runner cuts at half the image width, which puts the line ends of the verso at the cut edge.
- Forbid invented editorial apparatus, meaning deletion markup without a visible stroke and bracketed expansions without a visible abbreviation sign.
- Read numerals in a separate pass on the cropped line image, and stop reading repeat agreement on numbers as accuracy.
- Request a third run where the repeats of a page diverge. `check_pipeline.py` reports such pages as INFO and starts no run.
- Forbid placeholder text in the `text` field, offer fields for illegible and for deleted text instead, and keep such lines out of line count and agreement. Iteration 02 still asks for `[...]` as line text.
- Supply a genre lexicon per document. Iteration 02 carries one glossary for the whole inventory stock.

## Open handoff points

This Process Inbox contains only open handoff points. Before using a point, verify its source and current target. Integrate durable content into the responsible Declarative or Action Document, record the subject, source, target, and result or reason for rejection in `knowledge/journal.md`, and then remove the point completely.

- Joint acceptance of the local workflow. Begin with research goals, select the material, determine annotation needs and intended analysis, then demonstrate the relevant functions. The answers to the supplied questions about edition scope, source access, harvest and quantification are integrated in [plan.md](plan.md#joint-walkthrough). The editor still needs to perform the scholarly pilot herself, including the new register and annotation interaction.
- **Inventaria coordination through the project lead.** To clarify with the Inventaria project: whether DoCTA may use the published transcriptions in the current form and later bind the annotations as reference data. DoCTA offers its generated TEI files in return and settles attribution and licence terms directly. Target: the rights rule in `data.md` gains the agreed terms; until then the three-tier rule stands unchanged.
- **Transkribus images for the remaining sources.** Needed from the project lead: the relevant collection links or ids, the documents or shelfmarks, and authorised account access, with credentials staying at the account holder. Target: `docs/data/edition_pages.json`, then `evaluation/edition/run_edition.py` over the five A 006/A 024 inventories.
- **Ground version of the revised proposal.** When it arrives, reconcile the About page, the historical research questions and the cross-source analysis with it. Target: `docs/about.html`, `project.md`, `specification.md`.
- Correction evidence and reference sample. A representative sample spanning hands, source types and recognition qualities must be worked through before correction kinds and transcription accuracy can be assessed. Time tracking is excluded. Target: `htr-evaluation.md`.
- Structural line editing and multi-line spans. Single-line manual assignments are implemented. Define source regions, missing geometry and downstream anchor migration before introducing line insertion, split, merge or multi-line assignments. Integrating the editor-owned register into TEI and graph output requires an explicit mapping that preserves its independent identities.
