# Page register

The register is the data backbone of the agentic edition pipeline. It holds one entry per source document that carries a Transkribus doc_id and one entry per page of that document, and it records for every page what the page contains, how far it has been verified, and which transcription runs exist for it. It is derived data, rebuilt from repo-local files by `build_register.py`, and no step of the pipeline writes into it by hand.

## Layout

`documents.json` is a list of document entries: `docId`, `shelfmark` (archival signature), `title`, `dating` (`raw`, `start`, `end`), `category`, `pages`, `tier`, `has_text`, `provenance` (currently always `transkribus`) and `attribution`, which stays `null` until the published edition list allows an attribution such as `inventaria`.

`pages/<docId>.json` holds `docId` and a `pages` list. Each page entry carries `pageNr`, the `iiif` image URL where one is known, `content_class`, `empty_evidence`, `verification` and `runs`.

`empty_evidence` is `null` or an object with `method`, `runs` (how many runs support the evidence) and `scope`. Scope `full` means every reporting run saw the whole page image empty; `partial` means at least one part of a spread was reported empty, which is the usual case for a Raitbuch page, where a blank verso faces a written recto.

`verification` is an object with a `status` field, kept as an object so an adjudication step can add who verified and when without changing the schema.

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

A run is one transcription of one page from one source, and runs are immutable. A run is never edited or removed; a better transcription is a new run. Each run carries `id`, `source`, `model`, `prompt`, `prompt_hash`, `repeat`, `date`, `empty`, `empty_parts` and `lines`.

The run id encodes the origin and makes rebuilds stable. The Transkribus export is the single run `transkribus` on a page; a model run is `benchmark:<run file stem>` or `pilot:<run file stem>`, so its record in `evaluation/` remains the source of truth for everything the register does not repeat (image handling, duration, full structured output). `empty` is true only when the model reported every part of the page image empty; `empty_parts` lists the flag per image part in the order the run reported them, which for a Raitbuch spread means verso and recto.

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

Every file carries its work-step provenance in the header, following the pattern of the ZBZ project. The `titleStmt` declares one `respStmt` per step that actually happened, `resp-transkribus-layer` for the transcription layer, worded according to whether the pages were corrected and marked done in Transkribus or carry the unrevised recognition layer, and `resp-tei-generation` for the deterministic generation, which names `build_tei.py` together with a sha256 digest over its own source, so the generating code version is pinned in the data and a script change is visible as a change in every file. A responsibility for scholarly verification is not emitted anywhere, because no such step runs in the DoCTA workflow yet. In `revisionDesc` the generation entry points at its responsibility through `@who`, and one summary entry per stream carries the current state in `@status`, `transcription-summary` with `human-corrected`, `partly-corrected` or `machine-unrevised` derived from the DONE page count, and `tei-summary` with `machine-generated`.

The encoding is diplomatic and follows the page and the line. Each page contributes one `<ab>` opened by a `<pb>` whose `@facs` points at a `<surface>` in the `<facsimile>` section, and that surface carries the IIIF URL of the scan as a `<graphic>`. Images are referenced and never copied into the repository. Every transcribed line becomes an `<lb/>` followed by its text, so the line count of a TEI file equals the line count of the export, which the test suite checks. A line that consists only of a folio mark such as `[fol.3v]` is a reference point of the transcription rather than text of the source and becomes `<milestone unit="folio" n="3v"/>`.

Each line of the export also becomes a `<zone>` under the surface of its page, carrying the line polygon of the Transkribus layout analysis verbatim in `@points`, and the `<lb>` of that line points at the zone through `@facs`, so a text line and its image region are bound in both directions. Zones and `lb` are derived from the same iteration over the export, which is what keeps them in step; a line without coordinates gets no zone and its `lb` stays unbound rather than carrying a dangling reference. A folio milestone takes no `@facs`, because it marks a reference point of the transcription and not a read line.

One document carries a prototype entity layer from `docs/data/demo/`, encoded inline as `<persName>`, `<placeName>` and `<objectName>` with the normalised form in `@key`. It exists only in the file whose doc id the extraction names, and that file declares a third responsibility, `resp-entity-llm`, which says in plain words that an LLM agent produced the extraction in the prototype phase and that no scholar has verified it; every marked entity points at that responsibility through `@resp`, and its `editorialDecl` repeats the state for a reader of the file. No certainty attribute is emitted anywhere, because the confidence value the extraction reports is a self-assessment of the extracting agent and not evidence about the source. An entity is encoded only where its position is deterministic, meaning it names the line it sits in and its surface form occurs in that line verbatim, case-sensitive, exactly once. An entity without a line reference, of a type the encoding does not cover, or whose form is absent or ambiguous in its line is left unencoded and reported per run with its reason, because placing it would assert a reading that was never established.

Structure beyond the page is not asserted. The body holds a single `<div type="transcription">` with `<ab>` blocks, because the export gives no paragraph or section boundaries that an unread transcription could justify. Transkribus text regions are flattened into the reading order of the export; encoding one `<ab>` per region is the upgrade path once region types are curated.

The header carries only what the source register actually holds, which is the archival title and shelfmark, the repository, the collection and item number parsed from the shelfmark, the Transkribus doc id as an `altIdentifier`, and the archival dating as an `origDate` that keeps the raw string as its content and normalises it into `@when`, `@from`/`@to` or `@notBefore`/`@notAfter` according to its precision. An element whose data is missing is omitted instead of filled with a placeholder. The text is tagged `xml:lang="gmh"`; ISO 639-3 registers no code for Frühneuhochdeutsch, so the Middle High German code serves as the nearest registered approximation and `langUsage` says so.

The generation date comes from `--date` and never from the clock, so a rebuild without input changes produces byte-identical files and leaves no diff. Every document is re-parsed before it is written, so a malformed result fails the run rather than reaching the disk.

```
python build_tei.py                  # write docs/data/tei/
python build_tei.py --date 2026-09-01
python test_build_tei.py             # or: pytest pipeline/test_build_tei.py
```

## Known gaps in the input data

The CSV-to-Transkribus matcher in `docs/data/source_mapping.json` covers the inventories only, so Raitbuch 2 is paired with its archival entry in the builder itself, matched on title and page count. Documents that are matched but have no export yet get a page list without IIIF URLs, because the page images are only known from the export.
