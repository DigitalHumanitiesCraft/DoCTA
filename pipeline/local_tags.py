"""Persist manual research tags against effective transcription snapshots.

Tags are working annotations, separate from formal entity decisions and from
TEI/graph publication. Page anchors snapshot all effective lines joined by LF;
line anchors snapshot exactly one effective line. Optimistic revisions and the
shared review lock prevent edits from crossing transcription changes.
"""

from __future__ import annotations

import copy
import hashlib
import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import apply_review as ar
import build_register as br
from io_paths import PIPELINE_DIR, load_json, write_json

TAGS = PIPELINE_DIR / "tags"
DIGEST = re.compile(r"^[0-9a-f]{64}$")


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _revision(path: Path) -> str:
    return hashlib.sha256(path.read_bytes() if path.exists() else b"").hexdigest()


def _source_revision(doc_id: int, register_dir: Path) -> str:
    path = register_dir / f"{doc_id}.json"
    if not path.is_file():
        raise FileNotFoundError(f"No register for document {doc_id}")
    return _revision(path)


def _anchors(
    doc_id: int, register_dir: Path
) -> tuple[dict[int, str], dict[tuple[int, str], str]]:
    transcription = br.transcription_of(doc_id, register_dir)
    if transcription is None:
        raise FileNotFoundError(f"No transcription for document {doc_id}")
    pages: dict[int, str] = {}
    lines: dict[tuple[int, str], str] = {}
    for page in transcription["pages"]:
        page_lines = [
            line
            for region in page.get("regions", [])
            for line in region.get("lines", [])
        ]
        pages[page["pageNr"]] = "\n".join(line["text"] for line in page_lines)
        lines.update(
            ((page["pageNr"], line["id"]), line["text"]) for line in page_lines
        )
    return pages, lines


def _anchor_text(
    page_nr: int,
    line_id: str | None,
    pages: dict[int, str],
    lines: dict[tuple[int, str], str],
) -> str:
    if page_nr not in pages:
        raise ValueError(f"unknown page: {page_nr}")
    if line_id is None:
        return pages[page_nr]
    key = (page_nr, line_id)
    if key not in lines:
        raise ValueError(f"unknown line on page {page_nr}: {line_id}")
    return lines[key]


def _validate_stored(payload: object, doc_id: int, origin: Path) -> dict:
    if not isinstance(payload, dict):
        raise ValueError(f"{origin.name}: tag sidecar must be an object")
    stored_doc = payload.get("docId")
    if (
        not isinstance(stored_doc, int)
        or isinstance(stored_doc, bool)
        or stored_doc != doc_id
    ):
        raise ValueError(f"{origin.name}: docId does not match {doc_id}")
    records = payload.get("tags")
    if not isinstance(records, list):
        raise ValueError(f"{origin.name}: tags must be a list")
    seen: set[str] = set()
    for index, record in enumerate(records):
        where = f"{origin.name}, tag {index}"
        if not isinstance(record, dict):
            raise ValueError(f"{where}: record must be an object")
        tag_id = record.get("id")
        if not isinstance(tag_id, str) or not tag_id or tag_id in seen:
            raise ValueError(f"{where}: id is missing or duplicated")
        try:
            UUID(tag_id)
        except ValueError as exc:
            raise ValueError(f"{where}: id must be a UUID") from exc
        seen.add(tag_id)
        page_nr = record.get("pageNr")
        if not isinstance(page_nr, int) or isinstance(page_nr, bool):
            raise ValueError(f"{where}: pageNr must be an integer")
        line_id = record.get("lineId")
        if line_id is not None and not isinstance(line_id, str):
            raise ValueError(f"{where}: lineId must be text or null")
        _text(record.get("tag"), f"{where}: tag", 100)
        _text(record.get("note"), f"{where}: note", 2000, allow_empty=True)
        _text(record.get("reviewer"), f"{where}: reviewer", 100)
        created = _text(record.get("created"), f"{where}: created", 100)
        _utc_timestamp(created, f"{where}: created")
        _text(record.get("text"), f"{where}: text", 1_000_000, allow_empty=True)
        digest = record.get("textDigest")
        if not isinstance(digest, str) or not DIGEST.fullmatch(digest):
            raise ValueError(f"{where}: textDigest must be a SHA-256 digest")
        if "updated" in record:
            updated = _text(record["updated"], f"{where}: updated", 100)
            _utc_timestamp(updated, f"{where}: updated")
    return payload


