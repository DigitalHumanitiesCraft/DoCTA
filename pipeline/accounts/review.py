"""Immutable review decisions and accepted annotation sets.

Proposals remain unchanged after review. A human decision is a separate
artifact, tied to the proposal's exact transcription basis. Accepted sets contain
only proposals with an explicit accepted decision and receive a deterministic
content hash.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from .anchors import validate_anchor, validate_revision
from .models import (
    AnnotationProposal,
    AnnotationSet,
    EditorialDecision,
    PublicationStatus,
    ReviewDecision,
    TranscriptionRevision,
    payload_sha256,
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


def _annotation_set_hash(
    set_id: str,
    revision: TranscriptionRevision,
    proposal_ids: tuple[str, ...],
    decision_ids: tuple[str, ...],
    publication: PublicationStatus,
    created_at: datetime,
) -> str:
    return payload_sha256(
        {
            "id": set_id,
            "transcriptionRevisionId": revision.id,
            "transcriptionSha256": revision.sha256,
            "proposalIds": proposal_ids,
            "decisionIds": decision_ids,
            "editorialStatus": EditorialDecision.ACCEPTED.value,
            "publication": publication.value,
            "createdAt": created_at.isoformat(),
        }
    )


def build_accepted_annotation_set(
    *,
    set_id: str,
    revision: TranscriptionRevision,
    proposals: Iterable[AnnotationProposal],
    decisions: Iterable[ReviewDecision],
    created_at: datetime,
    publication: PublicationStatus = PublicationStatus.UNPUBLISHED,
) -> AnnotationSet:
    """Lock accepted proposals whose decisions match the current transcription."""

    validate_revision(revision)
    proposal_by_id = {item.id: item for item in proposals}
    decision_by_proposal: dict[str, ReviewDecision] = {}
    for decision in decisions:
        if decision.proposal_id in decision_by_proposal:
            raise ValueError(f"multiple decisions for proposal: {decision.proposal_id}")
        decision_by_proposal[decision.proposal_id] = decision
    if set(proposal_by_id) != set(decision_by_proposal):
        raise ValueError("accepted set needs exactly one decision for every proposal")

    accepted: list[tuple[AnnotationProposal, ReviewDecision]] = []
    for proposal_id in sorted(proposal_by_id):
        proposal = proposal_by_id[proposal_id]
        decision = decision_by_proposal[proposal_id]
        if proposal_is_stale(proposal, revision):
            raise ValueError(f"stale proposal cannot enter accepted set: {proposal.id}")
        if decision.outcome != EditorialDecision.ACCEPTED.value:
            raise ValueError(f"proposal is not accepted: {proposal.id}")
        if decision.transcription_revision_id != revision.id:
            raise ValueError(
                f"decision uses another transcription revision: {decision.id}"
            )
        if decision.transcription_sha256 != revision.sha256:
            raise ValueError(f"decision uses another transcription hash: {decision.id}")
        accepted.append((proposal, decision))

    proposal_ids = tuple(item.id for item, _ in accepted)
    decision_ids = tuple(item.id for _, item in accepted)
    digest = _annotation_set_hash(
        set_id,
        revision,
        proposal_ids,
        decision_ids,
        publication,
        created_at,
    )
    return AnnotationSet(
        id=set_id,
        transcription_revision_id=revision.id,
        transcription_sha256=revision.sha256,
        proposal_ids=proposal_ids,
        decision_ids=decision_ids,
        editorial_status=EditorialDecision.ACCEPTED,
        publication=publication,
        created_at=created_at,
        sha256=digest,
    )


def validate_annotation_set(annotation_set: AnnotationSet) -> None:
    """Verify the deterministic hash carried by an accepted annotation set."""

    actual = payload_sha256(
        {
            "id": annotation_set.id,
            "transcriptionRevisionId": annotation_set.transcription_revision_id,
            "transcriptionSha256": annotation_set.transcription_sha256,
            "proposalIds": annotation_set.proposal_ids,
            "decisionIds": annotation_set.decision_ids,
            "editorialStatus": annotation_set.editorial_status,
            "publication": annotation_set.publication,
            "createdAt": annotation_set.created_at.isoformat(),
        }
    )
    if actual != annotation_set.sha256:
        raise ValueError(
            f"annotation set hash mismatch: expected {annotation_set.sha256}, got {actual}"
        )
