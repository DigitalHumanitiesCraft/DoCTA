---
title: HTR Evaluation
project:
  name: DoCTA
  repository: https://github.com/DigitalHumanitiesCraft/DoCTA
method:
  name: Promptotyping
  url: https://dhcraft.org/Promptotyping/
status: complete
language: en
version: "1.0"
created: 2026-08-27
updated: 2026-08-28
authors: [Christopher Pollin]
generated-with: Claude Code (Claude Fable 5)
related: [INDEX, data, specification, editorial-model]
---

# HTR Evaluation

## Scope

This document sets out how DoCTA produces machine transcriptions, compares them and releases them for scholarly use. HTR serves here as an umbrella term. A vision-language model processes a whole page image; Transkribus recognises text on the basis of a layout and line structure. Both produce candidate text, and neither produces an edition.

The measuring cohorts, benchmark, pilot and pilot2, repeat every page because they measure. The edition cohort under `evaluation/edition/` stands outside that measurement. It transcribes each page once for edition use, writes no summary and computes no metric, and its text enters register and TEI as unrevised machine output under the same release rule as every other model transcription.

The pipeline rests on one asymmetry, argued in domain-knowledge.md: a model cannot tell you how good its own output is. Everything below follows from that. Measurement replaces self-assessment, repetition replaces a single run, and a scholar decides at the facsimile what counts as read.

## Reference classes

The label "ground truth" is used sparingly and never loosely. Of the inventory transcriptions in the Transkribus collection, only a small subset carries the workflow status `DONE`; the rest are `IN_PROGRESS`. A workflow status is not a scholarly approval. Two transcription conventions are present in the stock, so metrics may be aggregated across documents only after a convention partition or through a documented adapter.

| Reference class | Meaning | Permitted use |
|-----------------|---------|---------------|
| Editorially accepted ground-truth transcription | Image, line assignment and transcription have been facsimile-verified, versioned and accepted for a named evaluation corpus | Model comparison and defensible CER/WER |
| Facsimile-verified reference transcription | A sample was checked against the image but has no accepted evaluation-corpus status | Development comparison, with the status stated |
| Provisional reference transcription | Text exists, while convention or editorial acceptance remains unresolved | Error hunting and selection of adjudication points |
| Unrevised machine transcription | An automatically produced proposal | Inspection, comparison and manual correction |

Where a metric is reported without an editorially accepted ground-truth transcription, it is a comparison signal and not a quality figure. The pilot's CER against a provisional reference transcription is the clearest case. A systematic deviation may originate in either compared text.

## The prompt benchmark

The benchmark under `evaluation/benchmark/` is the measuring instrument of the pipeline. Its purpose is to develop prompt iterations without ever losing an earlier iteration or its results, and to make the quality of each iteration comparable. Full protocol and re-entry instructions are in that folder's README; the published export lives in `data/benchmark/` and is rendered by `benchmark.html`.

The protocol in short:

1. **Pages** are fixed in `pages.json`, chosen from a visual survey of all 123 openings of account book 2 plus an inventory sample, so that each page represents a distinct phenomenon. Inventory pages with `DONE` status serve as CER anchors. The set changes only additively and only with documentation.
2. **Prompts** are versioned under `prompts/`. An iteration is frozen after its first run; any change is a new iteration carrying its own rationale. Iteration 02 separates a shared core from text-type modules for account books and inventories.
3. **Runs** are stored one file per page, condition and repetition, with full provenance: prompt version and hash, model, temperature, image parameters, timestamp. Nothing is overwritten or deleted.
4. **Repetitions** are at least three per condition, five on ground-truth pages.
5. **Metrics** are stratified by page and by zone (rubric, running text, amounts), never reported only as an aggregate.

Two findings from iteration 01 shaped this design and are worth stating as method rather than as measurement. Identical requests at temperature zero scatter by several CER points, so a ranking derived from single runs is noise. And Jaccard word overlap turned out to be misleading as a stability measure, because it is insensitive to order; positionwise token agreement, separated for word tokens and for number and currency tokens, replaced it.

### What the benchmark measures

