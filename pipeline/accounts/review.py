"""Immutable review decisions over annotation proposals.

Proposals remain unchanged after review. A human decision is a separate
artifact, tied to the proposal's exact transcription basis. A proposal whose
transcription basis has moved is reported as stale instead of being re-anchored
silently.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from .anchors import validate_anchor
from .models import (
    AnnotationProposal,
    EditorialDecision,
    ReviewDecision,
    TranscriptionRevision,
)


def proposal_is_stale(
    proposal: AnnotationProposal,
    revision: TranscriptionRevision,
) -> bool:
    """Whether a proposal no longer resolves against the supplied revision."""

    if proposal.transcription_revision_id != revision.id:
        return True
    if proposal.transcription_sha256 != revision.sha256:
        return True
    try:
        validate_anchor(proposal.anchor, revision)
    except ValueError:
        return True
    return False


def stale_proposal_ids(
    proposals: Iterable[AnnotationProposal],
    revision: TranscriptionRevision,
) -> tuple[str, ...]:
    """Stable list of proposal ids invalidated by a transcription revision."""

    return tuple(
        sorted(item.id for item in proposals if proposal_is_stale(item, revision))
    )


def make_review_decision(
    proposal: AnnotationProposal,
    *,
    decision_id: str,
    outcome: EditorialDecision,
    reviewer: str,
    decided_at: datetime,
    note: str = "",
) -> ReviewDecision:
    """Create a decision that records, but never mutates, its proposal basis."""

    return ReviewDecision(
        id=decision_id,
        proposal_id=proposal.id,
        outcome=outcome,
        reviewer=reviewer,
        decided_at=decided_at,
        transcription_revision_id=proposal.transcription_revision_id,
        transcription_sha256=proposal.transcription_sha256,
        note=note,
    )
