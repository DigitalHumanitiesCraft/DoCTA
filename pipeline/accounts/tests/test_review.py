"""Editorial decision, stale detection and accepted-set tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from pipeline.accounts.anchors import import_page_xml
from pipeline.accounts.models import (
    AnnotationProposal,
    EditorialDecision,
    TranscriptionRevision,
)
from pipeline.accounts.review import (
    build_accepted_annotation_set,
    make_review_decision,
    proposal_is_stale,
    stale_proposal_ids,
    validate_annotation_set,
)

FIXTURES = Path(__file__).parent / "fixtures" / "core"
NOW = datetime(2026, 8, 27, 12, 0, tzinfo=UTC)


def _revision(revision_id: str = "tr-rb2-001") -> TranscriptionRevision:
    return import_page_xml(
        (FIXTURES / "page.xml").read_text(encoding="utf-8"),
        document_id=12514730,
        scan_number=1,
        revision_id=revision_id,
    )


def _proposal(
    revision: TranscriptionRevision,
    proposal_id: str = "proposal-person-1",
) -> AnnotationProposal:
    return AnnotationProposal(
        id=proposal_id,
        kind="entity-mention",
        anchor=revision.lines[0].anchor,
        payload={"entityType": "person", "normalisedLabel": "Hans"},
        transcription_revision_id=revision.id,
        transcription_sha256=revision.sha256,
        created_by="synthetic-editor",
        created_at=NOW,
    )


def test_proposal_becomes_stale_on_another_revision() -> None:
    first = _revision()
    later = _revision("tr-rb2-002")
    proposal = _proposal(first)
    assert not proposal_is_stale(proposal, first)
    assert proposal_is_stale(proposal, later)
    assert stale_proposal_ids([proposal], later) == (proposal.id,)


def test_accepted_set_requires_matching_human_decision() -> None:
    revision = _revision()
    proposal = _proposal(revision)
    decision = make_review_decision(
        proposal,
        decision_id="decision-person-1",
        outcome=EditorialDecision.ACCEPTED,
        reviewer="CE",
        decided_at=NOW,
    )
    annotation_set = build_accepted_annotation_set(
        set_id="annotations-rb2-001",
        revision=revision,
        proposals=[proposal],
        decisions=[decision],
        created_at=NOW,
    )
    assert annotation_set.proposal_ids == (proposal.id,)
    assert annotation_set.decision_ids == (decision.id,)
    assert annotation_set.editorial_status == "accepted"
    validate_annotation_set(annotation_set)


def test_rejected_proposal_cannot_enter_accepted_set() -> None:
    revision = _revision()
    proposal = _proposal(revision)
    decision = make_review_decision(
        proposal,
        decision_id="decision-person-1",
        outcome=EditorialDecision.REJECTED,
        reviewer="CE",
        decided_at=NOW,
    )
    with pytest.raises(ValueError, match="not accepted"):
        build_accepted_annotation_set(
            set_id="annotations-rb2-001",
            revision=revision,
            proposals=[proposal],
            decisions=[decision],
            created_at=NOW,
        )
