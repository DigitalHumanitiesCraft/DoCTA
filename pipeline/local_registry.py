"""Persist editorial registers and explicitly anchored mentions in the script pipeline.

The local editor calls these functions under the shared review lock. One atomic
sidecar holds entries, mentions and their audit events. Generated entity indexes
are independent. Offsets use JavaScript UTF-16 code units, never Python character
indices; a boundary inside a surrogate pair is rejected. Digests cover the full
saved UTF-8 line. See the working-edition contract in docs/knowledge/architecture.md.
"""

from __future__ import annotations

import copy
import hashlib
import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import apply_review as ar
from io_paths import load_json, write_json
from local_annotations import _lines, line_digest

KINDS = frozenset(("person", "term"))


def _text(value: object, field: str, maximum: int, empty: bool = False) -> str:
    if not isinstance(value, str) or len(value) > maximum:
        raise ValueError(f"{field} must be text of at most {maximum} characters")
    if not empty and not value.strip():
        raise ValueError(f"{field} must not be empty")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError(f"{field} contains an unpaired surrogate") from exc
    return value


def _uuid(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("id must be a UUID")
    try:
        parsed = UUID(value)
    except ValueError as exc:
        raise ValueError("id must be a UUID") from exc
    if str(parsed) != value:
        raise ValueError("id must be a canonical UUID")
    return value


def utf16_slice(text: str, start: int, end: int) -> str:
    """Reject empty/outside spans and boundaries splitting an astral character."""
    if type(start) is not int or type(end) is not int:
        raise ValueError("start and end must be integers")
    raw = text.encode("utf-16-le")
    if not 0 <= start < end <= len(raw) // 2:
        raise ValueError("mention range is outside the source line")
    try:
        return raw[start * 2 : end * 2].decode("utf-16-le")
    except UnicodeDecodeError as exc:
        raise ValueError("mention range splits a UTF-16 surrogate pair") from exc


def _entry(data: object) -> dict:
    if not isinstance(data, dict):
        raise ValueError("entry must be an object")
    kind = data.get("kind")
    if not isinstance(kind, str) or kind not in KINDS:
        raise ValueError("entry kind must be person or term")
    aliases = data.get("aliases", [])
    if not isinstance(aliases, list) or len(aliases) > 100:
        raise ValueError("aliases must be a list of at most 100 labels")
    broader = data.get("broaderId")
    if broader is not None:
        _uuid(broader)
        if kind != "term":
            raise ValueError("only a term can have a broader term")
    return {
        "id": _uuid(data.get("id")),
        "kind": kind,
        "label": _text(data.get("label"), "label", 500),
        "aliases": [_text(alias, "alias", 500) for alias in aliases],
        "note": _text(data.get("note", ""), "note", 10000, empty=True),
        "broaderId": broader,
    }


def _mention(data: object) -> dict:
    if not isinstance(data, dict):
        raise ValueError("mention must be an object")
    result = {
        key: data.get(key)
        for key in (
            "id",
            "docId",
            "pageNr",
            "lineId",
            "start",
            "end",
            "quote",
            "textDigest",
            "entryId",
            "kind",
        )
    }
    _uuid(result["id"])
    if not isinstance(result["kind"], str) or result["kind"] not in KINDS:
        raise ValueError("mention kind must be person or term")
    for field in ("docId", "pageNr"):
        if type(result[field]) is not int or result[field] < 1:
            raise ValueError(f"{field} must be a positive integer")
    _text(result["lineId"], "lineId", 500)
    _text(result["quote"], "quote", 100000)
    if (
        type(result["start"]) is not int
        or type(result["end"]) is not int
        or not 0 <= result["start"] < result["end"]
    ):
        raise ValueError("invalid mention offsets")
    digest = result["textDigest"]
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("textDigest must be a SHA-256 digest")
    if result["entryId"] is not None:
        _uuid(result["entryId"])
    result["note"] = _text(data.get("note", ""), "note", 10000, empty=True)
    return result


def _validate(state: object) -> dict:
    if (
        not isinstance(state, dict)
        or type(state.get("schemaVersion")) is not int
        or state["schemaVersion"] != 1
    ):
        raise ValueError("registry must have schemaVersion 1")
    for key in ("entries", "mentions", "history"):
        if not isinstance(state.get(key), list):
            raise ValueError(f"registry {key} must be a list")
    entries = [_entry(item) for item in state["entries"]]
    mentions = [_mention(item) for item in state["mentions"]]
    for records in (entries, mentions):
        if len({item["id"] for item in records}) != len(records):
            raise ValueError("duplicate registry id")
    by_id = {item["id"]: item for item in entries}
    for entry in entries:
        visited = {entry["id"]}
        parent = entry["broaderId"]
        while parent is not None:
            if parent not in by_id or by_id[parent]["kind"] != "term":
                raise ValueError("unknown broader term")
            if parent in visited:
                raise ValueError("broader term cycle")
            visited.add(parent)
            parent = by_id[parent]["broaderId"]
    for mention in mentions:
        target = mention["entryId"]
        if target is not None and (
            target not in by_id or by_id[target]["kind"] != mention["kind"]
        ):
            raise ValueError("mention entry must exist and have the same kind")
    for event in state["history"]:
        if not isinstance(event, dict) or event.get("action") not in (
            "save-entry",
            "save-mention",
            "remove-mention",
        ):
            raise ValueError("invalid registry audit event")
        _text(event.get("actor"), "event actor", 100)
        timestamp = _text(event.get("timestamp"), "event timestamp", 100)
        try:
            parsed = datetime.fromisoformat(timestamp)
        except ValueError as exc:
            raise ValueError("invalid event timestamp") from exc
        if parsed.tzinfo is None or "before" not in event or "after" not in event:
            raise ValueError("incomplete registry audit event")
        validate_record = _entry if event["action"] == "save-entry" else _mention
        for key in ("before", "after"):
            if event[key] is not None:
                validate_record(event[key])
        if event["before"] is None and event["after"] is None:
            raise ValueError("empty registry audit event")
        if event["action"] == "remove-mention" and event["after"] is not None:
            raise ValueError("invalid removal audit event")
    return {
        "schemaVersion": 1,
        "entries": entries,
        "mentions": mentions,
        "history": state["history"],
    }


def _read(register_dir: Path) -> tuple[dict, str]:
    path = register_dir.parent / "registry" / "index.json"
    state = (
        _validate(load_json(path))
        if path.exists()
        else {"schemaVersion": 1, "entries": [], "mentions": [], "history": []}
    )
    revision = hashlib.sha256(path.read_bytes() if path.exists() else b"").hexdigest()
    return state, revision


def _stale(mention: dict, lines: dict) -> bool:
    text = lines.get((mention["pageNr"], mention["lineId"]))
    if text is None or line_digest(text) != mention["textDigest"]:
        return True
    try:
        return utf16_slice(text, mention["start"], mention["end"]) != mention["quote"]
    except ValueError:
        return True


def _project(state: dict, revision: str, register_dir: Path) -> dict:
    result = copy.deepcopy(state)
    sources = {}
    for mention in result["mentions"]:
        doc_id = mention["docId"]
        if doc_id not in sources:
            try:
                sources[doc_id] = _source_lines(doc_id, register_dir)
            except FileNotFoundError:
                sources[doc_id] = {}
        mention["stale"] = _stale(mention, sources[doc_id])
    result["revision"] = revision
    return result


def _source_lines(doc_id: int, register_dir: Path) -> dict:
    if not (register_dir / f"{doc_id}.json").is_file():
        raise FileNotFoundError(f"No register for document {doc_id}")
    return _lines(doc_id, register_dir)


def read_registry(register_dir: Path) -> dict:
    with ar.review_lock(register_dir):
        state, revision = _read(register_dir)
        return _project(state, revision, register_dir)


def save_registry(payload: object, register_dir: Path) -> dict:
    with ar.review_lock(register_dir):
        if not isinstance(payload, dict):
            raise ValueError("registry payload must be an object")
        state, revision = _read(register_dir)
        if payload.get("baseRevision") != revision:
            raise RuntimeError("stale registry revision")
        actor = _text(payload.get("reviewer"), "reviewer", 100)
        action = payload.get("action")
        if action not in ("save-entry", "save-mention", "remove-mention"):
            raise ValueError("unknown registry action")
        records = state["entries" if action == "save-entry" else "mentions"]
        if action == "remove-mention":
            record_id = _uuid(payload.get("id"))
            after = None
        else:
            data = payload.get("entry" if action == "save-entry" else "mention")
            if not isinstance(data, dict):
                raise ValueError("record must be an object")
            data = {**data, "id": data.get("id", str(uuid4()))}
            after = _entry(data) if action == "save-entry" else _mention(data)
            record_id = after["id"]
            if action == "save-mention":
                lines = _source_lines(after["docId"], register_dir)
                if _stale(after, lines):
                    raise RuntimeError(
                        "stale or invalid source mention; save the transcription and select again"
                    )
        before = next((item for item in records if item["id"] == record_id), None)
        if before is None and action == "remove-mention":
            raise ValueError("unknown mention id")
        if before and after and before["kind"] != after["kind"]:
            raise ValueError("record kind cannot change")
        if before == after:
            return _project(state, revision, register_dir)
        if before is not None:
            records.remove(before)
        if after is not None:
            records.append(after)
        state["history"].append(
            {
                "action": action,
                "actor": actor,
                "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "before": before,
                "after": copy.deepcopy(after),
            }
        )
        state = _validate(state)
        write_json(register_dir.parent / "registry" / "index.json", state)
        state, revision = _read(register_dir)
        return _project(state, revision, register_dir)
