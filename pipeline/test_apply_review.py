"""Tests for the review ingest.

The repository holds no review export, so the input is a fixture export built
against a temporary copy of the real register.

Usage:
  pytest pipeline/test_apply_review.py
"""

import copy
import json
import re
import tempfile
from pathlib import Path

import apply_review as ar
import build_register as br
import pytest
from io_paths import load_json, write_json

DOC = 11327963
PAGE = 2
REVIEWER = "XY"
DATE = "2026-09-03"


def _register(tmp: Path) -> Path:
    """A fresh register below tmp; returns its pages directory."""
    br.build(tmp)
    return tmp / "pages"


def _page(pages_dir: Path, page_nr: int = PAGE) -> dict:
    payload = load_json(pages_dir / f"{DOC}.json")
    return next(p for p in payload["pages"] if p["pageNr"] == page_nr)


def _base_text(pages_dir: Path, line_id: str) -> str:
    page = _page(pages_dir)
    run = next(r for r in page["runs"] if r["source"] == "transkribus")
    return next(ln["text"] for ln in run["lines"] if ln["id"] == line_id)


def review_file(
    tmp: Path,
    pages_dir: Path,
    line_id: str = "r2l1",
    corrected: str = "Auf dem klainen estrich",
    original: str | None = None,
    status: str | None = "gesichtet",
) -> Path:
    """One viewer export against the current base text of the register."""
    payload = {
        "docId": DOC,
        "reviewer": REVIEWER,
        "pages": {
            str(PAGE): {
                "status": status,
                "date": DATE,
                "lines": [
                    {
                        "id": line_id,
                        "original": (
                            original
                            if original is not None
                            else _base_text(pages_dir, line_id)
                        ),
                        "corrected": corrected,
                    }
                ],
            }
        },
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
        assert page["verification"] == {
            "status": "gesichtet",
            "reviewer": REVIEWER,
            "date": DATE,
        }
        runs = [r for r in page["runs"] if r["source"] == "human"]
        assert len(runs) == 1, "expected exactly one review run"
        run = runs[0]
        assert run["id"] == f"review:{DOC}-{PAGE}-{DATE}-{REVIEWER}"
        assert run["reviewer"] == REVIEWER and run["date"] == DATE
        base = next(r for r in page["runs"] if r["source"] == "transkribus")
        assert [ln["id"] for ln in run["lines"]] == [
            ln["id"] for ln in base["lines"]
        ], "run must carry the full page"
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
        assert (pages_dir / f"{DOC}.json").read_bytes() == once, (
            "re-applying a review must be a no-op"
        )


def test_stale_review_is_refused() -> None:
    """An export made before another change must not overwrite that change."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        pages_dir = _register(tmp)
        path = review_file(tmp, pages_dir, original="something else entirely")
        before = (pages_dir / f"{DOC}.json").read_bytes()
        # The stale refusal is the one that quotes the reading the export
        # reported; matching that value, not the wording, keeps the check
        # independent of the message language.
        with pytest.raises(
            ar.ReviewError, match=re.escape(repr("something else entirely"))
        ):
            ar.ingest([path], pages_dir)
        assert (pages_dir / f"{DOC}.json").read_bytes() == before, (
            "register was touched by a refused review"
        )


def test_a_refused_file_blocks_the_whole_batch() -> None:
    """Ingest is all-or-nothing across files: nothing is written before every
    file of the batch has validated and applied in memory."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        pages_dir = _register(tmp)
        good = review_file(tmp, pages_dir)
        bad_dir = tmp / "bad"
        bad_dir.mkdir()
        bad = review_file(bad_dir, pages_dir, original="something else entirely")
        before = (pages_dir / f"{DOC}.json").read_bytes()
        try:
            ar.ingest([good, bad], pages_dir)
        except ar.ReviewError:
            pass
        else:
            raise AssertionError("stale file was accepted")
        assert (pages_dir / f"{DOC}.json").read_bytes() == before, (
            "an earlier file of a refused batch was written"
        )


def test_one_stale_page_refuses_the_whole_file() -> None:
    """Refusal is per file, not per page. The valid page of the same export is
    not written either, so a rerun after the fix has nothing to unpick."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        pages_dir = _register(tmp)
        path = tmp / f"review-{DOC}.json"
        path.write_text(
            json.dumps(
                {
                    "docId": DOC,
                    "reviewer": REVIEWER,
                    "pages": {
                        str(PAGE): {
                            "status": "gesichtet",
                            "date": DATE,
                            "lines": [
                                {
                                    "id": "r2l1",
                                    "original": _base_text(pages_dir, "r2l1"),
                                    "corrected": "Auf dem klainen estrich",
                                }
                            ],
                        },
                        "3": {
                            "status": "abgenommen",
                            "date": DATE,
                            "lines": [
                                {
                                    "id": "r1l1",
                                    "original": "eine ueberholte Lesung",
                                    "corrected": "[fol. 2r]",
                                }
                            ],
                        },
                    },
                    "exported": f"{DATE}T10:15:00Z",
                    "source": "docta-viewer",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        before = (pages_dir / f"{DOC}.json").read_bytes()
        # Only page 3 reports this reading, so the quoted value names the page.
        with pytest.raises(
            ar.ReviewError, match=re.escape(repr("eine ueberholte Lesung"))
        ):
            ar.ingest([path], pages_dir)
        assert (pages_dir / f"{DOC}.json").read_bytes() == before, (
            "the valid page of a refused file was written"
        )
        assert _page(pages_dir)["verification"] == {"status": "unbearbeitet"}


def test_a_later_review_builds_on_the_earlier_one() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        pages_dir = _register(tmp)
        ar.ingest([review_file(tmp, pages_dir)], pages_dir)
        second = tmp / "second.json"
        payload = json.loads((tmp / f"review-{DOC}.json").read_text("utf-8"))
        payload["pages"][str(PAGE)]["date"] = "2026-09-04"
        payload["pages"][str(PAGE)]["lines"] = [
            {
                "id": "r2l1",
                "original": "Auf dem klainen estrich",
                "corrected": "Auf dem klainen Estrich",
            },
        ]
        second.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
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
        path.write_text(
            json.dumps(
                {
                    "docId": DOC,
                    "reviewer": REVIEWER,
                    "pages": {
                        str(PAGE): {"status": "abgenommen", "date": DATE, "lines": []}
                    },
                    "exported": f"{DATE}T10:15:00Z",
                    "source": "docta-viewer",
                }
            ),
            encoding="utf-8",
        )
        ar.ingest([path], pages_dir)
        page = _page(pages_dir)
        assert page["verification"]["status"] == "abgenommen"
        assert not [r for r in page["runs"] if r["source"] == "human"]


def test_text_change_without_decision_reopens_an_approved_page() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        pages_dir = _register(tmp)
        approved = review_file(tmp, pages_dir, status="abgenommen")
        ar.ingest([approved], pages_dir)
        payload = load_json(approved)
        payload["pages"][str(PAGE)]["date"] = "2026-09-04"
        payload["pages"][str(PAGE)]["status"] = None
        payload["pages"][str(PAGE)]["lines"][0] = {
            "id": "r2l1",
            "original": "Auf dem klainen estrich",
            "corrected": "Auf dem klainen Estrich",
        }
        changed = tmp / "changed.json"
        changed.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        ar.ingest([changed], pages_dir)
        assert _page(pages_dir)["verification"] == {
            "status": "gesichtet",
            "reviewer": REVIEWER,
            "date": "2026-09-04",
            "reason": "review-reopened-after-text-change",
        }


def test_contract_violations_are_refused() -> None:
    """Every field of the export contract is checked before anything is written."""
    good = {
        "docId": DOC,
        "reviewer": REVIEWER,
        "pages": {
            str(PAGE): {
                "status": "gesichtet",
                "date": DATE,
                "lines": [{"id": "r2l1", "original": "a", "corrected": "b"}],
            }
        },
        "exported": f"{DATE}T10:15:00Z",
        "source": "docta-viewer",
    }
    ar.validate(good, "fixture")  # the fixture itself must pass

    def broken(**changes: object) -> dict:
        return {**good, **changes}

    page = good["pages"][str(PAGE)]
    cases = [
        broken(source="elsewhere"),
        broken(docId="11327963"),
        broken(reviewer=""),
        broken(schemaVersion=2, exported="not-a-timestamp"),
        broken(schemaVersion=2, exported=f"{DATE}T10:15:00"),
        broken(pages=[]),
        broken(pages={"one": page}),
        broken(pages={str(PAGE): {**page, "status": "maschinell"}}),
        # the key must be there; apply_document reads it and null is a decision
        broken(pages={str(PAGE): {k: v for k, v in page.items() if k != "status"}}),
        broken(pages={str(PAGE): {**page, "date": "03.09.2026"}}),
        broken(pages={str(PAGE): {**page, "lines": "none"}}),
        broken(pages={str(PAGE): {**page, "lines": [{"id": "r2l1"}]}}),
        broken(effort={"activeSeconds": float("nan"), "decisionCount": 1}),
        broken(
            pages={
                str(PAGE): {
                    **page,
                    "lines": [
                        {"id": "r2l1", "original": "a", "corrected": "b"},
                        {"id": "r2l1", "original": "b", "corrected": "c"},
                    ],
                }
            }
        ),
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
        with pytest.raises(ar.ReviewError, match=r"\br99l99\b") as refused:
            ar.ingest([path], pages_dir)
        # Refused as unknown, before any comparison with a reported original.
        assert repr("x") not in str(refused.value)

        payload = json.loads(path.read_text("utf-8"))
        payload["pages"] = {"9999": payload["pages"][str(PAGE)]}
        payload["pages"]["9999"]["lines"] = []
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        with pytest.raises(ar.ReviewError, match=r"\b9999\b"):
            ar.ingest([path], pages_dir)


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


def test_a_malformed_export_is_refused_as_a_review_error() -> None:
    """A broken export is a contract violation like any other, not a traceback."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        pages_dir = _register(tmp)
        path = tmp / "broken.json"
        path.write_text('{"docId": 11327963, "pages":', encoding="utf-8")
        before = (pages_dir / f"{DOC}.json").read_bytes()
        with pytest.raises(ar.ReviewError, match=re.escape(path.name)) as refused:
            ar.ingest([path], pages_dir)
        assert isinstance(refused.value.__cause__, json.JSONDecodeError)
        assert (pages_dir / f"{DOC}.json").read_bytes() == before


EDITION_DOC = 12593450  # A 024.1, transcribed by DoCTA itself, no Transkribus run


def test_an_edition_run_is_the_review_base_of_a_document_docta_transcribed() -> None:
    """A document of the edition track carries no Transkribus run, so its newest
    edition run is what a correction is written against; without that fallback
    exactly those documents could not be reviewed with corrections at all."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        pages_dir = _register(tmp)
        register = load_json(pages_dir / f"{EDITION_DOC}.json")
        page = next(p for p in register["pages"] if br.edition_runs(p))
        assert not [r for r in page["runs"] if r["source"] == "transkribus"]
        run = br.newest_edition_run(page)
        assert ar.base_lines(page, "review:none") == run["lines"]

        line = run["lines"][0]
        path = tmp / f"review-{EDITION_DOC}.json"
        path.write_text(
            json.dumps(
                {
                    "docId": EDITION_DOC,
                    "reviewer": REVIEWER,
                    "pages": {
                        str(page["pageNr"]): {
                            "status": "gesichtet",
                            "date": DATE,
                            "lines": [
                                {
                                    "id": line["id"],
                                    "original": line["text"],
                                    "corrected": "korrigierte Lesung",
                                }
                            ],
                        }
                    },
                    "exported": f"{DATE}T10:15:00Z",
                    "source": "docta-viewer",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        ar.ingest([path], pages_dir)
        written = next(
            p
            for p in load_json(pages_dir / f"{EDITION_DOC}.json")["pages"]
            if p["pageNr"] == page["pageNr"]
        )
        review = br.newest_review_run(written)
        assert review is not None, "no review run was written"
        assert [ln["id"] for ln in review["lines"]] == [
            ln["id"] for ln in run["lines"]
        ], "the review run must carry the full page"
        assert review["lines"][0]["text"] == "korrigierte Lesung"
        assert written["verification"]["status"] == "gesichtet"


@pytest.mark.parametrize("legacy", [False, True])
def test_older_event_replay_preserves_later_reading_and_verification(
    tmp_path: Path, legacy: bool
) -> None:
    """Replay real source corrections without undoing later editorial work."""
    pages = _register(tmp_path)
    first = review_file(tmp_path, pages)
    initial = load_json(first)
    initial["schemaVersion"] = 2
    write_json(first, initial)
    ar.ingest([first], pages)
    later = copy.deepcopy(initial)
    later["exported"] = "2026-09-04T10:15:00Z"
    later["pages"][str(PAGE)].update(date="2026-09-04", status="abgenommen")
    later["pages"][str(PAGE)]["lines"][0].update(
        original=initial["pages"][str(PAGE)]["lines"][0]["corrected"],
        corrected="Auf dem klainen Estrich",
    )
    second = tmp_path / "second.json"
    second.write_text(json.dumps(later), encoding="utf-8")
    ar.ingest([second], pages)
    path = pages / f"{DOC}.json"
    if legacy:
        register = load_json(path)
        for page in register["pages"]:
            for run in br.review_runs(page):
                run.pop("reviewDigest", None)
                run.pop("timestamp", None)
        path.write_text(json.dumps(register), encoding="utf-8")
    # Use canonical serialization so the replay check measures state changes.
    write_json(path, load_json(path))
    before = path.read_bytes()
    ar.ingest([first, second], pages)
    assert path.read_bytes() == before
    page = _page(pages)
    assert page["verification"]["status"] == "abgenommen"
    assert (
        next(
            line["text"]
            for line in br.newest_review_run(page)["lines"]
            if line["id"] == initial["pages"][str(PAGE)]["lines"][0]["id"]
        )
        == "Auf dem klainen Estrich"
    )


@pytest.mark.parametrize(
    "field,value", [("corrected", "different reading"), ("original", "different base")]
)
def test_existing_review_identity_rejects_changed_correction(
    tmp_path: Path, field: str, value: str
) -> None:
    pages = _register(tmp_path)
    event = review_file(tmp_path, pages)
    ar.ingest([event], pages)
    before = (pages / f"{DOC}.json").read_bytes()
    changed = load_json(event)
    changed["pages"][str(PAGE)]["lines"][0][field] = value
    event.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(ar.ReviewError, match="changed content"):
        ar.ingest([event], pages)
    assert (pages / f"{DOC}.json").read_bytes() == before


@pytest.mark.parametrize("same_day", [False, True])
def test_status_only_replay_cannot_reapprove_a_changed_reading(
    tmp_path: Path, same_day: bool
) -> None:
    """Replay a genuine approval export after a later real-source correction."""
    pages = _register(tmp_path)
    correction = review_file(tmp_path, pages, status=None)
    changed = load_json(correction)
    approved = copy.deepcopy(changed)
    approved["pages"][str(PAGE)].update(status="abgenommen", lines=[])
    if same_day:
        approved["schemaVersion"] = changed["schemaVersion"] = 2
    else:
        changed["pages"][str(PAGE)]["date"] = "2026-09-04"
    changed["exported"] = "2026-09-03T11:15:00Z" if same_day else "2026-09-04T11:15:00Z"
    approval = tmp_path / "approval.json"
    write_json(approval, approved)
    write_json(correction, changed)
    ar.ingest([approval], pages)
    ar.ingest([correction], pages)
    path = pages / f"{DOC}.json"
    before = path.read_bytes()
    log = ar.ingest([approval], pages)
    assert any("older page decision skipped" in entry for entry in log)
    assert path.read_bytes() == before
    assert _page(pages)["verification"]["status"] == "gesichtet"


def test_same_day_legacy_approval_after_correction_requires_clear_chronology(
    tmp_path: Path,
) -> None:
    """A date alone cannot establish whether approval covered the saved reading."""
    pages = _register(tmp_path)
    correction = review_file(tmp_path, pages, status=None)
    approved = load_json(correction)
    approved["pages"][str(PAGE)].update(status="abgenommen", lines=[])
    approval = tmp_path / "approval.json"
    write_json(approval, approved)
    ar.ingest([approval], pages)
    ar.ingest([correction], pages)
    path = pages / f"{DOC}.json"
    before = path.read_bytes()
    with pytest.raises(ar.ReviewError, match="ambiguous same-day"):
        ar.ingest([approval], pages)
    assert path.read_bytes() == before


def test_later_same_day_approval_can_accept_saved_correction(tmp_path: Path) -> None:
    pages = _register(tmp_path)
    correction = review_file(tmp_path, pages, status=None)
    changed = load_json(correction)
    changed["schemaVersion"] = 2
    write_json(correction, changed)
    ar.ingest([correction], pages)
    approved = copy.deepcopy(changed)
    approved["exported"] = "2026-09-03T11:15:00Z"
    approved["pages"][str(PAGE)].update(status="abgenommen", lines=[])
    approval = tmp_path / "approval.json"
    write_json(approval, approved)
    ar.ingest([approval], pages)
    path = pages / f"{DOC}.json"
    before = path.read_bytes()
    ar.ingest([approval], pages)
    assert path.read_bytes() == before
    assert _page(pages)["verification"]["status"] == "abgenommen"


def _minimal(pages: dict, **extra: object) -> dict:
    return {
        "docId": DOC,
        "reviewer": REVIEWER,
        "exported": f"{DATE}T10:15:00Z",
        "source": "docta-viewer",
        "pages": pages,
        **extra,
    }


@pytest.mark.parametrize(
    "date",
    [
        "2026-09-03\n",
        "2026-13-45",
        "2026-02-30",
        "".join(chr(0xFF10 + int(c)) for c in "2026") + "-09-03",
    ],
)
def test_an_impossible_or_padded_date_is_refused(date: str) -> None:
    with pytest.raises(ar.ReviewError):
        ar.validate(_minimal({"2": {"status": None, "date": date, "lines": []}}), "x")


def test_page_keys_naming_one_page_twice_are_refused() -> None:
    page = {"status": "gesichtet", "date": DATE, "lines": []}
    with pytest.raises(ar.ReviewError):
        ar.validate(_minimal({"2": page, "02": dict(page)}), "x")


def test_a_lone_surrogate_in_an_export_is_a_review_error() -> None:
    page = {
        "status": None,
        "date": DATE,
        "lines": [{"id": "r2l1", "original": "a", "corrected": "\ud800"}],
    }
    with pytest.raises(ar.ReviewError):
        ar.validate(_minimal({"2": page}), "x")


def test_an_unencodable_register_refuses_the_batch_before_any_write(
    tmp_path: Path,
) -> None:
    pages_dir = _register(tmp_path)
    other = 11328300
    first = review_file(tmp_path, pages_dir)
    second = tmp_path / f"review-{other}.json"
    second.write_text(
        json.dumps(
            {
                **_minimal({"1": {"status": "gesichtet", "date": DATE, "lines": []}}),
                "docId": other,
            }
        ),
        encoding="utf-8",
    )
    broken = load_json(pages_dir / f"{other}.json")
    broken["pages"][0]["runs"][0]["lines"][0]["text"] = "\ud800"
    (pages_dir / f"{other}.json").write_text(json.dumps(broken), encoding="utf-8")
    before = (pages_dir / f"{DOC}.json").read_bytes()
    with pytest.raises(ar.ReviewError):
        ar.ingest([first, second], pages_dir)
    assert (pages_dir / f"{DOC}.json").read_bytes() == before


def _exclusion(tmp: Path, pages_dir: Path, excluded: bool, date: str) -> Path:
    """An export that excludes or restores r2l1 without touching its text."""
    text = _base_text(pages_dir, "r2l1")
    path = tmp / f"exclude-{date}.json"
    payload = _minimal(
        {
            str(PAGE): {
                "status": None,
                "date": date,
                "lines": [
                    {
                        "id": "r2l1",
                        "original": text,
                        "corrected": text,
                        "excluded": excluded,
                    }
                ],
            }
        },
        schemaVersion=2,
        exported=f"{date}T10:15:00Z",
    )
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def test_an_excluded_line_leaves_the_text_and_can_be_restored() -> None:
    """Exclusion keeps the line, its id and its reading; restoring is a correction."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        pages_dir = _register(tmp)
        text = _base_text(pages_dir, "r2l1")
        ar.ingest([_exclusion(tmp, pages_dir, True, "2026-09-04")], pages_dir)
        run = br.newest_review_run(_page(pages_dir))
        saved = {ln["id"]: ln for ln in run["lines"]}
        assert saved["r2l1"] == {"id": "r2l1", "text": text, "excluded": True}
        assert all("excluded" not in ln for i, ln in saved.items() if i != "r2l1"), (
            "lines never excluded keep the shape they always had"
        )
        effective = br.transcription_of(DOC, pages_dir)
        page = next(p for p in effective["pages"] if p["pageNr"] == PAGE)
        line = next(ln for ln in br.iter_lines(page) if ln["id"] == "r2l1")
        assert line["excluded"] and line["corrected"] and line["text"] == text
        assert page["changedLines"] == 1, "an exclusion counts as a changed line"

        ar.ingest([_exclusion(tmp, pages_dir, False, "2026-09-05")], pages_dir)
        run = br.newest_review_run(_page(pages_dir))
        assert all("excluded" not in ln for ln in run["lines"])
        effective = br.transcription_of(DOC, pages_dir)
        page = next(p for p in effective["pages"] if p["pageNr"] == PAGE)
        assert page["changedLines"] == 0


def test_a_text_correction_keeps_an_earlier_exclusion() -> None:
    """A correction without the flag leaves the line's exclusion as it was."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        pages_dir = _register(tmp)
        ar.ingest([_exclusion(tmp, pages_dir, True, "2026-09-04")], pages_dir)
        payload = json.loads((tmp / "exclude-2026-09-04.json").read_text("utf-8"))
        payload["pages"][str(PAGE)]["date"] = "2026-09-05"
        payload["exported"] = "2026-09-05T10:15:00Z"
        payload["pages"][str(PAGE)]["lines"] = [
            {
                "id": "r2l2",
                "original": _base_text(pages_dir, "r2l2"),
                "corrected": "changed",
            },
        ]
        later = tmp / "later.json"
        later.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        ar.ingest([later], pages_dir)
        saved = {ln["id"]: ln for ln in br.newest_review_run(_page(pages_dir))["lines"]}
        assert saved["r2l1"].get("excluded") is True
        assert saved["r2l2"]["text"] == "changed"


def test_a_non_boolean_exclusion_is_refused() -> None:
    lines = [{"id": "r2l1", "original": "a", "corrected": "a", "excluded": "yes"}]
    data = _minimal({str(PAGE): {"status": None, "date": DATE, "lines": lines}})
    with pytest.raises(ar.ReviewError, match="excluded"):
        ar.validate(data, "test")
