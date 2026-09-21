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

Begin with the project lead's research purpose. The operator set the conversation order on 2026-09-21. Tool demonstration follows the answers and does not determine the research scope.

1. Establish the historical question and what the editor wants to examine or change herself. The documented general wish is to study who does what with which objects and where. A specific first question remains to be chosen.
2. Select the material capable of answering that question, including a bounded passage. Account books are the leading research source. An inventory demonstration does not decide the pilot corpus.
3. Identify what must be annotated in that passage. Discuss source wording, interpretation, uncertainty and the needed unit of annotation before choosing categories.
4. Establish the intended use of the annotations, such as finding passages, comparing evidence, counting defined observations or reconstructing relations. This determines whether working tags suffice or a structured model is required.
5. Demonstrate the relevant functions and collect the editor's experience against this concrete task.

Use [the Thaur inventory A 049.1](https://dhcraft.org/DoCTA/viewer.html?doc=11328300&page=1) for the initial interface demonstration when it fits the conversation. The [local editor](http://127.0.0.1:8742/viewer.html?doc=11328300&page=1) carries the revised working interface. Follow the Inventaria edition link to distinguish the imported transcription from DoCTA's machine annotation proposals. A Transkribus workflow status does not establish a reference transcription under the project's own convention.

Use [the silver inventory A 006.8 and .9](https://dhcraft.org/DoCTA/viewer.html?doc=12647153&page=1) to explain machine transcription and incomplete image references when that question arises. Its available transcription covers only part of the document. Technical demonstration corrections belong in an isolated test copy until a scholar confirms the reading.

The public viewer supports a browser draft and JSON export. Repository write-back uses the loopback editor started with `start-editor.ps1`. Demonstrate save and reload before opening the optional reading text or validated TEI build under Weitere Funktionen. Closing the browser is not publication. A local Git commit records a change, and pushing to the public repository is a separate operator action.

### Guided editor exercise

Continue the local walkthrough with Thaur A 049.1, document 11328300. The operator reported on 2026-09-21 that source orientation and page navigation worked. He requested a complete initial image, a shared metadata header and fewer simultaneous editing controls. Those observations motivated the [working editor hierarchy](design.md#working-editor-hierarchy). The revised interface still needs his hands-on acceptance.

1. Identify title, shelfmark and historical date. Open Quellenangaben only for the additional source context.
2. Inspect the complete image, zoom to a passage, restore it with Ganze Seite and navigate to the next image.
3. Open Bearbeiten, enter initials and select an existing text line. Enter confirms a browser draft, Escape cancels the open line edit. Change only a reading justified by the image.
4. Use Änderungen speichern, wait for the local-save confirmation and reload. The saved reading must remain. Änderungen verwerfen discards the current page draft and preserves saved text.
5. Add a page or line tag with a note after saving the text. Reload and inspect its source attachment. Distinguish a research observation from an accepted interpretation.
6. Inspect an automatic annotation separately. Keep an uncertain proposal open, and record a reason for acceptance or rejection when justified. Annotation decisions concern the selected proposal. Correcting the text requires no separate page approval step.
7. Under Weitere Funktionen, update the local edition output with its output date and inspect TEI if needed. This action derives files and does not publish them.

After each step, collect the operator's observation, the source passage, any unexpected behavior and the effect on the research workflow. Preserve reported experience separately from agent interpretation and automated verification. The operator requested the German meeting guide before completion of the walkthrough. Its factual basis is the verified implementation and the recorded questions, while hands-on acceptance remains pending. Revise the guide after the walkthrough with confirmed observations. It explains purpose, source provenance, the worked example, correction and annotation, saved versus published state, and the remaining scholarly decisions.

### Meeting answers and scope

The current local edition supports a bounded correction and annotation pilot. A funded project would establish its agreed source coverage, transcription convention, accepted reference sample, research vocabulary, account-book edition and cross-source interpretation. Those are substantive research outputs and cannot be inferred from a working viewer. The installation on the historical editor's computer still needs its own save-and-reload check. Source images can require network access even when editing runs locally.

The question about the five missing silver-inventory pages concerns absent image references. Authorized collection access or a document metadata export can supply them. Receipt of the references enables ingestion and a separate transcription run, and does not mean the pages have already been transcribed. The project lead identifies the intended document and grants access through the service or supplies its metadata, without putting account credentials in project documents.

Automated Inventaria import is technically implemented for an explicitly selected public document, including pagination and PAGE annotations. Permission must specify the intended material, attribution, annotation reuse and publication. A successful trial import does not establish corpus completeness, permission or a recurring synchronization service. Incoming source versions must preserve existing local corrections.

Quantification distinguishes transcription error against an accepted reference, documented correction kinds, and historical counts derived from interpreted entries. It records no working duration. A changed line is neither one error nor one scholarly decision. Historical quantities require a defined unit and denominator, with Roman numerals, monetary units, omissions, source coverage and duplicate mentions checked separately. The comparison of recognition methods requires a common reference and a specialized HTR comparator.

The editor-in-the-loop interaction is the scholar's correction of a source-bound reading and decision on an existing machine proposal. It does not retrain a recognition model or automatically write back to Transkribus. The [annotation contract](specification.md#annotation-curation-in-the-viewer) distinguishes text corrections, free research tags and decisions on machine proposals. Direct editing through a highlighted mention is a requested interaction improvement, deferred while the operator focuses on the conversation.

The meeting should establish the first historical question, a bounded source passage, transcription rules, useful working tags, the reference sample and the intended edition output. Inventory passages demonstrate the interface. Account books remain the project's leading research source and require their own accepted pilot. Repeated entity mentions and graph co-occurrence do not establish ownership, exchange or a historical event.

Before a clean demonstration, inspect the remaining browser draft and remove any operator test addition through a further documented correction. Do not present a test edit as a scholarly reading. The local interface changes and saved research data are distinct from the published website. The public links identify the examples, while the local editor is the demonstration target for the revised workflow.

## Work sequence and acceptance

| Work | Required input | Concrete result | Acceptance evidence | Responsible decision |
|---|---|---|---|---|
| Local editorial pilot | Repository clone and one available source | Saved correction with original text and reviewer provenance | Reload reproduces the reading, a stale concurrent edit is rejected, generated TEI validates | Project lead accepts the working interaction |
| Source completeness | Authorized Transkribus metadata or exported document metadata | Page manifest with image references and explicit omissions | Expected page numbers match retrieved metadata, each reference resolves | Account holder provides access to the intended collection |
| Inventaria reuse | Permission covering the intended texts, annotations and publication | Provenance-preserving import with PAGE annotations | Completeness, line anchoring and annotation offsets checked, attribution and license recorded | Project lead coordinates permission with Inventaria |
| Transcription convention | Decisions on original spelling, abbreviation expansion, illegibility, deletion, foliation and line structure | One convention and a versioned, accepted reference sample | Every sample page reviewed against its image and tied to the convention | Historical editor |
| Recognition evaluation | Accepted sample and a specialized HTR baseline | Comparisons by page and source stratum, with numeral errors inspected separately | Held-out evaluation, line omissions, normalization profile and failed cases reported | Project lead approves fitness for the research task |
| Correction documentation | Source-bound corrections under the convention | Original and corrected readings with actor and save time | Saved events resolve to their source document, page and line | Historical editor supplies the reading |
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

### First research-tagging exercise

The recorded core wish is to inspect who does what with which objects and where ([specification.md](specification.md#requirements-of-the-project-lead)). The research dimensions concern court practices, possession and object movement, and spatial hierarchies ([domain-knowledge.md](domain-knowledge.md#three-analytical-dimensions)). Manual working tags let the editor collect passages for these questions while correcting the transcription.

Start with the silver inventory, page 1, where the existing lines `v12` through `v15` describe plates. Attach a tag to the page or an existing line and use the note to identify the surrounding passage and the question it raises. `Inventarisierung` is a provisional search term for this passage. The list of plates alone does not establish an object transfer. A second passage is the Thaur inventory, page 2, line `r5l3`, whose current reading is `gnedigen herrn zekawffen gegeben.` A provisional `Kauf / Beschaffung` tag locates the action wording, while the note records that agent and object must be read from the surrounding lines. Both readings still require checking against their images.

The form suggests `Inventarisierung`, `Übergabe`, `Kauf / Beschaffung`, `Zahlung`, `Besitz / Verwahrung`, `Raumnutzung` and `Zeugenschaft`. These are editable working terms proposed for the exercise. They do not constitute an accepted vocabulary. Record what the passage says, what remains uncertain and which neighbouring lines matter. A practice tag does not establish an event, person identity, ownership direction or a complete accounting transaction. Event aggregation and the final verb-centred annotation guidelines remain scholarly decisions.

The editor can filter saved tags on the current page and export all tags of the loaded document as JSON. Cross-document faceted search and formal conversion to SiCPAS, TEI or RDF require a later explicit mapping. Review the terms used in the first passages together before introducing those functions.

### Historical claim

A source-bound question is how a documented transfer or payment places a person in relation to court material and an institution. An inventory may attest a holding or transfer, an account may attest a dated payment with a stated unit, and a court ordinance may prescribe a task. These are different evidential roles. Their combination requires explicit temporal and identity checks.

Use the selected passage to decide whether the research needs a material inventory, an accounting event, or a comparison of prescribed and recorded practice. Raitbuch 2 remains the working account book. Court kitchen and provision or pay outside the territory remain candidate cases until the project lead selects one.

A negative finding must remain representable. A payment without a named purpose cannot establish the corresponding practice, and a shared name without corroboration cannot establish identical persons. A proposed cross-source link therefore records its evidence and the reason an alternative reading was rejected or left open.

## Correction provenance

The operator excluded time tracking and separate page approval stages on 2026-09-21. The working process records a correction when it is saved. Each event identifies document, page, line, previous reading, corrected reading, actor and server timestamp. The source export remains unchanged. A later correction creates a further event and a new effective page reading. Git records selected file states after an explicit commit.

The historical editor selects passages across relevant hands, genres, layouts and difficult readings. Quantification can describe the documented changes and their kinds once a comparison convention and sample are agreed. Character and word error rates require an accepted reference. Numerals, omissions and monetary units need separate inspection because a small character error can change historical interpretation.

## Boundaries still requiring implementation or evidence

Structural insertion, split and merge of transcription lines require stable new line identities, explicit region membership, facsimile geometry rules and migration of downstream annotation anchors. Emptying an existing hallucinated reading is supported while preserving its anchor. These are distinct operations.

The account-book preparation build creates a machine-unrevised TranscriptionRevision and checksummed manifest. A generated test PAGE carrier proves software behavior only. A scholarly build requires genuine source anchors and accepted accounting annotations, and may not manufacture either.

Prompt changes identified in [handoff.md](handoff.md) become a new version after the reviewed sample exists. Frozen prompts and measuring runs remain unchanged. The specialized HTR comparator, proposal revision and scholarly approval remain explicit dependencies.