| Object | Metric or procedure | Purpose |
|--------|---------------------|---------|
| Character sequence | Strict CER against reference transcriptions, with their reference class stated | Diplomatic proximity without hidden normalisation |
| Convention differences | CER under a documented normalisation profile | Comparison after explicitly stated equivalences |
| Word recognition and order | WER and bag-of-words WER | Separating recognition errors from reading-order errors |
| Layout | Line coverage, region assignment, reading order | Checking page structure |
| Self-consistency | Positionwise token agreement between repetitions, separately for words and for numbers | Locating unstable passages without a reference |
| Uncertainty marking | Yield and precision of the model's uncertain markers | Whether the model flags what it in fact got wrong |
| Line loss | Missing lines against reference, or between repetitions | Detecting silent omission |
| Amounts | Exact match of value, unit and booking line; arithmetic consistency as an exclusion filter | Research-relevant accounting accuracy |
| Correction effort | Number of scholarly interventions per editorially accepted page | Practical comparability of procedures |

Arithmetic consistency of the amounts is used as an exclusion filter and never as proof of correctness. The models smooth balances, so a sum that adds up may have been made to add up.

## Observed findings

Current values per page and iteration are in `data/benchmark/summary.json` and in the benchmark viewer; the statements here are qualitative and survive a rerun.

### Iteration 01, snapshot of 26.08.2026

The origin run, preserved under `experiments/transcription-test/`, processed four openings of account book 2 and one inventory page with six prompt variants of `gemini-3.7-flash`. On the inventory page with 39 reference lines it produced the following. The fair CER uses a project-specific normalisation that removes diacritics, unifies `u/v` and `i/j` and resolves abbreviation marks, so it describes a different error class from the strict CER.

| Variant | Strict CER | Fair CER | Word overlap |
|---------|-----------|----------|--------------|
| V1 baseline | 20.3 % | 10.7 % | 41.3 % |
| V2 structured | 20.6 % | 9.9 % | 41.5 % |
| **V3 few-shot** | **17.1 %** | **7.9 %** | 40.0 % |
| V4 page split | 24.3 % | 14.6 % | 34.8 % |
| V5 repetition | 19.6 % | 9.1 % | 39.4 % |
| V6 image enhancement | 19.0 % | 8.9 % | **43.6 %** |

Few-shot prompting gave the best character accuracy, image enhancement the best word overlap, and splitting the page into halves made things clearly worse. A single inventory page carries no decision for the account books, because hand, layout and text type differ. These numbers are kept as a historical record of the first test; they are not comparable with later iterations, which use a different page set and a different consistency measure.

### Account book pages without ground-truth transcriptions

Across the account-book pages the repetitions of one and the same prompt differ materially. The models usually recognise headings, the division of the opening and the entry structure. Personal names, years and monetary amounts change between runs, and the amounts are what accounting research depends on. Iteration 02 raised number-token consistency substantially on several pages while also producing far more uncertain markers, which is the intended trade: the model is asked to admit doubt rather than to guess fluently.

| Page | Observation | Evidential value |
|------|-------------|------------------|
| fol. 1v–2r | Names, dates and amounts vary strongly | Structure recognisable, individual values unchecked |
| fol. 2v–3r | Main names relatively stable, amounts and formulae change | Good basis for adjudication, not research data |
| fol. 39v–40r | Lowest agreement between repetitions | Difficult page, targeted image details required |
| fol. 89v–90r | All structured variants recognise the blank page | Blank-page and layout triage works |

Consistency between runs measures agreement between outputs. It does not measure historical correctness. Model consensus and arithmetic plausibility are reference-free hints for prioritising human checking, nothing more.

### Pilot under operating conditions

The benchmark measures on hand-picked phenomenon pages. The pilot under `evaluation/pilot/` answers the follow-up question of how the same prompts behave on continuous, uncurated material. It runs two cohorts: a complete inventory document from a castle that does not appear in the benchmark, scored per page as fair CER against the Transkribus working transcription, and a run of consecutive openings from the beginning of account book 2 including blank and transitional pages, scored by self-consistency between repetitions. Pages with low number consistency are the candidates for inspection. Results are in `evaluation/pilot/pilot_summary.json`.

The inventory cohort is the more informative of the two, because it shows what happens when the prompt meets a hand it has not been tuned on. Its CER values sit visibly above those of the benchmark's reference pages, and part of that gap is attributable to the reference rather than to the model.

## Suitability by research purpose

