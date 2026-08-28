# Page register

The register is the data backbone of the agentic edition pipeline. It holds one entry per source document that carries a Transkribus doc_id and one entry per page of that document, and it records for every page what the page contains, how far it has been verified, and which transcription runs exist for it. It is derived data, rebuilt from repo-local files by `build_register.py`, and no step of the pipeline writes into it by hand.

## Layout

`documents.json` is a list of document entries. Each carries `docId`, `shelfmark` (archival signature), `title`, `dating` (`raw`, `start`, `end`), `category`, `pages`, `tier`, `has_text`, `transkribus_statuses`, a count of pages per Transkribus page status, `done_pages`, how many of them carry the status DONE, `provenance` (currently always `transkribus`) and `attribution`, which is unused and always `null`; who made a transcription is derived in the site projection from the `csv_transkribiert` flag of the source mapping.

`pages/<docId>.json` holds `docId` and a `pages` list. Each page entry carries `pageNr`, the `iiif` image URL where one is known, `content_class`, `empty_evidence`, `verification` and `runs`.

`empty_evidence` is `null` or an object with `method`, `runs` (how many runs support the evidence) and `scope`. Scope `full` means every reporting run saw the whole page image empty; `partial` means at least one part of a spread was reported empty, which is the usual case for a Raitbuch page, where a blank verso faces a written recto.

`verification` is an object with a `status` field. A page that a reviewer has handled in the viewer additionally carries `reviewer`, the initials of the person, and `date`, the day the review was exported.

## Vocabularies

`content_class`

- `text`: the page carries text
- `leer`: the page is blank
- `kassiert`: the page is struck through as settled or cancelled
- `einlage`: an inserted slip rather than a page of the book
- `unknown`: not yet determined

A page only reaches a class other than `unknown` on evidence. The Transkribus export establishes `text`; the remaining classes need the scan and an adjudication step, so a page without exported lines stays `unknown` even when a model reports it empty.

`empty_evidence.method`

- `heuristik`: derived from image statistics or layout analysis
- `vlm`: a vision model reported the page or a part of it empty
- `mensch`: established by a person on the scan

`verification.status`

- `unbearbeitet`: no transcription has been reviewed
- `maschinell`: a machine transcription exists and has passed automatic checks
- `gesichtet`: a person has read the transcription against the scan
- `abgenommen`: the transcription is accepted as the edition text

## Runs

A run is one transcription of one page from one source, and runs are immutable. A run is never edited or removed; a better transcription is a new run.

Every run carries `id`, `source`, `date`, `lines` and the six model fields `model`, `prompt`, `prompt_hash`, `repeat`, `empty` and `empty_parts`, so a consumer reads one shape whatever the origin. The Transkribus run carries all six as `null`, because the export names no recognition model, was not produced by a repeat and reports no emptiness of its own. A review run additionally carries `reviewer`.

`lines` is a list of `{"id", "text"}` objects in reading order. The id is the Transkribus layout line id where the run knows one. A vision model returns text without layout identity, so a VLM run has no such id, and what happens then depends on what the run is for. A measuring run of the benchmark or a pilot keeps `null`, because it is read as a whole and nothing addresses a single line of it. A run of the edition cohort carries the text the edition is built from, so its lines are given the synthetic ids `v1`, `v2` and so on, assigned at register build in the order the run reported them. Those ids are relative to their run and assert nothing about the layout of the page; they are what lets a review, an entity anchor and a TEI line address one line.

The run id encodes the origin and makes rebuilds stable. The Transkribus export is the single run `transkribus` on a page; a model run is `benchmark:<run file stem>`, `pilot:<run file stem>`, `pilot2:<run file stem>` or `edition:<run file stem>`, so its record in `evaluation/` remains the source of truth for everything the register does not repeat (image handling, duration, full structured output). `empty` is true only when the model reported every part of the page image empty; `empty_parts` lists the flag per image part in the order the run reported them, which for a Raitbuch spread means verso and recto.

The four model cohorts differ in purpose, not in shape. `benchmark`, `pilot` and `pilot2` measure a prompt configuration and repeat every page; `edition` transcribes the sources Transkribus holds no text for and runs each page once, and its runs are the text every later step reads. `evaluation/edition/README.md` states the scope of that cohort and what is not transcribed yet.

A page of a document without a Transkribus export gets its `iiif` from `docs/data/edition_pages.json`, the image table of the documents DoCTA transcribes itself. A page the table does not name keeps `iiif` `null` and stays untranscribed, since there is no image to send.

