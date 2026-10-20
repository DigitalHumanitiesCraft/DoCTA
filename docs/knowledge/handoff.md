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
updated: 2026-10-20
---

# Handoff

## Current result

The historical project lead tested the working edition and sent feedback on 2026-10-20. Her corrections were saved as intended. Annotation appeared to her not to work, most likely because she used the read-only GitHub Pages viewer, where the annotate controls are hidden without a hint that only the locally started edition can annotate. She is now a collaborator on the repository, clones it rather than forking, and works on `main` through the local editor. The operator replied on 2026-10-20 that a detailed answer follows, that annotation works only in the locally started working edition, and asked whether the proposal or the data matters more to her now, suggesting a first passage that can directly carry an argument for the proposal. Her requests and the findings on them are listed in [plan.md](plan.md#feedback-round-of-2026-10-20).

On 2026-10-20 the operator decided that the entire website, the guide included, is English, and that unclear readings receive one uniform notation in the transcription text, shown with a tooltip, editable in correction mode and converted into TEI ([specification.md](specification.md#interface-language-and-unclear-readings-decided-2026-10-20)). The notation (`[?]`, `[word?]`), its TEI form and line deletion are implemented in the working tree.

The exploration entities she asked about are LLM output. They come from the `entities_it01` extraction, are anchored to one line each and carry no human input. The PAGE annotations of the Inventaria edition are not used for them.

Internal working version 0.2.0 integrates source annotation into the reading interface. One nonmodal field beside the selected passage contains person, term, place and date categories, assignments, inline register-entry creation and editing, and occurrence history. Machine annotation proposals are excluded from the working interface. Index beside Viewer opens the saved person and place indexes and controlled vocabulary with search, category filters and exact source links. The register sidebar remains available during source work. Dates retain their source quotation with optional normalization, bounds and uncertainty. Saved changes retain actor, timestamp and previous values. Register assignments export as JSON and remain separate from generated TEI and graph entities. Windows and macOS starters share the locked Python environment. Native macOS execution and the editor's own acceptance of the new interaction remain unverified.

- The inventory path runs from model transcription through entity extraction to TEI that passes both validation stages for the documents where it was run. `evaluation/edition/README.md` names those documents and the pages still without an image reference. Model runs remain unrevised machine transcription. Saved human corrections are separate revisions and confer no document-wide scholarly acceptance.
- The viewer has a loopback write service, browser drafts, revision conflict checks and an explicit edition rebuild. Save and reload have been exercised against isolated copies of real project data. The simplified editor records corrections without page approval controls or time tracking. Demonstration changes supply technical evidence only.
- The readiness review covers register rebuilds concurrent with saving, repeated correction imports after later edits, focused corrections during unload, TEI cache invalidation and alternate-root isolation. Regression tests accompany the fixes. Local browser checks may use already cached source images; their success does not establish external image-service availability or installation on the recipient's machine.
- Account book 2 has measuring runs and no released TEI. `pipeline/accounts/build_edition.py` prepares a checksummed TranscriptionRevision and manifest from a selected run and text-identical PAGE. Genuine page anchors and accepted accounting annotations remain required for TEI/RDF generation (`accounting-encoding.md`).
- Inventaria import is executable and has been exercised on a public document with its PAGE annotations. Reuse terms remain pending. Missing silver-inventory image keys require authorized Transkribus metadata, for which a file-based import is available.
- [plan.md](plan.md) specifies the research-first walkthrough, historical pilot, correction provenance, contributions and acceptance evidence. The [working guide](../guide.html) explains installation and current use. Neither document establishes scholarly acceptance or publication permission.

## Current boundaries

- The historical editor still needs to assess correction, annotation and index interaction on a real research passage. The research question and source selection precede this assessment.
- A representative, convention-bound reference sample is required before transcription accuracy or correction patterns can support a scholarly claim. Time tracking is excluded.
- Rights and reuse terms for imported source material require institutional agreement. Missing image references require authorized source metadata, while credentials remain with the account holder.
- The editor-owned register is currently a separate JSON output. Its integration into TEI and graph requires an explicit mapping that preserves independent identities and source anchors.
- Single-line assignments are implemented. Only structural line insertion, split and merge require an anchor-migration contract. Excluding a line, marking an unclear reading and a mention made of segments that each sit in their own line keep every line identity and need no such contract.
- Lines that are not source text cannot yet be excluded. Emptying them is unsuitable ([plan.md](plan.md#boundaries-still-requiring-implementation-or-evidence)). The VLM `kind` of each line and the Transkribus region structure type are not carried into the register ([data.md](data.md#lines-that-are-not-source-text)).
- Open work from the feedback round: mentions across line breaks, SiCProD matching (to be asked of the project lead first), Transkribus access for the missing image keys and the Inventaria annotations as a source once reuse rights are settled. Site and guide are English in the working tree, with a persistent read-only hint on static hosting.
- The account-book release path still requires genuine PAGE anchors, accepted text, accepted accounting annotations and the specified validation chain.

## Open handoff points

### Priority between proposal and data

- Received: 2026-10-20
- Source: the operator's reply to the historical project lead's feedback
- Target: [plan.md](plan.md#joint-walkthrough), source and passage selection
- Context: The operator asked whether the proposal or the data matters more to her now and suggested starting with a passage that can directly carry an argument for the proposal.
- Blocker: Her answer is pending. It determines the next source selection.

### Stored sidecars outside this checkout

- Received: 2026-10-20
- Source: feedback-round review of the repository state
- Target: [architecture.md](architecture.md#retained-research-tag-data)
- Context: `pipeline/annotations/` and `pipeline/registry/` do not exist in this checkout and are created on first write. Whether annotation or register files exist in another working copy is unknown; the tag backend and its sidecars were removed on 2026-10-20.
- Next action: Check the other working copies before any migration or recovery step assumes these files.
