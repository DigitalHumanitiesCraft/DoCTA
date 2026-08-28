# /// script
# requires-python = ">=3.10"
# dependencies = ["requests", "pillow"]
# ///
"""Pilot: it02 prompts under operating conditions instead of hand-picked pages.

Two cohorts:
  A. One complete inventory document (Naudersberg A 152.1, docId 11330060),
     scored per page against the Transkribus working transcription
     (a comparison signal, not ground truth).
  B. Twenty consecutive Raitbuch 2 spreads from the start of the book,
     scored by self-consistency between repeats.

Reuses the benchmark runner (prompts, request logic, metrics) unchanged;
only the page list and the evaluation differ. Runs land in runs/ here.
"""

import importlib.util
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).parent
REPO = ROOT.parents[1]

spec = importlib.util.spec_from_file_location(
    "run_benchmark", ROOT.parent / "benchmark" / "run_benchmark.py"
)
bench = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench)

# Runs belong to this cohort; the image cache stays shared with the benchmark.
bench.RUNS = ROOT / "runs"

INV_DOC = "11330060"  # Naudersberg A 152.1: dense text, castle unseen by the benchmark
RB_PAGES = list(range(2, 22))  # twenty consecutive spreads from the start of Raitbuch 2
REPEATS = 2
ITERATION = "it02"


def build_pages() -> list[dict]:
    pages = []
    doc = json.loads(
        (REPO / "docs" / "data" / "transcriptions" / f"{INV_DOC}.json").read_text(
            encoding="utf-8"
        )
    )
    for p in doc["pages"]:
        ref = [ln["text"] for r in p["regions"] for ln in r["lines"]]
        pages.append(
            {
                "id": f"pilot_inv_{INV_DOC}_p{p['pageNr']}",
                "source": "inventar",
                "folio": f"A 152.1 S. {p['pageNr']}",
                "phenomena": ["pilot"],
                "iiif": p["iiif"],
                "spread": False,
                "gt": None,
                "ref_lines": ref,
            }
        )
    rb = {
        p["pageNr"]: p
        for p in json.loads(
            (REPO / "docs" / "data" / "raitbuch2_pages.json").read_text(
                encoding="utf-8"
            )
        )
    }
    for n in RB_PAGES:
        pages.append(
            {
                "id": f"pilot_rb2_p{n:03d}",
                "source": "raitbuch2",
                "folio": f"pageNr {n}",
                "phenomena": ["pilot"],
                "iiif": rb[n]["iiif_url"],
                "spread": True,
                "gt": None,
            }
        )
    return pages


def evaluate(pages: list[dict]) -> dict:
    out = {"iteration": ITERATION, "model": bench.MODEL, "pages": {}}
    for page in pages:
        runs = sorted(bench.RUNS.glob(f"{page['id']}__{ITERATION}__r*.json"))
        if not runs:
            continue
        recs = [json.loads(f.read_text(encoding="utf-8")) for f in runs]
        texts = ["\n".join(r["lines"]) for r in recs]
        e = {
            "source": page["source"],
            "folio": page["folio"],
            "k": len(recs),
            "lines": [len(r["lines"]) for r in recs],
            "uncertain": [
                sum(
                    len(ln.get("uncertain", []) or [])
                    for pg in r["parsed"]["pages"]
                    for ln in pg.get("lines", [])
                )
                for r in recs
            ],
        }
        if page.get("ref_lines"):
            ref = "\n".join(page["ref_lines"])
            fair = [
                bench.cer(bench.normalize(t, "fair"), bench.normalize(ref, "fair"))
                for t in texts
            ]
            e["ref_lines"] = len(page["ref_lines"])
            e["cer_fair_vs_working"] = [round(x, 4) for x in fair]
        toks = [bench.normalize(t, "fair").split() for t in texts]
        if len(toks) >= 2:
            w, n = bench.positionwise(toks[0], toks[1])
            e["consistency_words"], e["consistency_numbers"] = w, n
        out["pages"][page["id"]] = e
    (ROOT / "pilot_summary.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return out


def main() -> None:
    eval_only = "--eval" in sys.argv
    pages = build_pages()
    if not eval_only:
        key = bench.load_api_key()
        prompts = bench.build_prompts()
        fs = bench.fewshot_example()
        bench.RUNS.mkdir(exist_ok=True)
        jobs = [(p, r) for p in pages for r in range(1, REPEATS + 1)]
        errors = []
        with ThreadPoolExecutor(max_workers=4) as ex:
            futs = {
                ex.submit(bench.run_one, key, p, ITERATION, prompts, r, fs): (p, r)
                for p, r in jobs
            }
            for fut in as_completed(futs):
                p, r = futs[fut]
                try:
                    print(fut.result(), flush=True)
                except Exception as exc:
                    errors.append({"page": p["id"], "repeat": r, "error": str(exc)})
                    print(f"FEHLER {p['id']} r{r}: {exc}", flush=True)
        if errors:
            (ROOT / "errors.json").write_text(
                json.dumps(errors, ensure_ascii=False, indent=1), encoding="utf-8"
            )
    summary = evaluate(pages)
    inv = [(k, v) for k, v in summary["pages"].items() if v["source"] == "inventar"]
    rb = [(k, v) for k, v in summary["pages"].items() if v["source"] == "raitbuch2"]
    print("\n== Inventar (CER fair gegen Arbeitstranskription, je Wiederholung) ==")
    for k, v in inv:
        print(
            f"{k}: cer={v.get('cer_fair_vs_working')} zeilen={v['lines']} "
            f"(ref {v.get('ref_lines')}) uncertain={v['uncertain']}"
        )
    print("\n== Raitbuch (Selbstkonsistenz r1/r2) ==")
    for k, v in rb:
        print(
            f"{k}: w={v.get('consistency_words')} n={v.get('consistency_numbers')} "
            f"zeilen={v['lines']} uncertain={v['uncertain']}"
        )


if __name__ == "__main__":
    main()
