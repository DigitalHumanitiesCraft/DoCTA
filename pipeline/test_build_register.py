"""Tests for the page register builder, runnable with pytest or plain python.

Integration tests against the real repo data; the register has no fixtures of
its own, its input is the repo.

Usage:
  python test_build_register.py
  pytest pipeline/test_build_register.py
"""

import json
import sys
import tempfile
from pathlib import Path

import build_register as br


def _build(tmp: Path) -> tuple[list[dict], dict[int, list[dict]]]:
    return br.build(tmp)


# ------------------------------------------------------------------ unit tests
# The pure functions of the builder, against written-out literals; the repo data
# exercises only the shapes it happens to hold.

# evaluation page id, resolved (docId, pageNr)
PAGE_KEY_CASES = (
    ("pilot_rb2_p002", (br.RAITBUCH2_DOC, 2)),
    ("pilot2_rb2_p029", (br.RAITBUCH2_DOC, 29)),
    ("rb2_p029", (br.RAITBUCH2_DOC, 29)),
    ("pilot2_inv_123_p4", (123, 4)),
    ("pilot_inv_11348659_p10", (11348659, 10)),
    ("inv_11348659_p1", (11348659, 1)),
    ("edition_inv_12593450_p1", (12593450, 1)),
    # everything the pattern does not resolve stays unresolved instead of being
    # guessed onto a document
    ("inv_11348659", None),
    ("inv_abc_p1", None),
    ("pilot3_rb2_p1", None),
    ("rb2_pxii", None),
    ("scan_0007", None),
    ("", None),
)


def test_evaluation_page_ids_resolve_to_a_document_and_page() -> None:
    for page_id, expected in PAGE_KEY_CASES:
        assert br._page_key(page_id) == expected, f"_page_key({page_id!r})"


EXPORT_RUN = {
    "id": "transkribus",
    "source": "transkribus",
    "empty": None,
    "empty_parts": None,
    "lines": [],
}
# a VLM run per report it can make about a Raitbuch spread
SAW_ALL_EMPTY = {"id": "a", "source": "vlm", "empty": True, "empty_parts": [True, True]}
SAW_ONE_EMPTY = {
    "id": "b",
    "source": "vlm",
    "empty": False,
    "empty_parts": [True, False],
}
SAW_ALL_WRITTEN = {
    "id": "c",
    "source": "vlm",
    "empty": False,
    "empty_parts": [False, False],
}
SAW_NOTHING = {"id": "d", "source": "vlm", "empty": False, "empty_parts": []}
REPORTED_NO_PARTS = {"id": "e", "source": "vlm", "empty": False, "empty_parts": None}

# page runs, evidence that the page carries no text
EMPTY_EVIDENCE_CASES = (
    # every reporting run saw the whole page image empty
    ([SAW_ALL_EMPTY, SAW_ALL_EMPTY], {"method": "vlm", "runs": 2, "scope": "full"}),
    # one side of the spread was written, so the evidence covers a part only
    ([SAW_ONE_EMPTY, SAW_ALL_EMPTY], {"method": "vlm", "runs": 2, "scope": "partial"}),
    ([SAW_ONE_EMPTY], {"method": "vlm", "runs": 1, "scope": "partial"}),
    # no run reports emptiness, so there is nothing to record
    ([SAW_ALL_WRITTEN, EXPORT_RUN], None),
    ([SAW_NOTHING], None),
    ([REPORTED_NO_PARTS], None),
    ([EXPORT_RUN], None),
    ([], None),
)


def test_empty_evidence_counts_only_the_reporting_vlm_runs() -> None:
    for runs, expected in EMPTY_EVIDENCE_CASES:
        assert br._empty_evidence(runs) == expected, (
            f"_empty_evidence over {[r['id'] for r in runs]}"
        )


RUN_AB = {
    "id": "review:11327963-2-2026-09-01-AB",
    "source": "human",
    "reviewer": "AB",
    "date": "2026-09-01",
    "lines": [],
}
RUN_XY = {
    "id": "review:11327963-2-2026-09-01-XY",
    "source": "human",
    "reviewer": "XY",
    "date": "2026-09-01",
    "lines": [],
}
RUN_LATER = {
    "id": "review:11327963-2-2026-09-04-AB",
    "source": "human",
    "reviewer": "AB",
    "date": "2026-09-04",
    "lines": [],
}
RUN_UNDATED = {
    "id": "review:11327963-2-undated-AB",
    "source": "human",
    "reviewer": "AB",
    "date": None,
    "lines": [],
}

