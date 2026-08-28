---
title: Journal
project:
  name: DoCTA
  repository: https://github.com/DigitalHumanitiesCraft/DoCTA
method:
  name: Promptotyping
  url: https://dhcraft.org/Promptotyping/
status: active
language: en
version: "1.0"
created: 2026-02-18
updated: 2026-08-28
authors: [Christopher Pollin]
generated-with: Claude Code (Claude Fable 5)
template:
  name: Vorlage Journal
  version: 0.4
  url: https://dhcraft.org/Promptotyping/promptotyping-document/journal
  alias: https://dhcraft.org/Promptotyping/#promptotyping-document-journal
related: [INDEX, project, handoff]
---

# Journal

A dated log. Entries record the state at the date they carry, and figures inside an entry are the measurement of that day rather than a current value. Where a decision has since been superseded, the later entry says so.

## Stabilization pass over pipeline, viewer and stylesheet (28.08.2026)

A four-part deep review (pipeline, evaluation and scripts, site JavaScript, CSS and tooling) fed a first correction wave, applied in three commits with disjoint file scopes. The decisions that carry reasons:

The idempotence healthcheck now rebuilds the register with `carry_from` pointing at the real pipeline directory, because the previous empty-directory rebuild lost ingested review state and the projection comparison had no exemption, so the first committed review would have turned the pre-commit gate permanently red. The register-only exemption (`_only_review_state`) fell away with it; the check is one statement again. The review-export contract closed on three edges: a missing `status` key is refused in validation instead of crashing the ingest, malformed JSON becomes a named refusal, and edition runs are accepted as review base, which the README had promised and the code denied — without this, precisely the documents DoCTA transcribed itself were unreviewable.

In the viewer, the two status buttons received explicit toggle semantics because the old shared toggle silently demoted an approved page to `gesichtet` on a Reviewed click, and that demotion would have entered the export. The `page` URL parameter now means the page number rather than an array index; every producer already passed a page number, so the index reading was a latent wrong-folio bug for any document with a gap. The draft badge became the floor of the machine-output marking in synopsis mode, since the provenance chip could vanish on two silent paths and the marking must not depend on it.

