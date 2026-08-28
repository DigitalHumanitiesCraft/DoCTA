# Page register

The register is the data backbone of the agentic edition pipeline. It holds one entry per source document that carries a Transkribus doc_id and one entry per page of that document, and it records for every page what the page contains, how far it has been verified, and which transcription runs exist for it. It is derived data, rebuilt from repo-local files by `build_register.py`, and no step of the pipeline writes into it by hand.

## Layout

`documents.json` is a list of document entries: `docId`, `shelfmark` (archival signature), `title`, `dating` (`raw`, `start`, `end`), `category`, `pages`, `tier`, `has_text`, `provenance` (currently always `transkribus`) and `attribution`, which stays `null` until the published edition list allows an attribution such as `inventaria`.

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

A run is one transcription of one page from one source, and runs are immutable. A run is never edited or removed; a better transcription is a new run. Each run carries `id`, `source`, `date` and `lines`, a machine run additionally `model`, `prompt`, `prompt_hash`, `repeat`, `empty` and `empty_parts`, a review run additionally `reviewer`.

`lines` is a list of `{"id", "text"}` objects in reading order. The id is the Transkribus layout line id where the run knows one and `null` where it does not, which is the case for every VLM run, since a vision model returns text without layout identity. The ids are what lets a review address a single line of a page.

The run id encodes the origin and makes rebuilds stable. The Transkribus export is the single run `transkribus` on a page; a model run is `benchmark:<run file stem>` or `pilot:<run file stem>`, so its record in `evaluation/` remains the source of truth for everything the register does not repeat (image handling, duration, full structured output). `empty` is true only when the model reported every part of the page image empty; `empty_parts` lists the flag per image part in the order the run reported them, which for a Raitbuch spread means verso and recto.

## Review ingest

The browser viewer lets a reviewer read a page against its scan, mark it `gesichtet` or `abgenommen` and correct single lines. It exports that as one file per document, and `apply_review.py` writes the export into the register, which stays the only place where the state of a page is held.

```json
{"docId": 11327963, "reviewer": "XY",
 "pages": {"2": {"status": "gesichtet", "date": "2026-09-03",
                 "lines": [{"id": "r2l1", "original": "…", "corrected": "…"}]}},
 "exported": "2026-09-03T10:15:00Z", "source": "docta-viewer"}
```

The status of a page becomes its `verification` together with the initials and the date. The corrections of a page become a new run `review:<docId>-<pageNr>-<date>-<reviewer>` with `source` `human`. That run carries the full line list of the page with the corrections applied, so it is readable on its own and the transcription it produced can be reconstructed without replaying a diff. Re-applying the same export replaces the run in place, which makes the ingest idempotent and lets a viewer export be re-sent without care.

A review is written against the base text it was made on, meaning the newest earlier review run of the page or, where none exists, the Transkribus run. Every corrected line must still carry its reported `original` in that base. Where it does not, the export was taken before another change, and the ingest refuses the whole file with a nonzero exit instead of overwriting work with a stale reading. The same refusal covers a line or a page the register does not know and every violation of the review specification above.

A page marked reviewed without a single correction records the verification and no run, because there is no new transcription to record.

```
python apply_review.py                       # ingest pipeline/reviews/
python apply_review.py review-11327963.json  # one or more files
python apply_review.py DIR --dry-run         # validate and report only
python test_apply_review.py                  # or: pytest pipeline/test_apply_review.py
```

## Rebuilding

```
python build_register.py             # write documents.json and pages/
python build_register.py --project   # additionally write the site projection
python test_build_register.py        # or: pytest pipeline/test_build_register.py
```

The builder reads only files already in the repository and makes no network calls; Transkribus exports and evaluation runs are its input. It is deterministic, so a rebuild over an existing register reproduces the same bytes, which the test suite checks.

The projection at `docs/data/pipeline/register_summary.json` is the compact view for the site: per document the identity fields plus page counts by state, small enough to load in one fetch. It is generated output and never edited by hand.

## TEI baseline

