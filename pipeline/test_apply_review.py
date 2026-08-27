"""Tests for the review ingest, runnable with pytest or plain python.

The ingest has no review data in the repository yet, so its input is a fixture
export built against a temporary copy of the real register.

Usage:
  python test_apply_review.py
  pytest pipeline/test_apply_review.py
"""

import json
import sys
import tempfile
from pathlib import Path

import apply_review as ar
import build_register as br

DOC = 11327963
PAGE = 2
REVIEWER = "XY"
DATE = "2026-09-03"


def _register(tmp: Path) -> Path:
    """A fresh register below tmp; returns its pages directory."""
    br.build(tmp)
    return tmp / "pages"


def _page(pages_dir: Path, page_nr: int = PAGE) -> dict:
    payload = br._load(pages_dir / f"{DOC}.json")
    return next(p for p in payload["pages"] if p["pageNr"] == page_nr)


def _base_text(pages_dir: Path, line_id: str) -> str:
    page = _page(pages_dir)
    run = next(r for r in page["runs"] if r["source"] == "transkribus")
    return next(ln["text"] for ln in run["lines"] if ln["id"] == line_id)


def review_file(tmp: Path, pages_dir: Path, line_id: str = "r2l1",
                corrected: str = "Auf dem klainen estrich",
                original: str | None = None,
                status: str | None = "gesichtet") -> Path:
    """One viewer export against the current base text of the register."""
    payload = {
        "docId": DOC,
        "reviewer": REVIEWER,
        "pages": {str(PAGE): {
            "status": status,
            "date": DATE,
            "lines": [{"id": line_id,
                       "original": (original if original is not None
                                    else _base_text(pages_dir, line_id)),
                       "corrected": corrected}],
        }},
        "exported": f"{DATE}T10:15:00Z",
        "source": "docta-viewer",
    }
    path = tmp / f"review-{DOC}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def test_review_becomes_a_run_and_a_verification() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        pages_dir = _register(tmp)
        ar.ingest([review_file(tmp, pages_dir)], pages_dir)
        page = _page(pages_dir)
        assert page["verification"] == {"status": "gesichtet",
                                        "reviewer": REVIEWER, "date": DATE}
        runs = [r for r in page["runs"] if r["source"] == "human"]
        assert len(runs) == 1, "expected exactly one review run"
        run = runs[0]
        assert run["id"] == f"review:{DOC}-{PAGE}-{DATE}-{REVIEWER}"
        assert run["reviewer"] == REVIEWER and run["date"] == DATE
        base = next(r for r in page["runs"] if r["source"] == "transkribus")
        assert [ln["id"] for ln in run["lines"]] == \
            [ln["id"] for ln in base["lines"]], "run must carry the full page"
        corrected = {ln["id"]: ln["text"] for ln in run["lines"]}
        assert corrected["r2l1"] == "Auf dem klainen estrich"
        untouched = [ln for ln in base["lines"] if ln["id"] != "r2l1"]
        assert all(corrected[ln["id"]] == ln["text"] for ln in untouched)


def test_reapplying_the_same_review_changes_nothing() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        pages_dir = _register(tmp)
        path = review_file(tmp, pages_dir)
        ar.ingest([path], pages_dir)
        once = (pages_dir / f"{DOC}.json").read_bytes()
        ar.ingest([path], pages_dir)
        assert (pages_dir / f"{DOC}.json").read_bytes() == once, \
            "re-applying a review must be a no-op"