Editing `build_tei.py` forces a digest re-pin in all sixty TEI headers because the generator writes its own sha256 into every file; the regeneration used the on-disk date and changed nothing but the digest line. Deferred to a second wave, because they alter published figures or are larger cuts: the benchmark numeral metric (the fair profile's v-to-u collapse runs before a numeral check whose character class lacks `u`, so roman numerals containing `v` leave the number metric), the `consistency_numbers` zero for pages without numerals, the date normalization in `transform_sources.py` (century ranges collapse, a leading "bis" dash produces negative years on the published site), fail-closed writes in the SiCProD fetch scripts, the extraction of the viewer's inline JavaScript into testable modules, and a shared `io_paths` module for the six copies of JSON I/O.

## Register view, and the catalogue figure separated from the image count (28.08.2026)

Two approved packages landed together. The exploration gained `?view=register`, the corpus-wide entity index from `graph.jsonld` with tabs per type, attested spellings, every attestation as a deep link into the viewer and the `register.xml` fragment as citable address. And `sources.json` no longer carries the ambiguous `seiten`: `catalogue_extent {value, unit, raw}` holds the catalogue figure with a conservatively derived unit (`bilder` where the account-book evidence proves it, `seiten` where the A 006 side-count evidence holds, `unbekannt` otherwise, `raw` empty until the catalogue CSV is next available), `transkribus_docs` is an array so a shelfmark spanning two Transkribus documents loses neither, and `digital_images` is the derived sum. The site shows scans as the primary figure with the catalogue extent as a labelled secondary where it diverges, and the progress bar computes both sides from the register in one unit, so it no longer divides written sides by scanned openings. The migration runs as `transform_sources.py --migrate` because the CSV lives outside the public clone; the CSV path produces the same schema with the true raw cell.

## Feedback response sent to the project lead (28.08.2026)

The fourteen feedback points on the prototype were answered in a response document with per-point status and direct links: seven implemented on the published site, two clarified as data-function questions (the SiCProD exports against the SiCProD-mediated digitisations, and the source-based network in place of the old database view), four partly open (independent non-Inventaria source pending the remaining images, annotation harvest pending coordination, review-effort quantification pending a representative sample, proposal reconciliation pending its ground version), one superseded (the old SiCProD network observation). The accompanying mail proposes DoCTA's next form as a working edition tailored to the project lead's research, offers Inventaria the generated TEI files in return for clarified transcription use and annotation licensing, and announces the annotation editor with reconciliation against SiCProD, Wikidata, GND, Inventaria and Getty AAT. The open points moved into `handoff.md`; the working-edition framing into `project.md`; the annotation editor into `specification.md`. This partially revives the Inventaria coordination that the morning session had set aside, now mediated by the project lead and with the TEI return offer as the new element.

## Inventaria enters the TEI headers (28.08.2026)

The generated TEI had named the Inventaria project nowhere, and for the fully corrected documents the header even claimed an unrevised recognition layer. Every attributed document now carries `resp-inventaria-transcription` with a resp text differentiated by Transkribus done status (all pages, a stated split, or none), a `bibl` with the published edition link where the harvest holds one, and an editorialDecl that matches; the done status is named as a workflow status of the platform and a step of the Inventaria project, while DoCTA's own facsimile review stays a separate axis. The attribution mirrors the register projection's derivation from `source_mapping.json` and `inventaria_mapping.json`, `docta.rng` grew exactly the three shapes needed, and the entity-reference healthcheck was scoped to elements carrying the entity responsibility, because the new `@ref` on a project name addresses the project and never a register entry.

## Provenance made layer-explicit, controls sticky, exploration reworked (28.08.2026)

Operator session over the running site. The viewer's toolbar had shown the entity extraction's "gemini-3.7-flash · not verified" unlabelled beside the text chip "Human-corrected (Inventaria)", which read as a contradiction; the legend now leads with "Entities" and every text chip leads with "Text:". The Transkribus fallback chip was reworded to "Transkribus HTR · no correction recorded", because a missing done status documents nothing about actual correction work. On the home page the search row, category chips and stage key stick under the navbar as one block; the root cause of the navbar itself not sticking was the BETA-badge code adding Bootstrap's `position-relative` utility (with `!important`) to the navbar, which killed its `sticky-top`. A returning-visitor 404 in the viewer traced to the register projection having gained `transcription_source` without a `DATA_VERSION` bump; shape changes under `data/` must bump it. The exploration entities view drops per-source constant columns into a facts line, gains a free-text filter and row deep-links into the viewer; the network view gains neighbourhood isolation, a legend, shared tooltips, triangle object nodes and working keyboard access. VLM-transcribed documents are now clickable from the home page, and thumbnails fall back to the collection metadata for mapped documents without a register entry.

## Knowledge vault page removed from the site (28.08.2026)

`knowledge.html` is gone, together with its sidebar styles and its entry points from other pages; About and benchmark now link to `docs/knowledge/` on GitHub. Operator decision of the same day: the knowledge base addresses agents and repository readers, site visitors do not understand it, and a public repository leaves the Markdown readable without a renderer. The refactoring of the same morning (viewer manifest, legacy anchors, frontmatter stripping) is thereby superseded where it concerns the viewer; the naming contract and frontmatter of the documents stay. This partially supersedes the entry below.

## Knowledge base refactored onto the Promptotyping convention (28.08.2026)

The knowledge folder now follows the naming contract of the Promptotyping documents convention, lowercase canonical function names with `INDEX.md` as the registered uppercase exception. `REQUIREMENTS.md` became `specification.md` and `TECH.md` became `architecture.md`, because the convention names these functions canonically; `CONTEXT.md` became `domain-knowledge.md`, matching the template slug of the Domain Knowledge function; the remaining documents kept their names in lowercase. Every hand-written document carries the frontmatter core of the convention (`title`, `project`, `method`, `status`, `created`, `updated`) with `version: "1.0"` as the repo-wide schema version, and documents with a catalogue template reference it in a `template:` field. Two documents the convention triggers unconditionally were added, `project.md` as the charter, distilled from the former INDEX state section and the README, and `handoff.md` as the standing process inbox. `INDEX.md` was rewritten as navigation plus glossary with a document register of routing questions; its phase narrative moved to `project.md`. The knowledge viewer strips frontmatter before rendering and keeps the old uppercase hash anchors working through a redirect map. The alternative, keeping the historical uppercase names, was rejected because the file name is the primary routing signal for agents and the convention is what the method site itself practises.

## About-page reframing (28.08.2026)

The About page no longer presents the prototype as a response to reviewers or as proof of a predetermined methodological claim. It begins with the historical research scope, identifies the questions tested by the prototype, states the current coverage and separates the provenance of source editions from DoCTA annotations. The digital workflow is described as research infrastructure for comparative source analysis. Technical reproducibility guarantees remain documented in the Knowledge Vault rather than in the public project description.

## A document DoCTA transcribes itself, end to end (28.08.2026)

Until now every text in the pipeline came from Transkribus, and the whole chain was built on that assumption. The edition track breaks it. Document 12593450 (A 024.1, one sheet, 1489) has no Transkribus transcription, and the pipeline now produces its text itself, encodes it, extracts entities from it and shows it in the viewer, with DoCTA named as the responsible party at every step. Document 12647153 (A 006.8) takes the same route for its first page.

Five decisions were needed, and each one had an alternative that was rejected for a stated reason.

**A fifth responsibility, `resp-vlm-transcription`.** The closed list in `schema/docta.rng` held one transcription step, `resp-transkribus-layer`, whose prose names the Transkribus recognition layer. Reusing it for a text produced by our own model would have asserted a work step that never ran on that source, which is exactly what the closed list exists to prevent. The new value names the model and the prompt iteration in its `name`. The status axis stays as it was, and such a document reports `machine-unrevised`, because that axis measures how far a text has been revised and a model reading is unrevised whichever model produced it.

**Synthetic line ids `v1`, `v2`, ... for edition runs.** A review decision, an entity anchor and an `lb` all address a single line, and a vision model returns text without layout identity. The ids are assigned deterministically at register build from the line order of the run, they are relative to that run, and the register says so. Only the edition cohort gets them; a benchmark or pilot run keeps `null`, since it is measured as a whole and nothing addresses a line of it. The alternative, minting ids for every VLM run, would have rewritten hundreds of measuring runs to no purpose.

**A separate run cohort `edition`.** The benchmark and the pilots repeat every page because they measure; this cohort transcribes each page once, because a second reading would raise the question which of the two is the edition text and nothing in the pipeline answers that. Its runs are append-only like every other cohort, and it writes no summary file, since without repeats and without a reference there is no metric to compute.

**A site projection instead of a fake export.** `docs/data/transcriptions/` is the Transkribus export and nothing else writes into it. The viewer therefore reads a document DoCTA transcribed from `docs/data/pipeline/transcriptions/<docId>.json`, generated beside the register projection and carrying its provenance and the state `machine-unrevised`. `source_mapping.json` keeps `has_text: false` for these documents, because that field states what Transkribus holds.

**No entry in the content-class vocabulary.** A page carrying an edition run stays `unknown`. What a page holds is settled on the scan in an adjudication step, and that step has not run; recording the transcription as a run asserts nothing beyond what happened. The consequence is visible in the site figures, where such a page is not counted as a page with text.

The TEI files carry no zones for these documents and their `lb` elements stay unbound, because no layout analysis produced a polygon. The facsimile stays, with the IIIF URL of the page the model actually read, and the body has one `<ab>` per page rather than an invented region structure.

What is not done is the rest of document 12647153. A document without a Transkribus export carries no page list, so the only image key the repository holds for it is the first page, from `transkribus_collection.json`. The keys of pages 2 to 6 need an authenticated Transkribus `fulldoc` call, and no environment of this repository currently holds `TRANSKRIBUS_USER` and `TRANSKRIBUS_PASS`. The five pages stay empty in the register until that call runs.

## Phase status (as of 26.08.2026)

| Phase | State | Result |
|-------|-------|--------|
| 1. Preparation | Done | Source documents collected (project-internal, not in the public repository) |
| 2. Exploration | Done | SiCProD API probed, catalogue CSV analysed, Transkribus collection mapped (115 documents, 12,236 pages), IIIF verified |
| 3. Distillation | Done | Eight knowledge files plus a project-internal implementation plan (`IMPLEMENTATION.md`, likewise not in the public repository) |
| 4. Implementation | Done | Eight pages built, data wired in, public since 19.02.2026 at https://dhcraft.org/DoCTA/ |
| HTR iteration | Running | Five test images evaluated with six prompt variants; the comparison against a specialised HTR model and a scholarly account-book reference are still open |

## Promptotyping iteration (26.08.2026)

### The VLM transcription test

The test processes four openings from account book 2 and one inventory page with six variants of `gemini-3.7-flash`. Raw outputs, metrics and a synopsis viewer are under `experiments/transcription-test/`. Technical function was observed. Scholarly checking and user acceptance are outstanding, so every output of this run is unrevised machine transcription.

| Finding | Consequence |
|---------|-------------|
| V3 few-shot reaches the best strict and fair CER on the inventory reference candidate | V3 is carried on as the current development configuration |
| V6 image enhancement reaches the highest word overlap and the second-best fair CER | V6 stays a comparison candidate for hard-to-read pages |
| V4 page splitting worsens the inventory values | Crops are used only in a targeted way, for difficult regions |
| Account-book outputs vary in names, years and monetary amounts | The configuration currently suits structural and category survey; research data need adjudication |
| The blank test page is recognised correctly by all structured variants | Blank-page and layout triage can go into a continuous run |

### Correcting the notion of a reference

The inventories in the collection carry working transcriptions. Three documents hold the Transkribus status `DONE`, the remainder `IN_PROGRESS`. None holds a formal ground-truth status documented within the project, and two transcription conventions are present besides. The viewer's use of the term "ground truth" is therefore read methodologically as **inventory reference candidate** until convention and scholarly approval are documented.

### Methodological decision

The production decision is taken per task. Category survey, diplomatic transcription and the reading of amounts receive separate checks. The next model comparison uses the same held-out account-book set for the current configuration, a stronger vision-language model and a specialised Transkribus model. Divergences are presented with image details for scholarly adjudication. The full review contract is in `htr-evaluation.md`.

## Decisions (17.02.2026)

### Agreed with the DH partner

| Question | Decision | Reason |
|----------|----------|--------|
| Type of prototype | A functional tool rather than a mockup | The reviewer should be able to interact with it |
| Priorities | Pipeline demo first, faceted search second, source exploration third | The pipeline addresses the review criticism most directly |
| Technology stack | Vanilla JavaScript, as in coOCR/HTR | Consistency, no build process |
| Deployment | GitHub Pages | Static and public |
| Authentication | None | The prototype has to be reachable for reviewers |
| Images | Transkribus IIIF URLs, with a fallback if needed | IIIF in `<img>` presumed to be CORS-free |

### Open decisions at that date

| Question | Options | Who decides |
|----------|---------|-------------|
| Case study for the prototype | Search account book 2 for kitchen categories, treat "Provision und Sold" as its own study, or choose a different account book | The project lead, after verifying the possible mention of a master of the kitchen |
| Entity granularity | Four entity types in the demo (person, place, object, time) against nine in SiCPAS | The project lead with the BeNASch team |
| Mapping practice onto BeNASch | Worked out on a handful of example entries | The project lead with the Bern team |
| Open-source positioning of coOCR/HTR | Raised with the project lead on 04.02.2026 | The project lead, response outstanding |

## Decisions (18.–19.02.2026, implementation phase)

| Question | Decision | Reason |
|----------|----------|--------|
| Entry point into the network (commit 86783f2, 18.02.) | The ego network as the default view, with Sigmund at the centre, up to fifty neighbours and a concentric layout. Clicking a node opens that node's ego network. The full network, the seventy-five best-connected nodes under a COSE layout, sits behind a toggle. | The previous entry point through the full network was a cloud without a statement. An ego network answers a question immediately, namely who stands around this person, and makes exploration the obvious next action. |
| Handling faulty node types (commit d89a58c, 19.02.) | Entities without an entry in the index (`event-*`) are filtered out before drawing. | The full network crashed otherwise. |
| Positioning of coOCR/HTR (commits d89a58c and 25489aa, 19.02.) | coOCR/HTR is named explicitly as a tool in two places, in the HTR step of the pipeline demo and in the reviewer section of the help page, each time as the editor in the loop for validating and correcting Transkribus results. | The sister project answers review point 3 on language-model approaches concretely instead of abstractly, and shows that quality assurance does not still have to be invented. |
| Data commitments towards reviewers (commit 25489aa, 19.02.) | The help page names two commitments for the full project: publication of all research data under the FAIR principles, and a documented REST API over persons, relations, sources and transcriptions, alongside the open GitHub repository. | Reusability was only asserted in the proposal. Named as a commitment in the prototype it becomes checkable. |
| Figures on the home page | Six raw counts (persons, relations, places, sources, transcriptions, functions) and no derived ratios. | A ratio such as relation coverage in percent would need a defined denominator that does not yet exist methodologically. An invented percentage does more harm than an honest count does good. |

## Exploration results (17.02.2026)

### SiCProD API, expectation against reality

| What we assumed | What we found | Consequence |
|-----------------|---------------|-------------|
| Events, number unknown | **Only 28 events**, namely diets, imperial diets and weddings | Everyday practices come from the account books rather than from SiCProD |
| Salaries, 2,906 records | **No monetary amounts**, only links between person and function | Financial data have to be extracted from the account books |
| Institutions, 215 with types | **207 without a type** | An institution filter is of little use |
| Functions, some 99 distinct | Around eighty court offices, good variety | Excellent for faceted search and for analysing court structure |
| Places, 736 with coordinates | Many without lat/lng | A map will have gaps |
| Persons, 6,288 | Well documented. `first_name` is filled for 6,281 of 6,288, `status` is empty throughout. | The given name is shown in search and network, `status` is not exported at all. Name variants (`alternative_label`) are present and useful. |

### The catalogue CSV, quality problems

Serious problems:

- Sixteen empty ghost columns, artifacts of an Excel export
- The Digitalisiert column holds a page count rather than a boolean
- The Transkribiert column holds either "Inventaria" or nothing
- More than ten different date formats
- En dash against hyphen used inconsistently, the Repertorium section against the rest

Duplicates and errors:

- Hs. 0041, a true duplicate
- A 002.1 and A 2.1, a near duplicate with a typo
- Seven sources outside Sigismund's lifetime
- A date value in the Art column, row 304

Structural finding: 57 of 312 sources are transcribed, exclusively castle inventories from the Inventaria project. No account book is transcribed.

### File inventory, coverage gaps (closed)

The source documents named below are project-internal and are not contained in the public repository (see INDEX.md).

| Gap | Source document (project-internal) | Now captured in |
|-----|------------------------------------|-----------------|
| Epistemic asymmetry | `sources/coocr-htr-epistemologie.md` | domain-knowledge.md |
| Sequencing of phase 1 | `sources/strategische-planung.md` | specification.md |
| The project lead's own wording of the requirements | `sources/requirements-projektleitung.md` | specification.md |
| Entity category discrepancy | `sources/fwf-proposal-2025.md` against SiCPAS | domain-knowledge.md |
| Open source questions on account book 2 | `sources/raitbuch-2-analyse.md` | data.md |

### Deliberately not captured, proposal level rather than code

- The bibliography of the proposal, around a hundred references
- Work-package detail and the Gantt chart over 36 months
- The financial detail of the proposal

## Dead ends

| What | Why it was a dead end | Lesson |
|------|-----------------------|--------|
| The Transkribus API in the browser | CORS blocks it, and OAuth2 in the client is insecure | Pre-fetch with Python |
| SiCProD events as a source of practice data | Only 28 major events | Everyday practices come from the account books |
| SiCProD salaries as a source of financial data | No amounts, only links | Financial data come from the account books |
| Reading the SVG model diagram | 742 KB on a single line | The content was carried over as text into domain-knowledge.md |
| Reading the PDF on Windows | pdftoppm unavailable | Agent-based extraction |
| Transkribus authentication | The initial authentication failed with 401; it succeeded after correcting the credentials | Take credentials directly from the user |
| The "correction" of the funding body (18.02.2026) | A review round classified the correct references to the funding body as errors and replaced them project-wide with "FWF". Reverted on 05.08.2026: APART-GSK is a programme of the body originally named, and the review of the first submission was that body's review. | A review can turn a correct statement into a wrong one. Proper names of funding programmes and institutions are checked against an external source rather than against the majority of occurrences inside the repository. |

## Transkribus exploration (17.02.2026, updated 26.08.2026)

### Collection 2197991, expectation against reality

| What we assumed | What we found | Consequence |
|-----------------|---------------|-------------|
| Around 55 inventories transcribed | **57 carry text** (8,979 lines, 35,724 words). Three `DONE`, 54 `IN_PROGRESS`, no documented formal ground-truth status. | Treat them as working transcriptions and partition them by convention |
| Account books not transcribed | **Confirmed for Transkribus.** 26 account books, 8,561 pages, no text. Volumes 1 to 6 carry a layout analysis. Since 26.08.2026 experimental, unrevised VLM output exists for four openings of account book 2. | Compare a specialised HTR model against a scholarly checked account-book reference |
| Extent of the collection unclear | **115 documents, 12,236 pages**, comprising 64 inventories, 26 account books, 12 copybooks and 13 others | Considerably more material than expected |
| IIIF URLs possibly a CORS problem | **No problem.** IIIF and direct URLs load without authentication. | OpenSeadragon can use IIIF directly, no pre-fetch needed for images |
| PAGE XML format unknown | Structured as Page, then TextRegion with coordinates, then TextLine with coordinates, baseline and Unicode | The parser logic is clear and a pre-fetch script can be written |

### Additional documents, absent from the CSV

The collection holds documents that the catalogue CSV does not mark as transcribed:

- Twelve copybooks, 2,224 pages, images only
- Court and regiment ordinances, TLA_HS_208.1 and 208.2, 149 pages
- The wedding cluster: Hs. 2466 with 33, Hs. 2467 with 58, Hs. 2468 with 19 and Hs. 2469 with 54 scans. These are counted scans from Transkribus. For the same four volumes the CSV states 60, 100, 35 and 140 pages, which are catalogue statements. Both sets are real; which of them represents the complete volume is unresolved (see data.md on the court ordinances).
- Further manuscripts: Hs. 113 with 133, Hs. 324 with 86, Hs. 514 with 16, Hs. 792 with 7 and Hs. 5087.1+2 with 218 pages

## Open points (consolidated)

### Blocking for the prototype, all resolved

- [x] Transkribus credentials, verified through the environment variables TRANSKRIBUS_USER and TRANSKRIBUS_PASS
- [x] Collection ID, 2197991 at https://app.transkribus.org/collection/2197991
- [x] Document IDs enumerated, 115 documents mapped, in `data/transkribus_collection.json`
- [x] IIIF URLs tested without authentication, they work
- [x] Sample facsimiles made accessible, IIIF URLs for all 123 openings of account book 2 in `data/raitbuch2_pages.json`
- [x] PAGE XML of the transcribed inventories exported as JSON, 57 files in `data/transcriptions/`
- [x] Mapping from Transkribus titles to catalogue shelfmarks, all 64 inventories matched, in `data/source_mapping.json`

### Important for the proposal

- [ ] A short methodological text module for the planned resubmission
- [ ] Finalise the case study, including verification of the possible mention of a master of the kitchen (the project lead)
- [ ] The mapping between practice and BeNASch, with the Bern team
- [ ] Literature on historical linguistics, review point 5

### Nice to have

- [ ] A spreadsheet URL for additional metadata
- [ ] Evaluate the glossary idea raised by the project lead
