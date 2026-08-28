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
version: "1.1"
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

The pipeline rests on one asymmetry, argued in domain-knowledge.md. A model cannot tell you how good its own output is. Everything below follows from that. Measurement replaces self-assessment and repetition replaces the single run. What counts as read is decided by a scholar at the facsimile.

The document separates two things that earlier versions ran together. What the pipeline measures today stands under "Operating state" and is dated at the point of measurement. What the project has specified and not yet built stands under "Requirements register" and makes no claim about the current code.

## Reference classes

The label "ground truth" is used sparingly and never loosely. Of the inventory transcriptions in the Transkribus collection, only a small subset carries the workflow status `DONE`; the rest are `IN_PROGRESS`. A workflow status records a completed step in a production workflow. Editorial acceptance for an evaluation corpus is a separate decision that no page of this collection has passed. Two transcription conventions are present in the stock, so metrics may be aggregated across documents only after a convention partition or through a documented adapter.

| Reference class | Meaning | Permitted use |
|-----------------|---------|---------------|
| Editorially accepted ground-truth transcription | Image, line assignment and transcription have been facsimile-verified, versioned and accepted for a named evaluation corpus | Model comparison and defensible CER/WER |
| Facsimile-verified reference transcription | A sample was checked against the image but has no accepted evaluation-corpus status | Development comparison, with the status stated |
| Provisional reference transcription | Text exists, while convention or editorial acceptance remains unresolved | Error hunting and selection of adjudication points |
| Unrevised machine transcription | An automatically produced proposal | Inspection, comparison and manual correction |

DoCTA holds no reference of the first class. The benchmark's nine reference pages are Transkribus transcripts with workflow status `DONE` from the collection of the Inventaria project, the pilot cohorts are scored against `IN_PROGRESS` working transcriptions, and both belong to the provisional class. Every CER reported anywhere in this project is therefore a comparison signal. A systematic deviation may originate in either compared text. `summary.json` states the class per page in `reference_class`, so a consumer reads it from the data.

## The prompt benchmark

The benchmark under `evaluation/benchmark/` is the measuring instrument of the pipeline. Its purpose is to develop prompt iterations without ever losing an earlier iteration or its results, and to make the quality of each iteration comparable. Full protocol and re-entry instructions are in that folder's README; the published export lives in `data/benchmark/` and is rendered by `benchmark.html`.

The protocol in short:

1. **Pages** are fixed in `pages.json`, chosen from a visual survey of all 123 openings of account book 2 plus an inventory sample, so that each page represents a distinct phenomenon. Inventory pages with `DONE` status serve as CER anchors. The set changes only additively and only with documentation.
2. **Prompts** are versioned under `prompts/`. An iteration is frozen after its first run; any change is a new iteration carrying its own rationale. Iteration 02 separates a shared core from text-type modules for account books and inventories.
3. **Runs** are stored one file per page, condition and repetition, with full provenance, meaning prompt version and hash, model, temperature, image parameters and timestamp. Nothing is overwritten or deleted.
4. **Repetitions** are at least three per condition, five on the reference pages.
5. **Metrics** are reported per page and never only as an aggregate. Where an aggregate is given, it is given twice, weighted by reference length and weighted per page.

Two findings from iteration 01 shaped this design and are worth stating as method rather than as measurement. Identical requests at temperature zero scatter by several CER points, so a ranking derived from single runs is noise. And Jaccard word overlap turned out to be misleading as a stability measure, because it is insensitive to order; positionwise token agreement, separated for word tokens and for number and currency tokens, replaced it.

### What the benchmark measures

The status column separates what the code computes today from what this document specifies. A row marked as specified describes an intention and is repeated with its rationale in the requirements register below.