def test_stale_review_is_refused() -> None:
    """An export made before another change must not overwrite that change."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        pages_dir = _register(tmp)
        path = review_file(tmp, pages_dir, original="something else entirely")
        before = (pages_dir / f"{DOC}.json").read_bytes()
        try:
            ar.ingest([path], pages_dir)
        except ar.ReviewError as exc:
            assert "veraltet" in str(exc), f"unexpected refusal: {exc}"
        else:
            raise AssertionError("stale review was applied")
        assert (pages_dir / f"{DOC}.json").read_bytes() == before, \
            "register was touched by a refused review"


def test_a_later_review_builds_on_the_earlier_one() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        pages_dir = _register(tmp)
        ar.ingest([review_file(tmp, pages_dir)], pages_dir)
        second = tmp / "second.json"
        payload = json.loads((tmp / f"review-{DOC}.json").read_text("utf-8"))
        payload["pages"][str(PAGE)]["date"] = "2026-09-04"
        payload["pages"][str(PAGE)]["lines"] = [
            {"id": "r2l1", "original": "Auf dem klainen estrich",
             "corrected": "Auf dem klainen Estrich"},
        ]
        second.write_text(json.dumps(payload, ensure_ascii=False),
                          encoding="utf-8")
        ar.ingest([second], pages_dir)
        runs = [r for r in _page(pages_dir)["runs"] if r["source"] == "human"]
        assert len(runs) == 2, "a second review is a second run"
        latest = {ln["id"]: ln["text"] for ln in runs[-1]["lines"]}
        assert latest["r2l1"] == "Auf dem klainen Estrich"


def test_review_without_corrections_records_only_the_verification() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        pages_dir = _register(tmp)
        path = tmp / "plain.json"
        path.write_text(json.dumps({
            "docId": DOC, "reviewer": REVIEWER,
            "pages": {str(PAGE): {"status": "abgenommen", "date": DATE,
                                  "lines": []}},
            "exported": f"{DATE}T10:15:00Z", "source": "docta-viewer",
        }), encoding="utf-8")
        ar.ingest([path], pages_dir)
        page = _page(pages_dir)
        assert page["verification"]["status"] == "abgenommen"
        assert not [r for r in page["runs"] if r["source"] == "human"]


def test_contract_violations_are_refused() -> None:
    """Every field of the export contract is checked before anything is written."""
    good = {"docId": DOC, "reviewer": REVIEWER,
            "pages": {str(PAGE): {"status": "gesichtet", "date": DATE,
                                  "lines": [{"id": "r2l1", "original": "a",
                                             "corrected": "b"}]}},
            "exported": f"{DATE}T10:15:00Z", "source": "docta-viewer"}
    ar.validate(good, "fixture")  # the fixture itself must pass

    def broken(**changes: object) -> dict:
        return {**good, **changes}

    page = good["pages"][str(PAGE)]
    cases = [
        broken(source="elsewhere"),
        broken(docId="11327963"),
        broken(reviewer=""),
        broken(pages=[]),
        broken(pages={"one": page}),
        broken(pages={str(PAGE): {**page, "status": "maschinell"}}),
        broken(pages={str(PAGE): {**page, "date": "03.09.2026"}}),
        broken(pages={str(PAGE): {**page, "lines": "none"}}),
        broken(pages={str(PAGE): {**page, "lines": [{"id": "r2l1"}]}}),
        broken(pages={str(PAGE): {**page, "lines": [
            {"id": "r2l1", "original": "a", "corrected": "b"},
            {"id": "r2l1", "original": "b", "corrected": "c"}]}}),
    ]
    for case in cases:
        try:
            ar.validate(case, "fixture")
        except ar.ReviewError:
            continue
        raise AssertionError(f"contract violation accepted: {case}")


def test_unknown_line_and_missing_page_are_refused() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        pages_dir = _register(tmp)
        path = review_file(tmp, pages_dir, line_id="r99l99", original="x")
        try:
            ar.ingest([path], pages_dir)
        except ar.ReviewError as exc:
            assert "steht nicht im Register" in str(exc)
        else:
            raise AssertionError("unknown line was accepted")

        payload = json.loads(path.read_text("utf-8"))
        payload["pages"] = {"9999": payload["pages"][str(PAGE)]}
        payload["pages"]["9999"]["lines"] = []
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        try:
            ar.ingest([path], pages_dir)
        except ar.ReviewError as exc:
            assert "fehlt im Register" in str(exc)
        else:
            raise AssertionError("unknown page was accepted")


def test_a_directory_is_ingested_and_dry_run_writes_nothing() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        pages_dir = _register(tmp)
        folder = tmp / "reviews"
        folder.mkdir()
        path = review_file(tmp, pages_dir)
        path.rename(folder / path.name)
        before = (pages_dir / f"{DOC}.json").read_bytes()
        assert ar.ingest([folder], pages_dir, dry_run=True), "no log produced"
        assert (pages_dir / f"{DOC}.json").read_bytes() == before
        ar.ingest([folder], pages_dir)
        assert _page(pages_dir)["verification"]["status"] == "gesichtet"


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
