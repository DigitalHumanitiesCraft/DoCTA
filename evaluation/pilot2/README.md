# Pilot 2: it02 on a wider slice of unseen material

The first pilot (`../pilot/`) established that the frozen it02 prompt configuration works on one complete inventory and on the opening spreads of Raitbuch 2. Pilot 2 keeps that configuration fixed and widens the material, so the question it answers is whether the observed behaviour holds across different hands, different castles and a later section of the account book.

Model, prompts, temperature, image scaling and the folio-split handling of spreads come from `../benchmark/run_benchmark.py`, which this runner imports unchanged. Only the page list and the evaluation differ.

## Scope

Two cohorts, two repeats per page, iteration it02 throughout.

1. **Three complete inventory documents**, each unseen by `../benchmark/runs/` and `../pilot/runs/` and each carrying a Transkribus text export.

   | docId | Shelfmark | Castle | Dating |
   |---|---|---|---|
   | 11348481 | A 273.5 | Pergine | 1446 |
   | 11330759 | A 225.1 | Sigmundskron | 1487 |
   | 11330219 | A 185.1 | Schöneck | 1492 |

   Every matched source entry with a text export falls into the category Burgeninventar, so a second category was not available for this selection.

   Scoring per page is CER fair against the Transkribus working transcription plus self-consistency between the two repeats. The working transcription is a comparison signal and no ground truth; a deviation may sit on either side. Pages whose export holds only a foliation line produce a degenerate reference, and their CER carries no information.

2. **Raitbuch 2 spreads 22 to 41**, the twenty following the first pilot's 2 to 21. No export exists for this book, so scoring is self-consistency alone, split into word tokens and number or currency tokens. Each spread is sent as two requests, verso and recto, which is the it02 default.

`pilot2_summary.json` is the source of truth for page counts, run counts and all metrics.

## Metric state

Since 2026-08-28 the summary carries the corrected metric of the benchmark runner, meaning the symmetric agreement, the numeral classification before the v/u collapse, and a missing value instead of a zero where a token class is absent from both repeats. `pilot2_summary_oldmetric.json` preserves the figures as they were originally published; the runs themselves are untouched and were never requested again.

## Rerunning

1. `python run_pilot2.py` fills in missing runs (skip-if-exists via the benchmark runner) and writes the summary
2. `python run_pilot2.py --eval` recomputes the evaluation from the runs on disk
3. Runs live in `runs/`, failed or blocked calls in `errors.json`
4. Page images are cached in the shared, gitignored `../benchmark/images/` and never enter the repository
5. The API key is read from `GEMINI_API_KEY` in the repository root `.env`

The scope constants sit at the top of `run_pilot2.py` and are deterministic, so a rerun reproduces the same page set.

## Register ingest

Run page identifiers follow the pattern `pilot2_inv_<docId>_p<n>` and `pilot2_rb2_p<nnn>`. `pipeline/build_register.py` reads this cohort alongside the benchmark and the first pilot and resolves the identifiers to document and page numbers.

License as for the repository: code MIT, documents and data CC BY 4.0.
