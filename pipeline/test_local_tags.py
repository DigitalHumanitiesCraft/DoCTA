"""Persistence and staleness checks for manual research tags."""

import copy
import tempfile
from pathlib import Path

import apply_review as ar
import build_register as br
import local_tags as lt
from io_paths import load_json, write_json

DOC = 11327963
PAGE = 2


def _fixture(tmp: Path) -> tuple[Path, Path]:
    br.build(tmp)
    return tmp / "pages", tmp / "tags"


def _add_payload(register: Path, tags: Path, line_id: str | None) -> dict:
    current = lt.read_tags(DOC, register, tags)
    return {
        "docId": DOC,
        "baseRevision": current["revision"],
        "sourceRevision": current["sourceRevision"],
        "action": "add",
        "tag": {
            "pageNr": PAGE,
            "lineId": line_id,
            "tag": "Arbeitsbegriff",
            "note": "Prüfnotiz",
            "reviewer": "XY",
        },
    }


def _first_line(register: Path) -> dict:
    transcription = br.transcription_of(DOC, register)
    page = next(page for page in transcription["pages"] if page["pageNr"] == PAGE)
    return page["regions"][0]["lines"][0]


def _change_line(register: Path, line: dict) -> None:
    payload = {
        "docId": DOC,
        "reviewer": "XY",
        "pages": {
            str(PAGE): {
                "status": None,
                "date": "2026-09-21",
                "lines": [
                    {
                        "id": line["id"],
                        "original": line["text"],
                        "corrected": f"{line['text']} korrigiert",
                    }
                ],
            }
        },
        "exported": "2026-09-21T10:00:00Z",
        "source": "docta-viewer",
        "reviewId": "tag-stale-test",
    }
    pages = ar.validate(payload, "test")
    path = register / f"{DOC}.json"
    document = load_json(path)
    ar.apply_document(document, payload, pages, "test")
    write_json(path, document)


def test_line_and_page_tags_persist_and_become_stale_after_text_change() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        register, tags = _fixture(tmp)
        before = (register / f"{DOC}.json").read_bytes()
        line = _first_line(register)
        first = lt.save_tags(_add_payload(register, tags, line["id"]), register, tags)
        second_payload = _add_payload(register, tags, None)
        second_payload["baseRevision"] = first["revision"]
        second = lt.save_tags(second_payload, register, tags)
        assert len(second["tags"]) == 2
        assert all(not tag["stale"] for tag in second["tags"])
        assert (register / f"{DOC}.json").read_bytes() == before

        _change_line(register, line)
        stale = lt.read_tags(DOC, register, tags)
        assert all(tag["stale"] for tag in stale["tags"])

        rechecked = lt.save_tags(
            {
                "docId": DOC,
                "baseRevision": stale["revision"],
                "sourceRevision": stale["sourceRevision"],
                "action": "recheck",
                "id": stale["tags"][0]["id"],
                "reviewer": "AB",
            },
            register,
            tags,
        )
        assert rechecked["tags"][0]["stale"] is False
        assert rechecked["tags"][0]["created"] == stale["tags"][0]["created"]
        assert "updated" in rechecked["tags"][0]


def test_delete_and_strict_boundaries() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        register, tags = _fixture(tmp)
        line = _first_line(register)
        saved = lt.save_tags(_add_payload(register, tags, line["id"]), register, tags)
        deleted = lt.save_tags(
            {
                "docId": DOC,
                "baseRevision": saved["revision"],
                "sourceRevision": saved["sourceRevision"],
                "action": "delete",
                "id": saved["tags"][0]["id"],
            },
            register,
            tags,
        )
        assert deleted["tags"] == []

        cases = [
            {**_add_payload(register, tags, line["id"]), "docId": True},
            {
                **_add_payload(register, tags, line["id"]),
                "tag": {
                    **_add_payload(register, tags, line["id"])["tag"],
                    "pageNr": True,
                },
            },
            _add_payload(register, tags, "unknown"),
        ]
        for payload in cases:
            try:
                lt.save_tags(payload, register, tags)
            except (ValueError, FileNotFoundError):
                continue
            raise AssertionError(f"invalid tag payload accepted: {payload}")


def test_source_and_sidecar_cas_reject_stale_writes() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        register, tags = _fixture(tmp)
        payload = _add_payload(register, tags, _first_line(register)["id"])
        stale_sidecar = copy.deepcopy(payload)
        stale_sidecar["baseRevision"] = "0" * 64
        stale_source = copy.deepcopy(payload)
        stale_source["sourceRevision"] = "0" * 64
        for candidate, message in (
            (stale_sidecar, "stale revision"),
            (stale_source, "stale source revision"),
        ):
            try:
                lt.save_tags(candidate, register, tags)
            except RuntimeError as exc:
                assert str(exc) == message
            else:
                raise AssertionError("stale tag write accepted")


def test_misnamed_and_malformed_sidecars_fail_closed_without_changes() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        register, tags = _fixture(tmp)
        tags.mkdir()
        path = tags / f"{DOC}.json"
        source_before = (register / f"{DOC}.json").read_bytes()
        cases = [
            {"docId": DOC + 1, "tags": []},
            {"docId": DOC, "tags": {}},
            {"docId": DOC, "tags": [{"id": "broken"}]},
            {
                "docId": DOC,
                "tags": [
                    {
                        "id": "00000000-0000-4000-8000-000000000001",
                        "pageNr": 9999,
                        "lineId": "orphan",
                        "tag": "Arbeitsbegriff",
                        "note": "",
                        "reviewer": "XY",
                        "created": "2026-09-21T10:00:00Z",
                        "text": "alter Snapshot",
                        "textDigest": "0" * 64,
                    },
                    {
                        "id": "00000000-0000-4000-8000-000000000001",
                        "pageNr": 9999,
                        "lineId": None,
                        "tag": "Arbeitsbegriff",
                        "note": "",
                        "reviewer": "XY",
                        "created": "2026-09-21T10:00:00Z",
                        "text": "alter Snapshot",
                        "textDigest": "0" * 64,
                    },
                ],
            },
        ]
        for payload in cases:
            write_json(path, payload)
            before = path.read_bytes()
            try:
                lt.read_tags(DOC, register, tags)
            except ValueError:
                pass
            else:
                raise AssertionError(f"malformed sidecar accepted: {payload}")
            assert path.read_bytes() == before
            assert (register / f"{DOC}.json").read_bytes() == source_before
        orphan = {
            "docId": DOC,
            "tags": [
                {
                    "id": "00000000-0000-4000-8000-000000000002",
                    "pageNr": 9999,
                    "lineId": "missing-line",
                    "tag": "Arbeitsbegriff",
                    "note": "",
                    "reviewer": "XY",
                    "created": "2026-09-21T10:00:00Z",
                    "text": "alter Snapshot",
                    "textDigest": "0" * 64,
                }
            ],
        }
        write_json(path, orphan)
        assert lt.read_tags(DOC, register, tags)["tags"][0]["stale"] is True
