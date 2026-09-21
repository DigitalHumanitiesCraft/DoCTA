"""Curated projection tests over a copied corpus extraction and page register."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import build_graph as bg
import build_register as br
import build_tei as bt
import curated_entities as ce
import entity_index as ei
import local_annotations as la
import pytest
import validate_tei as vt
from io_paths import DATA, PIPELINE_DIR, load_json

DOC_ID = 11328300


def _fixture(tmp_path: Path) -> tuple[Path, Path, Path, list[dict]]:
    entity_dir = tmp_path / "entities"
    annotation_dir = tmp_path / "annotations"
    register_dir = tmp_path / "pages"
    entity_dir.mkdir()
    annotation_dir.mkdir()
    register_dir.mkdir()
    shutil.copy2(DATA / "entities" / f"{DOC_ID}.json", entity_dir)
    shutil.copy2(PIPELINE_DIR / "pages" / f"{DOC_ID}.json", register_dir)
    source = load_json(entity_dir / f"{DOC_ID}.json")
    selected = [
        next(entity for entity in source["entities"] if entity["id"] == entity_id)
        for entity_id in ("p1", "p2", "pl1")
    ]
    transcription = br.transcription_of(DOC_ID, register_dir)
    lines = {
        (page["pageNr"], line["id"]): line["text"]
        for page in transcription["pages"]
        for region in page["regions"]
        for line in region["lines"]
    }
    statuses = ("accepted", "rejected", "pending")
    decisions = []
    for entity, status in zip(selected, statuses, strict=True):
        decisions.append(
            {
                "id": entity["id"],
                "kind": entity["type"],
                "normalized": entity["text"],
                "authority": (
                    "https://example.invalid/authority"
                    if status == "accepted"
                    else None
                ),
                "status": status,
                "reason": None,
                "textDigest": la.line_digest(
                    lines[(entity["pageNr"], entity["lineId"])]
                ),
            }
        )
    (annotation_dir / f"{DOC_ID}.json").write_text(
        json.dumps({"docId": DOC_ID, "decisions": decisions}), encoding="utf-8"
    )
    return entity_dir, annotation_dir, register_dir, selected


def test_projection_applies_only_current_final_decisions(tmp_path: Path) -> None:
    entity_dir, annotation_dir, register_dir, selected = _fixture(tmp_path)

    extraction = ce.effective_extractions(entity_dir, annotation_dir, register_dir)[0]
    entities = {entity["id"]: entity for entity in extraction["entities"]}

    accepted, rejected, pending = selected
    assert entities[accepted["id"]]["normalized"] == accepted["text"]
    assert entities[accepted["id"]]["authority"] == "https://example.invalid/authority"
    assert entities[accepted["id"]]["curation"]["status"] == "accepted"
    assert rejected["id"] not in entities
    assert entities[pending["id"]]["normalized"] == pending["normalized"]
    assert entities[pending["id"]]["curation"] == {"status": "pending"}


def test_stale_decision_aborts_projection(tmp_path: Path) -> None:
    entity_dir, annotation_dir, register_dir, _ = _fixture(tmp_path)
    path = annotation_dir / f"{DOC_ID}.json"
    payload = load_json(path)
    payload["decisions"][0]["textDigest"] = "0" * 64
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RuntimeError, match="Stale annotation decision"):
        ce.effective_extractions(entity_dir, annotation_dir, register_dir)


def test_graph_carries_accepted_authority_without_promoting_pending(
    tmp_path: Path,
) -> None:
    entity_dir, annotation_dir, register_dir, selected = _fixture(tmp_path)

    payload = bg.build(entity_dir, annotation_dir, register_dir)
    accepted, rejected, pending = selected
    nodes = {node["@id"]: node for node in payload["@graph"]}
    entries = ce.effective_extractions(entity_dir, annotation_dir, register_dir)
    index = ce.decorate_entries(ei.build_index(entries), entries)
    by_normalized = {(entry["type"], entry["normalized"]): entry for entry in index}

    accepted_entry = by_normalized[(accepted["type"], accepted["text"])]
    accepted_node = nodes[f"docta:{accepted_entry['id']}"]
    accepted_attestation = next(
        attestation
        for attestation in accepted_node["attestation"]
        if attestation["docId"] == DOC_ID
        and attestation["page"] == accepted["pageNr"]
        and attestation["line"] == accepted["lineId"]
        and attestation["form"] == accepted["text"]
    )
    assert accepted_attestation["authority"] == "https://example.invalid/authority"
    assert accepted_attestation["curationStatus"] == "accepted"
    assert "authority" not in accepted_node
    rejected_entry = by_normalized[(rejected["type"], rejected["normalized"])]
    assert {
        "docId": DOC_ID,
        "page": rejected["pageNr"],
        "line": rejected["lineId"],
        "form": rejected["text"],
    } not in rejected_entry["attestations"]
    pending_entry = by_normalized[(pending["type"], pending["normalized"])]
    pending_node = nodes[f"docta:{pending_entry['id']}"]
    pending_attestation = next(
        attestation
        for attestation in pending_node["attestation"]
        if attestation["docId"] == DOC_ID
        and attestation["page"] == pending["pageNr"]
        and attestation["line"] == pending["lineId"]
        and attestation["form"] == pending["text"]
    )
    assert pending_attestation["curationStatus"] == "pending"
    assert "authority" not in pending_attestation


def test_tei_build_uses_curated_normalization_and_keeps_schema(
    tmp_path: Path,
) -> None:
    entity_dir, annotation_dir, register_dir, selected = _fixture(tmp_path)
    out = tmp_path / "tei"

    built = bt.build(
        out,
        register_dir=register_dir,
        entity_dir=entity_dir,
        annotation_dir=annotation_dir,
    )

    accepted, _, pending = selected
    register = (out / bt.REGISTER_FILE).read_text(encoding="utf-8")
    assert f">{accepted['text']}<" in register
    assert f">{pending['normalized']}<" in register
    document = built[DOC_ID]
    assert (
        "Accepted and rejected decisions from the local annotation sidecar" in document
    )
    files = [out / f"{DOC_ID}.xml", out / bt.REGISTER_FILE]
    for _, schema in vt.STAGES:
        assert vt.validate_with_lxml(files, schema, 3) == []
