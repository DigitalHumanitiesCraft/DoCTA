"""Exercise registry persistence against copied real inventory register pages."""

import copy
import json
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import local_annotations as annotations
import local_editor as editor
import local_registry as registry
import pytest
from io_paths import PIPELINE_DIR, load_json, write_json

DOC = 11327963


@pytest.fixture
def pages(tmp_path: Path) -> Path:
    path = tmp_path / "pages"
    path.mkdir()
    shutil.copy2(PIPELINE_DIR / "pages" / f"{DOC}.json", path)
    return path


def save(pages: Path, action: str, **fields: object) -> dict:
    return registry.save_registry(
        {
            "baseRevision": registry.read_registry(pages)["revision"],
            "reviewer": "XY",
            "action": action,
            **fields,
        },
        pages,
    )


def entry(kind: str = "person", **fields: object) -> dict:
    source = load_json(PIPELINE_DIR / "pages" / f"{DOC}.json")
    label = source["pages"][0]["runs"][0]["lines"][3]["text"]
    return {"kind": kind, "label": label, "aliases": [], **fields}


def mention(pages: Path, **fields: object) -> dict:
    ((page_nr, line_id), text) = next(iter(annotations._lines(DOC, pages).items()))
    return {
        "docId": DOC,
        "pageNr": page_nr,
        "lineId": line_id,
        "start": 0,
        "end": len(text.encode("utf-16-le")) // 2,
        "quote": text,
        "textDigest": annotations.line_digest(text),
        "entryId": None,
        "kind": "person",
        **fields,
    }


def test_same_labels_stay_distinct_and_history_survives(pages: Path) -> None:
    first = save(pages, "save-entry", entry=entry())["entries"][0]
    saved = save(pages, "save-entry", entry=entry())
    assert len(saved["entries"]) == 2
    assert len({record["id"] for record in saved["entries"]}) == 2
    saved = save(pages, "save-entry", entry={**first, "note": "editorial note"})
    event = saved["history"][-1]
    assert event["before"] == first
    assert event["after"]["note"] == "editorial note"
    assert event["actor"] == "XY"
    assert event["timestamp"].endswith("Z")
    assert registry.read_registry(pages) == saved
    assert not (pages.parent / "entity_index.json").exists()


def test_term_hierarchy_rejects_cycles_and_wrong_kind(pages: Path) -> None:
    first = save(pages, "save-entry", entry=entry("term"))["entries"][0]
    second = save(pages, "save-entry", entry=entry("term", broaderId=first["id"]))[
        "entries"
    ][-1]
    with pytest.raises(ValueError, match="cycle"):
        save(pages, "save-entry", entry={**first, "broaderId": second["id"]})
    with pytest.raises(ValueError, match="only a term"):
        save(pages, "save-entry", entry=entry(broaderId=first["id"]))
    with pytest.raises(ValueError, match="unknown broader"):
        save(pages, "save-entry", entry=entry("term", broaderId=str(uuid4())))


def test_mentions_link_explicitly_and_preserve_deleted_history(pages: Path) -> None:
    person = save(pages, "save-entry", entry=entry())["entries"][0]
    unresolved = save(pages, "save-mention", mention=mention(pages))["mentions"][0]
    assert unresolved["entryId"] is None
    resolved = save(
        pages, "save-mention", mention={**unresolved, "entryId": person["id"]}
    )
    assert resolved["mentions"][0]["entryId"] == person["id"]
    assert resolved["mentions"][0]["stale"] is False
    term = save(pages, "save-entry", entry=entry("term"))["entries"][-1]
    with pytest.raises(ValueError, match="same kind"):
        save(pages, "save-mention", mention={**unresolved, "entryId": term["id"]})
    result = save(pages, "remove-mention", id=unresolved["id"])
    assert result["mentions"] == []
    assert result["history"][-1]["after"] is None
    assert result["history"][-1]["before"]["entryId"] == person["id"]


def test_source_change_marks_stale_without_moving_and_rejects_save(pages: Path) -> None:
    saved = save(pages, "save-mention", mention=mention(pages))
    record = saved["mentions"][0]
    document = editor.document_payload(DOC, pages)
    editor.save_review(
        {
            "docId": DOC,
            "baseRevision": document["revision"],
            "reviewer": "XY",
            "pages": {
                str(record["pageNr"]): {
                    "date": "2026-09-21",
                    "status": None,
                    "lines": [
                        {
                            "id": record["lineId"],
                            "original": record["quote"],
                            "corrected": "",
                        }
                    ],
                }
            },
        },
        pages,
        pages.parent / "reviews",
    )
    current = registry.read_registry(pages)
    assert current["mentions"][0] == {**record, "stale": True}
    assert current["revision"] == saved["revision"]
    with pytest.raises(RuntimeError, match="source"):
        save(pages, "save-mention", mention={**record, "note": "changed"})
    provenance = editor.document_payload(DOC, pages)["pages"][0]["provenance"]
    assert provenance["originalRuns"][0]["source"] == "transkribus"
    assert provenance["originalRuns"][0]["model"] is None
    assert provenance["humanCorrections"][-1]["reviewer"] == "XY"
    assert "T" in provenance["humanCorrections"][-1]["timestamp"]
    assert provenance["originalRunId"] == "transkribus"
    assert "prompt_hash" in provenance["originalRuns"][0]