# runs of a page, excluded run id, the run that is the newest review
NEWEST_REVIEW_CASES = (
    ([], None, None),
    ([EXPORT_RUN], None, None),
    ([EXPORT_RUN, RUN_AB], None, RUN_AB),
    # the later date wins over the stored order
    ([RUN_LATER, RUN_AB], None, RUN_LATER),
    # same date: the id decides, so the choice stays deterministic
    ([RUN_XY, RUN_AB], None, RUN_XY),
    # a run without a date sorts below every dated one
    ([RUN_UNDATED, RUN_AB], None, RUN_AB),
    ([RUN_UNDATED], None, RUN_UNDATED),
    # the run a re-ingest is about to replace is not its own base
    ([RUN_LATER, RUN_AB], "review:11327963-2-2026-09-04-AB", RUN_AB),
    ([RUN_AB], "review:11327963-2-2026-09-01-AB", None),
)


def test_the_newest_review_run_is_decided_by_date_then_id() -> None:
    for runs, exclude, expected in NEWEST_REVIEW_CASES:
        page = {"pageNr": 2, "runs": runs}
        assert br.newest_review_run(page, exclude) is expected, (
            f"newest_review_run over {[r['id'] for r in runs]}, without {exclude}"
        )


def test_only_an_edition_run_gets_synthetic_line_ids() -> None:
    """The cohort that produces edition text names its lines; measuring runs do not.

    A review, an entity anchor and the TEI address a single line, which needs an
    id; a benchmark repeat is read as a whole and keeps the null of a bare VLM
    reading.
    """
    texts = ["erste zeile", "zweite zeile"]
    assert br._vlm_lines(texts, br.EDITION) == [
        {"id": "v1", "text": "erste zeile"},
        {"id": "v2", "text": "zweite zeile"},
    ]
    for cohort in ("benchmark", "pilot", "pilot2"):
        assert br._vlm_lines(texts, cohort) == [
            {"id": None, "text": "erste zeile"},
            {"id": None, "text": "zweite zeile"},
        ], cohort
    assert br._vlm_lines([], br.EDITION) == []


# --------------------------------------------------------- integration tests


def test_export_pages_appear_exactly_once() -> None:
    """Every page of every Transkribus export is in its document register, once,
    and a page with exported lines carries that export as its single run."""
    with tempfile.TemporaryDirectory() as td:
        _, pages_by_doc = _build(Path(td))
    for export in sorted((br.DATA / "transcriptions").glob("*.json")):
        doc_id = int(export.stem)
        assert doc_id in pages_by_doc, f"document {doc_id} missing from the register"
        registered = {p["pageNr"]: p for p in pages_by_doc[doc_id]}
        assert len(registered) == len(pages_by_doc[doc_id]), (
            f"duplicate pages in {doc_id}"
        )
        pages = br._load(export)["pages"]
        assert sorted(registered) == sorted(p["pageNr"] for p in pages), (
            f"page set differs in {doc_id}"
        )
        for page in pages:
            where = f"{doc_id}/{page['pageNr']}"
            exported = [
                ln
                for region in page.get("regions") or []
                for ln in region.get("lines") or []
            ]
            runs = [
                r
                for r in registered[page["pageNr"]]["runs"]
                if r["source"] == "transkribus"
            ]
            assert len(runs) == (1 if exported else 0), (
                f"{where}: {len(runs)} transkribus runs for {len(exported)} lines"
            )
            if exported:
                assert [ln["id"] for ln in runs[0]["lines"]] == [
                    ln["id"] for ln in exported
                ], f"{where}: line set differs"


def test_rebuild_is_byte_identical() -> None:
    """Runs are immutable: a second build reproduces the same files exactly."""
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        _build(Path(a))
        _build(Path(a))  # rebuild over the existing register
        _build(Path(b))
        for first in sorted(Path(a).rglob("*.json")):
            second = Path(b) / first.relative_to(a)
            assert first.read_bytes() == second.read_bytes(), f"drift in {first.name}"


def test_pilot_empty_page_carries_vlm_evidence() -> None:
    """Raitbuch spread 7 was reported empty on one side by both pilot runs."""
    with tempfile.TemporaryDirectory() as td:
        _, pages_by_doc = _build(Path(td))
    page = next(p for p in pages_by_doc[br.RAITBUCH2_DOC] if p["pageNr"] == 7)
    assert page["empty_evidence"] == {"method": "vlm", "runs": 2, "scope": "partial"}
    assert page["content_class"] == "unknown", "evidence must not flip the class"
    assert any(r["source"] == "vlm" and r["prompt"] == "it02" for r in page["runs"])