| Purpose | Current status | Consequence |
|---------|----------------|-------------|
| Blank-page and layout triage | Working | The model can pre-sort pages and produce structured output |
| Category overview of a volume | Plausible, piloted | Model output can generate search and inspection hypotheses; samples remain necessary |
| Person and function candidates | Not yet scholarly checked | Entity extraction may run only on text carrying a source link and a review status |
| Diplomatic edition | Not sufficiently evidenced | Release requires line-by-line checking against the facsimile |
| Amounts and accounting relations | Unstable in testing | Exact value, unit and line assignment need separate validation |

## Generation procedure

1. A manifest fixes document ID, folio, image URL, checksum, model version, prompt version and image transformation.
2. The existing Transkribus baselines and regions are taken as a layout reference. For whole openings a page-level model run is kept in addition.
3. Every page of the held-out test set is processed both with a specialised HTR base model and with the current model configuration. The Text Titan I ter model is the obvious first Transkribus baseline candidate; its published vendor figures do not replace a direct comparison on DoCTA material.
4. Regional crops are used deliberately for difficult names, marginal columns and amounts, rather than as a general strategy.
5. Divergences between systems produce a divergence list with image detail, line reference and competing readings. The scholar decides directly at the facsimile.
6. Unrevised machine output, formally checked text and accepted edition text remain separate data states. Every downstream step carries the evidence and decision status together with its provenance.

A stronger vision-language model is compared on the same held-out page set. Model family and general vendor description are not sufficient grounds for a choice. Training a project-specific HTR model is considered only once enough corrected account-book lines exist and a separate test set can be preserved.

### Evaluator implementation

The evaluation component reads Transkribus PAGE XML and the derived DoCTA data contract directly. The reader carries over page ID, region and line order, transcription, convention label and reference status. The normalisation profile `docta-diplomatic-v1` is implemented as a versioned configuration. Every run produces machine-readable per-page metrics and a divergence list with the corresponding image regions.

**Open question.** Whether the normalisation profile is now specified or still pending is not settled in this document; the runner in `evaluation/benchmark/run_benchmark.py` holds the profile actually in use, and the two should be reconciled.

## Evaluation contract

### Test design

- Development material and a held-out test set are kept separate.
- The sample covers scribes, page types, states of preservation, text density, tabular or columnar layout and blank pages.
- Inventories and account books are evaluated separately.
- The two inventory conventions receive their own labels. An adapter maps both onto a versioned data contract.
- Every figure names reference class, normalisation profile, model version and sample size.

### Release rule

A configuration is released for exactly the research purpose for which it passes the held-out test. Category overview, diplomatic edition and the reading of amounts receive separate decisions. A production decision follows the comparison with a specialised HTR model and the scholarly checking of a representative account-book sample.

## Scholarly review points

- The project lead sets the diplomatic target convention and the permissible normalisations.
- A representative account-book sample receives line-by-line reference transcriptions.
- Amounts are adjudicated together with unit, line and any relation to a total.
- SiCProD name variants are used only in post-processing. Every fuzzy match is preserved as a proposal alongside the original reading.

Two items are outstanding at the time of writing and are named as open: the adjudication of a regression on the Thaur inventory pages, and two reference pages whose measured CER exceeds one hundred percent, which points at a reference or alignment problem rather than at recognition quality.

## Evidence and sources

### Local evidence

- `evaluation/benchmark/summary.json` and `evaluation/benchmark/runs/`
- `evaluation/benchmark/prompts/` (versioned prompt iterations)
- `evaluation/pilot/pilot_summary.json`
- `experiments/transcription-test/results/` (frozen origin run)
- `data/benchmark/` (published export, rendered by `benchmark.html`)

### Methodological and technical sources

- Google, [Gemini 3.7 Flash](https://ai.google.dev/gemini-api/docs/models/gemini-3.7-flash). Model description and support for structured output.
- READ-COOP, [The Text Titan I ter](https://www.transkribus.org/models/the-text-titan-i-ter). Official model description; performance figures are vendor figures.
- Ströbel et al. 2022, [Evaluation of HTR models without Ground Truth Material](https://aclanthology.org/2022.lrec-1.467/). Reference-free metrics support model selection in an application context.
- Vidal et al. 2023, [End-to-End Page-Level Assessment of Handwritten Text Recognition](https://arxiv.org/abs/2301.05935). Page-level evaluation should measure recognition quality and reading order separately.
