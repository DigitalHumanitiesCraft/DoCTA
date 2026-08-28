# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

DoCTA turns facsimiles of fifteenth-century Tyrolean court records (Transkribus collection 2197991, Tyrolean State Archives) into research data and a digital edition. VLM transcription, a versioned prompt benchmark, scholarly review, TEI encoding and a static site form one pipeline. The knowledge base in `docs/knowledge/` is the source of truth for how the project understands its sources, methods and decisions; the code is the disposable artifact. Read `docs/knowledge/INDEX.md` first, it names the reading order for the other knowledge documents.

Built with Promptotyping. Before conceptual or design work, consult the knowledge documents; after decisions with reasons, record them in `docs/knowledge/journal.md`.

## Commands

Python is managed with uv (Python 3.11+, `pyproject.toml`, `uv.lock`). When `uv` is not on PATH, the project venv works directly: `.venv\Scripts\python.exe -m pytest` etc.

```
uv sync                                   # install runtime + dev dependencies
uv run pytest                             # all tests (pipeline/, evaluation/checks/)
uv run pytest -m slow                     # the clean-rebuild healthcheck, also run by the commit hook
uv run pytest pipeline/test_build_tei.py  # one test file
uv run pytest pipeline/test_build_tei.py::test_name   # one test
uv run ruff check --fix . && uv run ruff format .     # lint + format
uv run pre-commit run --all-files         # everything the commit hook runs
```

Pipeline scripts anchor their paths at their own file location and run from anywhere:

```
uv run python pipeline/build_register.py            # rebuild documents.json + pages/
uv run python pipeline/build_register.py --project  # + site projection register_summary.json
uv run python pipeline/build_tei.py --date YYYY-MM-DD   # TEI to docs/data/tei/ (date from flag, never the clock)
uv run python pipeline/validate_tei.py              # both schema stages
uv run python pipeline/apply_review.py [file|DIR] [--dry-run]   # ingest viewer review exports
uv run python pipeline/check_pipeline.py            # cross-artifact healthcheck, exit 0 only when clean
uv run python pipeline/check_pipeline.py --list     # check ids
```

Benchmark runner (needs `GEMINI_API_KEY` in the gitignored repo-root `.env`, provided by the operator per session):

```
python evaluation/benchmark/run_benchmark.py         # fill missing runs (skip-if-exists), write summary.json
python evaluation/benchmark/run_benchmark.py --eval  # recompute evaluation only
```

Site tests are Playwright scripts, installed separately (`npm install playwright && npx playwright install chromium`, deliberately gitignored). They serve the repo under the subpath `/DoCTA/` like GitHub Pages, derive their page list from the `*.html` files in `docs/`, and exit nonzero on any finding, so they work as a gate:

```
node tests/smoketest.mjs
node tests/interaction-test.mjs
```

Local preview of site and viewers: `python -m http.server 8742` from the repo root, then e.g. `http://127.0.0.1:8742/evaluation/benchmark/viewer.html`.

## Architecture

Data flows in one direction. Transkribus exports and evaluation runs are inputs already in the repository; `pipeline/build_register.py` derives the page register from them; `pipeline/build_tei.py` derives TEI from register plus exports; the site under `docs/` reads pre-processed JSON from `docs/data/`. Generated outputs (`pipeline/documents.json`, `pipeline/pages/`, `docs/data/tei/`, `docs/data/pipeline/register_summary.json`) are never edited by hand.