| Object | Metric or procedure | Status | Purpose |
|--------|---------------------|--------|---------|
| Character sequence | Strict CER against the reference, with the reference class carried per page | measured, `summary.json` | Diplomatic proximity without hidden normalisation |
| Convention differences | CER under the versioned normalisation profile `docta-fair-v2` | measured, `summary.json` | Comparison after explicitly stated equivalences |
| Aggregation | Edit distance summed over runs and pages against summed reference length, beside the mean of the page means | measured, `analysis.json` and `benchmark.html` | Keeping the length distribution of the page set out of the headline figure |
| Self-consistency | Symmetric positionwise token agreement between repetitions, separately for words and for numbers | measured, `summary.json` | Locating unstable passages without a reference |
| Uncertainty marking, yield | Count of the model's uncertain markers per run | measured, `summary.json` | How readily the model admits doubt |
| Uncertainty marking, precision and recall | Markers against a token alignment to the reference | measured, `analysis.json` | Whether the model flags what it in fact got wrong |
| Blank page | `empty` flag per run and per image part of a spread | measured, `summary.json` | Blank-page triage as a data property |
| Segmentation stability | Line count per run | measured, `summary.json` | Detecting a page the model divides differently from run to run |
| Amounts, arithmetic consistency | Items of a block against its Summa line, per denomination, no assumed conversion | measured for the pilot cohorts, `evaluation/checks/` | Reference-free exclusion filter for account pages |
| Word recognition and order | WER and bag-of-words WER | specified, not implemented | Separating recognition errors from reading-order errors |
| Layout | Line coverage, region assignment, reading order | specified, not implemented | Checking page structure |
| Zone stratification | The above metrics split by rubric, running text and amounts | specified, not implemented | Reporting where on the page the errors sit |
| Line loss | Missing lines against reference, or between repetitions | specified, not implemented | Detecting silent omission |
| Amounts, exact match | Value, unit and booking line against a reference | specified, not implemented | Research-relevant accounting accuracy |
| Correction effort | Number of scholarly interventions per editorially accepted page | specified, not implemented | Practical comparability of procedures |

Arithmetic consistency of the amounts is used as an exclusion filter and never as proof of correctness. The models smooth balances, so a sum that adds up may have been made to add up.

### The measuring instrument and its version

`summary.json` carries a version id for the fair and the strict profile, the temperature, the reference class per page, and per reference page the fair-normalised reference length together with the derived `reference_degenerate` flag. Every run contributes its edit distance and the reference length it was measured against, so a rate can be recomputed without rerunning the normalisation. The versioning rule is that any change to `normalize()`, to the token classification or to the agreement formula raises the version of every profile it touches, because summaries of different versions are not comparable. Current state is `docta-fair-v2` and `docta-strict-v2`, dated 28.08.2026.

Two reference pages are cover labels whose Transkribus export carries three and four lines while the image holds a full page. Their fair-normalised references are 30 and 38 characters against 1006 for the shortest informative reference of the set, so `reference_degenerate` marks them from the reference length rather than from the rate they produced. Every consumer, the site included, excludes them by that field.

## Operating state

Current values per page and iteration are in `data/benchmark/summary.json`, the derived statistics in `evaluation/benchmark/analysis.json` and `analysis.md`. Reproduce the second with

```
python evaluation/benchmark/analyze_summary.py
```

The statements in the observation table are qualitative and survive a rerun. The dated sections carry figures, and they carry the date of the measurement that produced them.

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

### Account-book pages without a reference transcription

The cohort is the eight account-book openings of the benchmark page set, three repetitions per iteration, without a reference of any class. Across them the repetitions of one and the same prompt differ materially. The models usually recognise headings, the division of the opening and the entry structure. Personal names, years and monetary amounts change between runs, and the amounts are what accounting research depends on. Iteration 02 raised number-token agreement on every one of these pages while also producing several times as many uncertain markers, which is the intended trade. The model is asked to admit doubt rather than to guess fluently.

