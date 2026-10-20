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
updated: 2026-10-20
authors: [Christopher Pollin]
generated-with: Claude Code (Claude Fable 5, Claude Opus 5.5)
template:
  name: Vorlage Journal
  version: 0.5
  url: https://dhcraft.org/Promptotyping/promptotyping-document/journal
  alias: https://dhcraft.org/Promptotyping/#promptotyping-document-journal
related: [INDEX, project, specification, handoff]
---

# Journal

## Entries

Newest first. Each entry records one transition with its type (integrated, rejected, corrected, compacted), source, target and result. Figures inside an entry are the measurement of its date, not a current value; a later entry names any decision it supersedes.

### 2026-10-20 integrated: unclear readings and line deletion

- Source: operator decisions of 2026-10-20 on the feedback round; a survey of every bracket form in the page register.
- Target: [specification.md](specification.md#interface-language-and-unclear-readings-decided-2026-10-20), `pipeline/README.md`, design.md, plan.md, `apply_review.py`, `build_register.py`, `build_tei.py`, `docta.rng`, `docs/js/readings.js`, `viewer-render.js`, `viewer-review.js`.
- Result: `[?]` and `[word?]` are the notation, encoded as `gap` and `unclear`; the Transkribus dot and dash forms count as `[?]` and stay as written. The survey found these forms only in the Transkribus layer, `[...]` and one `[sberg?]` in model output, and folio marks and supplied letters such as `[er]` as text. The model's brackets stay text in TEI until a reviewer changes the line. Review lines may carry `excluded`, which keeps line identity and reading and leaves reading text and TEI; Restore unsets it. The viewer marks exactly what the TEI encodes, which a parity test holds, and the corpus test reads every transcribed line back without loss.

### 2026-10-20 corrected: line overlay on large scans

- Source: misplaced line regions on 11327964 page 1, whose original is 2448 by 6912 pixels.
- Target: `docs/js/viewer.js`, architecture.md.
- Result: Transkribus serves `full/max` scaled down above ten megapixels while PAGE coordinates address the original; the overlay takes its coordinate space from the IIIF `info.json` and falls back to the loaded size. The corrected-state dot of the status pill became its own blue token.

### 2026-10-20 compacted: whole journal

- Predecessor: commit `a2a960e`.
- Scope: all entries from 2026-02-17 to 2026-10-20.
- Result: every entry recast as type, source, target and result, wording condensed and repetition removed. All decisions, reasons, measurements and open points were kept, the closed prototype checklist of February 2026 as one summary line. Only narrative framing and the misplaced self-description paragraph, now the reading note under Entries, are preserved in Git alone.

### 2026-10-20 corrected: demonstration corrections removed

- Source: operator, who identified the three correction events of 2026-09-21 as their own test entries (11328300 page 2 with its reversal, 12647153 page 1 with two lines).
- Target: `pipeline/reviews/`, page register, static projections, TEI; `pipeline/test_build_tei.py`, `tests/viewer-ui-test.mjs`.
- Result: events and review runs removed; register, projection and TEI rebuilt; the projection of 11328300, produced only by the review, deleted. Both documents carry their source text without a recorded review. The TEI regression replays the same two line corrections as a synthetic fixture, and the viewer line-count check serves a fixture projection, since the corpus now holds no saved correction. The corrected readings were never confirmed against the facsimile.

### 2026-10-20 integrated: feedback round, interface language and unclear readings

- Source: the historical project lead's test of the working edition and feedback mail; operator decisions of the same day; repository inspection.
- Target: [plan.md](plan.md#feedback-round-of-2026-10-20), specification.md, data.md, design.md, handoff.md, CLAUDE.md, READMEs.
- Result:
  - Feedback: corrections worked. Annotation looked non-functional, most likely because she used the read-only GitHub Pages viewer, which hid the annotate controls without a reason. Requests: remove unneeded lines, mark unclear readings, annotate across line breaks, see work progress, reach more pages of the household chamberlain inventories, link persons to SiCProD, confirm whether exploration entities came from an LLM, a fully English working edition for an FWF proposal, and whether to fork.
  - Collaboration: she was added as collaborator and clones rather than forks. The operator replied that a detailed answer follows, that annotation needs the locally started edition, and asked whether the proposal or the data matters more to her now; her answer decides the next source selection.
  - Findings: the unwanted lines are most likely modern archival notes, foliation and folio markers, as in the last lines of A 024.1. The VLM labels such lines through `kind` and Transkribus records region structure types, but the register drops `kind` and `scripts/fetch_transcriptions.py` loses the type. Emptying a line keeps an empty TEI line and stales its anchors. Line-break mentions such as `Jo` / `seph` split because every entity is bound to one line. Only structural insertion, split and merge need the anchor-migration contract. The exploration entities are `entities_it01` LLM output without human input.
  - Decisions: the whole website including the guide is English. Unclear readings get one uniform notation with tooltip, correction-mode editing and TEI conversion; the syntax was left to a later package.
  - Documentation: stale statements corrected across CLAUDE.md, the READMEs and the knowledge documents (starters, commit hook, tests, accounts build, review overlay, absent sidecar folders, pilot2, reading order). The documents record the English site with its read-only hint, `strings.js` and `vocabLabel`, the stricter review contract, JSON error answers of the local API with removal of orphaned review events, the shared site-transcription path of the local build and the `json.entity-corrected` finding. No code, data or published page changed in this documentation step.

### 2026-10-19 integrated: compact installation guide

- Source: operator request.
- Target: guide.html.
- Result: setup leads directly from cloning to the project terminal, then one command block per operating system. The dependency list is explained at the installation step, with a direct link to starting the editor. Commands, anchors and the split between one-time installation and later sessions unchanged.

### 2026-10-19 integrated: dependency file for editorial onboarding

- Source: operator request.
- Target: guide, README, maintainer command, test instructions.
- Result: the runtime-only lock export is named `requirements.txt`. The guide explains that cloning downloads it and that the one-time pip step installs its packages. Versions and the installed-Python workflow unchanged.

### 2026-10-17 integrated: technical readiness for the feedback round

- Source: operator request for a reviewed, cleaned codebase; two separate local code reviews.
- Target: pipeline, viewer, specification.md, plan.md, architecture.md, handoff.md.
- Result: fixed gaps in rebuild/save serialization, correction replay, alternate-root source isolation, focused-input protection and TEI cache invalidation, each with a regression. The shared review lock moved to `io_paths` behind its compatibility import. Browser checks may reuse cached facsimiles, and isolated fixtures carry effective static text projections. The documents separate readiness of existing functions from outstanding scholarly decisions and feedback. No source processing, recognition run or publication.

### 2026-10-17 corrected: source coverage after a saved correction

- Source: trace of the silver inventory A 006.8 (and .9), document 12647153, from cached facsimile and edition run through a saved correction event to TEI.
- Target: `pipeline/build_tei.py`, [architecture.md](architecture.md).
- Result: the header had lost its incomplete-coverage notice when a correction existed and described correction-only provenance as page review. Coverage reporting moved outside the review branches, revision prose keeps the correction reason, and the generator's fidelity claim is restricted to preserving the effective register text. A regression replays the correction (since 2026-10-20 a synthetic fixture). Original spelling and saved readings unchanged; abbreviation treatment and uncertain readings remain editorial decisions.

### 2026-10-16 integrated: independent use and original spelling

- Source: operator confirmation.
- Target: project.md, plan.md, specification.md.
- Result: the working edition may be used independently across all source material already in the project, with original spelling. Small passages remain technical trial cases. Partner collaboration stays non-binding and proposal submission unconfirmed. Abbreviation expansion, uncertain readings, accepted references, source access, reuse rights and scholarly acceptance keep their separate decisions.

### 2026-09-21 integrated: editorial collaboration on main

- Source: operator decision.
- Target: README, architecture.md.
- Result: all editorial collaboration runs on main; branch selection and separate-branch integration removed. Local saving, commits and public uploads stay distinct, and publication scope is agreed before research data are transferred.

### 2026-09-21 corrected: compact guide with installed Python

- Source: operator, who found the combined onboarding and reference text too long; the supplied teaching route.
- Target: guide.html, README, `requirements.txt`.
- Result: the guide covers setup, launch, editing and saving; Git operations and recovery stay in the README. Setup uses installed Python and the VS Code terminal, with a runtime-only requirements export from the lock so the editor's machine needs no uv. Replaces the earlier pip-install-project suggestion. Exercised: Python 3.14 venv creation and package installation on Windows, followed by the real-backend browser walkthrough. Unobserved: Store installation, native macOS setup, recipient-side GitHub Desktop operation.

### 2026-09-21 corrected: installation and repository exchange

- Source: operator, who identified confusion between Python, VS Code and Live Server; the technical-preparation slides describe a development environment.
- Target: guide, README.
- Result: the working edition starts its own write-capable server through the launchers. GitHub Desktop cloning became the sole installation route, replacing ZIP instructions. Guide and README explain account creation, uv as installation helper, optional VS Code, commits and synchronization with explicit public-data visibility and preservation of earlier local work. The example stays optional. GitHub Desktop steps follow provider documentation, not an observed installation.

### 2026-09-21 integrated: guided first use and preservation of local work

- Source: guide rework; isolated launcher checks; executable guide walkthrough.
- Target: guide (then German), README, `tests/guide-walkthrough-test.mjs`.
- Result:
  - Guide: ZIP setup (superseded the same day by GitHub Desktop), separate operating-system steps, one source-bound person exercise. The local example link requires the editor capability, so a public reader is sent to the local application. Entry creation and occurrence saving explained separately. Text correction optional where the image supports it; a further saved correction remedies a mistaken reading. Backups distinguish saved files from browser drafts. A compatible update keeps canonical text and editorial folders and leaves the old project intact.
  - Checks: Windows launchers covered a fresh locked environment, its environment fallback and transfer of saved corrections and registry identities. A reviews-only control confirmed that startup does not rebuild effective readings from events alone. The walkthrough exercised the real backend over isolated corpus copies: entry creation, occurrence save and reload, Index lookup and return, annotation edit and removal, correction and restoration, static and local routing, keyboard navigation, narrow reflow at increased scale. Source selection was scripted through the DOM. Research-file hashes and inventories unchanged.
  - Limits: native macOS startup and first-time uv installation unobserved. Technical evidence only, no first-time-user acceptance.

### 2026-09-21 integrated: public working guide and documentation boundary

- Source: operator request; review-ordering and keyboard defects.
- Target: guide.html, README, architecture.md, handoff.md, `build_register.newest_review_run`, viewer.
- Result: the guide became a site entry point. Knowledge documents hold durable decisions without correspondence summaries. The handoff distinguishes working version 0.2.0, saved corrections, retained machine output and open scholarly decisions. Review selection orders schema-2 runs by their timezone-aware save timestamp and reads the time suffix of older local run ids, independently of reviewer initials. Shift with horizontal arrows keeps native text selection instead of paging. Targeted backend and browser tests cover both.

### 2026-09-21 integrated: source overview and consolidated vocabulary

- Source: interface inspection.
- Target: index page, viewer, design.md.
- Result: the separate research-tag surface retired, its data and API kept. Source selection reworked around search, availability and provenance; aggregate progress and pipeline-stage initials removed; BETA replaced by Research preview. A source with only a first image opens it without constructing missing pages or masking transcription errors. The shared annotation field and Index are the entry points for controlled vocabulary. Browser checks cover filtering, image-only navigation, the absent tag interface and responsive access.

### 2026-09-21 rejected: machine proposals in the working interface

- Source: inspection of the combined annotation field.
- Target: viewer, design.md, CLAUDE.md.
- Reason: the working editor serves the editor's own assignments; machine proposals fragmented the interaction.
- Result: proposals, their marks and editing controls removed; extraction files and curation decisions kept for pipeline compatibility. Index added beside Viewer to browse saved persons, places and terms by search, category filter and source link; it resolves identities by entry id, writes nothing and reconciles nothing. Decorative horizontal separators removed. Supersedes the proposal surface of the shared annotation field below.

### 2026-09-21 integrated: shared annotation field

- Source: inspection of a source-bound assignment; independent review.
- Target: viewer registry modules, design.md.
- Result: selection, assignment and proposal information consolidated into one source-bound popover, where register entries are also created and edited; the sidebar stays for browsing. Machine evidence and human assignment keep separate histories and explicit saves. Navigation guards preserve drafts across dismissal and block source changes while input is unsaved. An older registry response could replace a newer saved state; request and mutation generations now guard it. Browser regressions cover the field, inline entry editing, persistence and the delayed response.

### 2026-09-21 integrated: source-bound annotation interaction

- Source: interface inspection; independent review.
- Target: viewer (working version 0.2.0), README, architecture.md, Vault overview.
- Result: annotation moved into the reading workspace with a selection toolbar, anchored nonmodal editing and a collapsible register sidebar. Persons, terms and places have independent register identities. Dates keep their source quotation with optional exact or bounded normalization, uncertainty separate from precision. Right-click supplements the toolbar and keyboard entry. The first tall form hid its source, so optional notes collapse and the form fits beside the passage. The interaction was split into controller, form markup, display, source-anchor and popover modules under the unchanged persistence contract. Review fixed delayed-load and outdated-response failures in the proposal editor and stopped an in-progress decision from silently taking a corrected source's digest. The Vault overview records editorial responsibilities and separates human assignments from machine proposals.

### 2026-09-21 integrated: internal working version 0.1.0

- Source: register requirements of the same day.
- Target: `pipeline/local_editor.py`, registry modules, launchers, CI, README, handoff.md.
- Result:
  - Register: person register and controlled vocabulary with name-independent identities, variants, optional broader terms and source-bound single-line assignments; local search, manual annotation editing, decisions on highlighted proposals (later removed), separate transcription provenance. Changes keep actor, timestamp and before/after values; changed source text requires anchor rechecking. Assignments stay separate from TEI and graph identities and export as JSON. No external reconciliation or model calls.
  - Operation: Windows and macOS launchers with locked dependencies that open the browser after a successful bind; package version 0.1.0. Regenerating the stale lockfile removed unused JSON Schema dependencies. CI declares Linux, Windows and macOS; native macOS unobserved locally.
  - Verification: Python suite (slow tests in the commit gate), browser checks for register, tags, viewer and static site. Register tests ran an isolated real backend over corpus data: save and reload, history, stale anchors, equal names, keyboard, narrow views. TEI baseline tests derive fixtures from source exports, not from a corrected register.

### 2026-09-21 integrated: editorial onboarding and register requirements

- Source: cross-source person and object research.
- Target: specification.md, README.
- Result: requirement for an editor-owned person index and vocabulary, with uncertain links and object classification kept apart from physical-object identity. Inspection found automatic name-based aggregation in the generated index and no event history in the earlier annotation sidecars. README gained startup, separate saves, reload, local versioning and feedback instructions.

### 2026-09-21 integrated: research-first documentation alignment

- Source: meeting preparation.
- Target: README, CLAUDE.md, pipeline and test documentation, Vault project overview.
- Result: entry points, correction contract and knowledge follow the order goals, material, annotation needs, intended analysis, then demonstration. Legacy status fields are distinguished from the correction-only interface. Independent provenance of Inventaria transcription and DoCTA annotations recorded. "Disposable code" replaced by maintained, tested implementation. Historical prompts, runs and research corrections kept.

### 2026-09-21 integrated: meeting guide and evidence boundaries

- Source: joint walkthrough preparation.
- Target: guide, [plan.md](plan.md#meeting-answers-and-scope).
- Result: a working guide for the walkthrough. The meeting boundaries separate the local pilot from funded scope, explain source access and import, and separate transcription accuracy, correction evidence and historical quantification. Obsolete effort-measurement wording corrected.

### 2026-09-21 rejected: time tracking and page review stages

- Source: continued walkthrough inspection.
- Target: viewer, [design.md](design.md#working-editor-hierarchy), architecture.md, plan.md.
- Reason: the operator excluded time measurement and separate page approval from the working workflow.
- Result: these controls and active measurement removed. Correction provenance stays in the saved event and the effective page register; legacy records kept. Metadata and annotation entry points share one wrapping row, and the source attribution opens the original edition.

### 2026-09-21 integrated: working editor navigation and controls

- Source: walkthrough observations.
- Target: viewer, [design.md](design.md#working-editor-hierarchy), [plan.md](plan.md#guided-editor-exercise).
- Result: source identity above image and text, the image opens fitted, corrections have a direct editing entry point, supplemental actions are disclosed at their point of use. The build rejects unsaved transcription drafts. Browser regressions cover image bounds, page changes, dialog focus, reflow under CSS zoom and save/reload against an in-memory service, and the running viewer was inspected for full-image presentation, metadata access and the simplified controls. No screen-reader audit.

### 2026-09-21 integrated: local working edition and source-bound pilot plan

- Source: owner request for a first correction and annotation exercise, following the project lead's question who does what with which objects and where; independent review; Hersch and SZD as write-back references.
- Target: `pipeline/local_editor.py`, project.md, specification.md, plan.md, architecture.md.
- Result:
  - Editor: manual page and line tags with notes, reviewers and retained source readings, as provisional working terms separate from entity decisions and TEI/RDF claims (tags later retired); a source change marks tags for recheck. Loopback saving of review records and effective readings, conflict detection, rebuild of the connected TEI set and static projections. Empty readings are real corrections; editing an approved text reopened its review. Annotation decisions stored against source digests and projected into TEI and graph, with curation and authority per attestation. Source import keeps Inventaria PAGE annotations, and the accounts preparation build supplies a checked TranscriptionRevision and manifest without inventing accounting annotations.
  - Plan: the exercise uses the silver inventory and a purchase wording in the Thaur inventory, and binds demonstration, reference sample, permissions and case selection to contributions and acceptance evidence. Technical availability is distinguished from commission and acceptance.
  - Review: write races, inconsistent partial builds and a draft-status omission fixed. A real-source scratch copy passed save, reload, reading view, TEI rebuild and annotation read-back. Persistence checks and an isolated browser exercise covered save, reload, filtering and the changed-source warning. Python suite, lint and formatting passed, and the healthcheck confirmed schema validity and byte-identical rebuild. Derived files regenerated under the existing edition date. No research correction, reference approval, paid run or publication.
  - References: SZD keeps machine text and correction history, but its unchecked asynchronous save, direct file replacement and implicit approval miss the editor's persistence contract; pinned links in architecture.md.
  - Open at the time: the Inventaria test import stays private and ignored; missing image keys need authorized Transkribus metadata; structural line edits, new annotation spans, the accepted account-book reference, specialized HTR comparison and released accounting TEI/RDF; narrow-viewport acceptance (the browser adapter ignored the viewport). Scientific decisions and proposal text lie with the project lead.

### 2026-09-20 integrated: three owner decisions

- Source: project owner.
- Target: specification.md, accounting-encoding.md, `pipeline/schema/SOURCES.md`.
- Result:
  - DoCTA becomes a locally run editing tool. The editor clones the repository, edits research data in the running application and commits with GitHub Desktop. It replaces browser localStorage drafts ingested by the operator through `apply_review.py`, because the project lead must operate the pipeline herself; interfaces and functions are worked out with her.
  - No TEI ODD. RELAX NG, and in the accounts pilot Schematron and SHACL, carry validation; an ODD follows only if DoCTA publishes a reusable customisation. Replaces "deferred".
  - The working edition proposed on 2026-08-28 was still unconfirmed; an introduction meeting was set for 2026-09-21. Transcription convention, annotation vocabulary (priority object categories, order of reconciliation sources, the free-text `role` field of entity iteration 01, place versus space) and confirmation lie with the project lead.

### 2026-09-20 corrected: knowledge base checked against the repository

- Source: read of every knowledge document against code, data and artefacts.
- Target: architecture.md, design.md, INDEX.md, specification.md, README, `pipeline/README.md`, `apply_review.py`, edition README, handoff.md.
- Result: the viewer has a line overlay (`buildLineOverlay`). The entity layer comes from `data/entities/`; the demo fallback no longer triggers. No page loads `lib/marked.min.js`. The display takes no grading from model output (the entity prompt forbids a confidence field, the loader drops the demo file's), and the `--conf-*` tokens colour text-layer states. `transkribus_collection.json`, `transkribus_status.json` and `raitbuch2_pages.json` are pipeline inputs; `stats.json` holds no current figures. The benchmark computes metrics per page; zone stratification and line loss are specified only. The `provenance` field of `documents.json` is a constant. The handoff states that the review step was implemented but never run with a real export and that no account-book edition path exists; the pilot 2 process lessons wait for a reviewed sample. Open then: how edit mode writes into the repository; the constant `provenance` misstating the two self-transcribed documents; the unused `marked.min.js`; the `--conf-*` names.

### 2026-08-28 corrected: methods review of the HTR evaluation

- Source: critical methodological review.
- Target: htr-evaluation.md, benchmark and pilot summaries, `analyze_summary.py`, site.
- Result:
  - Weaknesses: it02 was developed on the measured reference pages (glossary lemmata verbatim in the gt_lines, strict-CER gain as the prompt document expected, fair CER flat), so the in-sample comparison cannot carry the iteration choice; remedy, an it01 run over the pilot page sets (needs API access). htr-evaluation.md had described unimplemented components in the present tense and now separates operating state from a requirements register. The reference is the Transkribus transcript with workflow status DONE, not a human Inventaria reference; corrected wherever displayed.
  - Phase one: symmetric repeat agreement (Dice over a deterministically oriented alignment, since difflib depends on argument order); folio markers stripped in all spellings; summary with distances, reference class, a degenerate flag (fair reference under 100 characters, reproducing the two excluded pages) and a versioned normalisation profile; pilots recomputed with the old figures kept as oldmetric files; amounts report with coverage (17 of 70 blocks decide); benchmark summary and published copy under the healthcheck.
  - Phase two: word consistency correlates with fair CER at Spearman -0.93 (it01) and -0.79 (it02), exact permutation p 0.007 and 0.048 at n=7, which licenses consistency-based triage. it02 has lower strict CER on 7 of 7 pages (sign test p=0.0078) at flat fair CER, replacing the site's undersized noise threshold. Uncertain markers reach 95.4 % precision at 25.4 % recall under it01 against 88.4 % at 39.3 % under it02. The site uses length-weighted micro CER (page mean secondary) and excludes degenerate references by flag. The untuned pilot document scores about four CER points better than the benchmark pages. The it02 prompts are accepted as the frozen production configuration of the edition track; their hashes match the committed runs.

### 2026-08-28 corrected: second stabilization wave

- Source: items deferred from the morning pass.
- Target: benchmark metric, `io_paths.py`, `build_register.py`, `build_graph.py`, viewer modules, `transform_sources.py`.
- Result:
  - Numeral metric: numberishness is decided on the uncollapsed token, before the fair profile's v-to-u collapse; 684 tokens in 61 types returned to numbers at about two percent false positives (`vil`, `vm`). Pages without numerals report null. 31 of 36 page-iteration values changed (numbers down, words slightly up); it02 still raises number consistency. Pilot figures keep the old metric because both experiments are closed. Prompt assembly byte-identical by hash.
  - Consolidation: one atomic JSON writer, loader and `PIPELINE_DIR`/`REPO_ROOT` in `io_paths.py`; Inventaria derivation and input loaders once in `build_register`; `build_graph --out` puts `graph.jsonld` under the byte-identical gate. `extract_entities` keeps its own writer, because its committed files are research data without trailing newline. Known consequence: the TEI self-digest hashes `build_tei.py` alone although imported modules shape its output.
  - Viewer: inline JavaScript moved into `entity-view.js`, `viewer-render.js` and `viewer-review.js`, verified byte-identical in exports and markup; `nextStatus` exported for testing.
  - Dating: century ranges had collapsed to the first century, "15.–18. Jh." read as the eighteenth, a leading "bis" became a negative year. Eleven entries changed; an open start is null, renders from the raw string and sorts with the undated. The migrate path recomputes `datierung` from `raw`. Open: two years with intervening material (`1280 (ca.)-1480 (ca.)`) collapse to the first year, and trailing-dash open ends stay asymmetric, pending a decision on forms like `ca. (1450) 1600–1850`.

### 2026-08-28 corrected: stabilization pass over pipeline, viewer and stylesheet

- Source: four-part deep review (pipeline, evaluation and scripts, site JavaScript, CSS and tooling).
- Target: `check_pipeline.py`, `apply_review.py`, viewer, TEI.
- Result:
  - The idempotence check rebuilds the register with `carry_from` at the real pipeline directory; the empty-directory rebuild lost review state and would have turned the gate red with the first review. `_only_review_state` removed.
  - Review export: a missing `status` key is refused in validation, malformed JSON is a named refusal, and edition runs are accepted as review base, without which self-transcribed documents were unreviewable.
  - Viewer: status buttons got explicit toggle semantics (the shared toggle demoted an approved page to `gesichtet`). The `page` parameter is a page number, not an array index. The draft badge is the floor of machine-output marking in synopsis mode.
  - Editing `build_tei.py` re-pins the digest in all TEI headers; regenerated under the on-disk date. Deferred to the second wave: numeral metric, zero consistency for pages without numerals, date normalization, fail-closed writes in the SiCProD fetch scripts, viewer module extraction, shared `io_paths`.

### 2026-08-28 integrated: register view and catalogue extent

- Source: two approved packages.
- Target: exploration, `sources.json`, `transform_sources.py`, site.
- Result: `?view=register` shows the corpus-wide entity index from `graph.jsonld` with type tabs, attested spellings, deep links per attestation and the `register.xml` fragment as citable address. `seiten` replaced by `catalogue_extent {value, unit, raw}` with a conservatively derived unit (`bilder` where account-book evidence proves it, `seiten` where A 006 side counts hold, `unbekannt` otherwise; `raw` empty until the catalogue CSV is next available); `transkribus_docs` is an array; `digital_images` the derived sum. The site shows scans first with the catalogue extent as labelled secondary, and the progress bar computes both sides from the register in one unit. Migration runs as `transform_sources.py --migrate` because the CSV is outside the public clone.

### 2026-08-28 integrated: feedback response to the project lead

- Source: fourteen feedback points on the prototype.
- Target: response document, handoff.md, project.md, specification.md.
- Result: seven implemented, two clarified as data-function questions (SiCProD exports versus SiCProD-mediated digitisations; source-based network instead of the old database view), four partly open (independent non-Inventaria source, annotation harvest, review-effort quantification, proposal reconciliation), one superseded. The mail proposed a working edition for the project lead's research, offered Inventaria the generated TEI in return for clarified transcription use and annotation licensing, and announced an annotation editor with reconciliation against SiCProD, Wikidata, GND, Inventaria and Getty AAT. This revived the Inventaria coordination set aside that morning, now mediated by the project lead.

### 2026-08-28 corrected: Inventaria in the TEI headers

- Source: TEI that named Inventaria nowhere and claimed an unrevised layer for fully corrected documents.
- Target: `build_tei.py`, `docta.rng`, `check_pipeline.py`.
- Result: every attributed document carries `resp-inventaria-transcription`, worded by Transkribus done status (all pages, a stated split, or none), a `bibl` with the edition link where known, and a matching editorialDecl. Done is named a platform workflow status and an Inventaria step; DoCTA's facsimile review stays a separate axis. Attribution mirrors the projection's derivation from `source_mapping.json` and `inventaria_mapping.json`. `docta.rng` gained the three needed shapes; the entity-reference check is scoped to elements with the entity responsibility, since `@ref` on a project name addresses the project.

### 2026-08-28 corrected: layer-explicit provenance, sticky controls, exploration

- Source: operator session over the running site.
- Target: viewer, home page, exploration.
- Result: the entity legend leads with "Entities" and every text chip with "Text:", since an unlabelled extraction model beside "Human-corrected (Inventaria)" read as a contradiction. The Transkribus fallback reads "no correction recorded", because a missing done status documents nothing. Search row, chips and key stick under the navbar; the navbar itself had lost `sticky-top` to Bootstrap's `position-relative !important` added by the BETA code. A returning-visitor 404 came from a projection shape change without a `DATA_VERSION` bump; shape changes under `data/` must bump it. The entities view moves constant columns into a facts line and gains a filter and deep links; the network gains neighbourhood isolation, legend, shared tooltips, triangle object nodes and keyboard access. VLM-transcribed documents are clickable from home, and thumbnails fall back to collection metadata.

### 2026-08-28 rejected: knowledge page on the site

- Source: operator decision.
- Target: `docs/knowledge.html` (removed), About, benchmark.
- Reason: the knowledge base addresses agents and repository readers; site visitors do not use it, and GitHub renders the Markdown.
- Result: page, sidebar styles and entry points removed; About and benchmark link to `docs/knowledge/` on GitHub. Supersedes the knowledge viewer part of the refactor below; naming and frontmatter stay.

### 2026-08-28 integrated: knowledge base on the Promptotyping convention

- Source: the convention's naming contract.
- Target: `docs/knowledge/`.
- Result: lowercase canonical names with `INDEX.md` as registered exception: `REQUIREMENTS.md` to `specification.md`, `TECH.md` to `architecture.md`, `CONTEXT.md` to `domain-knowledge.md`. Frontmatter core on every hand-written document with `version: "1.0"` and `template:` where a template exists. `project.md` (charter from INDEX and README) and `handoff.md` added. `INDEX.md` became navigation, glossary and routing register; its phase narrative moved to `project.md`. Keeping uppercase names was rejected, because the file name is the agents' primary routing signal.

### 2026-08-28 corrected: About page framing

- Source: operator review.
- Target: about.html.
- Result: the page no longer presents the prototype as a reply to reviewers or proof of a predetermined claim. It starts from the historical scope, names the questions the prototype tests, states coverage and separates edition provenance from DoCTA annotations; the workflow is research infrastructure for comparative source analysis. Reproducibility guarantees stay in the knowledge base.

### 2026-08-28 integrated: a document DoCTA transcribes itself

- Source: document 12593450 (A 024.1, one sheet, 1489) without Transkribus transcription; 12647153 (A 006.8) page 1.
- Target: `docta.rng`, `build_register.py`, `build_tei.py`, `evaluation/edition/`, viewer.
- Result: the pipeline transcribes, encodes, extracts entities and displays these documents, naming DoCTA at every step. Five decisions, each against a named alternative:
  - `resp-vlm-transcription` as a fifth responsibility naming model and prompt iteration; reusing `resp-transkribus-layer` would assert a work step that never ran. Status stays `machine-unrevised`, since the axis measures revision, not the model.
  - Synthetic line ids `v1..vn`, assigned deterministically from run line order and relative to the run, for the edition cohort only; benchmark and pilot runs keep `null`. Ids for every VLM run would rewrite hundreds of measuring runs to no purpose.
  - A separate append-only `edition` cohort with one reading per page and no summary, because a second reading raises the question which is the edition text, and without repeats or reference there is no metric.
  - A site projection at `docs/data/pipeline/transcriptions/<docId>.json` instead of a fake export; `docs/data/transcriptions/` stays Transkribus alone and `source_mapping.json` keeps `has_text: false`.
  - No content-class value: such a page stays `unknown` until adjudication on the scan, and is not counted as a page with text.
  - The TEI has no zones and unbound `lb`, keeps the facsimile with the IIIF URL the model read, and one `<ab>` per page. Pages 2 to 6 of 12647153 need an authenticated Transkribus `fulldoc` call with `TRANSKRIBUS_USER` and `TRANSKRIBUS_PASS`; they stay empty until it runs.

### 2026-08-26 integrated: VLM transcription test

- Source: four openings of account book 2 and one inventory page, six variants of `gemini-3.7-flash`, outputs under `experiments/transcription-test/`.
- Target: htr-evaluation.md.
- Result:

| Finding | Consequence |
|---------|-------------|
| V3 few-shot reaches the best strict and fair CER on the inventory reference candidate | V3 carried on as development configuration |
| V6 image enhancement reaches the highest word overlap and second-best fair CER | V6 stays a candidate for hard pages |
| V4 page splitting worsens the inventory values | Crops only for difficult regions |
| Account-book outputs vary in names, years and amounts | Suits structural and category survey; research data need adjudication |
| The blank test page is recognised by all structured variants | Blank-page and layout triage can enter a continuous run |

  Three inventories hold `DONE`, the rest `IN_PROGRESS`, none a documented ground-truth status, and two transcription conventions occur; "ground truth" therefore reads as **inventory reference candidate**. Production decisions are taken per task (category survey, diplomatic transcription, amounts), and the next comparison uses one held-out account-book set for the current configuration, a stronger VLM and a specialised Transkribus model, with divergences shown with image details for adjudication. All outputs are unrevised.

  Phase status on 2026-08-26: preparation, exploration (SiCProD, catalogue CSV, Transkribus collection of 115 documents and 12,236 pages, IIIF), distillation (eight knowledge files and a project-internal `IMPLEMENTATION.md`) and implementation (eight pages, public since 2026-02-19) done; HTR iteration running.

### 2026-02-19 integrated: implementation-phase decisions

- Source: implementation commits of 2026-02-18 and 2026-02-19.
- Target: network view, help page, home page.
- Result:

| Question | Decision | Reason |
|----------|----------|--------|
| Network entry (86783f2) | Ego network by default, Sigmund at the centre, up to fifty neighbours, concentric layout; click opens a node's ego network; full network of the 75 best-connected nodes (COSE) behind a toggle | The full network was a cloud without a statement; an ego network answers who stands around a person |
| Faulty node types (d89a58c) | Entities without index entry (`event-*`) filtered before drawing | The full network crashed |
| coOCR/HTR (d89a58c, 25489aa) | Named in the HTR pipeline step and the reviewer section as editor in the loop for Transkribus results | Answers review point 3 concretely |
| Data commitments (25489aa) | FAIR publication of all research data and a documented REST API over persons, relations, sources and transcriptions, beside the open repository | Makes reusability checkable |
| Home figures | Six raw counts, no derived ratios | A ratio needs a denominator that does not yet exist |

### 2026-02-17 integrated: prototype decisions with the DH partner

- Source: agreement with the DH partner.
- Target: architecture.md, specification.md.
- Result:

| Question | Decision | Reason |
|----------|----------|--------|
| Prototype type | Functional tool, not a mockup | The reviewer should interact with it |
| Priorities | Pipeline demo, then faceted search, then source exploration | The pipeline answers the review criticism most directly |
| Stack | Vanilla JavaScript as in coOCR/HTR | Consistency, no build |
| Deployment | GitHub Pages | Static and public |
| Authentication | None | Reachable for reviewers |
| Images | Transkribus IIIF URLs, fallback if needed | IIIF in `<img>` presumed CORS-free |

  Open at that date: the case study (kitchen categories in account book 2, "Provision und Sold" as its own study, or another account book; the project lead after checking a possible master of the kitchen), entity granularity (four demo types against nine in SiCPAS; project lead with the BeNASch team), mapping practice onto BeNASch (on example entries, with the Bern team), open-source positioning of coOCR/HTR (raised 2026-02-04, response outstanding). Still open for the proposal: a methodological text module for the resubmission, the case study, the BeNASch mapping, literature on historical linguistics (review point 5); optional: a spreadsheet URL for further metadata and the glossary idea of the project lead.

### 2026-02-17 integrated: SiCProD, catalogue and Transkribus exploration

- Source: SiCProD API, catalogue CSV, Transkribus collection 2197991 (figures updated 2026-08-26).
- Target: data.md, domain-knowledge.md, specification.md.
- Result:

| Assumed | Found | Consequence |
|---------|-------|-------------|
| SiCProD events, number unknown | Only 28 (diets, imperial diets, weddings) | Everyday practice comes from the account books |
| Salaries, 2,906 records | No amounts, only person-function links | Financial data from the account books |
| Institutions, 215 typed | 207 without type | Institution filter of little use |
| About 99 functions | About eighty court offices | Good for faceted search and court structure |
| 736 places with coordinates | Many without lat/lng | A map will have gaps |
| 6,288 persons | `first_name` filled for 6,281, `status` always empty, `alternative_label` useful | Given name shown, `status` not exported |
| About 55 inventories transcribed | 57 carry text (8,979 lines, 35,724 words); three `DONE`, 54 `IN_PROGRESS` | Working transcriptions, partitioned by convention |
| Account books untranscribed | Confirmed: 26 books, 8,561 pages; volumes 1 to 6 have layout analysis; since 2026-08-26 unrevised VLM output for four openings of book 2 | Compare a specialised HTR model against a checked reference |
| Collection extent unclear | 115 documents, 12,236 pages: 64 inventories, 26 account books, 12 copybooks, 13 others | More material than expected |
| IIIF possibly blocked by CORS | Loads without authentication | OpenSeadragon uses IIIF directly |
| PAGE XML unknown | Page, TextRegion with coordinates, TextLine with coordinates, baseline and Unicode | Pre-fetch parser is straightforward |

  Prototype prerequisites, all closed: credentials through `TRANSKRIBUS_USER` and `TRANSKRIBUS_PASS`; collection 2197991; 115 documents in `data/transkribus_collection.json`; IIIF without authentication; IIIF URLs for all 123 openings of account book 2 in `data/raitbuch2_pages.json`; 57 PAGE exports as JSON in `data/transcriptions/`; all 64 inventories matched to shelfmarks in `data/source_mapping.json`.

  Catalogue CSV: sixteen empty Excel columns; Digitalisiert holds a page count; Transkribiert holds "Inventaria" or nothing; more than ten date formats; inconsistent dashes between the Repertorium section and the rest; Hs. 0041 duplicated, A 002.1 and A 2.1 a near duplicate; seven sources outside Sigismund's lifetime; a date in the Art column (row 304). 57 of 312 sources are transcribed, all castle inventories from Inventaria, no account book.

  Documents in the collection not marked transcribed in the CSV: twelve copybooks (2,224 pages, images only); court and regiment ordinances TLA_HS_208.1 and 208.2 (149 pages); the wedding cluster Hs. 2466, 2467, 2468, 2469 with 33, 58, 19 and 54 scans against catalogue statements of 60, 100, 35 and 140 pages, which set represents the complete volume being unresolved (data.md); Hs. 113 (133), Hs. 324 (86), Hs. 514 (16), Hs. 792 (7), Hs. 5087.1+2 (218).

  Coverage gaps closed from project-internal sources (not in the public repository): epistemic asymmetry (`sources/coocr-htr-epistemologie.md`) and the category discrepancy between the proposal and SiCPAS into domain-knowledge.md; phase 1 sequencing and the project lead's requirements into specification.md; open questions on account book 2 into data.md. Deliberately not captured: the proposal's bibliography, work packages and Gantt chart, financial detail.

### 2026-02-17 rejected: dead ends

- Source: exploration and prototype work, one item from 2026-08-05.
- Target: none; lessons apply to future work.
- Result:

| What | Why | Lesson |
|------|-----|--------|
| Transkribus API in the browser | CORS, and OAuth2 in the client is insecure | Pre-fetch with Python |
| SiCProD events for practice data | Only 28 major events | Practice comes from the account books |
| SiCProD salaries for financial data | No amounts | Financial data from the account books |
| Reading the SVG model diagram | 742 KB on one line | Content carried into domain-knowledge.md as text |
| PDF reading on Windows | pdftoppm unavailable | Agent-based extraction |
| Transkribus authentication | 401 until the credentials were corrected | Take credentials directly from the user |
| "Correcting" the funding body (2026-02-18) | A review replaced correct references project-wide with "FWF"; reverted 2026-08-05, since APART-GSK is a programme of the originally named body, whose review it was | Check proper names of programmes and institutions against an external source, not against majority use in the repository |