A page carrying an edition run keeps `content_class` `unknown` like every page without an export. What a page holds is settled on the scan in an adjudication step, and that step has not run for these documents; the transcription is recorded as a run and asserts no class.

## Review ingest

The browser viewer lets a reviewer read a page against its scan, mark it `gesichtet` or `abgenommen` and correct single lines. It exports that as one file per document, and `apply_review.py` writes the export into the register, which stays the only place where the state of a page is held.

```json
{"docId": 11327963, "reviewer": "XY",
 "pages": {"2": {"status": "gesichtet", "date": "2026-09-03",
                 "lines": [{"id": "r2l1", "original": "…", "corrected": "…"}]}},
 "exported": "2026-09-03T10:15:00Z", "source": "docta-viewer"}
```

The status of a page becomes its `verification` together with the initials and the date. The corrections of a page become a new run `review:<docId>-<pageNr>-<date>-<reviewer>` with `source` `human`. That run carries the full line list of the page with the corrections applied, so it is readable on its own and the transcription it produced can be reconstructed without replaying a diff. Re-applying the newest export of a page replaces its run in place, which makes the ingest idempotent for that export. An older export of the same page is a different matter, because the corrections it reports were written against a base text that the newer export has since replaced; it fails the check on the reported original and is refused.

A review is written against the base text it was made on, meaning the newest earlier review run of the page, where none exists the Transkribus run, and for a document DoCTA transcribed itself the newest edition run, whose synthetic line ids are what the viewer addresses there. Every corrected line must still carry its reported `original` in that base. Where it does not, the export was taken before another change, and the ingest refuses instead of overwriting work with a stale reading. The same refusal covers a line or a page the register does not know and every violation of the review specification above.

Validation and writing are separate phases over the whole invocation. Every file passed to a run is validated first, and the register is written only when all of them pass. A single bad file therefore leaves the register untouched and the run exits nonzero, so a batch never lands half applied and a rerun after the fix has nothing to unpick. `--dry-run` stops after the validation phase and reports what would be written.

A page marked reviewed without a single correction records the verification and no run, because there is no new transcription to record.

```
python apply_review.py                       # ingest pipeline/reviews/
python apply_review.py review-11327963.json  # one or more files
python apply_review.py DIR --dry-run         # validate and report only
pytest pipeline/test_apply_review.py
```

## Rebuilding

```
python build_register.py             # write documents.json and pages/
python build_register.py --project   # additionally write the site projection
pytest pipeline/test_build_register.py
```

The builder reads only files already in the repository and makes no network calls; Transkribus exports and evaluation runs are its input. It is deterministic, so a rebuild over an existing register reproduces the same bytes, which the test suite checks.

The review state is the one thing the rebuild cannot derive from those inputs, since it was written by `apply_review.py` from a viewer export. The builder therefore reads the existing register before it writes and carries that state over, meaning every page whose `verification` differs from `unbearbeitet` together with the `review:` runs of that page. A rebuild after new Transkribus data leaves the reviewed pages as they stand and destroys no review. Which register the state is carried from is a parameter of `build`, defaulting to the directory it writes into. The healthcheck builds into a temporary directory and points that parameter at `pipeline/`, so its byte comparison runs against the reviewed working tree instead of against a register nobody has reviewed.

The projection at `docs/data/pipeline/register_summary.json` is the compact view for the site: per document the identity fields plus page counts by state, small enough to load in one fetch. It is generated output and never edited by hand. `transcription_source` says where the text of a document comes from, `transkribus` for the export, `vlm` for a text DoCTA produced itself, `null` for a document with no text at all, and the viewer reads both the file it loads and the wording of its provenance chip off that field.

Beside the projection the same run writes `docs/data/pipeline/transcriptions/<docId>.json`, one file per document DoCTA transcribed itself. It holds the lines of the newest edition run of every transcribed page in the shape of a Transkribus export, so the viewer reads one structure whatever produced the text, together with a provenance block naming the runs and the state `machine-unrevised`. The line coordinates stay empty, because a vision model reads text and analyses no layout, and the viewer therefore draws no line regions for such a document. `docs/data/transcriptions/` stays what it is, the Transkribus export, and no pipeline step writes into it.

## TEI baseline

