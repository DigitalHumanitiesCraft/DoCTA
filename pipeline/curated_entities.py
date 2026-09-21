"""Project local annotation sidecars onto immutable entity extractions.

The source extraction files remain unchanged. A rejected proposal disappears,
an accepted decision replaces its normalized form and carries its authority URI,
and a pending or absent decision remains machine output. Every saved decision is
checked against the effective transcription line before any projection is
returned, so a stale sidecar aborts TEI and graph generation visibly.
"""

from __future__ import annotations

import copy
import re
from pathlib import Path

import build_register as br
import entity_index as ei
import local_annotations as la
from io_paths import PIPELINE_DIR, load_json

ANNOTATIONS = PIPELINE_DIR / "annotations"
AUTHORITY_URI = re.compile(r"https?://[^\s]+$")


def _effective_lines(doc_id: int, register_dir: Path) -> dict[tuple[int, str], str]:
    transcription = br.transcription_of(doc_id, register_dir)
    if transcription is None:
        raise FileNotFoundError(f"No effective transcription for document {doc_id}")
    return {
        (page["pageNr"], line["id"]): line["text"]
        for page in transcription["pages"]
        for region in page.get("regions") or []
        for line in region.get("lines") or []
    }


def _decisions(doc_id: int, annotation_dir: Path) -> list[dict]:
    path = annotation_dir / f"{doc_id}.json"
    if not path.exists():
        return []
    payload = load_json(path)
    if payload.get("docId") != doc_id or not isinstance(payload.get("decisions"), list):
        raise ValueError(f"Invalid annotation sidecar for document {doc_id}")
    return payload["decisions"]


def effective_extractions(
    entity_dir: Path = ei.ENTITY_DIR,
    annotation_dir: Path = ANNOTATIONS,
    register_dir: Path = PIPELINE_DIR / "pages",
) -> list[dict]:
    """Return extraction-shaped data with current curation decisions applied."""
    projected = []
    for extraction in ei.load_extractions(entity_dir):
        doc_id = extraction.get("docId")
        decisions = _decisions(doc_id, annotation_dir)
        if not decisions:
            projected.append(copy.deepcopy(extraction))
            continue
        lines = _effective_lines(doc_id, register_dir)
        by_id: dict[str, dict] = {}
        for decision in decisions:
            entity_id = decision.get("id")
            if not isinstance(entity_id, str) or entity_id in by_id:
                raise ValueError(
                    f"Invalid or duplicate entity decision in document {doc_id}"
                )
            by_id[entity_id] = decision

        entities = []
        known = {entity.get("id") for entity in extraction.get("entities") or []}
        unknown = sorted(set(by_id) - known)
        if unknown:
            raise ValueError(
                f"Document {doc_id} has decisions for unknown entities: {unknown}"
            )
        applied = False
        for source in extraction.get("entities") or []:
            entity = copy.deepcopy(source)
            decision = by_id.get(entity.get("id"))
            if decision is None:
                entities.append(entity)
                continue
            if decision.get("kind") != entity.get("type"):
                raise ValueError(
                    f"Document {doc_id}, entity {entity['id']}: kind changed"
                )
            line = lines.get((entity.get("pageNr"), entity.get("lineId")))
            if line is None or decision.get("textDigest") != la.line_digest(line):
                raise RuntimeError(
                    f"Stale annotation decision for document {doc_id}, entity {entity['id']}"
                )
            status = decision.get("status")
            if status not in la.STATES:
                raise ValueError(
                    f"Document {doc_id}, entity {entity['id']}: invalid status {status!r}"
                )
            if status == "rejected":
                applied = True
                continue
            if status == "accepted":
                normalized = decision.get("normalized")
                authority = decision.get("authority")
                if not isinstance(normalized, str) or not normalized.strip():
                    raise ValueError(
                        f"Document {doc_id}, entity {entity['id']}: accepted normalized form missing"
                    )
                if authority is not None and not isinstance(authority, str):
                    raise ValueError(
                        f"Document {doc_id}, entity {entity['id']}: authority must be text"
                    )
                if authority and not AUTHORITY_URI.fullmatch(authority):
                    raise ValueError(
                        f"Document {doc_id}, entity {entity['id']}: authority is not an HTTP URI"
                    )
                entity["normalized"] = normalized.strip()
                entity["authority"] = authority or None
                entity["curation"] = {
                    "status": "accepted",
                    "textDigest": decision["textDigest"],
                    "reason": decision.get("reason"),
                }
                applied = True
            else:
                entity["curation"] = {"status": "pending"}
            entities.append(entity)
        result = copy.deepcopy(extraction)
        result["entities"] = entities
        result["curationApplied"] = applied
        projected.append(result)
    return projected


def decorate_entries(entries: list[dict], extractions: list[dict]) -> list[dict]:
    """Carry curation state on the exact attestation it qualifies."""
    annotations: dict[tuple, list[dict]] = {}
    for extraction in extractions:
        for entity in extraction.get("entities") or []:
            key = (
                entity.get("type"),
                entity.get("normalized") or entity.get("text"),
                extraction.get("docId"),
                entity.get("pageNr"),
                entity.get("lineId"),
                entity.get("text") or entity.get("normalized"),
            )
            curation = entity.get("curation") or {}
            state = {"entityId": entity.get("id")}
            if status := curation.get("status"):
                state["curationStatus"] = status
            if entity.get("authority"):
                state["authority"] = entity["authority"]
            annotations.setdefault(key, []).append(state)
    for states in annotations.values():
        states.sort(key=lambda state: state["entityId"] or "")
    decorated = copy.deepcopy(entries)
    for entry in decorated:
        for attestation in entry["attestations"]:
            key = (
                entry["type"],
                entry["normalized"],
                attestation["docId"],
                attestation["page"],
                attestation["line"],
                attestation["form"],
            )
            states = annotations.get(key)
            if not states:
                continue
            state = states.pop(0)
            if state.get("curationStatus"):
                attestation["curationStatus"] = state["curationStatus"]
            if state.get("authority"):
                attestation["authority"] = state["authority"]
    return decorated