`build_tei.py` writes one TEI P5 file per document with a Transkribus export to `docs/data/tei/<docId>.xml`. What the text of a file is depends on its correction state in Transkribus, and the `editorialDecl` says it in plain words for that state. The files are a working substrate for the edition; a citable edition text needs the scholarly pass that has still to happen.

Every file carries its work-step provenance in the header, following the pattern of the ZBZ project. The `titleStmt` declares one `respStmt` per step that actually happened, `resp-transkribus-layer` for the transcription layer, worded according to whether the pages were corrected and marked done in Transkribus or carry the unrevised recognition layer, and `resp-tei-generation` for the deterministic generation, which names `build_tei.py` together with a sha256 digest over its own source, so the generating code version is pinned in the data and a script change is visible as a change in every file. A file that carries a review layer additionally declares `resp-expert-verification` for the page-level review in the viewer; a file without one never does, because a responsibility declaration asserts a step that ran. In `revisionDesc` the generation entry points at its responsibility through `@who`, each reviewed page adds one `n="review"` entry naming the page and the initials of the reviewer, and one summary entry per stream carries the current state in `@status`, `transcription-summary` with `human-corrected`, `partly-corrected` or `machine-unrevised` derived from the DONE page count, and `tei-summary` with `machine-generated`.

### Text source

The text of a page comes from the review layer of the register where one exists. A page whose register verification is `gesichtet` or `abgenommen` and which carries a review run is written from the lines of its newest review run; every other page is written from the raw Transkribus export. The layout data always comes from the export, so zones and `lb` bindings are unaffected, since a correction changes a reading and leaves the position of the line on the image alone. Entity anchors are cut against the text the file actually carries, so a corrected line is matched on its reviewed reading.

The review layer outranks the Transkribus states in `transcription-summary`. A document with some reviewed pages reports `partly-reviewed`, a document whose every page is `abgenommen` reports `approved`, and a document without a review keeps the state derived from the DONE page count. The `editorialDecl` says the same in plain words for a reader of the file.

The register is read from `pipeline/pages/` and can be pointed elsewhere with `--register`, which is what the fixture test uses to build a reviewed document without any review data in the repository.

### Structure

The encoding is diplomatic and follows the page, the text region and the line. Each page opens with a `<pb>` whose `@facs` points at a `<surface>` in the `<facsimile>` section, and that surface carries the IIIF URL of the scan as a `<graphic>`. Images are referenced and never copied into the repository. Each text region of the export becomes one `<ab>` under that `<pb>`, carrying the region id of the layout analysis in `xml:id` as `ab-<docId>-<pageNr>-<regionId>`, so a block of the TEI and a block of the layout analysis stay addressable in both directions. Every transcribed line becomes an `<lb/>` followed by its text, so the line count of a TEI file equals the line count of the export, which the test suite checks. A line that consists only of a folio mark such as `[fol.3v]` is a reference point of the transcription rather than text of the source and becomes `<milestone unit="folio" n="3v"/>`.

Each line of the export also becomes a `<zone>` under the surface of its page, carrying the line polygon of the Transkribus layout analysis verbatim in `@points`, and the `<lb>` of that line points at the zone through `@facs`, so a text line and its image region are bound in both directions. Zones and `lb` are derived from the same iteration over the export, which is what keeps them in step; a line without coordinates gets no zone and its `lb` stays unbound rather than carrying a dangling reference. A folio milestone takes no `@facs`, because it marks a reference point of the transcription and not a read line.

An entity layer is read per document from `docs/data/entities/<docId>.json`, and the prototype extraction in `docs/data/demo/thaur_entities.json` serves the one document it names as long as no per-document file exists for it. Both sources carry the same schema and state the docId they belong to, so no document can pick a layer up by accident, and a document with neither file simply has no entity layer. The layer is encoded inline as `<persName>`, `<placeName>` and `<objectName>` with the normalised form in `@key`. A file with an entity layer declares a further responsibility, `resp-entity-llm`, which says in plain words that an LLM agent produced the extraction in the prototype phase and that no scholar has verified it; every marked entity points at that responsibility through `@resp`, and its `editorialDecl` repeats the state for a reader of the file. No certainty attribute is emitted anywhere, because the confidence value the extraction reports is a self-assessment of the extracting agent and not evidence about the source. An entity is encoded only where its position is deterministic, meaning it names the line it sits in and its surface form occurs in that line verbatim, case-sensitive, exactly once. An entity without a line reference, of a type the encoding does not cover, or whose form is absent or ambiguous in its line is left unencoded and reported per run with its reason, because placing it would assert a reading that was never established.