`build_tei.py` writes one TEI P5 file per document that carries a text to `docs/data/tei/<docId>.xml`. What the text of a file is depends on its layer, on who transcribed it and, for the Transkribus layer, on its correction state, and the `editorialDecl` says it in plain words for that state. A document the Inventaria project corrected and marked done in Transkribus is therefore never presented as unrevised machine transcription; its declaration names the project, states that DoCTA has not independently verified the text against the facsimile, and keeps the two status axes apart. The files are a working substrate for the edition; a citable edition text needs the scholarly pass that has still to happen.

Every file carries its work-step provenance in the header, following the pattern of the ZBZ project. The `titleStmt` declares one `respStmt` per step that actually happened, one of the two transcription steps and `resp-tei-generation` for the deterministic generation, which names `build_tei.py` together with a sha256 digest over its own source, so the generating code version is pinned in the data and a script change is visible as a change in every file.

Most of the corpus carries a transcription the Inventaria project made in Transkribus, and every such file declares that origin as `resp-inventaria-transcription` directly after the Transkribus layer it qualifies, with `<name ref="https://www.inventaria.at/">Inventaria project</name>`. The wording follows the DONE page count, a transcription produced and corrected by the project for a document marked done throughout, the same with the page split where only part of it is done, and the transcription campaign with no page marked done for the rest. It says outright that DONE is a workflow status of Transkribus, because the DoCTA review of a page against the facsimile is a separate axis that lives in the page register and is never derived from a Transkribus status. Where the harvest found the published edition of a document, `sourceDesc` carries a `<bibl>` linking it beside the archival description. Which documents are attributed and which link belongs to them comes from the two files the site projection also reads, the flag `csv_transkribiert` in `docs/data/source_mapping.json` and the deep links in `docs/data/inventaria_mapping.json`, so the TEI and the site cannot disagree about who made a transcription. A text DoCTA produced itself never picks the attribution up, whatever the mapping says about the source.

The two transcription steps are alternatives, and which one a file declares says where its text came from. `resp-transkribus-layer` covers the export, worded according to whether the pages were corrected and marked done in Transkribus or carry the unrevised recognition layer. `resp-vlm-transcription` covers a text the DoCTA pipeline produced itself with a vision-language model, for a source Transkribus holds no transcription of, and it names the model and the prompt iteration that produced it. Declaring the Transkribus layer on such a file would assert a step that never ran on that source, which is why the second responsibility exists rather than a reuse of the first. Its stream status stays `machine-unrevised`, since the status axis measures how far a text has been revised and a model reading is unrevised whichever model produced it. A file that carries a review layer additionally declares `resp-expert-verification` for the page-level review in the viewer; a file without one never does, because a responsibility declaration asserts a step that ran. In `revisionDesc` the generation entry points at its responsibility through `@who`, each reviewed page adds one `n="review"` entry naming the page and the initials of the reviewer, and one summary entry per stream carries the current state in `@status`, `transcription-summary` with `human-corrected`, `partly-corrected` or `machine-unrevised` derived from the DONE page count, and `tei-summary` with `machine-generated`.

### Text source

Where the text of a document comes from is answered in one place, `build_register.transcription_of`, which returns the Transkribus export where one exists and otherwise the edition runs of the register in the same shape. TEI generation, entity extraction and the healthcheck all ask there, so the three cannot disagree about what a document says.

Within that, the text of a page comes from the review layer of the register where one exists. A page whose register verification is `gesichtet` or `abgenommen` and which carries a review run is written from the lines of its newest review run; every other page is written from the raw Transkribus export. The layout data always comes from the export, so zones and `lb` bindings are unaffected, since a correction changes a reading and leaves the position of the line on the image alone. Entity anchors are cut against the text the file actually carries, so a corrected line is matched on its reviewed reading.

The review layer outranks the Transkribus states in `transcription-summary`. A document with some reviewed pages reports `partly-reviewed`, a document whose every page is `abgenommen` reports `approved`, and a document without a review keeps the state derived from the DONE page count. The `editorialDecl` says the same in plain words for a reader of the file.

The register is read from `pipeline/pages/` and can be pointed elsewhere with `--register`, which is what the fixture test uses to build a reviewed document without any review data in the repository.

### Structure