@pytest.mark.parametrize(
    "fields",
    [
        {"start": -1},
        {"end": 100000},
        {"lineId": "missing"},
        {"quote": "different"},
        {"textDigest": "0" * 64},
        {"pageNr": True},
        {"entryId": "not-a-uuid"},
        {"kind": []},
    ],
)
def test_invalid_mention_cannot_create_file(pages: Path, fields: dict) -> None:
    with pytest.raises((ValueError, RuntimeError)):
        save(pages, "save-mention", mention=mention(pages, **fields))
    assert not (pages.parent / "registry" / "index.json").exists()


def test_utf16_boundaries() -> None:
    """Astral characters are a Unicode boundary fixture, not historical evidence."""
    assert registry.utf16_slice("A\U0001f600B", 1, 3) == "\U0001f600"
    assert registry.utf16_slice("A\U0001f600B", 3, 4) == "B"
    for start, end in ((1, 2), (2, 3), (0, 5), (True, 3)):
        with pytest.raises(ValueError):
            registry.utf16_slice("A\U0001f600B", start, end)


def test_concurrent_registry_writes_accept_one(pages: Path) -> None:
    payload = {
        "baseRevision": registry.read_registry(pages)["revision"],
        "reviewer": "XY",
        "action": "save-entry",
        "entry": entry(),
    }

    def attempt(_: int) -> str:
        try:
            registry.save_registry(copy.deepcopy(payload), pages)
        except RuntimeError:
            return "conflict"
        return "saved"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(attempt, range(2))) == ["conflict", "saved"]
    assert len(registry.read_registry(pages)["history"]) == 1


@pytest.mark.parametrize(
    "contents",
    ["{", "[]", '{"schemaVersion":1,"entries":[],"mentions":[],"history":[{}]}'],
)
def test_corrupt_registry_is_not_replaced(pages: Path, contents: str) -> None:
    path = pages.parent / "registry" / "index.json"
    path.parent.mkdir()
    path.write_text(contents, encoding="utf-8")
    with pytest.raises(ValueError):
        registry.read_registry(pages)
    with pytest.raises(ValueError):
        registry.save_registry({}, pages)
    assert path.read_text(encoding="utf-8") == contents


def test_atomic_failure_keeps_state_and_history(
    pages: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = save(pages, "save-entry", entry=entry())

    def fail(*args: object, **kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(registry, "write_json", fail)
    with pytest.raises(OSError):
        save(pages, "save-entry", entry=entry())
    assert registry.read_registry(pages) == original


def test_legacy_annotation_save_adds_audit_only_on_change(
    pages: Path, tmp_path: Path
) -> None:
    extraction = load_json(PIPELINE_DIR.parent / "docs/data/entities/11328300.json")
    doc = extraction["docId"]
    shutil.copy2(PIPELINE_DIR / "pages" / f"{doc}.json", pages)
    source = extraction["entities"][0]
    text = annotations._lines(doc, pages)[(source["pageNr"], source["lineId"])]
    decision = {
        "id": source["id"],
        "kind": source["type"],
        "status": "pending",
        "normalized": source["normalized"],
        "textDigest": annotations.line_digest(text),
    }
    sidecars = tmp_path / "annotations"
    path = sidecars / f"{doc}.json"
    write_json(path, {"docId": doc, "decisions": [decision]})
    before = path.read_bytes()
    current = annotations.read_decisions(doc, sidecars)
    assert current["history"] == []
    assert path.read_bytes() == before
    payload = {
        "docId": doc,
        "baseRevision": current["revision"],
        "decisions": [{**decision, "status": "accepted"}],
    }
    with pytest.raises(ValueError, match="reviewer"):
        annotations.save_decisions(payload, pages, sidecars)
    saved = annotations.save_decisions({**payload, "reviewer": "XY"}, pages, sidecars)
    assert saved["history"][-1]["before"] == decision
    assert saved["history"][-1]["after"]["status"] == "accepted"
    again = annotations.save_decisions(
        {
            "docId": doc,
            "baseRevision": saved["revision"],
            "decisions": saved["decisions"],
        },
        pages,
        sidecars,
    )
    assert again["history"] == saved["history"]
    assert json.loads(path.read_text(encoding="utf-8"))["history"] == saved["history"]
