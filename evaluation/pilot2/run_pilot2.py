# /// script
# requires-python = ">=3.10"
# dependencies = ["requests", "pillow"]
# ///
"""Pilot 2: the frozen it02 configuration on a wider slice of unseen material.

Extends the first pilot along both of its axes, with the model, prompts,
temperature and folio-split handling of the benchmark runner left untouched.

  A. Three complete inventory documents that appear in neither the benchmark
     nor the first pilot, scored per page against the Transkribus working
     transcription (a comparison signal, not ground truth) and by
     self-consistency between the two repeats.
  B. Raitbuch 2 spreads 22-41, the twenty following the first pilot's 2-21,
     scored by self-consistency alone.

Runs land in runs/ here, failures in errors.json, metrics in
pilot2_summary.json. The summary file is the source of truth for counts.

Usage:
  python run_pilot2.py           # run all missing (page x repeat), then evaluate
  python run_pilot2.py --eval    # only recompute the evaluation
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

# Redirect the runner's output dir into this folder; the image cache stays
# shared with the benchmark (gitignored, and no page overlaps anyway).
bench.RUNS = ROOT / "runs"

# Deterministic scope. Every listed document is unseen by evaluation/benchmark/
# and evaluation/pilot/, carries a Transkribus text export, and is a
# Burgeninventar; the matched source set holds no second category.
INV_DOCS = {
    "11348481": "Pergine, A 273.5, 1446",
    "11330759": "Sigmundskron, A 225.1, 1487",
    "11330219": "Schoeneck, A 185.1, 1492",
}
RB_PAGES = list(range(22, 42))  # the twenty spreads following the first pilot
REPEATS = 2
ITERATION = "it02"
WORKERS = 4


def build_pages() -> list[dict]:
    pages = []
    for doc_id, label in INV_DOCS.items():
        doc = json.loads(
            (REPO / "docs" / "data" / "transcriptions" / f"{doc_id}.json").read_text(
                encoding="utf-8"
            )
        )
        for p in doc["pages"]:
            ref = [ln["text"] for r in p["regions"] for ln in r["lines"]]
            pages.append(
                {
                    "id": f"pilot2_inv_{doc_id}_p{p['pageNr']}",
                    "source": "inventar",
                    "folio": f"{label} S. {p['pageNr']}",
                    "phenomena": ["pilot2"],
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
                "id": f"pilot2_rb2_p{n:03d}",
                "source": "raitbuch2",
                "folio": f"pageNr {n}",
                "phenomena": ["pilot2"],
                "iiif": rb[n]["iiif_url"],
                "spread": True,
                "gt": None,
            }
        )
    return pages


def evaluate(pages: list[dict]) -> dict:
    out = {
        "iteration": ITERATION,
        "model": bench.MODEL,
        "repeats": REPEATS,
        "inventories": INV_DOCS,
        "raitbuch2_pages": RB_PAGES,
        "pages": {},
    }
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
            "runs": [f.name for f in runs],
            "lines": [len(r["lines"]) for r in recs],
            # one flag per image part, so a spread reports verso and recto
            "empty_parts": [
                [pg.get("empty") is True for pg in r["parsed"]["pages"]] for r in recs
            ],
            "empty": [
                bool(r["parsed"]["pages"])
                and all(pg.get("empty") is True for pg in r["parsed"]["pages"])
                for r in recs
            ],
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
    (ROOT / "pilot2_summary.json").write_text(
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
        bench.RUNS.mkdir(parents=True, exist_ok=True)
        jobs = [(p, r) for p in pages for r in range(1, REPEATS + 1)]
        print(
            f"{len(jobs)} Laeufe geplant ({len(pages)} Seiten x k={REPEATS})",
            flush=True,
        )
        errors = []
        done = 0
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            futs = {
                ex.submit(bench.run_one, key, p, ITERATION, prompts, r, fs): (p, r)
                for p, r in jobs
            }
            for fut in as_completed(futs):
                p, r = futs[fut]
                done += 1
                try:
                    print(f"[{done}/{len(jobs)}] {fut.result()}", flush=True)
                except Exception as exc:
                    errors.append(
                        {
                            "page": p["id"],
                            "source": p["source"],
                            "iteration": ITERATION,
                            "repeat": r,
                            "error": str(exc),
                        }
                    )
                    print(
                        f"[{done}/{len(jobs)}] FEHLER {p['id']} r{r}: {exc}", flush=True
                    )
        (ROOT / "errors.json").write_text(
            json.dumps(errors, ensure_ascii=False, indent=1), encoding="utf-8"
        )
    summary = evaluate(pages)
    inv = [(k, v) for k, v in summary["pages"].items() if v["source"] == "inventar"]
    rb = [(k, v) for k, v in summary["pages"].items() if v["source"] == "raitbuch2"]
    print("\n== Inventare (CER fair gegen Arbeitstranskription, je Wiederholung) ==")
    for k, v in inv:
        print(
            f"{k}: cer={v.get('cer_fair_vs_working')} zeilen={v['lines']} "
            f"(ref {v.get('ref_lines')}) leer={v['empty']} "
            f"w={v.get('consistency_words')} n={v.get('consistency_numbers')}"
        )
    print("\n== Raitbuch 2 (Selbstkonsistenz r1/r2) ==")
    for k, v in rb:
        print(
            f"{k}: w={v.get('consistency_words')} n={v.get('consistency_numbers')} "
            f"zeilen={v['lines']} leer={v['empty_parts']} uncertain={v['uncertain']}"
        )


if __name__ == "__main__":
    main()