The encoding is diplomatic and follows the page, the text region and the line. Each page opens with a `<pb>` whose `@facs` points at a `<surface>` in the `<facsimile>` section, and that surface carries the IIIF URL of the scan as a `<graphic>`. Images are referenced and never copied into the repository. Each text region of the export becomes one `<ab>` under that `<pb>`, carrying the region id of the layout analysis in `xml:id` as `ab-<docId>-<pageNr>-<regionId>`, so a block of the TEI and a block of the layout analysis stay addressable in both directions. Every transcribed line becomes an `<lb/>` followed by its text, so the line count of a TEI file equals the line count of the export, which the test suite checks. A line that consists only of a folio mark such as `[fol.3v]` is a reference point of the transcription rather than text of the source and becomes `<milestone unit="folio" n="3v"/>`; a line marking a cover or pastedown becomes `<milestone unit="cover"/>` with the corresponding `@n`.

Each transcribed line of the export also becomes a `<zone>` under the surface of its page, carrying the line polygon of the Transkribus layout analysis verbatim in `@points`, and the `<lb>` of that line points at the zone through `@facs`, so a text line and its image region are bound in both directions. Zones and `lb` are derived from the same iteration over the export, which is what keeps them in step; a line without coordinates gets no zone and its `lb` stays unbound rather than carrying a dangling reference.

A document whose text DoCTA transcribed itself has no layout analysis behind it, so it carries no zone at all and its `lb` elements stay unbound. It keeps its `<facsimile>` all the same, with one `<surface>` and the IIIF URL of the page that was transcribed, because that image is what the model read. Its body has one `<ab>` per page, `ab-<docId>-<pageNr>-vlm`, since a vision model returns no region structure and inventing one would claim a division the source analysis never made. The line ids are the synthetic ids of the edition run.

A line that became a milestone gets no zone at all. Folio and cover marks are reference points the transcriber wrote into the text, so they carry no `@facs` and leave no surface region behind; emitting a zone for them would assert an image region for something the source does not hold. Zones therefore count the read lines of a page.

An entity layer is read per document from `docs/data/entities/<docId>.json`. The file states the docId it belongs to, so no document can pick a layer up by accident, and a document without such a file simply has no entity layer. The same directory is what `entity_index.py` builds the register ids from, so the encoded anchors and the register entries cannot address different extractions. The layer is encoded inline as `<persName>`, `<placeName>` and `<term>`, each one pointing with `@ref` at its entry in the corpus-wide register described below; an object of these inventories is a common noun, which is why it becomes a `<term>` and never a name. The normalised form itself is written nowhere in the document file, so `@key` is absent and one entity attested in several documents is one register entry rather than a form repeated per occurrence. A file with an entity layer declares a further responsibility, `resp-entity-llm`, which says in plain words that an LLM agent produced the extraction in the prototype phase and that no scholar has verified it; every marked entity points at that responsibility through `@resp`, and its `editorialDecl` repeats the state for a reader of the file. No certainty attribute is emitted anywhere, because the confidence value the extraction reports is a self-assessment of the extracting agent and not evidence about the source. An entity is encoded only where its position is deterministic, meaning it names the line it sits in and its surface form occurs in that line verbatim, case-sensitive, exactly once. An entity without a line reference, of a type the encoding does not cover, or whose form is absent or ambiguous in its line is left unencoded and reported per run with its reason, because placing it would assert a reading that was never established. Two entities whose spans overlap in the same line are the fourth such case. The encoding admits no nesting, so one of them is left out, and it appears in the same report with its reason instead of vanishing silently.

### The entity register

`build_tei.py` also writes `docs/data/tei/register.xml`, one TEI file holding the corpus-wide entity index as `<standOff>`. Persons stand in a `<listPerson>` as `<person>`, places in a `<listPlace>` as `<place>`, and the object terms in a `<list type="objects">` as `<item>`, since an object of these inventories is a common noun that no name element fits. Each entry opens with the normalised form and then carries every spelling attested for it in the transcriptions, marked `type="attested"`, so the variants stay readable beside the form the documents are addressed by. Time entities have no entry, because the extraction resolves no calendar dates yet and an unresolved date is no register entity.

The ids come from `entity_index.py`, which merges one entry per distinct pair of type and normalised form and gives it a slug id such as `per-hans-clamer`, `pl-kronburg` or `obj-kuerass`. `docs/data/graph.jsonld` names its nodes by the same ids, so an entity carries one identifier across the TEI documents, the register and the JSON-LD graph, and the healthcheck holds the three sides to it. An entry that no document points at is normal, because an entity whose anchor was not placeable stays unencoded in the text while the extraction remains readable in the register.