| Page | Observation | Evidential value |
|------|-------------|------------------|
| fol. 2v–3r | Number agreement is among the lowest of the cohort under it01 and more than doubles under it02; names and formulae keep changing | Structure recognisable, individual values unchecked |
| fol. 27v–28r | Cancellation strokes and number columns; both agreement measures rise under it02, the line count rises with them | Good basis for adjudication, not research data |
| fol. 39v–40r | Mixed show-through and a faded rubric; agreement stays mid-field under both iterations | Structure readable, rubric and currency unchecked |
| fol. 98v–99r | Lowest number agreement of the whole set under iteration 01, raised markedly by iteration 02; the verso half is reported as empty in every run of both iterations | Amounts of the extreme show-through page are unusable without checking |
| fol. 112v–113r | Lowest word agreement of the account-book pages under both iterations, and the highest marker count of the set under it02 | Inserted leaf, overlapping written surfaces and two hands; targeted image details required |
| fol. 89v–90r | Blank-page control. Every run of both iterations flags the verso half as empty and returns one line for the opening. The run-level `empty` flag stays false because the recto half carries that line, and word agreement reports no value where the number agreement reports 1.0 on a single token | Blank-page triage works at the level of the image part; the run-level flag needs the part-level one beside it |

Agreement between runs measures agreement between outputs. It does not measure historical correctness. Model consensus and arithmetic plausibility are reference-free hints for prioritising human checking.

### Iteration 01 against iteration 02, measured 28.08.2026

Seven of the nine reference pages carry a usable reference. Compared page by page, iteration 02 reaches a lower strict CER on all seven, which an exact sign test puts at p = 0.008 one-sided and p = 0.016 two-sided. Aggregated, strict CER falls from 37.3 % to 34.1 % length-weighted and from 37.3 % to 34.3 % as the mean of the page means. Under the fair profile the effect disappears. Iteration 02 is lower on four of seven pages, the length-weighted aggregate moves from 23.7 % to 23.5 % and the page mean moves the other way, from 23.4 % to 23.7 %.

That split has an explanation the material supports. Iteration 02 was developed on the same seven pages the benchmark measures. Its inventory module carries a glossary of stock spellings whose lemmata occur verbatim in the reference texts of the measured pages, `kůss`, `leilach`, `polster`, `golter`, `harnasch`, `tisch` and `pankh` among them, and its transcription conventions were aligned to those references during the analysis day of 26.08.2026. A glossary fixes the exact character sequence of a word, which is what the strict profile scores and what the fair profile already forgave. The expected effect of the development is a gain in the strict profile with a flat fair profile, and that is the measured pattern.

No out-of-sample comparison of the two iterations exists. Pilot 2 shows iteration 02 on castle inventories that were never in its development material, without running iteration 01 beside it, so it supports the configuration without separating it from its predecessor. The remedy is a run of iteration 01 over the pilot and pilot 2 page sets, which produces the missing out-of-sample pair without touching a frozen prompt. It is open.

### Pilot and pilot 2 under operating conditions

The benchmark measures on hand-picked phenomenon pages. The pilot under `evaluation/pilot/` answers the follow-up question of how the same prompts behave on continuous, uncurated material. It runs two cohorts, a complete inventory document from a castle that does not appear in the benchmark, scored per page as fair CER against the Transkribus working transcription, and a run of consecutive openings from the beginning of account book 2 including blank and transitional pages, scored by agreement between repetitions. Results are in `evaluation/pilot/pilot_summary.json`.

The inventory cohort is the more informative of the two, because it shows what happens when the prompt meets a hand it has not been tuned on. Earlier versions of this document reported its CER as sitting above the benchmark's reference pages. That is wrong. Over its seven text pages, the eighth being a one-line cover label of the same degenerate kind the benchmark flags, the mean of the page means is 19.8 % fair CER against 23.4 % and 23.7 % on the benchmark reference pages under it01 and it02. The uncurated document from an untuned hand is read about four CER points better than the curated anchor set.

Two things follow. The benchmark's error level is not an artefact of a page set assembled for difficulty in the model's favour, since the untouched document does not read worse. And the benchmark's own reference pages are the harder material of the two, which is what a phenomenon-driven selection is for. The comparison stays across reference classes, `DONE` in the benchmark against `IN_PROGRESS` in the pilot, so the two rates share a method while their scales differ.

