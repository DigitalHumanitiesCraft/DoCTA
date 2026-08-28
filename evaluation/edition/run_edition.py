# /// script
# requires-python = ">=3.11"
# dependencies = ["requests", "pillow"]
# ///
"""Edition track: the frozen it02 configuration on documents DoCTA transcribes itself.

The benchmark and the two pilots measure a prompt configuration and therefore
repeat every page. This cohort produces edition text instead, so it runs one
transcription per page and its records are what the page register, the TEI and
the site are built from. Model, prompts, temperature and image handling come
from ../benchmark/run_benchmark.py unchanged; only the page set and the repeat
count differ.

The page set is every page listed in docs/data/edition_pages.json, which is the
image table for the documents without a Transkribus text export. A page whose
image key is not known yet is simply not in that file and stays untranscribed.

Runs land in runs/, failures in errors.json. There is no summary file: without a
reference transcription and without repeats there is no metric to compute, and
the run records themselves are the source of truth.

Usage:
  python run_edition.py            # transcribe every missing page (skip-if-exists)
  python run_edition.py --list     # print the page set and exit
"""

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent
REPO = ROOT.parents[1]

spec = importlib.util.spec_from_file_location(
    "run_benchmark", ROOT.parent / "benchmark" / "run_benchmark.py"
)
bench = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench)

# Runs belong to this cohort; the image cache stays shared with the benchmark,
# which is gitignored and holds no page of this set.
bench.RUNS = ROOT / "runs"

ITERATION = "it02"
REPEAT = 1
PAGE_TABLE = REPO / "docs" / "data" / "edition_pages.json"


def build_pages() -> list[dict]:
    """The page set, in document and page order, from the image table."""
    table = json.loads(PAGE_TABLE.read_text(encoding="utf-8"))["pages"]
    return [
        {
            "id": f"edition_inv_{entry['docId']}_p{entry['pageNr']}",
            "source": "inventar",
            "folio": f"document {entry['docId']}, page {entry['pageNr']}",
            "iiif": entry["iiif"],
            "spread": False,
            "gt": None,
        }
        for entry in sorted(table, key=lambda e: (e["docId"], e["pageNr"]))
    ]


def main() -> int:
    pages = build_pages()
    if "--list" in sys.argv:
        for page in pages:
            print(f"{page['id']}  {page['iiif']}")
        return 0

    key = bench.load_api_key()
    prompts = bench.build_prompts()
    fewshot = bench.fewshot_example()
    bench.RUNS.mkdir(parents=True, exist_ok=True)
    errors = []
    for page in pages:
        try:
            print(bench.run_one(key, page, ITERATION, prompts, REPEAT, fewshot))
        except Exception as exc:  # skip-and-log-and-collect, as in the benchmark
            print(f"FEHLER {page['id']}: {exc}", file=sys.stderr)
            errors.append(
                {
                    "page": page["id"],
                    "iteration": ITERATION,
                    "repeat": REPEAT,
                    "error": str(exc),
                }
            )
    (ROOT / "errors.json").write_text(
        json.dumps(errors, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