Structure beyond the page and the region is not asserted. The body holds a single `<div type="transcription">` with `<pb>` and `<ab>` blocks, because the export gives no paragraph or section boundaries that an unread transcription could justify. The `<ab>` element avoids claiming a `<p>` the source has not been read for; a region type curated later can be added as an attribute on the block that already exists.

The header carries only what the source register actually holds, which is the archival title and shelfmark, the repository, the collection and item number parsed from the shelfmark, the Transkribus doc id as an `altIdentifier`, and the archival dating as an `origDate` that keeps the raw string as its content and normalises it into `@when`, `@from`/`@to` or `@notBefore`/`@notAfter` according to its precision. An element whose data is missing is omitted instead of filled with a placeholder. The text is tagged `xml:lang="gmh"`; ISO 639-3 registers no code for Frühneuhochdeutsch, so the Middle High German code serves as the nearest registered approximation and `langUsage` says so.

The generation date comes from `--date` and never from the clock, so a rebuild without input changes produces byte-identical files and leaves no diff. Every document is re-parsed before it is written, so a malformed result fails the run rather than reaching the disk.

```
python build_tei.py                  # write docs/data/tei/
python build_tei.py --date 2026-09-01
python build_tei.py --register DIR   # read the register elsewhere
python test_build_tei.py             # or: pytest pipeline/test_build_tei.py
```

## Quality gates

Two gates stand between the generators and a commit, and both are run before every commit.

### The two schemas

`validate_tei.py` validates the generated TEI in two stages and reports them separately, because they answer different questions. Stage one is TEI conformance against the vendored `schema/tei_all.rng`, a pinned TEI P5 release. Stage two checks the DoCTA encoding specification against `schema/docta.rng`, a hand-written RelaxNG derived from `build_tei.py` that admits exactly the elements, attributes and structures the generator emits and nothing else. The responsibility ids, the stream statuses, the milestone units and the entity elements are enumerated there as closed lists, the identifiers of surface, zone and `ab` are pinned as patterns, and free text and legitimately varying values stay unconstrained. A certainty claim is impossible by construction, since `@cert`, `@certainty` and `<certainty>` are not in the grammar, so a file carrying one fails stage two even though it is valid TEI. `--schema PATH` runs a single stage against one schema. Provenance and upgrade path of both schemas are in `schema/SOURCES.md`.

```
python validate_tei.py                            # both stages
python validate_tei.py --schema schema/docta.rng  # one schema only
```

### The healthcheck

`check_pipeline.py` checks the cross-artifact specifications that no single pipeline script can verify on its own. It checks the register against the export and against its own vocabularies, the three document sets against each other, the entity files, review exports and evaluation runs against their data specifications, the provenance rules that keep a model's self-assessment out of the edition data, the resolution of every cross-reference, the value ranges of the evaluation summaries, both schema stages, and finally the generators against themselves by rebuilding register and TEI into a temporary directory and comparing byte for byte.

A finding is FAIL or INFO and carries the id of the check that raised it. INFO is a fact worth seeing that is not a defect, such as a page whose reference transcription is degenerate, a repeat pair whose line counts diverge far enough to want a third run, or a document that sits in one set and not in another for a reason already settled in the data. Only FAIL decides the exit code.

```
python check_pipeline.py             # every check, exit 0 only when clean
python check_pipeline.py --list      # the check ids
python test_check_pipeline.py        # or: pytest pipeline/test_check_pipeline.py
```

## Known gaps in the input data

The CSV-to-Transkribus matcher in `docs/data/source_mapping.json` covers the inventories only, so Raitbuch 2 is paired with its archival entry in the builder itself, matched on title and page count. Documents that are matched but have no export yet get a page list without IIIF URLs, because the page images are only known from the export.