Pilot 2 under `evaluation/pilot2/` extends the same configuration to three further castle inventories with two repetitions per page. On its text pages the fair CER runs from 3.5 % on the best Pergine pages through 17 % on Schöneck to 39 % on the weakest Sigmundskron page. The spread between documents is an order of magnitude larger than the iteration effect of about three CER points measured above, which is the practical reason a figure without its document is uninformative. Pilot 2 also carries the cohort's blank pages, where a run that returns nothing and a reference of one line produce a rate of either 0 or 1 depending on which side is empty; those pages are read from the `empty` flag rather than from the rate.

### Metric correction of 28.08.2026

The self-consistency measure classified every Roman numeral carrying a `v` or a `j` as a word token. The fair normalisation collapses `v` to `u` and `j` to `i` before the numeral pattern is applied, and that pattern knew neither letter, so common forms such as `vij` and `xxv` left the number metric and landed in the word metric. Numberishness is now decided on the token before the collapse, and the benchmark summary has been recomputed from the run files on disk.

The direction of the change is uniform. Number agreement falls on most pages and word agreement rises slightly, because the numerals that moved are the least stable tokens of a page. A page whose repeats carry no numeral token at all now reports no value where it previously reported zero, which removes a class of false review candidates.

The second step of the same revision made the agreement symmetric, stripped every folio-marker spelling from reference and hypothesis alike, introduced the profile versions, and added edit distance, reference length and the `empty` flags per run. Prompts, runs and iterations are untouched throughout, so the correction changes the measurement while the material stands.

The pilot and pilot 2 summaries were recomputed on the corrected metric; the originally published figures stand beside them as `pilot_summary_oldmetric.json` and `pilot2_summary_oldmetric.json`.

## What the agreement measure licenses

The practical claim of the whole reference-free branch is that a page whose repetitions disagree is a page worth checking first. On the seven reference pages that claim can be tested, because both quantities exist there.

Word agreement ranks the pages the way the fair CER ranks them, with Spearman −0.93 under it01, exact permutation p = 0.007 over all 5040 relabelings, and −0.79 under it02 with p = 0.048. Number agreement points the same way with a weaker rank, −0.71 with p = 0.088 and −0.57 with p = 0.200, which at n = 7 is compatible with chance. Measured 28.08.2026 from `analysis.json`.

Read as an operating point, a cut at word agreement of 0.55 or lower selects exactly the worst-read third of the it01 pages with no false positive; under it02 the equivalent cut sits at 0.59 and takes one further page with it. The threshold is a suggestion. It comes from seven pages of three documents, it is read off the same pages it is evaluated on, and no holdout exists. On unseen material it serves as a starting order for inspection, and a decision about an individual page stays with the facsimile.

## What the uncertain markers are worth

Over all runs of the seven reference pages, a marker sits on a token that the alignment to the reference does not match in 95.4 % of cases under it01 and in 88.4 % under it02. The comparison figure is the share of unmatched tokens overall, 49.1 % and 50.4 %, which is the precision a marker placed at random would reach. Recall rises from 25.4 % to 39.3 % as the marker count grows from 1161 to 1988. Iteration 02 buys coverage of the errors with a lower hit rate per marker, which is the trade the iteration was written for. Measured 28.08.2026 from `analysis.json`.

The measurement rests on an approximation that has to be stated. An error is defined as a token of the run that the alignment to the reference leaves unmatched. A correctly read token that loses its alignment to a neighbouring insertion counts as an error, and a wrong token that happens to align counts as correct. With about half of all tokens unmatched on this material, the absolute rates carry less weight than the distance between marker precision and the base rate.

## Limitations

