"""PAGE-XML import and source-anchor verification for DoCTA accounts.

The importer keeps every PAGE ``TextLine``, including one without a
``TextEquiv``, and retains region and line polygons, baselines and explicit
region reading order.

The returned transcription revision is self-contained and requires no network
access. Hash verification deliberately covers textual identity and line order;
layout coordinates may be corrected without pretending that the reading itself
changed.

Identity therefore rests on document, scan, PAGE region id and PAGE line id,
which the importer validates as unique per page. ``Side`` is derived from
polygon geometry and stays out of the qualified line id, out of the text hash
and out of anchor resolution. A corrected polygon that moves a line across the
middle of the image changes the recorded side and leaves every existing anchor
valid. Anchors carry the side as descriptive layout data.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from xml.etree import ElementTree

from .models import (
    PublicationStatus,
    Side,
    SourceAnchor,
    TranscriptionLine,
    TranscriptionRevision,
    VerificationStatus,
    payload_sha256,
)

_XML_ID_PART = re.compile(r"[^A-Za-z0-9_.-]+")


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _children(element: ElementTree.Element, name: str) -> list[ElementTree.Element]:
    return [child for child in element if _local_name(child.tag) == name]


def _first_descendant(
    element: ElementTree.Element,
    name: str,
) -> ElementTree.Element | None:
    return next(
        (item for item in element.iter() if _local_name(item.tag) == name), None
    )


def _points(raw: str | None) -> tuple[tuple[int, int], ...]:
    if not raw:
        return ()
    points: list[tuple[int, int]] = []
    for item in raw.split():
        try:
            x_text, y_text = item.split(",", 1)
            points.append((round(float(x_text)), round(float(y_text))))
        except ValueError as exc:
            raise ValueError(f"invalid PAGE point: {item!r}") from exc
    return tuple(points)


def _coords(element: ElementTree.Element) -> tuple[tuple[int, int], ...]:
    coord = next(
        (child for child in element if _local_name(child.tag) == "Coords"), None
    )
    return _points(coord.get("points") if coord is not None else None)


def _baseline(element: ElementTree.Element) -> tuple[tuple[int, int], ...]:
    baseline = next(
        (child for child in element if _local_name(child.tag) == "Baseline"), None
    )
    return _points(baseline.get("points") if baseline is not None else None)


def _line_text(element: ElementTree.Element) -> str:
    unicode_node = _first_descendant(element, "Unicode")
    return (
        "" if unicode_node is None or unicode_node.text is None else unicode_node.text
    )


def _safe_id_part(value: str) -> str:
    part = _XML_ID_PART.sub("-", value.strip()).strip("-")
    if not part:
        raise ValueError("PAGE ids must contain at least one XML-id character")
    return part


def qualified_line_id(
    document_id: int,
    scan_number: int,
    region_id: str,
    line_id: str,
) -> str:
    """Stable XML-compatible identifier for one native PAGE line.

    Deliberately free of derived layout information so that a coordinate
    correction cannot change the id, the text hash or anchor validity.
    """

    return (
        f"line-{document_id}-{scan_number}-"
        f"{_safe_id_part(region_id)}-{_safe_id_part(line_id)}"
    )


def _side(
    points: tuple[tuple[int, int], ...],
    region_points: tuple[tuple[int, int], ...],
    image_width: int,
    spread: bool,
) -> Side:
    if not spread:
        return Side.SINGLE
    evidence = points or region_points
    if not evidence:
        return Side.SINGLE
    midpoint = sum(point[0] for point in evidence) / len(evidence)
    return Side.LEFT if midpoint < image_width / 2 else Side.RIGHT


def _region_order(page: ElementTree.Element) -> dict[str, int]:
    indexed: list[tuple[int, str]] = []
    for element in page.iter():
        if _local_name(element.tag) != "RegionRefIndexed":
            continue
        reference = element.get("regionRef")
        index = element.get("index")
        if reference and index is not None:
            try:
                indexed.append((int(index), reference))
            except ValueError as exc:
                raise ValueError(
                    f"invalid PAGE reading-order index: {index!r}"
                ) from exc
    indexed.sort()
    if len({reference for _, reference in indexed}) != len(indexed):
        raise ValueError("duplicate PAGE region reference in reading order")
    return {reference: index for index, reference in indexed}


def _hash_rows(
    document_id: int,
    revision_id: str,
    rows: Iterable[tuple[str, str]],
) -> str:
    payload = {
        "documentId": document_id,
        "revisionId": revision_id,
        "lines": [{"id": line_id, "text": text} for line_id, text in rows],
    }
    return payload_sha256(payload)


def transcription_sha256(revision: TranscriptionRevision) -> str:
    """Recompute the canonical textual hash of a transcription revision."""

    return _hash_rows(
        revision.document_id,
        revision.id,
        ((line.id, line.text) for line in revision.lines),
    )


def import_page_xml(
    xml: str | bytes,
    *,
    document_id: int,
    scan_number: int,
    revision_id: str,
    spread: bool = True,
    verification: VerificationStatus = VerificationStatus.UNREVIEWED,
    publication: PublicationStatus = PublicationStatus.UNPUBLISHED,
) -> TranscriptionRevision:
    """Create one revision from a PAGE document without dropping empty lines."""

    root = ElementTree.fromstring(xml)
    page = _first_descendant(root, "Page")
    if page is None:
        raise ValueError("PAGE XML has no Page element")
    try:
        image_width = int(page.get("imageWidth", ""))
    except ValueError as exc:
        raise ValueError("PAGE Page needs an integer imageWidth") from exc
    if image_width <= 0:
        raise ValueError("PAGE imageWidth must be positive")

    regions = _children(page, "TextRegion")
    explicit_order = _region_order(page)
    fallback_start = max(explicit_order.values(), default=-1) + 1
    document_order = {
        region.get("id", ""): index for index, region in enumerate(regions)
    }
    regions.sort(
        key=lambda region: (
            explicit_order.get(
                region.get("id", ""),
                fallback_start + document_order[region.get("id", "")],
            ),
            document_order[region.get("id", "")],
        )
    )

    drafts: list[dict[str, object]] = []
    seen_native: set[tuple[str, str]] = set()
    for fallback_region_order, region in enumerate(regions):
        region_id = region.get("id", "").strip()
        if not region_id:
            raise ValueError("TextRegion without id")
        region_order = explicit_order.get(
            region_id, fallback_start + fallback_region_order
        )
        region_polygon = _coords(region)
        for line_order, line in enumerate(_children(region, "TextLine")):
            native_line_id = line.get("id", "").strip()
            if not native_line_id:
                raise ValueError(f"TextLine without id in region {region_id}")
            native_key = (region_id, native_line_id)
            if native_key in seen_native:
                raise ValueError(
                    f"duplicate PAGE line id in region: {region_id}/{native_line_id}"
                )
            seen_native.add(native_key)
            line_polygon = _coords(line)
            side = _side(line_polygon, region_polygon, image_width, spread)
            text = _line_text(line)
            drafts.append(
                {
                    "id": qualified_line_id(
                        document_id,
                        scan_number,
                        region_id,
                        native_line_id,
                    ),
                    "side": side,
                    "region_id": region_id,
                    "line_id": native_line_id,
                    "text": text,
                    "region_polygon": region_polygon,
                    "line_polygon": line_polygon,
                    "baseline": _baseline(line),
                    "region_reading_order": region_order,
                    "line_reading_order": line_order,
                }
            )

    digest = _hash_rows(
        document_id,
        revision_id,
        ((str(item["id"]), str(item["text"])) for item in drafts),
    )
    lines: list[TranscriptionLine] = []
    for reading_order, item in enumerate(drafts):
        text = str(item["text"])
        anchor = SourceAnchor(
            document_id=document_id,
            scan_number=scan_number,
            side=item["side"],
            region_id=item["region_id"],
            line_id=item["line_id"],
            start=0,
            end=len(text),
            quote=text,
            transcription_revision_id=revision_id,
            transcription_sha256=digest,
        )
        lines.append(
            TranscriptionLine(
                id=item["id"],
                anchor=anchor,
                text=text,
                region_polygon=item["region_polygon"],
                line_polygon=item["line_polygon"],
                baseline=item["baseline"],
                region_reading_order=item["region_reading_order"],
                line_reading_order=item["line_reading_order"],
                reading_order=reading_order,
            )
        )
    return TranscriptionRevision(
        id=revision_id,
        document_id=document_id,
        verification=verification,
        publication=publication,
        lines=tuple(lines),
        sha256=digest,
    )


def validate_revision(revision: TranscriptionRevision) -> None:
    """Fail when a revision's stored hash no longer identifies its text."""

    actual = transcription_sha256(revision)
    if actual != revision.sha256:
        raise ValueError(
            f"transcription hash mismatch: expected {revision.sha256}, got {actual}"
        )


def validate_anchor(anchor: SourceAnchor, revision: TranscriptionRevision) -> None:
    """Resolve and verify one anchor against its exact transcription basis."""

    validate_revision(revision)
    if anchor.document_id != revision.document_id:
        raise ValueError("anchor document does not match transcription revision")
    if anchor.transcription_revision_id != revision.id:
        raise ValueError("anchor revision id does not match transcription revision")
    if anchor.transcription_sha256 != revision.sha256:
        raise ValueError("anchor hash does not match transcription revision")
    line = next(
        (
            item
            for item in revision.lines
            if item.anchor.scan_number == anchor.scan_number
            and item.anchor.region_id == anchor.region_id
            and item.anchor.line_id == anchor.line_id
        ),
        None,
    )
    if line is None:
        raise ValueError("anchor line does not exist in transcription revision")
    if anchor.end > len(line.text):
        raise ValueError("anchor ends beyond transcription line")
    if line.text[anchor.start : anchor.end] != anchor.quote:
        raise ValueError("anchor quote does not match transcription revision")
