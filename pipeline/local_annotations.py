"""Validate and persist local curation decisions for extracted entities.

The model extraction under ``docs/data/entities`` stays immutable. Decisions are
stored as a small sidecar keyed by stable extraction ids and guarded by both the
loaded sidecar revision and a digest of the effective transcription line.
"""

from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import apply_review as ar
import build_register as br
from io_paths import DATA, PIPELINE_DIR, load_json, write_json

ANNOTATIONS = PIPELINE_DIR / "annotations"
KINDS = frozenset(("person", "place", "object", "time"))
STATES = frozenset(("accepted", "rejected", "pending"))


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _lines(doc_id: int, register_dir: Path) -> dict[tuple[int, str], str]:
    transcription = br.transcription_of(doc_id, register_dir)
    if transcription is None:
        raise FileNotFoundError(f"No transcription for document {doc_id}")
    return {
        (page["pageNr"], line["id"]): line["text"]
        for page in transcription["pages"]
        for region in page.get("regions", [])
        for line in region.get("lines", [])
    }


def read_decisions(doc_id: int, sidecar_dir: Path = ANNOTATIONS) -> dict:
    path = sidecar_dir / f"{doc_id}.json"
    payload = load_json(path) if path.exists() else {"docId": doc_id, "decisions": []}
    raw = path.read_bytes() if path.exists() else b""
    payload["revision"] = hashlib.sha256(raw).hexdigest()
    return payload


def save_decisions(
    payload: dict,
    register_dir: Path,
    sidecar_dir: Path = ANNOTATIONS,
) -> dict:
    with ar.review_lock(register_dir):
        return _save_decisions(payload, register_dir, sidecar_dir)


def _save_decisions(payload: dict, register_dir: Path, sidecar_dir: Path) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("annotation payload must be an object")
    doc_id = payload.get("docId")
    if not isinstance(doc_id, int) or isinstance(doc_id, bool):
        raise ValueError("docId must be an integer")
    current = read_decisions(doc_id, sidecar_dir)
    if payload.get("baseRevision") != current["revision"]:
        raise RuntimeError("stale revision")
    decisions = payload.get("decisions")
    if not isinstance(decisions, list):
        raise ValueError("decisions must be a list")
    extraction_path = DATA / "entities" / f"{doc_id}.json"
    if not extraction_path.is_file():
        raise FileNotFoundError(f"No entity extraction for document {doc_id}")
    extracted = {
        entity["id"]: entity for entity in load_json(extraction_path)["entities"]
    }
    lines = _lines(doc_id, register_dir)
    checked = []
    existing = {decision["id"]: decision for decision in current["decisions"]}
    seen: set[str] = set()
    for decision in decisions:
        if not isinstance(decision, dict):
            raise ValueError("annotation decision must be an object")
        entity_id = decision.get("id")
        if (
            not isinstance(entity_id, str)
            or entity_id in seen
            or entity_id not in extracted
        ):
            raise ValueError(f"invalid or duplicate entity id: {entity_id!r}")
        seen.add(entity_id)
        entity = extracted[entity_id]
        kind = decision.get("kind")
        status = decision.get("status")
        if kind not in KINDS or status not in STATES:
            raise ValueError(f"invalid annotation decision for {entity_id}")
        if kind != entity["type"]:
            raise ValueError(f"entity kind changed for {entity_id}")
        line = lines.get((entity["pageNr"], entity["lineId"]))
        stale = line is None or decision.get("textDigest") != _digest(line)
        if stale and decision != existing.get(entity_id):
            raise RuntimeError(f"stale text for entity {entity_id}")
        normalized = decision.get("normalized")
        authority = decision.get("authority")
        reason = decision.get("reason")
        if not isinstance(normalized, str):
            raise ValueError(f"normalized form missing for {entity_id}")
        if status == "accepted" and not normalized.strip():
            raise ValueError(f"accepted normalized form is empty for {entity_id}")
        if authority is not None and not isinstance(authority, str):
            raise ValueError(f"authority must be text for {entity_id}")
        if authority is not None and not authority.startswith(("http://", "https://")):
            raise ValueError(f"authority must be an HTTP(S) URL for {entity_id}")
        if reason is not None and (not isinstance(reason, str) or len(reason) > 2000):
            raise ValueError(f"reason is invalid for {entity_id}")
        checked.append(copy.deepcopy(decision))
    path = sidecar_dir / f"{doc_id}.json"
    write_json(path, {"docId": doc_id, "decisions": checked})
    return read_decisions(doc_id, sidecar_dir)


def line_digest(text: str) -> str:
    """Public digest helper for the local API projection and its tests."""
    return _digest(text)
