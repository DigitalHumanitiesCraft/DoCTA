"""Build and verify deterministic DoCTA accounts edition manifests.

An EditionBuildManifest pins approved transcription revisions, accepted
annotation sets and versioned specifications by id and SHA-256. It is a
reproducibility artifact; its publication state does not confer scholarly
approval on any input.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime

from .anchors import validate_revision
from .models import (
    AnnotationSet,
    EditionBuildManifest,
    PublicationStatus,
    TranscriptionRevision,
    payload_sha256,
)
from .review import validate_annotation_set


def _manifest_payload(
    *,
    manifest_id: str,
    profile: str,
    transcription_revision_ids: tuple[str, ...],
    annotation_set_ids: tuple[str, ...],
    artifact_hashes: dict[str, str],
    specification_versions: dict[str, str],
    publication: PublicationStatus,
    created_at: datetime,
) -> dict[str, object]:
    return {
        "id": manifest_id,
        "profile": profile,
        "transcriptionRevisionIds": transcription_revision_ids,
        "annotationSetIds": annotation_set_ids,
        "artifactHashes": artifact_hashes,
        "specificationVersions": specification_versions,
        "publication": publication.value,
        "createdAt": created_at.isoformat(),
    }


def build_manifest(
    *,
    manifest_id: str,
    profile: str,
    transcriptions: Iterable[TranscriptionRevision],
    annotation_sets: Iterable[AnnotationSet],
    specification_versions: Mapping[str, str],
    created_at: datetime,
    publication: PublicationStatus = PublicationStatus.UNPUBLISHED,
) -> EditionBuildManifest:
    """Pin a coherent accepted input selection in deterministic id order."""

    revisions = sorted(transcriptions, key=lambda item: item.id)
    sets = sorted(annotation_sets, key=lambda item: item.id)
    revision_by_id = {item.id: item for item in revisions}
    if len(revision_by_id) != len(revisions):
        raise ValueError("duplicate transcription revision id")
    set_by_id = {item.id: item for item in sets}
    if len(set_by_id) != len(sets):
        raise ValueError("duplicate annotation set id")

    for revision in revisions:
        validate_revision(revision)
    for annotation_set in sets:
        validate_annotation_set(annotation_set)
        revision = revision_by_id.get(annotation_set.transcription_revision_id)
        if revision is None:
            raise ValueError(
                f"annotation set has no pinned transcription: {annotation_set.id}"
            )
        if annotation_set.transcription_sha256 != revision.sha256:
            raise ValueError(
                f"annotation set and transcription hash differ: {annotation_set.id}"
            )

    revision_ids = tuple(revision_by_id)
    annotation_ids = tuple(set_by_id)
    artifact_hashes = {
        **{item.id: item.sha256 for item in revisions},
        **{item.id: item.sha256 for item in sets},
    }
    artifact_hashes = dict(sorted(artifact_hashes.items()))
    versions = dict(sorted(specification_versions.items()))
    payload = _manifest_payload(
        manifest_id=manifest_id,
        profile=profile,
        transcription_revision_ids=revision_ids,
        annotation_set_ids=annotation_ids,
        artifact_hashes=artifact_hashes,
        specification_versions=versions,
        publication=publication,
        created_at=created_at,
    )
    return EditionBuildManifest(
        **payload,
        sha256=payload_sha256(payload),
    )


def validate_manifest(manifest: EditionBuildManifest) -> None:
    """Verify stable ordering and the hash carried by a build manifest."""

    if manifest.transcription_revision_ids != tuple(
        sorted(manifest.transcription_revision_ids)
    ):
        raise ValueError("transcription revision ids are not in deterministic order")
    if manifest.annotation_set_ids != tuple(sorted(manifest.annotation_set_ids)):
        raise ValueError("annotation set ids are not in deterministic order")
    if list(manifest.artifact_hashes) != sorted(manifest.artifact_hashes):
        raise ValueError("artifact hashes are not in deterministic order")
    if list(manifest.specification_versions) != sorted(manifest.specification_versions):
        raise ValueError("specification versions are not in deterministic order")
    payload = _manifest_payload(
        manifest_id=manifest.id,
        profile=manifest.profile,
        transcription_revision_ids=manifest.transcription_revision_ids,
        annotation_set_ids=manifest.annotation_set_ids,
        artifact_hashes=manifest.artifact_hashes,
        specification_versions=manifest.specification_versions,
        publication=PublicationStatus(manifest.publication),
        created_at=manifest.created_at,
    )
    actual = payload_sha256(payload)
    if actual != manifest.sha256:
        raise ValueError(
            f"manifest hash mismatch: expected {manifest.sha256}, got {actual}"
        )