The register declares the two steps that produced it. `resp-entity-llm` covers both the identification of an entity in a line and the merging of its spelling variants under one normalised form, since the extraction reported both, and the header prose says so; `resp-tei-generation` covers the deterministic assembly of the file and names the script digest. The register gets the same treatment as every other file of the directory, meaning the date from `--date`, byte-identical rebuilds, and both validation stages.

Structure beyond the page and the region is not asserted. The body holds a single `<div type="transcription">` with `<pb>` and `<ab>` blocks, because the export gives no paragraph or section boundaries that an unread transcription could justify. The `<ab>` element avoids claiming a `<p>` the source has not been read for; a region type curated later can be added as an attribute on the block that already exists.

The header carries only what the source register actually holds, which is the archival title and shelfmark, the repository, the collection and item number parsed from the shelfmark, the Transkribus doc id as an `altIdentifier`, and the archival dating as an `origDate` that keeps the raw string as its content and normalises it into `@when`, `@from`/`@to` or `@notBefore`/`@notAfter` according to its precision. An element whose data is missing is omitted instead of filled with a placeholder. The text is tagged `xml:lang="gmh"`; ISO 639-3 registers no code for Frühneuhochdeutsch, so the Middle High German code serves as the nearest registered approximation and `langUsage` says so.

The generation date comes from `--date` and never from the clock, so a rebuild without input changes produces byte-identical files and leaves no diff. Every document is re-parsed before it is written, so a malformed result fails the run rather than reaching the disk.

```
python build_tei.py                  # write docs/data/tei/
python build_tei.py --date 2026-09-01
python build_tei.py --register DIR   # read the register elsewhere
pytest pipeline/test_build_tei.py
```

## Quality gates

Two gates stand between the generators and a commit, the two-stage schema validation and the cross-artifact healthcheck. Both are wired into the pre-commit hook configured in `.pre-commit-config.yaml`, which is what actually runs them; `uv run pre-commit run --all-files` reproduces that run by hand. The healthcheck's clean rebuild is slow, so under pytest it sits behind the `slow` marker and runs with `uv run pytest -m slow` and in the hook, while the ordinary test run stays fast.

### The two schemas

`validate_tei.py` validates the generated TEI in two stages and reports them separately, because they answer different questions. Stage one is TEI conformance against the vendored `schema/tei_all.rng`, a pinned TEI P5 release. Stage two checks the DoCTA encoding specification against `schema/docta.rng`, a hand-written RelaxNG derived from `build_tei.py` that admits exactly the elements, attributes and structures the generator emits and nothing else. Its start is a choice of the two file shapes the directory holds, one document TEI per transcribed source and the single entity register. The responsibility ids, the stream statuses, the milestone units and the entity elements are enumerated there as closed lists, the identifiers of surface, zone and `ab` and the slug ids of the register entries are pinned as patterns, and free text and legitimately varying values stay unconstrained. Two things are impossible by construction. A certainty claim, since `@cert`, `@certainty` and `<certainty>` are not in the grammar, so a file carrying one fails stage two even though it is valid TEI. And a normalised form on the entity itself, since an entity admits no `@key` and its `@ref` must match the pointer shape into `register.xml`. `--schema PATH` runs a single stage against one schema. Provenance and upgrade path of both schemas are in `schema/SOURCES.md`.

```
python validate_tei.py                            # both stages
python validate_tei.py --schema schema/docta.rng  # one schema only
```

### The healthcheck

`check_pipeline.py` checks the cross-artifact specifications that no single pipeline script can verify on its own. It checks the register against the export and against its own vocabularies, the three document sets against each other, the entity files, review exports and evaluation runs against their data specifications, the provenance rules that keep a model's self-assessment out of the edition data, the resolution of every cross-reference, the value ranges of the evaluation summaries, both schema stages, and finally the generators against themselves by rebuilding register, TEI and the JSON-LD graph into a temporary directory and comparing byte for byte.

The site transcriptions under `docs/data/pipeline/transcriptions/` are part of that comparison, in both directions like the TEI, so a drifted one and a stale one are both found. The projection writes them into the directory of the projection file it was given, which is what keeps a healthcheck rebuild inside its temporary directory.

