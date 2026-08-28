# Edition track: the transcriptions DoCTA produces itself

The benchmark and the two pilots measure a prompt configuration, so they repeat every page and score the repeats against each other. This cohort does something else. It transcribes the sources Transkribus holds no text for, and its runs are the text the page register, the TEI files and the site carry. There is one run per page, because a second reading would raise the question which of the two is the edition text, and nothing in the pipeline answers that yet.

Model, prompts, temperature, image scaling and few-shot handling come from `../benchmark/run_benchmark.py` unchanged, iteration it02 with the inventory module. Only the page set and the repeat count differ.

## Scope

The page set is `docs/data/edition_pages.json`, the image table of the documents without a Transkribus export. Two documents stand in it.

| docId | Shelfmark | Title | Pages transcribed |
|---|---|---|---|
| 12593450 | A 024.1 | Inventare des Hauskämmeramtes in Innsbruck, 1489 | 1 of 1 |
| 12647153 | A 006.8 (und .9) | Inventar des Silbergeschirrs, das Martein Aichorn anvertraut ist, 1487 | 1 of 6 |

Document 12593450 is complete, because it is a single sheet. Of document 12647153 only the first page is transcribed, and that is a limit of the image references rather than of the transcription. A document without a Transkribus export carries no page list, so the only image key the repository holds for it is the one in `docs/data/transkribus_collection.json`, which is the first page. The keys of pages 2 to 6 need an authenticated Transkribus `fulldoc` call with `TRANSKRIBUS_USER` and `TRANSKRIBUS_PASS`, which no environment of this repository currently holds. Until that call runs, those five pages stay untranscribed and their register entries stay empty; nothing in the pipeline pretends otherwise.

## What a run produces

Runs live in `runs/`, one file per page, named `edition_inv_<docId>_p<n>__it02__r1.json`. The record is the one the benchmark runner writes, so it carries the model, the temperature, the prompt hash, the image parameters, the duration, the timestamp and the full structured answer beside the plain line list. Runs are never overwritten or deleted; a better transcription is a new run and the register picks the newest one.

There is no summary file. Without a reference transcription and without repeats there is no metric to compute, and the run records are the source of truth for everything else.

Failures are collected in `errors.json`, empty when every page went through. The API refused nothing in this run set; the benchmark saw one blocked page on a dense Raitbuch spread, which is the kind of failure this file is for.

## Where the runs go from here

`pipeline/build_register.py` reads this folder as the cohort `edition` and writes one run per page into the register under the id `edition:<run file stem>`. The lines of an edition run get the synthetic ids `v1`, `v2` and so on, in the order the run reported them, because a review, an entity anchor and a TEI line have to address a single line and a vision model returns no layout identity. Those ids are relative to their run and say nothing about the layout of the page.

Everything downstream follows from the register. `build_tei.py` writes `docs/data/tei/<docId>.xml` with the responsibility `resp-vlm-transcription`, `extract_entities.py` anchors entities on the `v` ids, and `build_register.py --project` writes the transcription the viewer reads to `docs/data/pipeline/transcriptions/<docId>.json`.

## Rerunning

```
python run_edition.py          # transcribe every page of the table that has no run yet
python run_edition.py --list   # print the page set and exit
```

Existing runs are skipped, so a rerun only fills gaps. Page images are cached in the shared, gitignored `../benchmark/images/` and never enter the repository. The API key is read from `GEMINI_API_KEY` in the repository root `.env`.

Everything this cohort produces is unrevised machine output. It is marked as such in the register, in the TEI header, in the site projection and in the viewer, and it stays that way until a scholar has read it against the scan.

License as for the repository: code MIT, documents and data CC BY 4.0.