def read_tags(
    doc_id: int, register_dir: Path, tag_dir: Path = TAGS, locked: bool = False
) -> dict:
    if not isinstance(doc_id, int) or isinstance(doc_id, bool):
        raise ValueError("docId must be an integer")
    if not locked:
        with ar.review_lock(register_dir):
            return read_tags(doc_id, register_dir, tag_dir, locked=True)
    path = tag_dir / f"{doc_id}.json"
    stored = (
        _validate_stored(load_json(path), doc_id, path)
        if path.exists()
        else {"docId": doc_id, "tags": []}
    )
    pages, lines = _anchors(doc_id, register_dir)
    tags = copy.deepcopy(stored.get("tags", []))
    for tag in tags:
        try:
            current = _anchor_text(tag["pageNr"], tag["lineId"], pages, lines)
        except ValueError:
            tag["stale"] = True
        else:
            tag["stale"] = tag.get("textDigest") != _digest(current)
    return {
        "docId": doc_id,
        "revision": _revision(path),
        "sourceRevision": _source_revision(doc_id, register_dir),
        "tags": tags,
    }


def _text(value: object, name: str, maximum: int, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or len(value) > maximum:
        raise ValueError(f"{name} must be text of at most {maximum} characters")
    if not allow_empty and not value.strip():
        raise ValueError(f"{name} must not be empty")
    return value


def _utc_timestamp(value: str, name: str) -> None:
    if not value.endswith("Z"):
        raise ValueError(f"{name} must be a UTC timestamp")
    try:
        datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{name} must be an ISO timestamp") from exc


def save_tags(payload: object, register_dir: Path, tag_dir: Path = TAGS) -> dict:
    with ar.review_lock(register_dir):
        return _save_tags(payload, register_dir, tag_dir)


def _save_tags(payload: object, register_dir: Path, tag_dir: Path) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("tag payload must be an object")
    doc_id = payload.get("docId")
    if not isinstance(doc_id, int) or isinstance(doc_id, bool):
        raise ValueError("docId must be an integer")
    current = read_tags(doc_id, register_dir, tag_dir, locked=True)
    if payload.get("baseRevision") != current["revision"]:
        raise RuntimeError("stale revision")
    if payload.get("sourceRevision") != current["sourceRevision"]:
        raise RuntimeError("stale source revision")
    action = payload.get("action")
    if action not in ("add", "delete", "recheck"):
        raise ValueError("action must be add, delete or recheck")
    tags = [{k: v for k, v in tag.items() if k != "stale"} for tag in current["tags"]]
    pages, lines = _anchors(doc_id, register_dir)
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    if action == "add":
        data = payload.get("tag")
        if not isinstance(data, dict):
            raise ValueError("tag must be an object")
        page_nr = data.get("pageNr")
        line_id = data.get("lineId")
        if not isinstance(page_nr, int) or isinstance(page_nr, bool):
            raise ValueError("pageNr must be an integer")
        if line_id is not None and not isinstance(line_id, str):
            raise ValueError("lineId must be text or null")
        text = _anchor_text(page_nr, line_id, pages, lines)
        tags.append(
            {
                "id": str(uuid4()),
                "pageNr": page_nr,
                "lineId": line_id,
                "tag": _text(data.get("tag"), "tag", 100),
                "note": _text(data.get("note"), "note", 2000, allow_empty=True),
                "reviewer": _text(data.get("reviewer"), "reviewer", 100),
                "created": now,
                "text": text,
                "textDigest": _digest(text),
            }
        )
    else:
        tag_id = payload.get("id")
        if not isinstance(tag_id, str):
            raise ValueError("id must be text")
        index = next((i for i, tag in enumerate(tags) if tag["id"] == tag_id), None)
        if index is None:
            raise ValueError(f"unknown tag id: {tag_id}")
        if action == "delete":
            tags.pop(index)
        else:
            reviewer = _text(payload.get("reviewer"), "reviewer", 100)
            tag = tags[index]
            text = _anchor_text(tag["pageNr"], tag["lineId"], pages, lines)
            tag.update(
                {
                    "reviewer": reviewer,
                    "updated": now,
                    "text": text,
                    "textDigest": _digest(text),
                }
            )
    path = tag_dir / f"{doc_id}.json"
    write_json(path, {"docId": doc_id, "tags": tags})
    return read_tags(doc_id, register_dir, tag_dir, locked=True)