- **Page register** (`pipeline/`, see `pipeline/README.md`): one entry per document and per page, holding `content_class`, `empty_evidence`, `verification` status and transcription `runs`. Runs are immutable; a better transcription is a new run, never an edit. Run ids encode origin (`transkribus`, `benchmark:<stem>`, `pilot:<stem>`, `pilot2:<stem>`, `edition:<stem>`, `review:<...>`). German vocabulary values (`leer`, `kassiert`, `gesichtet`, `abgenommen`, ...) are part of the data specification, defined in the README. A rebuild carries the ingested review state over from the existing register, so it destroys no review.
- **Review loop**: the browser viewer exports page decisions and line corrections per document; `apply_review.py` validates every file of an invocation before it writes any of them, so a stale base text or an unknown line anywhere in the batch leaves the register untouched and exits nonzero. Re-sending the newest export of a page is idempotent; an older export fails on the reported original.
- **TEI generation** (`build_tei.py`): diplomatic encoding, one file per document, page/region/line structure only, `<ab>` not `<p>` because no source has been read for more. Work-step provenance as `respStmt`/`revisionDesc`; the generator pins its own source with a sha256 digest in every file. A document the Inventaria project transcribed declares `resp-inventaria-transcription` beside the Transkribus layer and links its published edition as a `<bibl>` in `sourceDesc`; the wording follows the DONE page count and keeps the Transkribus workflow status apart from DoCTA's own facsimile review. Entities are encoded only where their position is deterministic in a named line; no certainty attributes anywhere, a model's confidence self-assessment never enters edition data.
- **Entity register** (`docs/data/tei/register.xml`, also from `build_tei.py`): the corpus-wide entity index as a `<standOff>` TEI file, `<listPerson>`, `<listPlace>` and a `<list type="objects">`, each entry holding the normalised form and the spellings attested for it. A marked entity in a document TEI carries no normalised form of its own and points at its entry with `ref="register.xml#<id>"`; objects are `<term>` because they are common nouns. The ids come from `pipeline/entity_index.py` and are shared with `docs/data/graph.jsonld`, so TEI and graph address the same entities.
- **Two-stage validation** (`validate_tei.py`): stage one TEI conformance against vendored `pipeline/schema/tei_all.rng`, stage two the project's own encoding specification `pipeline/schema/docta.rng`, a closed grammar over both file shapes of the directory in which `@cert`/`<certainty>` and `@key` on an entity are impossible by construction. Provenance of both in `pipeline/schema/SOURCES.md`.
- **Healthcheck** (`check_pipeline.py`): cross-artifact checks including byte-identical rebuild of register and TEI into a temp dir, with the TEI date taken from the files on disk and the TEI comparison run over the glob so `register.xml` is covered, plus orphan detection for artifacts in the working tree that the rebuild no longer produces and a reference check binding document `@ref`, `register.xml` and `graph.jsonld` to one id space. Determinism is a tested property; builders make no network calls and never read the clock.
- **Accounts module** (`pipeline/accounts/`): the executable part of the account-book (Raitbuch) encoding specification, with its own fixtures, schemas and tests. It holds the PAGE import, the pydantic models with the separate status axes of the editorial model, the staleness and review-decision functions, and the TEI/RDF validators against RELAX NG, Schematron and SHACL. Annotation Sets, the Edition Build Manifest and the generation steps of the deterministic build stay prose specification until a consumer exists. The side of an opening is derived from the page geometry and is deliberately absent from the qualified line id and from the text digest. See `docs/knowledge/accounting-encoding.md` and `editorial-model.md`.
- **Benchmark** (`evaluation/benchmark/`): fixed page set, frozen prompt iterations (a change is a new iteration), append-only runs with full provenance, k >= 3 repeats because single runs are noise. Never overwrite or delete a run or an iteration.
- **Edition track** (`evaluation/edition/`): the pipeline's own VLM transcriptions for edition use, one run per page, append-only, without summary or metrics because nothing is repeated or measured. The page set lives in `docs/data/edition_pages.json`. The register assigns synthetic line ids `v1..vn` to edition runs alone; the TEI of a document without a Transkribus export names `resp-vlm-transcription` and carries no zones, since no layout analysis produced polygons. The viewer reads such a document from `docs/data/pipeline/transcriptions/<docId>.json`, written by `build_register.py --project`; `docs/data/transcriptions/` remains the Transkribus export alone, and the text stays `machine-unrevised` until review.
- **Site** (`docs/`, served by GitHub Pages on `main`): static, vanilla JS with ES6 modules, no build step, no runtime package manager; dependencies vendored in `docs/lib/` at deliberately frozen versions. Details in `docs/knowledge/architecture.md`.

## Constraints worth knowing

- Everything committed under `docs/` is published immediately on push to `main`.
- All VLM output is unrevised machine transcription until a scholar approves it, and is marked as such wherever displayed. Keep that framing in any UI or data change.
- `sources/` (project-internal, absent from the public clone) holds unpublished proposal text and correspondence; never recreate or commit it.
- Figures shown by the site are computed in the browser from `docs/data/sources.json` and `docs/data/pipeline/register_summary.json`; do not hard-code counts. `docs/data/stats.json` is a prototype-era artifact that no page loads.
- Language split: code, code comments, this file, the knowledge documents in `docs/knowledge/`, the top-level README and `pipeline/README.md` are English. German prose with English technical terms remains in `tests/README.md` and in the benchmark and pilot READMEs under `evaluation/`, while `evaluation/pilot2/` and `evaluation/checks/` are English. A new README under `evaluation/` is written in English; an existing one keeps its language. Follow the language of the document being edited.
- License: code MIT, documents and research data CC BY 4.0; published Inventaria transcriptions are cited with attribution wherever displayed or evaluated.
