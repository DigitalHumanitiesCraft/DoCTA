"""Build the page register: one document index plus one page file per document.

The register is the data backbone of the agentic edition pipeline. It answers,
for every page of every DoCTA document with a Transkribus doc_id, what the page
is (content class), how far it has been verified, and which transcription runs
exist for it.

Data flow (repo-local only, no network):
  docs/data/source_mapping.json      matched CSV entry <-> Transkribus doc
  docs/data/sources.json             archival metadata (shelfmark, dating, tier)
  docs/data/transcriptions/*.json    Transkribus export: pages, IIIF, lines
  docs/data/raitbuch2_pages.json     page list of Raitbuch 2 (no export yet)
  evaluation/benchmark/runs/*.json   VLM runs on the benchmark page set
  evaluation/pilot/runs/*.json       VLM runs on the pilot cohorts

Writes:
  pipeline/documents.json            one entry per document
  pipeline/pages/<docId>.json        one entry per page
  docs/data/pipeline/register_summary.json   compact projection for the site (--project)

Design decisions:
  Runs are immutable and provenance-tagged. A run is identified by its origin
  ("transkribus" for the export, "<cohort>:<run file stem>" for a VLM run), so a
  rebuild reproduces the same run list byte for byte and never duplicates.
  content_class stays "unknown" where no export text exists; an empty page can
  only be established from the scan, which is a later pipeline step. VLM reports
  of an empty page are recorded as empty_evidence without changing the class.

Usage:
  python build_register.py             # rebuild pipeline/documents.json and pipeline/pages/
  python build_register.py --project   # additionally write the site projection
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent
REPO = ROOT.parent
DATA = REPO / "docs" / "data"
BENCHMARK_RUNS = REPO / "evaluation" / "benchmark" / "runs"
PILOT_RUNS = REPO / "evaluation" / "pilot" / "runs"

RAITBUCH2_DOC = 12514730  # "Raitbuch 2"; the CSV/Transkribus matcher covers only
RAITBUCH2_SIGNATUR = "TLA Raitbuch 02"  # the inventories, so this pair is set here
# (title and page count agree) to give the rb2_* evaluation runs a document to hang on.

CONTENT_CLASSES = ("text", "leer", "kassiert", "einlage", "unknown")
VERIFICATION_STATUS = ("unbearbeitet", "maschinell", "gesichtet", "abgenommen")

RUN_ID = re.compile(r"^(?:pilot_)?(?:inv_(?P<doc>\d+)|(?P<book>rb2))_p(?P<page>\d+)$")


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
                    encoding="utf-8")


def _page_key(page_id: str) -> tuple[int, int] | None:
    """Resolve an evaluation page id such as pilot_rb2_p002 to (docId, pageNr)."""
    m = RUN_ID.match(page_id)
    if not m:
        return None
    doc = RAITBUCH2_DOC if m.group("book") else int(m.group("doc"))
    return doc, int(m.group("page"))


def _vlm_runs() -> dict[tuple[int, int], list[dict]]:
    """Collect VLM runs from both evaluation cohorts, keyed by (docId, pageNr)."""
    runs: dict[tuple[int, int], list[dict]] = {}
    skipped: list[str] = []
    for cohort, folder in (("benchmark", BENCHMARK_RUNS), ("pilot", PILOT_RUNS)):
        if not folder.is_dir():
            continue
        for f in sorted(folder.glob("*.json")):
            rec = _load(f)
            key = _page_key(rec["page"])
            if key is None:
                skipped.append(f"{cohort}/{f.name}")
                continue
            parsed = rec.get("parsed") or {}
            parts = [p.get("empty") is True for p in parsed.get("pages") or []]
            empty = bool(parts) and all(parts)
            runs.setdefault(key, []).append({
                "id": f"{cohort}:{f.stem}",
                "source": "vlm",
                "model": rec.get("model"),
                "prompt": rec.get("iteration"),
                "prompt_hash": rec.get("prompt_hash"),
                "repeat": rec.get("repeat"),
                "date": rec.get("timestamp"),
                "empty": empty,
                # per image part in the order the run reported them; a raitbuch
                # page is a spread and is sent as verso and recto
                "empty_parts": parts,
                "lines": list(rec.get("lines") or []),
            })
    for key in runs:
        runs[key].sort(key=lambda r: r["id"])
    if skipped:
        print(f"WARNUNG unaufloesbare Run-Seiten-Kennungen: {len(skipped)}",
              file=sys.stderr)
        for name in skipped:
            print(f"  SKIP {name}", file=sys.stderr)
    return runs


def _documents() -> list[dict]:
    """One entry per document that has a Transkribus doc_id."""
    mapping = _load(DATA / "source_mapping.json")["matched"]
    sources = _load(DATA / "sources.json")
    by_signatur = {s["signatur"]: s for s in sources}

    docs: list[dict] = []
    for entry in mapping:
        docs.append(_document(entry["transkribus_id"],
                              by_signatur.get(entry["csv_signatur"]),
                              entry["csv_signatur"],
                              entry.get("pages") or 0,
                              bool(entry.get("has_text"))))
    rb2 = by_signatur.get(RAITBUCH2_SIGNATUR)
    docs.append(_document(RAITBUCH2_DOC, rb2, RAITBUCH2_SIGNATUR,
                          len(_load(DATA / "raitbuch2_pages.json")), False))
    docs.sort(key=lambda d: d["docId"])
    return docs


def _document(doc_id: int, source: dict | None, signatur: str,
              pages: int, has_text: bool) -> dict:
    dating = (source or {}).get("datierung") or {}
    return {
        "docId": doc_id,
        "shelfmark": signatur,
        "title": (source or {}).get("titel"),
        "dating": {
            "raw": dating.get("raw"),
            "start": dating.get("start"),
            "end": dating.get("end"),
        },
        "category": (source or {}).get("kategorie"),
        "pages": pages,
        "tier": (source or {}).get("tier"),
        "has_text": has_text,
        "provenance": "transkribus",
        # reserved for "inventaria" once the published edition list is available
        "attribution": None,
    }


def _pages(doc: dict, runs: dict[tuple[int, int], list[dict]]) -> list[dict]:
    """Page entries for one document, from the export where one exists."""
    doc_id = doc["docId"]
    export = DATA / "transcriptions" / f"{doc_id}.json"
    if export.exists():
        entries = [_page_from_export(p) for p in _load(export)["pages"]]
    elif doc_id == RAITBUCH2_DOC:
        entries = [{"pageNr": p["pageNr"], "iiif": p.get("iiif_url"), "lines": []}
                   for p in _load(DATA / "raitbuch2_pages.json")]
    else:
        entries = [{"pageNr": n, "iiif": None, "lines": []}
                   for n in range(1, doc["pages"] + 1)]

    pages = []
    for e in sorted(entries, key=lambda x: x["pageNr"]):
        page_runs: list[dict] = []
        if e["lines"]:
            page_runs.append({
                "id": "transkribus",
                "source": "transkribus",
                "model": None,
                "prompt": None,
                "prompt_hash": None,
                "repeat": None,
                "date": None,
                "empty": None,
                "empty_parts": None,
                "lines": e["lines"],
            })
        page_runs.extend(runs.get((doc_id, e["pageNr"]), []))
        pages.append({
            "pageNr": e["pageNr"],
            "iiif": e["iiif"],
            "content_class": "text" if e["lines"] else "unknown",
            "empty_evidence": _empty_evidence(page_runs),
            "verification": {"status": "unbearbeitet"},
            "runs": page_runs,
        })
    return pages


def _empty_evidence(page_runs: list[dict]) -> dict | None:
    """Evidence that the page carries no text, counted over the VLM runs.

    scope "full" means every reporting run saw the whole page image empty,
    "partial" means at least one part of a spread was reported empty. The
    evidence never changes content_class; adjudication is a later step.
    """
    reporting = [r for r in page_runs
                 if r["source"] == "vlm" and any(r["empty_parts"] or [])]
    if not reporting:
        return None
    scope = "full" if all(r["empty"] for r in reporting) else "partial"
    return {"method": "vlm", "runs": len(reporting), "scope": scope}


def _page_from_export(page: dict) -> dict:
    lines = [ln["text"] for region in page.get("regions", [])
             for ln in region.get("lines", [])]
    return {"pageNr": page["pageNr"], "iiif": page.get("iiif"), "lines": lines}


def build(out_dir: Path) -> tuple[list[dict], dict[int, list[dict]]]:
    """Build the register and write it below out_dir. Deterministic and re-runnable."""
    runs = _vlm_runs()
    docs = _documents()
    pages_by_doc = {d["docId"]: _pages(d, runs) for d in docs}

    _write(out_dir / "documents.json", docs)
    for doc_id, pages in pages_by_doc.items():
        _write(out_dir / "pages" / f"{doc_id}.json",
               {"docId": doc_id, "pages": pages})
    return docs, pages_by_doc


def project(docs: list[dict], pages_by_doc: dict[int, list[dict]],
            out_path: Path) -> dict:
    """Compact per-document projection for the site, loadable in one fetch."""
    summary = []
    for doc in docs:
        pages = pages_by_doc[doc["docId"]]
        status = Counter(p["verification"]["status"] for p in pages)
        summary.append({
            "docId": doc["docId"],
            "shelfmark": doc["shelfmark"],
            "title": doc["title"],
            "pages_total": len(pages),
            "pages_with_text": sum(1 for p in pages if p["content_class"] == "text"),
            "pages_with_vlm_runs": sum(
                1 for p in pages if any(r["source"] == "vlm" for r in p["runs"])),
            "pages_with_empty_evidence": sum(
                1 for p in pages if p["empty_evidence"]),
            "verification": {s: status.get(s, 0) for s in VERIFICATION_STATUS},
        })
    payload = {"documents": summary}
    _write(out_path, payload)
    return payload


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=ROOT,
                    help="register target directory (default: pipeline/)")
    ap.add_argument("--project", action="store_true",
                    help="also write the site projection to docs/data/pipeline/")
    ap.add_argument("--project-out", type=Path,
                    default=DATA / "pipeline" / "register_summary.json")
    args = ap.parse_args()

    docs, pages_by_doc = build(args.out)
    total = sum(len(p) for p in pages_by_doc.values())
    print(f"OK Register: {len(docs)} Dokumente, {total} Seiten -> {args.out}")
    if args.project:
        project(docs, pages_by_doc, args.project_out)
        print(f"OK Projektion -> {args.project_out}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