- **Reference class.** No editorially accepted ground truth exists in the project. Every CER reported here compares a machine transcription against a Transkribus transcript of provisional status, so it measures the distance between two texts and ranks configurations against one another. A statement about quality would need a reference of the first class.
- **What the fair profile forgives.** The fair normalisation removes diacritics, collapses `u/v` and `i/j`, drops bracket markup and punctuation, and lowercases. Editorial expansions in the reference, written in round brackets, are unwrapped and then scored as though they stood on the page. Loss markers are dropped rather than counted as content the run failed to deliver. A model that never writes a diacritic is not penalised under this profile.
- **What temperature zero measures.** Repeated identical requests differ, so the agreement between repetitions measures the nondeterminism of the serving stack together with the ambiguity of the page. It is a lower bound on stability, and any statement about correctness needs the reference.
- **The iteration is a bundle.** Iteration 02 changed the prompt text, split the spread into two requests per folio, added the amount object to the response schema and reworked the few-shot example, all at once. No ablation separates the four, so the measured strict-CER gain cannot be attributed to any of them.
- **Numeral tokens mean different things per text type.** In an account book a numeral token is an amount; in an inventory it is a piece count. `is_numberish` accepts any token composed only of the letters `i v x l c d m j`, plus the unit list. On the reference texts that class covers 13.7 % of all tokens, of which 2.1 % of all tokens fall outside a subtractive Roman grammar. Most of those are additive forms this hand actually writes, `iiii` and `xiiii` among them. The residue of genuine false positives, German words such as `im` and `vil` counted as numerals, is about 0.5 % of all tokens.
- **The amounts check reaches a quarter of the material.** Across the two pilot cohorts, 17 of 70 detected blocks reach a verdict, 24 %, and 5 of 20 pages carry any finding in each cohort. Most undecided blocks fail on a Summa line without preceding items, on differing denominations, or on a token the parser refuses to guess. The check is also blind to a smoothed balance, because a model that adjusts an item to make the sum work produces a block that adds up. Its validity depends on the prompt that produced the amounts, so it does not transfer unchanged to a new iteration.
- **The reference base is an availability sample.** Seven usable text pages from three inventory documents, taken because they carry the `DONE` status rather than because they represent the corpus. Between those documents the fair CER of it02 runs from 14.6 % to 30.4 %, and across the pilot 2 inventories from 3.5 % to 39 %. Both spreads exceed the it01 to it02 effect of about three CER points by a wide margin, so a configuration decision read off this base carries the document mix with it.

## Suitability by research purpose

| Purpose | Current status | Consequence |
|---------|----------------|-------------|
| Blank-page and layout triage | Working | The model can pre-sort pages and produce structured output |
| Category overview of a volume | Plausible, piloted | Model output can generate search and inspection hypotheses; samples remain necessary |
| Person and function candidates | Not yet scholarly checked | Entity extraction may run only on text carrying a source link and a review status |
| Diplomatic edition | Not sufficiently evidenced | Release requires line-by-line checking against the facsimile |
| Amounts and accounting relations | Unstable in testing | Exact value, unit and line assignment need separate validation |

## Requirements register

Everything in this section is specification. None of it describes code that runs today, and each item names what would have to exist for the claim above it to become a measurement.

### Generation procedure

1. A manifest fixes document ID, folio, image URL, checksum, model version, prompt version and image transformation. Partly present today, since a run record carries the prompt hash, the few-shot hash, the model, the temperature and the image dimensions sent. The image checksum and a manifest file as such are missing.
2. The existing Transkribus baselines and regions are taken as a layout reference. For whole openings a page-level model run is kept in addition.
3. Every page of a held-out test set is processed both with a specialised HTR base model and with the current model configuration. The Text Titan I ter model is the obvious first Transkribus baseline candidate; its published vendor figures do not replace a direct comparison on DoCTA material. No such comparison has been run.
4. Regional crops are used deliberately for difficult names, marginal columns and amounts, rather than as a general strategy.
5. Divergences between systems produce a divergence list with image detail, line reference and competing readings, and the scholar decides directly at the facsimile. No divergence list is generated today; the pilot 2 referee review under `evaluation/pilot2/review/` is the manual precursor.
6. Unrevised machine output, formally checked text and accepted edition text remain separate data states. This one is implemented, in the register and in the TEI provenance.

