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
updated: 2026-09-20
---

# Handoff

## Current result

State of 2026-09-20, checked against the repository.

- The inventory path runs from the pipeline's own transcription through entity extraction to TEI that passes both validation stages, for the documents where it was run. `evaluation/edition/README.md` names those documents and the pages still without an image reference. All of that text is unrevised machine transcription.
- The review step is implemented in the viewer and in `pipeline/apply_review.py` and is covered by tests. It has never been run with a real export, so the register holds no reviewed page and no review run.
- No edition path is built for the account books. Account book 2 has measuring runs under `evaluation/` and no TEI. `pipeline/accounts/` implements anchoring, the record models, the staleness rule and the validators of the encoding specification, and the generating build remains specification (`accounting-encoding.md`).
- The decision of 2026-09-20 to turn DoCTA into a locally run editing tool is recorded in `specification.md`. The decisions that lie with the project lead are listed there as well.

## Open work after the reviewed sample exists

The scholarly review of the pilot 2 transcriptions under `evaluation/pilot2/review/` ended in process lessons. None of them is implemented in a prompt iteration, in the runner or in the evaluation. They are open work for a new prompt iteration and a runner change once the reviewed sample of the effort measurement below exists.

- Forbid the transcription of show-through also where it reads in the normal direction, define the empty page positively and make the `empty` field mandatory. Iteration 02 covers only mirror-inverted show-through.
- Split an opening at the detected gutter with a small overlap. The runner cuts at half the image width, which puts the line ends of the verso at the cut edge.
- Forbid invented editorial apparatus, meaning deletion markup without a visible stroke and bracketed expansions without a visible abbreviation sign.
- Read numerals in a separate pass on the cropped line image, and stop reading repeat agreement on numbers as accuracy.
- Request a third run where the repeats of a page diverge. `check_pipeline.py` reports such pages as INFO and starts no run.
- Forbid placeholder text in the `text` field, offer fields for illegible and for deleted text instead, and keep such lines out of line count and agreement. Iteration 02 still asks for `[...]` as line text.
- Supply a genre lexicon per document. Iteration 02 carries one glossary for the whole inventory stock.

## Open handoff points

This Process Inbox contains only open handoff points. Before using a point, verify its source and current target. Integrate durable content into the responsible Declarative or Action Document, record the subject, source, target, and result or reason for rejection in `knowledge/journal.md`, and then remove the point completely.

- **Feedback round of the project lead.** Source: the response document and mail of 28.08.2026, which answered the fourteen feedback points with their statuses (recorded in `journal.md`) and offered a joint online walkthrough. Waiting on her next round; collect what comes and incorporate it.
- **Inventaria coordination through the project lead.** To clarify with the Inventaria project: whether DoCTA may use the published transcriptions in the current form and later bind the annotations as reference data. DoCTA offers its generated TEI files in return and settles attribution and licence terms directly. Target: the rights rule in `data.md` gains the agreed terms; until then the three-tier rule stands unchanged.
- **Transkribus images for the remaining sources.** Needed from the project lead: the relevant collection links or ids, the documents or shelfmarks, and authorised account access, with credentials staying at the account holder. Target: `docs/data/edition_pages.json`, then `evaluation/edition/run_edition.py` over the five A 006/A 024 inventories.
- **Ground version of the revised proposal.** When it arrives, reconcile the About page, the historical research questions and the cross-source analysis with it. Target: `docs/about.html`, `project.md`, `specification.md`.
- **Effort measurement for the review step.** A representative sample spanning hands, source types and model qualities must be worked through in the viewer's curation workflow before correction volume and scholarly decision need can be quantified. Target: `htr-evaluation.md`.
