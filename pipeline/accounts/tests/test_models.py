"""Contract tests for the DoCTA accounts core models."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from pipeline.accounts.models import (
    AnnotationProposal,
    EditorialDecision,
    SourceAnchor,
    load_model,
    model_payload,
    write_model_atomic,
)

FIXTURES = Path(__file__).parent / "fixtures" / "core"


def test_source_anchor_uses_camel_case_json() -> None:
    anchor = load_model(FIXTURES / "source-anchor.json", SourceAnchor)
    payload = model_payload(anchor)
    assert payload["documentId"] == 12514730
    assert payload["transcriptionRevisionId"] == "tr-rb2-001"
    assert "document_id" not in payload


def test_invalid_anchor_span_is_rejected() -> None:
    with pytest.raises(ValidationError, match="quote length"):
        load_model(FIXTURES / "invalid-anchor.json", SourceAnchor)


def test_proposal_is_frozen_and_must_remain_proposed() -> None:
    anchor = load_model(FIXTURES / "source-anchor.json", SourceAnchor)
    proposal = AnnotationProposal(
        id="proposal-1",
        kind="entity-mention",
        anchor=anchor,
        payload={"entityType": "person"},
        transcription_revision_id=anchor.transcription_revision_id,
        transcription_sha256=anchor.transcription_sha256,
        created_by="synthetic-test",
        created_at=datetime(2026, 8, 27, tzinfo=UTC),
    )
    with pytest.raises(ValidationError, match="frozen"):
        proposal.kind = "changed"  # type: ignore[misc]
    with pytest.raises(ValidationError, match="must remain proposed"):
        AnnotationProposal.model_validate(
            {**model_payload(proposal), "editorialStatus": EditorialDecision.ACCEPTED}
        )


def test_atomic_write_is_idempotent_and_refuses_changed_artifact(
    tmp_path: Path,
) -> None:
    anchor = load_model(FIXTURES / "source-anchor.json", SourceAnchor)
    target = tmp_path / "anchor.json"
    write_model_atomic(target, anchor)
    first = target.read_bytes()
    write_model_atomic(target, anchor)
    assert target.read_bytes() == first

    changed = SourceAnchor.model_validate(
        {**json.loads(first), "quote": "Hans", "end": 4}
    )
    with pytest.raises(FileExistsError):
        write_model_atomic(target, changed)
