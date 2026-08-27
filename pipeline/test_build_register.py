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


def test_export_pages_appear_exactly_once() -> None:
    """Every page of every Transkribus export is in its document register, once."""
    with tempfile.TemporaryDirectory() as td:
        _, pages_by_doc = _build(Path(td))
    for export in sorted((br.DATA / "transcriptions").glob("*.json")):
        doc_id = int(export.stem)
        assert doc_id in pages_by_doc, f"document {doc_id} missing from the register"
        registered = [p["pageNr"] for p in pages_by_doc[doc_id]]
        assert len(registered) == len(set(registered)), f"duplicate pages in {doc_id}"
        exported = [p["pageNr"] for p in br._load(export)["pages"]]
        assert sorted(registered) == sorted(exported), f"page set differs in {doc_id}"


def test_rebuild_is_byte_identical() -> None:
    """Runs are immutable: a second build reproduces the same files exactly."""
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        _build(Path(a))
        _build(Path(a))  # rebuild over the existing register
        _build(Path(b))
        for first in sorted(Path(a).rglob("*.json")):
            second = Path(b) / first.relative_to(a)
            assert first.read_bytes() == second.read_bytes(), f"drift in {first.name}"


def test_no_duplicate_run_ids() -> None:
    with tempfile.TemporaryDirectory() as td:
        _, pages_by_doc = _build(Path(td))
    for doc_id, pages in pages_by_doc.items():
        for page in pages:
            ids = [r["id"] for r in page["runs"]]
            assert len(ids) == len(set(ids)), f"duplicate run on {doc_id}/{page['pageNr']}"


def test_pilot_empty_page_carries_vlm_evidence() -> None:
    """Raitbuch spread 7 was reported empty on one side by both pilot runs."""
    with tempfile.TemporaryDirectory() as td:
        _, pages_by_doc = _build(Path(td))
    page = next(p for p in pages_by_doc[br.RAITBUCH2_DOC] if p["pageNr"] == 7)
    assert page["empty_evidence"] == {"method": "vlm", "runs": 2, "scope": "partial"}
    assert page["content_class"] == "unknown", "evidence must not flip the class"
    assert any(r["source"] == "vlm" and r["prompt"] == "it02" for r in page["runs"])


def test_vocabularies_and_transkribus_run() -> None:
    with tempfile.TemporaryDirectory() as td:
        docs, pages_by_doc = _build(Path(td))
    assert docs, "no documents built"
    for doc in docs:
        assert doc["provenance"] == "transkribus"
        assert doc["attribution"] is None
        for page in pages_by_doc[doc["docId"]]:
            assert page["content_class"] in br.CONTENT_CLASSES
            assert page["verification"]["status"] in br.VERIFICATION_STATUS
            transkribus = [r for r in page["runs"] if r["source"] == "transkribus"]
            assert len(transkribus) <= 1
            if page["content_class"] == "text":
                assert transkribus and transkribus[0]["lines"]


def test_projection_matches_register() -> None:
    with tempfile.TemporaryDirectory() as td:
        docs, pages_by_doc = _build(Path(td))
        payload = br.project(docs, pages_by_doc, Path(td) / "register_summary.json")
        assert json.loads((Path(td) / "register_summary.json")
                          .read_text(encoding="utf-8")) == payload
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
