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

- The inventory path runs from model transcription through entity extraction to TEI that passes both validation stages for the documents where it was run. `evaluation/edition/README.md` names those documents and the pages still without an image reference. Model runs remain unrevised machine transcription. Saved human corrections are separate revisions and confer no document-wide scholarly acceptance.
- The viewer has a loopback write service, browser drafts, revision conflict checks and an explicit edition rebuild. Save and reload have been exercised against isolated copies of real project data. The simplified editor records corrections without page approval controls or time tracking. Demonstration changes supply technical evidence only.
- Account book 2 has measuring runs and no released TEI. `pipeline/accounts/build_edition.py` prepares a checksummed TranscriptionRevision and manifest from a selected run and text-identical PAGE. Genuine page anchors and accepted accounting annotations remain required for TEI/RDF generation (`accounting-encoding.md`).
- Inventaria import is executable and has been exercised on a public document with its PAGE annotations. Reuse terms remain pending. Missing silver-inventory image keys require authorized Transkribus metadata, for which a file-based import is available.
- [plan.md](plan.md) specifies the research-first walkthrough, historical pilot, correction provenance, contributions and acceptance evidence. The [German working guide](../guide.html) explains installation and current use. Neither document establishes scholarly acceptance or publication permission.

## Current boundaries

- The historical editor still needs to assess correction, annotation and index interaction on a real research passage. The research question and source selection precede this assessment.
- A representative, convention-bound reference sample is required before transcription accuracy or correction patterns can support a scholarly claim. Time tracking is excluded.
- Rights and reuse terms for imported source material require institutional agreement. Missing image references require authorized source metadata, while credentials remain with the account holder.
- The editor-owned register is currently a separate JSON output. Its integration into TEI and graph requires an explicit mapping that preserves independent identities and source anchors.
- Single-line assignments are implemented. Structural line insertion, split, merge and multi-line spans require an anchor-migration contract before implementation.
- The account-book release path still requires genuine PAGE anchors, accepted text, accepted accounting annotations and the specified validation chain.

## Open handoff points

Keine offenen Handoff-Punkte.
