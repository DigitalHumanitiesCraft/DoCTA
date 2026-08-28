"""Versioned data contracts for the DoCTA account-book pipeline.

The models form the JSON trust boundary shared by transcription, annotation,
review, TEI generation and RDF generation. Python uses snake_case while JSON
uses the camelCase convention of the existing repository. Models are frozen so
that a proposal or decision is replaced by a new artifact rather than edited in
memory. Domain operations live in ``anchors.py``, ``review.py`` and
``build_manifest.py``.

The module makes no network calls. JSON writes are atomic and refuse to replace
an existing artifact unless the caller explicitly requests it.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from typing import Annotated, Any, ClassVar, TypeVar

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

SHA256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
XML_ID = Annotated[str, StringConstraints(pattern=r"^[A-Za-z_][A-Za-z0-9_.-]*$")]
NON_EMPTY = Annotated[str, StringConstraints(min_length=1)]
Point = tuple[int, int]


def _to_camel(name: str) -> str:
    head, *tail = name.split("_")
    return head + "".join(part.capitalize() for part in tail)


class ContractModel(BaseModel):
    """Strict, frozen base for every serialized accounts contract."""

    model_config = ConfigDict(
        alias_generator=_to_camel,
        extra="forbid",
        frozen=True,
        populate_by_name=True,
        use_enum_values=True,
    )


class VerificationStatus(StrEnum):
    """Human verification level of a transcription artifact."""

    UNREVIEWED = "unreviewed"
    FACSIMILE_REVIEWED = "facsimile-reviewed"
    FACSIMILE_VERIFIED = "facsimile-verified"


class EditorialDecision(StrEnum):
    """Editorial decision state of an annotation artifact."""

    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    AMBIGUOUS = "ambiguous"
    WITHHELD = "withheld"
    STALE = "stale"
    SUPERSEDED = "superseded"


class PublicationStatus(StrEnum):
    """Publication state, independent of verification and editorial review."""

    UNPUBLISHED = "unpublished"
    PUBLISHED = "published"
    WITHDRAWN = "withdrawn"


class Side(StrEnum):
    """Physical side represented by a line on a scan."""

    LEFT = "left"
    RIGHT = "right"
    SINGLE = "single"


class SourceAnchor(ContractModel):
    """Character-exact source reference tied to one transcription revision."""

    document_id: int = Field(gt=0)
    scan_number: int = Field(gt=0)
    side: Side
    region_id: NON_EMPTY
    line_id: NON_EMPTY
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    quote: str
    transcription_revision_id: XML_ID
    transcription_sha256: SHA256

    @model_validator(mode="after")
    def _valid_span(self) -> SourceAnchor:
        if self.end < self.start:
            raise ValueError("end must not precede start")
        if self.end - self.start != len(self.quote):
            raise ValueError("quote length must equal end minus start")
        return self


class TranscriptionLine(ContractModel):
    """One PAGE line with text, source geometry and stable reading order."""

    id: XML_ID
    anchor: SourceAnchor
    text: str
    region_polygon: tuple[Point, ...] = ()
    line_polygon: tuple[Point, ...] = ()
    baseline: tuple[Point, ...] = ()
    region_reading_order: int = Field(ge=0)
    line_reading_order: int = Field(ge=0)
    reading_order: int = Field(ge=0)

    @model_validator(mode="after")
    def _anchor_matches_text(self) -> TranscriptionLine:
        if self.anchor.end > len(self.text):
            raise ValueError("anchor ends beyond transcription line")
        if self.text[self.anchor.start : self.anchor.end] != self.anchor.quote:
            raise ValueError("anchor quote does not match transcription line")
        return self


class TranscriptionRevision(ContractModel):
    """Immutable, ordered transcription state for one source document."""

    id: XML_ID
    document_id: int = Field(gt=0)
    verification: VerificationStatus
    publication: PublicationStatus = PublicationStatus.UNPUBLISHED
    lines: tuple[TranscriptionLine, ...]
    sha256: SHA256

    @model_validator(mode="after")
    def _consistent_lines(self) -> TranscriptionRevision:
        line_ids: set[str] = set()
        reading_orders: set[int] = set()
        for line in self.lines:
            anchor = line.anchor
            if line.id in line_ids:
                raise ValueError(f"duplicate transcription line id: {line.id}")
            if line.reading_order in reading_orders:
                raise ValueError(f"duplicate reading order: {line.reading_order}")
            if anchor.document_id != self.document_id:
                raise ValueError(f"line {line.id} belongs to another document")
            if anchor.transcription_revision_id != self.id:
                raise ValueError(f"line {line.id} belongs to another revision")
            if anchor.transcription_sha256 != self.sha256:
                raise ValueError(f"line {line.id} carries another revision hash")
            line_ids.add(line.id)
            reading_orders.add(line.reading_order)
        return self


class AnnotationProposal(ContractModel):
    """Immutable candidate annotation awaiting a separate review decision."""

    id: XML_ID
    kind: NON_EMPTY
    anchor: SourceAnchor
    payload: dict[str, Any]
    transcription_revision_id: XML_ID
    transcription_sha256: SHA256
    editorial_status: EditorialDecision = EditorialDecision.PROPOSED
    created_by: NON_EMPTY
    created_at: datetime
    provenance: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _proposal_contract(self) -> AnnotationProposal:
        if self.editorial_status != EditorialDecision.PROPOSED.value:
            raise ValueError("an AnnotationProposal must remain proposed")
        if self.anchor.transcription_revision_id != self.transcription_revision_id:
            raise ValueError("proposal and anchor use different revisions")
        if self.anchor.transcription_sha256 != self.transcription_sha256:
            raise ValueError("proposal and anchor use different transcription hashes")
        return self


class ReviewDecision(ContractModel):
    """Human decision on one immutable annotation proposal."""

    id: XML_ID
    proposal_id: XML_ID
    outcome: EditorialDecision
    reviewer: NON_EMPTY
    decided_at: datetime
    transcription_revision_id: XML_ID
    transcription_sha256: SHA256
    note: str = ""

    @model_validator(mode="after")
    def _is_decision(self) -> ReviewDecision:
        if self.outcome == EditorialDecision.PROPOSED.value:
            raise ValueError("a ReviewDecision needs an outcome other than proposed")
        return self


class AnnotationSet(ContractModel):
    """Accepted annotation selection locked to one transcription revision."""

    id: XML_ID
    transcription_revision_id: XML_ID
    transcription_sha256: SHA256
    proposal_ids: tuple[XML_ID, ...]
    decision_ids: tuple[XML_ID, ...]
    editorial_status: EditorialDecision = EditorialDecision.ACCEPTED
    publication: PublicationStatus = PublicationStatus.UNPUBLISHED
    created_at: datetime
    sha256: SHA256

    @model_validator(mode="after")
    def _accepted_set(self) -> AnnotationSet:
        if self.editorial_status != EditorialDecision.ACCEPTED.value:
            raise ValueError("an AnnotationSet contains accepted proposals only")
        if len(self.proposal_ids) != len(set(self.proposal_ids)):
            raise ValueError("proposal ids must be unique")
        if len(self.decision_ids) != len(set(self.decision_ids)):
            raise ValueError("decision ids must be unique")
        if len(self.proposal_ids) != len(self.decision_ids):
            raise ValueError("each accepted proposal needs one review decision")
        return self


class EditionBuildManifest(ContractModel):
    """Deterministic lock of accepted inputs for one edition build."""

    id: XML_ID
    profile: NON_EMPTY
    transcription_revision_ids: tuple[XML_ID, ...]
    annotation_set_ids: tuple[XML_ID, ...]
    artifact_hashes: dict[str, SHA256]
    specification_versions: dict[str, NON_EMPTY]
    publication: PublicationStatus = PublicationStatus.UNPUBLISHED
    created_at: datetime
    sha256: SHA256

    @model_validator(mode="after")
    def _unique_references(self) -> EditionBuildManifest:
        for name, values in (
            ("transcription revision", self.transcription_revision_ids),
            ("annotation set", self.annotation_set_ids),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"{name} ids must be unique")
        referenced = set(self.transcription_revision_ids) | set(self.annotation_set_ids)
        if referenced != set(self.artifact_hashes):
            raise ValueError(
                "artifactHashes must cover exactly the referenced artifacts"
            )
        return self


ArtifactModel = TypeVar("ArtifactModel", bound=ContractModel)
CORE_MODELS: tuple[type[ContractModel], ...] = (
    SourceAnchor,
    TranscriptionLine,
    TranscriptionRevision,
    AnnotationProposal,
    ReviewDecision,
    AnnotationSet,
    EditionBuildManifest,
)
CORE_SPECIFICATION_ID: ClassVar[str] = "docta-accounts-core"
CORE_SPECIFICATION_VERSION: ClassVar[str] = "1.0.0"


def model_payload(
    model: ContractModel,
    *,
    exclude: set[str] | None = None,
) -> dict[str, Any]:
    """JSON-ready camelCase payload used by files and deterministic hashes."""

    return model.model_dump(mode="json", by_alias=True, exclude=exclude or set())


def canonical_json(payload: Any) -> str:
    """Stable compact JSON representation for content hashes."""

    return json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )


def payload_sha256(payload: Any) -> str:
    """SHA-256 over the canonical UTF-8 JSON form of a payload."""

    return sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def load_model(path: Path, model_type: type[ArtifactModel]) -> ArtifactModel:
    """Read and validate one contract artifact from JSON."""

    return model_type.model_validate_json(path.read_text(encoding="utf-8"))


def write_model_atomic(
    path: Path,
    model: ContractModel,
    *,
    overwrite: bool = False,
) -> None:
    """Write one model atomically, preserving immutable artifact files.

    Rewriting byte-identical content is idempotent. Different existing content
    is refused unless ``overwrite`` is explicit.
    """

    payload = json.dumps(model_payload(model), ensure_ascii=False, indent=1) + "\n"
    encoded = payload.encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() == encoded:
            return
        if not overwrite:
            raise FileExistsError(
                f"artifact already exists with different content: {path}"
            )

    handle, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        temp_path.replace(path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def model_schemas() -> dict[str, dict[str, Any]]:
    """CamelCase JSON Schemas for the versioned core data specification."""

    return {
        model.__name__: model.model_json_schema(by_alias=True) for model in CORE_MODELS
    }
