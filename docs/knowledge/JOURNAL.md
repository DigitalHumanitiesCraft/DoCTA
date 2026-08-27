# JOURNAL: Decisions, Exploration, Open Questions

A dated log. Entries record the state at the date they carry, and figures inside an entry are the measurement of that day rather than a current value. Where a decision has since been superseded, the later entry says so.

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

The production decision is taken per task. Category survey, diplomatic transcription and the reading of amounts receive separate checks. The next model comparison uses the same held-out account-book set for the current configuration, a stronger vision-language model and a specialised Transkribus model. Divergences are presented with image details for scholarly adjudication. The full review contract is in `HTR-EVALUATION.md`.

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
| Epistemic asymmetry | `sources/coocr-htr-epistemologie.md` | CONTEXT.md |
| Sequencing of phase 1 | `sources/strategische-planung.md` | REQUIREMENTS.md |
| The project lead's own wording of the requirements | `sources/requirements-projektleitung.md` | REQUIREMENTS.md |
| Entity category discrepancy | `sources/fwf-proposal-2025.md` against SiCPAS | CONTEXT.md |
| Open source questions on account book 2 | `sources/raitbuch-2-analyse.md` | DATA.md |

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
| Reading the SVG model diagram | 742 KB on a single line | The content was carried over as text into CONTEXT.md |
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
- The wedding cluster: Hs. 2466 with 33, Hs. 2467 with 58, Hs. 2468 with 19 and Hs. 2469 with 54 scans. These are counted scans from Transkribus. For the same four volumes the CSV states 60, 100, 35 and 140 pages, which are catalogue statements. Both sets are real; which of them represents the complete volume is unresolved (see DATA.md on the court ordinances).
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
