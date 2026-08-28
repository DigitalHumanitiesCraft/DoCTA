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
  docs/data/edition_pages.json       page images of the documents DoCTA transcribes
  evaluation/benchmark/runs/*.json   VLM runs on the benchmark page set
  evaluation/pilot/runs/*.json       VLM runs on the pilot cohorts
  evaluation/pilot2/runs/*.json      VLM runs on the pilot-2 cohorts
  evaluation/edition/runs/*.json     VLM runs of the edition track

Writes:
  pipeline/documents.json            one entry per document
  pipeline/pages/<docId>.json        one entry per page
  docs/data/pipeline/register_summary.json   compact projection for the site (--project)
  docs/data/pipeline/transcriptions/<docId>.json   the text of a document DoCTA
                                     transcribed itself, for the site (--project)

Design decisions:
  Runs are immutable and provenance-tagged. A run is identified by its origin
  ("transkribus" for the export, "<cohort>:<run file stem>" for a VLM run), so a
  rebuild reproduces the same run list byte for byte and never duplicates.
  A run stores its lines uniformly as {"id", "text"} objects. The id is the
  Transkribus layout line id where the run knows one and null where it does not,
  which is what lets a later review address a single line of a page.
  content_class stays "unknown" where no export text exists; an empty page can
  only be established from the scan, which is a later pipeline step. VLM reports
  of an empty page are recorded as empty_evidence without changing the class.
  A run of the edition cohort is the one VLM run whose lines become edition text,
  so its lines are given synthetic ids v1, v2, ... in the order the run reported
  them. The measuring cohorts keep the null id of a bare VLM reading, because
  nothing downstream addresses a single line of theirs.

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
PILOT2_RUNS = REPO / "evaluation" / "pilot2" / "runs"
EDITION_RUNS = REPO / "evaluation" / "edition" / "runs"

# The cohort that produces edition text rather than measurements.
EDITION = "edition"
# Line ids of an edition run, run-relative and assigned here; a VLM reading has
# no layout identity of its own.
VLM_LINE_PREFIX = "v"
# The one block a VLM transcription has, since no layout analysis divided it.
VLM_REGION = "vlm"

# "Raitbuch 2", paired here because the CSV/Transkribus matcher covers the
# inventories only and the rb2_* evaluation runs need a document to hang on.
RAITBUCH2_DOC = 12514730
RAITBUCH2_SIGNATUR = "TLA Raitbuch 02"

CONTENT_CLASSES = ("text", "leer", "kassiert", "einlage", "unknown")
VERIFICATION_STATUS = ("unbearbeitet", "maschinell", "gesichtet", "abgenommen")

RUN_ID = re.compile(
    r"^(?:pilot2?_|edition_)?(?:inv_(?P<doc>\d+)|(?P<book>rb2))_p(?P<page>\d+)$"
)


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def review_runs(page: dict) -> list[dict]:
    """Review runs of a register page, in stored order.

    Single definition of what a review run is; apply_review, build_tei and the
    healthcheck all select on it, so the prefix cannot drift apart.
    """
    return [
        r for r in page.get("runs") or [] if str(r.get("id", "")).startswith("review:")
    ]


def newest_review_run(page: dict, exclude_id: str | None = None) -> dict | None:
    """The newest review run of a page by date then id, optionally excluding one."""
    runs = [r for r in review_runs(page) if r["id"] != exclude_id]
    if not runs:
        return None
    return max(runs, key=lambda r: (r.get("date") or "", r["id"]))


def edition_runs(page: dict) -> list[dict]:
    """Edition-cohort runs of a register page, in stored order."""
    return [
        r
        for r in page.get("runs") or []
        if str(r.get("id", "")).startswith(f"{EDITION}:")
    ]


def newest_edition_run(page: dict) -> dict | None:
    """The edition run whose lines are the text of the page, by date then id.

    A page can accumulate edition runs like any other, and the newest one is the
    reading the pipeline carries forward; the older ones stay in the register.
    """
    runs = edition_runs(page)
    if not runs:
        return None
    return max(runs, key=lambda r: (r.get("date") or "", r["id"]))


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
    for cohort, folder in (
        ("benchmark", BENCHMARK_RUNS),
        ("pilot", PILOT_RUNS),
        ("pilot2", PILOT2_RUNS),
        (EDITION, EDITION_RUNS),
    ):
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
            runs.setdefault(key, []).append(
                {
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
                    # uniform line shape across all runs; a VLM run reports bare
                    # text and has no layout line identity, so its id stays null
                    # outside the edition cohort, whose lines are addressed by
                    # review, entity anchor and TEI and therefore get one here
                    "lines": _vlm_lines(rec.get("lines") or [], cohort),
                }
            )
    for key in runs:
        runs[key].sort(key=lambda r: r["id"])
    if skipped:
        print(
            f"WARNUNG unaufloesbare Run-Seiten-Kennungen: {len(skipped)}",
            file=sys.stderr,
        )
        for name in skipped:
            print(f"  SKIP {name}", file=sys.stderr)
    return runs


def _vlm_lines(texts: list[str], cohort: str) -> list[dict]:
    """Line records of a VLM run, with a synthetic id in the edition cohort.

    The id is the position of the line in the run, so it is stable for a given
    run file and says nothing about the layout of the page, which the model did
    not analyse.
    """
    if cohort != EDITION:
        return [{"id": None, "text": t} for t in texts]
    return [{"id": f"{VLM_LINE_PREFIX}{n}", "text": t} for n, t in enumerate(texts, 1)]


def _documents() -> list[dict]:
    """One entry per document that has a Transkribus doc_id."""
    mapping = _load(DATA / "source_mapping.json")["matched"]
    sources = _load(DATA / "sources.json")
    by_signatur = {s["signatur"]: s for s in sources}
    # Per-document page-status distribution from the Transkribus collection;
    # DONE pages are human-corrected, everything else is machine layer.
    status_by_id = {d["id"]: d for d in _load(DATA / "transkribus_status.json")}

    docs: list[dict] = []
    for entry in mapping:
        docs.append(
            _document(
                entry["transkribus_id"],
                by_signatur.get(entry["csv_signatur"]),
                entry["csv_signatur"],
                entry.get("pages") or 0,
                bool(entry.get("has_text")),
                status_by_id.get(entry["transkribus_id"]),
            )
        )
    rb2 = by_signatur.get(RAITBUCH2_SIGNATUR)
    docs.append(
        _document(
            RAITBUCH2_DOC,
            rb2,
            RAITBUCH2_SIGNATUR,
            len(_load(DATA / "raitbuch2_pages.json")),
            False,
            status_by_id.get(RAITBUCH2_DOC),
        )
    )
    docs.sort(key=lambda d: d["docId"])
    return docs


def _document(
    doc_id: int,
    source: dict | None,
    signatur: str,
    pages: int,
    has_text: bool,
    status: dict | None = None,
) -> dict:
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
        # Page-status distribution in Transkribus (DONE = human-corrected);
        # per-page assignment needs the authenticated status fetch.
        "transkribus_statuses": (status or {}).get("statuses"),
        "done_pages": (status or {}).get("done_pages"),
    }


def _pages(doc: dict, runs: dict[tuple[int, int], list[dict]]) -> list[dict]:
    """Page entries for one document, from the export where one exists."""
    doc_id = doc["docId"]
    export = DATA / "transcriptions" / f"{doc_id}.json"
    if export.exists():
        entries = [_page_from_export(p) for p in _load(export)["pages"]]
    elif doc_id == RAITBUCH2_DOC:
        entries = [
            {"pageNr": p["pageNr"], "iiif": p.get("iiif_url"), "lines": []}
            for p in _load(DATA / "raitbuch2_pages.json")
        ]
    else:
        # No export, so no page list either; the images DoCTA transcribes on are
        # the ones named in the edition page table, the rest stay without a URL.
        images = _edition_images()
        entries = [
            {"pageNr": n, "iiif": images.get((doc_id, n)), "lines": []}
            for n in range(1, doc["pages"] + 1)
        ]

    pages = []
    for e in sorted(entries, key=lambda x: x["pageNr"]):
        page_runs: list[dict] = []
        if e["lines"]:
            page_runs.append(
                {
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
                }
            )
        page_runs.extend(runs.get((doc_id, e["pageNr"]), []))
        pages.append(
            {
                "pageNr": e["pageNr"],
                "iiif": e["iiif"],
                "content_class": "text" if e["lines"] else "unknown",
                "empty_evidence": _empty_evidence(page_runs),
                "verification": {"status": "unbearbeitet"},
                "runs": page_runs,
            }
        )
    return pages


def _edition_images() -> dict[tuple[int, int], str]:
    """(docId, pageNr) to IIIF URL, from the edition page table."""
    path = DATA / "edition_pages.json"
    if not path.exists():
        return {}
    return {(e["docId"], e["pageNr"]): e["iiif"] for e in _load(path)["pages"]}


def vlm_transcription(doc: dict, pages: list[dict]) -> dict | None:
    """The text of a document DoCTA transcribed itself, in the export shape.

    One block per page, the lines of the newest edition run of that page, and no
    coordinates, because a vision model reads text and analyses no layout. The
    shape is the one the Transkribus export carries, so TEI generation, entity
    extraction and the viewer read one structure whatever produced the text.
    Returns None for a document without a single edition run.
    """
    out_pages, runs = [], []
    for page in sorted(pages, key=lambda p: p["pageNr"]):
        run = newest_edition_run(page)
        if run is None:
            continue
        runs.append(run)
        out_pages.append(
            {
                "pageNr": page["pageNr"],
                "iiif": page["iiif"],
                "run": run["id"],
                "regions": [
                    {
                        "id": VLM_REGION,
                        "type": "",
                        "coords": "",
                        "lines": [
                            {
                                "id": line["id"],
                                "text": line["text"],
                                "coords": "",
                                "baseline": "",
                            }
                            for line in run["lines"]
                        ],
                    }
                ],
            }
        )
    if not out_pages:
        return None
    first = runs[0]
    return {
        "docId": doc["docId"],
        "title": doc["title"],
        "provenance": {
            "source": "vlm",
            "state": "machine-unrevised",
            "model": first["model"],
            "prompt": first["prompt"],
            "prompt_hash": first["prompt_hash"],
            "runs": [p["run"] for p in out_pages],
            # A page the pipeline has no image reference for cannot be
            # transcribed, so a file may cover part of its document; the ratio
            # travels with the text instead of being inferred from its length.
            "pagesTranscribed": len(out_pages),
            "pagesInDocument": len(pages),
            "note": "Unrevised vision-model transcription produced by the DoCTA"
            " pipeline. No page has been read against the scan by a scholar.",
        },
        "totalPages": len(out_pages),
        "totalLines": sum(len(p["regions"][0]["lines"]) for p in out_pages),
        "pages": out_pages,
    }


def transcription_of(
    doc_id: int, register_dir: Path | None = None, title: str | None = None
) -> dict | None:
    """The transcription of a document, whichever layer carries it.

    The Transkribus export where one exists, the DoCTA edition runs of the page
    register otherwise, both in the export shape. This is the single place that
    answers where the text of a document comes from; TEI generation, entity
    extraction and the healthcheck all ask here.
    """
    export = DATA / "transcriptions" / f"{doc_id}.json"
    if export.exists():
        data = _load(export)
        data["pages"] = sorted(data["pages"], key=lambda p: p["pageNr"])
        return data
    path = (register_dir or ROOT / "pages") / f"{doc_id}.json"
    if not path.exists():
        return None
    return vlm_transcription({"docId": doc_id, "title": title}, _load(path)["pages"])


def _empty_evidence(page_runs: list[dict]) -> dict | None:
    """Evidence that the page carries no text, counted over the VLM runs.

    scope "full" means every reporting run saw the whole page image empty,
    "partial" means at least one part of a spread was reported empty. The
    evidence never changes content_class; adjudication is a later step.
    """
    reporting = [
        r for r in page_runs if r["source"] == "vlm" and any(r["empty_parts"] or [])
    ]
    if not reporting:
        return None
    scope = "full" if all(r["empty"] for r in reporting) else "partial"
    return {"method": "vlm", "runs": len(reporting), "scope": scope}


def _page_from_export(page: dict) -> dict:
    lines = [
        {"id": ln["id"], "text": ln["text"]}
        for region in page.get("regions", [])
        for ln in region.get("lines", [])
    ]
    return {"pageNr": page["pageNr"], "iiif": page.get("iiif"), "lines": lines}


def _carry_review_state(out_dir: Path, doc_id: int, pages: list[dict]) -> None:
    """Carry the ingested review state of an existing register into a rebuild.

    Verification and review runs come from apply_review.py and are the one part
    of a page the builder cannot derive from its inputs; a rebuild that dropped
    them would destroy reviewer work without leaving a trace.
    """
    path = out_dir / "pages" / f"{doc_id}.json"
    if not path.exists():
        return
    by_nr = {p["pageNr"]: p for p in _load(path)["pages"]}
    for page in pages:
        old = by_nr.get(page["pageNr"])
        if old is None:
            continue
        page["runs"] += review_runs(old)
        verification = old.get("verification") or {}
        if verification.get("status") in ("gesichtet", "abgenommen"):
            page["verification"] = verification


def build(out_dir: Path) -> tuple[list[dict], dict[int, list[dict]]]:
    """Build the register and write it below out_dir. Deterministic and re-runnable."""
    runs = _vlm_runs()
    docs = _documents()
    pages_by_doc = {d["docId"]: _pages(d, runs) for d in docs}
    for doc_id, pages in pages_by_doc.items():
        _carry_review_state(out_dir, doc_id, pages)

    _write(out_dir / "documents.json", docs)
    for doc_id, pages in pages_by_doc.items():
        _write(out_dir / "pages" / f"{doc_id}.json", {"docId": doc_id, "pages": pages})
    return docs, pages_by_doc


def project(
    docs: list[dict], pages_by_doc: dict[int, list[dict]], out_path: Path
) -> dict:
    """Compact per-document projection for the site, loadable in one fetch.

    The transcription files of the documents DoCTA transcribed itself are
    written beside it, into a transcriptions/ folder of the same directory, so
    the whole site projection moves as one and a healthcheck rebuild stays
    inside its temporary directory.
    """
    # Attribution source: which documents carry a transcription made by the
    # Inventaria project (www.inventaria.at). The site must name that origin
    # wherever such a transcription is displayed, so the flag travels in the
    # projection instead of being joined client-side.
    mapping_path = DATA / "source_mapping.json"
    inventaria_ids: set[int] = set()
    if mapping_path.exists():
        inventaria_ids = {
            m["transkribus_id"]
            for m in _load(mapping_path).get("matched", [])
            if m.get("csv_transkribiert") == "Inventaria"
        }
    # Deep links to the published edition of each document on Transkribus
    # Sites, harvested by scripts/harvest_inventaria_mapping.py; a flagged
    # document without an entry stays attributed without a deep link.
    edition_path = DATA / "inventaria_mapping.json"
    edition_urls: dict[int, str] = {}
    if edition_path.exists():
        edition_urls = {
            d["docId"]: d["url"] for d in _load(edition_path).get("documents", [])
        }
    summary = []
    for doc in docs:
        pages = pages_by_doc[doc["docId"]]
        status = Counter(p["verification"]["status"] for p in pages)
        # Where the text of this document comes from, which decides both the
        # file the viewer loads and the wording of its provenance chip.
        transcription = vlm_transcription(doc, pages)
        if transcription is not None:
            _write(
                out_path.parent / "transcriptions" / f"{doc['docId']}.json",
                transcription,
            )
        has_export = (DATA / "transcriptions" / f"{doc['docId']}.json").exists()
        # First written page as the document's thumbnail source; the site
        # requests a scaled IIIF variant at runtime, no image enters the repo.
        # A document DoCTA transcribed itself has no page classed as text, since
        # that class needs the adjudication step, so its first transcribed page
        # stands in; the page is written either way.
        first_text = next(
            (p for p in pages if p["content_class"] == "text" and p["iiif"]), None
        ) or next((p for p in pages if edition_runs(p) and p["iiif"]), None)
        summary.append(
            {
                "docId": doc["docId"],
                "shelfmark": doc["shelfmark"],
                "title": doc["title"],
                "pages_total": len(pages),
                "pages_with_text": sum(
                    1 for p in pages if p["content_class"] == "text"
                ),
                "pages_with_vlm_runs": sum(
                    1 for p in pages if any(r["source"] == "vlm" for r in p["runs"])
                ),
                "pages_with_empty_evidence": sum(
                    1 for p in pages if p["empty_evidence"]
                ),
                "verification": {s: status.get(s, 0) for s in VERIFICATION_STATUS},
                "thumb": first_text["iiif"] if first_text else None,
                "thumb_page": first_text["pageNr"] if first_text else None,
                "done_pages": doc.get("done_pages"),
                # same predicate as build_tei.py: a TEI file exists for every
                # matched document with a Transkribus export on disk and for
                # every document DoCTA transcribed itself
                "has_tei": (bool(doc["has_text"]) and has_export)
                or transcription is not None,
                # "transkribus" for the export layer, "vlm" for a text DoCTA
                # produced itself, null for a document with no text at all
                "transcription_source": (
                    "transkribus"
                    if bool(doc["has_text"]) and has_export
                    else ("vlm" if transcription is not None else None)
                ),
                # lets the site skip the per-document entity probe; the demo
                # fallback for the one hand-made extraction stays client-side
                "has_entities": (DATA / "entities" / f"{doc['docId']}.json").exists(),
                "transcription_by": (
                    "Inventaria" if doc["docId"] in inventaria_ids else None
                ),
                "edition_url": edition_urls.get(doc["docId"]),
            }
        )
    payload = {"documents": summary}
    _write(out_path, payload)
    return payload


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--out",
        type=Path,
        default=ROOT,
        help="register target directory (default: pipeline/)",
    )
    ap.add_argument(
        "--project",
        action="store_true",
        help="also write the site projection to docs/data/pipeline/",
    )
    ap.add_argument(
        "--project-out", type=Path, default=DATA / "pipeline" / "register_summary.json"
    )
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
