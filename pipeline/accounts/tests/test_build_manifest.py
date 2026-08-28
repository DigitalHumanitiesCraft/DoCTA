"""Deterministic EditionBuildManifest tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from pipeline.accounts.anchors import import_page_xml
from pipeline.accounts.build_manifest import build_manifest, validate_manifest
from pipeline.accounts.models import (
    AnnotationProposal,
    AnnotationSet,
    EditorialDecision,
    TranscriptionRevision,
)
from pipeline.accounts.review import build_accepted_annotation_set, make_review_decision

FIXTURES = Path(__file__).parent / "fixtures" / "core"
NOW = datetime(2026, 8, 27, 12, 0, tzinfo=UTC)


def _accepted_pair(
    revision_id: str,
    suffix: str,
) -> tuple[TranscriptionRevision, AnnotationSet]:
    revision = import_page_xml(
        (FIXTURES / "page.xml").read_text(encoding="utf-8"),
        document_id=12514730,
        scan_number=int(suffix),
        revision_id=revision_id,
    )
    proposal = AnnotationProposal(
        id=f"proposal-{suffix}",
        kind="entry",
        anchor=revision.lines[0].anchor,
        payload={"class": "Entry"},
        transcription_revision_id=revision.id,
        transcription_sha256=revision.sha256,
        created_by="synthetic-editor",
        created_at=NOW,
    )
    decision = make_review_decision(
        proposal,
        decision_id=f"decision-{suffix}",
        outcome=EditorialDecision.ACCEPTED,
        reviewer="CE",
        decided_at=NOW,
    )
    annotation_set = build_accepted_annotation_set(
        set_id=f"annotations-{suffix}",
        revision=revision,
        proposals=[proposal],
        decisions=[decision],
        created_at=NOW,
    )
    return revision, annotation_set


def test_manifest_is_deterministic_across_input_order() -> None:
    first = _accepted_pair("tr-rb2-001", "1")
    second = _accepted_pair("tr-rb2-002", "2")
    kwargs = {
        "manifest_id": "edition-build-1",
        "profile": "docta-accounts-1.0",
        "specification_versions": {"tei": "1.0.0", "core": "1.0.0"},
        "created_at": NOW,
    }
    left = build_manifest(
        transcriptions=[second[0], first[0]],
        annotation_sets=[second[1], first[1]],
        **kwargs,
    )
    right = build_manifest(
        transcriptions=[first[0], second[0]],
        annotation_sets=[first[1], second[1]],
        **kwargs,
    )
    assert left == right
    assert left.transcription_revision_ids == ("tr-rb2-001", "tr-rb2-002")
    assert list(left.specification_versions) == ["core", "tei"]
    validate_manifest(left)


def test_manifest_rejects_annotation_set_without_transcription() -> None:
    revision, annotation_set = _accepted_pair("tr-rb2-001", "1")
    with pytest.raises(ValueError, match="no pinned transcription"):
        build_manifest(
            manifest_id="edition-build-1",
            profile="docta-accounts-1.0",
            transcriptions=[],
            annotation_sets=[annotation_set],
            specification_versions={"core": "1.0.0"},
            created_at=NOW,
        )
    assert revision.id == annotation_set.transcription_revision_id
