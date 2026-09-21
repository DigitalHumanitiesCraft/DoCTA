---
title: Plan
project:
  name: DoCTA
  repository: https://github.com/DigitalHumanitiesCraft/DoCTA
method:
  name: Promptotyping
  url: https://dhcraft.org/Promptotyping/
status: draft
language: en
created: 2026-09-21
updated: 2026-09-21
authors: [Christopher Pollin]
template:
  name: Vorlage Plan
  version: 0.3
  url: https://dhcraft.org/Promptotyping/promptotyping-document/plan
related: [INDEX, project, specification, data, htr-evaluation, editorial-model, accounting-encoding, handoff]
---

# Plan

The working edition supplies the environment for a bounded historical pilot. General willingness to use it is documented in the project lead's reply supplied on 2026-09-21. The reply does not establish an accepted feature set, funding commitment, transcription convention or publication permission.

## Joint walkthrough

Start with [the silver inventory A 006.8 and .9](https://dhcraft.org/DoCTA/viewer.html?doc=12647153&page=1). Its first page demonstrates the distinction between a source image, a machine reading and an editorial decision. The available transcription covers only part of the document. Use the right-page image focus, inspect a real discrepancy together, enter a correction and explain the saved state. A technical demonstration correction must stay in an isolated test copy until a scholar confirms the reading.

Open [the Thaur inventory A 049.1](https://dhcraft.org/DoCTA/viewer.html?doc=11328300&page=1) to discuss attribution, existing external transcription and anchored entity proposals. A Transkribus workflow status does not establish a reference transcription under the project's own convention. Follow the Inventaria edition link to compare the published source context.

The public viewer supports a browser draft and JSON export. Repository write-back uses the loopback editor started with `start-editor.ps1`. Demonstrate save, reload, Reading and the validated TEI rebuild separately. Closing the browser is not publication. A local Git commit records a change, and pushing to the public repository is a separate operator action.

## Work sequence and acceptance

| Work | Required input | Concrete result | Acceptance evidence | Responsible decision |
|---|---|---|---|---|
| Local editorial pilot | Repository clone and one available source | Saved correction with original text and reviewer provenance | Reload reproduces the reading, a stale concurrent edit is rejected, generated TEI validates | Project lead accepts the working interaction |
| Source completeness | Authorized Transkribus metadata or exported document metadata | Page manifest with image references and explicit omissions | Expected page numbers match retrieved metadata, each reference resolves | Account holder provides access to the intended collection |
| Inventaria reuse | Permission covering the intended texts, annotations and publication | Provenance-preserving import with PAGE annotations | Completeness, line anchoring and annotation offsets checked, attribution and license recorded | Project lead coordinates permission with Inventaria |
| Transcription convention | Decisions on original spelling, abbreviation expansion, illegibility, deletion, foliation and line structure | One convention and a versioned, accepted reference sample | Every sample page reviewed against its image and tied to the convention | Historical editor |
| Recognition evaluation | Accepted sample and a specialized HTR baseline | Comparisons by page and source stratum, with numeral errors inspected separately | Held-out evaluation, line omissions, normalization profile and failed cases reported | Project lead approves fitness for the research task |
| Effort measurement | Representative correction sessions under the convention | Observed active review time and documented editorial decisions | Timing scope, source stratum, interruptions and corrections are inspectable | Historical editor records actual work |
| Inventory annotations | Controlled vocabulary and verified transcription anchors | Accepted or rejected entity decisions with normalized form and authority URI | Decisions survive reload and become stale when their source text changes | Historical editor resolves ambiguous identity and category |
| Account-book edition | Real PAGE anchors, accepted text and an accepted Annotation Set | TEI and RDF for a selected accounting passage | JSON contracts, RELAX NG, Schematron and SHACL all pass | Historical editor confirms accounting interpretation |
| Historical pilot | Source passage, research question and an observable contrary finding | Traceable claims connecting source passages across genres | Each claim resolves to evidence and distinguishes interpretation from transcription | Project lead chooses the case and interprets it |
| Proposal revision | Pilot evidence and revised proposal text | Methods, responsibilities and scope matched to demonstrated work | Every promised output has an input, acceptance criterion and owner | Project lead agrees scope, resources and submission text |

Each step may expose a change needed in an earlier one. Bulk recognition remains dependent on the scientific release conditions in [htr-evaluation.md](htr-evaluation.md). No new paid recognition run is required for the local editing demonstration.

## Decisions to obtain in the conversation

| Decision or input | Why it is needed | Smallest useful answer |
|---|---|---|
| First source passage and research question | A source-wide promise cannot be tested by a generic prototype | Select one passage and state the historical observation sought |
| Edition convention | A correction cannot be evaluated without specifying the target reading | Decide how the selected passage represents spelling, abbreviation and uncertainty |
| Representative reference | Repeated agreement between machines does not establish accuracy | Name pages spanning the relevant hands and layouts, and who will accept them |
| Inventaria permission | Public readability does not determine reuse terms | Confirm allowed corpus, annotation reuse, attribution, license and publication |
| Missing Transkribus pages | The viewer can only open references actually present | Supply collection/document access or a metadata export with page image keys |
| Working scope | Willingness to use the edition does not define a commissioned deliverable | Distinguish a correction pilot, an accepted pilot edition and a later funded corpus |
| SiCPAS interpretation | Entity occurrence alone cannot establish a practice or event | Annotate one real action and explain the evidence needed to aggregate an event |

## Historical pilot proposal for discussion

A source-bound question is how a documented transfer or payment places a person in relation to court material and an institution. An inventory may attest a holding or transfer, an account may attest a dated payment with a stated unit, and a court ordinance may prescribe a task. These are different evidential roles. Their combination requires explicit temporal and identity checks.

Use the selected passage to decide whether the research needs a material inventory, an accounting event, or a comparison of prescribed and recorded practice. Raitbuch 2 remains the working account book. Court kitchen and provision or pay outside the territory remain candidate cases until the project lead selects one.

A negative finding must remain representable. A payment without a named purpose cannot establish the corresponding practice, and a shared name without corroboration cannot establish identical persons. A proposed cross-source link therefore records its evidence and the reason an alternative reading was rejected or left open.

## Effort protocol

The viewer timer records active seconds between an explicit start and pause and pauses when the browser tab is hidden or the document changes. The review event records this interval, interaction count and a decision note. Interaction count includes changed decisions and is not a count of independently adjudicated scholarly questions.

The historical editor selects a sample covering hands, source genres, layouts and difficult readings. Work on the whole selected passage, including parts that require no change. Record reading and correction together when the timer covers both. Record breaks outside the active interval and use the note for unresolved interpretation. Do not divide one short demonstration by the entire corpus.

Report observed time per reviewed page or opening with its transcription extent, corrected lines and kinds of intervention. Character and word error rates require an accepted reference. Numerals, omissions and monetary units need separate inspection because a small character error can change the historical interpretation. The sample must be large and varied enough for the intended inference before extrapolation is considered.

## Boundaries still requiring implementation or evidence

Structural insertion, split and merge of transcription lines require stable new line identities, explicit region membership, facsimile geometry rules and migration of downstream annotation anchors. Emptying an existing hallucinated reading is supported while preserving its anchor. These are distinct operations.

The account-book preparation build creates a machine-unrevised TranscriptionRevision and checksummed manifest. A generated test PAGE carrier proves software behavior only. A scholarly build requires genuine source anchors and accepted accounting annotations, and may not manufacture either.

Prompt changes identified in [handoff.md](handoff.md) become a new version after the reviewed sample exists. Frozen prompts and measuring runs remain unchanged. The specialized HTR comparator, proposal revision and scholarly approval remain explicit dependencies.