That rebuild also answers the opposite question, which files the working tree holds that the rebuild no longer produces. A page file of a document that has left the collection, or a TEI file whose document lost its export, survives in the tree and is invisible to a comparison that only walks the freshly built side. Such orphans are reported by name, so a stale artifact is removed rather than published. The TEI side is compared over the glob of `docs/data/tei/*.xml` rather than over a list of document ids, which covers `register.xml` like any other file. For that comparison the check takes the generation date from the files on disk instead of from a constant in its own source, so the two sides differ only where the content differs and a rebuild after a date change needs no edit to the check.

The reference check also holds the projection flag `has_tei` against the TEI directory in both directions, because the projection derives the flag from the register while `build_tei.py` iterates the source mapping; a document paired outside that mapping would otherwise carry the flag with no file behind it and the site would offer a TEI view that resolves to nothing.

The reference check runs over the entity layer as well. Every `@ref` of a document has to resolve to an `xml:id` of `register.xml`, and the register and `graph.jsonld` have to name the same entities, since both take their ids from `entity_index.py`. An entry that no document points at is reported as INFO rather than as a defect, because an entity whose anchor was not placeable keeps its register entry on purpose.

The metrics check covers all three evaluation summaries, the two pilots and the benchmark. For the benchmark it reads the degenerate reference from the `reference_degenerate` flag the summary persists, never from the measured rate, and a page whose rate exceeds one while the flag is absent is a FAIL, because the criterion behind the flag then missed a case a consumer would have to exclude by value again. The same check holds `evaluation/benchmark/summary.json` and its site copy `docs/data/benchmark/summary.json` byte for byte, since that copy is made by hand and nothing else keeps the published figures and the measured ones together.

A finding is FAIL or INFO and carries the id of the check that raised it. INFO is a fact worth seeing that is not a defect, such as a page whose reference transcription is degenerate, a repeat pair whose line counts diverge far enough to want a third run, or a document that sits in one set and not in another for a reason already settled in the data. Only FAIL decides the exit code.

```
python check_pipeline.py             # every check, exit 0 only when clean
python check_pipeline.py --list      # the check ids
pytest pipeline/test_check_pipeline.py
```

## The accounts module

`accounts/` is the executable part of the account-book encoding specification. `docs/knowledge/accounting-encoding.md` and `docs/knowledge/editorial-model.md` are the specification; this module implements the part of it that a test can hold to, and it carries its own fixtures, schemas and tests.

Implemented are four things. `anchors.py` reads PAGE XML into source anchors and lines. `models.py` holds the pydantic models `SourceAnchor`, `TranscriptionLine`, `TranscriptionRevision`, `AnnotationProposal` and `ReviewDecision` with the separate status axes of the editorial model, so verification, editorial decision, formal validation and publication stay four independent fields. `review.py` supplies `proposal_is_stale`, `stale_proposal_ids` and `make_review_decision`, which is the machinery that makes a proposal fall out of date when the text it points into changes. `validate_tei.py` and `validate_rdf.py` run the account-book artefacts against the project RELAX NG, the Schematron rules and the SHACL shapes in `accounts/schema/` and `accounts/shapes/`.

The qualified line identity is the source, the document, the page, the region and the line, and the text digest is taken over that identity together with the text. The side of an opening, verso or recto, is derived from the page geometry and stays out of both. A derived value in an identifier would let a change in the geometry heuristic rename a line and invalidate every anchor pointing at it, which is exactly what the identity is supposed to prevent.

Annotation Sets, the Edition Build Manifest and the generation steps of the deterministic build, from TEI generation through the byte-for-byte clean rebuild, remain prose specification in `accounting-encoding.md`. A set hash and a manifest are testable only against the build that reads them, and that build does not exist yet; they enter the module with their first consumer.

## Known gaps in the input data

The CSV-to-Transkribus matcher in `docs/data/source_mapping.json` covers the inventories only, so Raitbuch 2 is paired with its archival entry in the builder itself, matched on title and page count.

Documents that are matched but have no export get a page list without IIIF URLs, because the page images are only known from the export. `docs/data/edition_pages.json` closes that gap for the pages DoCTA transcribes itself, but only as far as the repository knows the image keys, and it knows one key per such document, the first page, from `docs/data/transkribus_collection.json`. The keys of the further pages need an authenticated Transkribus `fulldoc` call with `TRANSKRIBUS_USER` and `TRANSKRIBUS_PASS`, of the kind `scripts/fetch_transcriptions.py` makes. Until it runs, five of the six pages of document 12647153 have no image reference and therefore no transcription.