def test_rebuild_preserves_ingested_review_state() -> None:
    """A rebuild keeps what apply_review.py wrote, the one non-derivable state."""
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        _, pages_by_doc = _build(out)
        doc_id = next(
            d
            for d, pages in sorted(pages_by_doc.items())
            if any(p["runs"] for p in pages)
        )
        path = out / "pages" / f"{doc_id}.json"
        register = br._load(path)
        page = next(p for p in register["pages"] if p["runs"])
        review_run = {
            "id": f"review:{doc_id}-{page['pageNr']}-2026-09-01-AB",
            "source": "human",
            "reviewer": "AB",
            "date": "2026-09-01",
            "lines": [{"id": "l1", "text": "korrigiert"}],
        }
        page["runs"].append(review_run)
        page["verification"] = {
            "status": "gesichtet",
            "reviewer": "AB",
            "date": "2026-09-01",
        }
        br._write(path, register)
        _build(out)  # rebuild over a register that now holds a review
        rebuilt = next(
            p for p in br._load(path)["pages"] if p["pageNr"] == page["pageNr"]
        )
        assert review_run in rebuilt["runs"], "review run lost on rebuild"
        assert rebuilt["verification"]["status"] == "gesichtet"
        ids = [r["id"] for r in rebuilt["runs"]]
        assert len(ids) == len(set(ids)), "review run duplicated on rebuild"


EDITION_DOC = 12593450  # A 024.1, one page, transcribed by DoCTA itself


def test_a_document_without_an_export_carries_its_edition_run() -> None:
    """The edition cohort reaches the register, with an image and named lines."""
    with tempfile.TemporaryDirectory() as td:
        _, pages_by_doc = _build(Path(td))
    pages = pages_by_doc[EDITION_DOC]
    page = next(p for p in pages if p["pageNr"] == 1)
    runs = br.edition_runs(page)
    assert len(runs) == 1, "the edition run of the page is missing"
    assert br.newest_edition_run(page) is runs[0]
    assert page["iiif"], "no page image for a page that was transcribed"
    assert runs[0]["source"] == "vlm" and runs[0]["model"]
    ids = [line["id"] for line in runs[0]["lines"]]
    assert ids == [f"v{n}" for n in range(1, len(ids) + 1)], "line ids are not v1..vn"
    # The class stays unknown: what a page holds is settled on the scan, and no
    # adjudication step has run for this document.
    assert page["content_class"] == "unknown"


def test_the_site_transcription_mirrors_the_edition_run() -> None:
    """The projection carries the text of the newest edition run, page by page,
    marked as unrevised machine output and without invented layout data."""
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        docs, pages_by_doc = _build(out)
        br.project(docs, pages_by_doc, out / "register_summary.json")
        written = json.loads(
            (out / "transcriptions" / f"{EDITION_DOC}.json").read_text(encoding="utf-8")
        )
        # Exactly the documents DoCTA transcribed itself get such a file; a
        # document with a Transkribus export is read from the export.
        assert {int(p.stem) for p in (out / "transcriptions").glob("*.json")} == {
            doc_id
            for doc_id, pages in pages_by_doc.items()
            if any(br.edition_runs(p) for p in pages)
        }
    doc = next(d for d in docs if d["docId"] == EDITION_DOC)
    assert written == br.vlm_transcription(doc, pages_by_doc[EDITION_DOC])
    assert written["provenance"]["state"] == "machine-unrevised"
    assert written["provenance"]["runs"] == [
        br.newest_edition_run(pages_by_doc[EDITION_DOC][0])["id"]
    ]
    for page in written["pages"]:
        regions = page["regions"]
        assert [r["id"] for r in regions] == [br.VLM_REGION], "one block per page"
        run = br.newest_edition_run(
            next(p for p in pages_by_doc[EDITION_DOC] if p["pageNr"] == page["pageNr"])
        )
        assert [ln["text"] for ln in regions[0]["lines"]] == [
            ln["text"] for ln in run["lines"]
        ]
        assert not any(ln["coords"] for ln in regions[0]["lines"]), (
            "a vision model analyses no layout, so it claims no coordinates"
        )


def test_projection_matches_register() -> None:
    with tempfile.TemporaryDirectory() as td:
        docs, pages_by_doc = _build(Path(td))
        payload = br.project(docs, pages_by_doc, Path(td) / "register_summary.json")
        assert (
            json.loads((Path(td) / "register_summary.json").read_text(encoding="utf-8"))
            == payload
        )
    for entry in payload["documents"]:
        pages = pages_by_doc[entry["docId"]]
        assert entry["pages_total"] == len(pages)
        assert sum(entry["verification"].values()) == entry["pages_total"]


def main() -> int:
    failed = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_"):
            continue
        try:
            fn()
            print(f"OK   {name}")
        except AssertionError as exc:
            failed += 1
            print(f"FEHLER {name}: {exc}", file=sys.stderr)
    print(f"{'FEHLER' if failed else 'OK'}: {failed} fehlgeschlagen")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