A stronger vision-language model is compared on the same held-out page set. Model family and general vendor description are not sufficient grounds for a choice. Training a project-specific HTR model is considered only once enough corrected account-book lines exist and a separate test set can be preserved.

### Evaluator implementation

A full evaluator reads Transkribus PAGE XML and the derived DoCTA data contract directly, carrying over page ID, region and line order, transcription, convention label and reference status, and it produces per-page metrics together with a divergence list keyed to the corresponding image regions. The current runner reads the derived JSON exports rather than PAGE XML, produces the per-page metrics named in the status table, and produces no divergence list.

The normalisation profile is settled and no longer open. It is implemented in `run_benchmark.py`, versioned as `docta-fair-v2` and `docta-strict-v2`, and written into every summary the runner produces. The earlier name `docta-diplomatic-v1` in this document referred to a profile that was never implemented under that name.

### Evaluation contract

- Development material and a held-out test set are kept separate. This is currently violated by construction, as the iteration comparison section states.
- The sample covers scribes, page types, states of preservation, text density, tabular or columnar layout and blank pages. The benchmark page set does this for phenomena; the reference subset does not, being an availability sample.
- Inventories and account books are evaluated separately. Implemented, the two cohorts never share an aggregate.
- The two inventory conventions receive their own labels. An adapter maps both onto a versioned data contract. Not implemented.
- Every figure names reference class, normalisation profile, model version and sample size. Implemented for the benchmark, where `summary.json` carries `reference_class` per page, the profile versions, the model, the temperature and k per page and iteration.

### Release rule

A configuration is released for exactly the research purpose for which it passes the held-out test. Category overview, diplomatic edition and the reading of amounts receive separate decisions. A production decision follows the comparison with a specialised HTR model and the scholarly checking of a representative account-book sample. Neither precondition is met, so no configuration is released for any purpose beyond producing unrevised machine transcription.

## Scholarly review points

- The project lead sets the diplomatic target convention and the permissible normalisations.
- A representative account-book sample receives line-by-line reference transcriptions.
- Amounts are adjudicated together with unit, line and any relation to a total.
- SiCProD name variants are used only in post-processing. Every fuzzy match is preserved as a proposal alongside the original reading.

Two items are outstanding at the time of writing. The regression on the Thaur inventory pages needs adjudication at the image. And the two cover-label reference pages need a decision about their reference; the measurement no longer counts them, since `reference_degenerate` excludes them from every aggregate, and the underlying export still claims to transcribe a page it does not transcribe.

## Evidence and sources

### Local evidence

- `evaluation/benchmark/summary.json` and `evaluation/benchmark/runs/`
- `evaluation/benchmark/analysis.json` and `analysis.md`, produced by `analyze_summary.py`
- `evaluation/benchmark/prompts/` (versioned prompt iterations)
- `evaluation/pilot/pilot_summary.json` and `evaluation/pilot2/pilot2_summary.json`
- `evaluation/checks/amounts_report.md` (reference-free arithmetic probe)
- `experiments/transcription-test/results/` (frozen origin run)
- `data/benchmark/` (published export, rendered by `benchmark.html`)

### Methodological and technical sources

- Google, [Gemini 3.7 Flash](https://ai.google.dev/gemini-api/docs/models/gemini-3.7-flash). Model description and support for structured output.
- READ-COOP, [The Text Titan I ter](https://www.transkribus.org/models/the-text-titan-i-ter). Official model description; performance figures are vendor figures.
- Ströbel et al. 2022, [Evaluation of HTR models without Ground Truth Material](https://aclanthology.org/2022.lrec-1.467/). Reference-free metrics support model selection in an application context.
- Vidal et al. 2023, [End-to-End Page-Level Assessment of Handwritten Text Recognition](https://arxiv.org/abs/2301.05935). Page-level evaluation should measure recognition quality and reading order separately.
