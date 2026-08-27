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

## Known gaps in the input data

The CSV-to-Transkribus matcher in `docs/data/source_mapping.json` covers the inventories only, so Raitbuch 2 is paired with its archival entry in the builder itself, matched on title and page count. Documents that are matched but have no export yet get a page list without IIIF URLs, because the page images are only known from the export.
