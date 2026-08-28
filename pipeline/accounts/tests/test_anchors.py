"""PAGE import and exact source-anchor tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from pipeline.accounts.anchors import (
    import_page_xml,
    transcription_sha256,
    validate_anchor,
    validate_revision,
)
from pipeline.accounts.models import Side, SourceAnchor, TranscriptionRevision

FIXTURES = Path(__file__).parent / "fixtures" / "core"


def _revision(page: str = "page.xml") -> TranscriptionRevision:
    return import_page_xml(
        (FIXTURES / page).read_text(encoding="utf-8"),
        document_id=12514730,
        scan_number=1,
        revision_id="tr-rb2-001",
    )


def test_page_import_keeps_empty_lines_and_explicit_reading_order() -> None:
    revision = _revision()
    assert [line.text for line in revision.lines] == ["Hanns", "", "Item sechs Pfund"]
    assert [line.reading_order for line in revision.lines] == [0, 1, 2]
    assert revision.lines[0].anchor.side is Side.LEFT
    assert revision.lines[2].anchor.side is Side.RIGHT
    assert revision.lines[1].anchor.start == revision.lines[1].anchor.end == 0
    assert revision.lines[1].anchor.quote == ""


def test_page_import_preserves_geometry_and_stable_qualified_ids() -> None:
    first = _revision().lines[0]
    assert first.id == "line-12514730-1-r-left-l-left-1"
    assert first.region_polygon == ((100, 100), (900, 100), (900, 1000), (100, 1000))
    assert first.line_polygon == ((150, 200), (800, 200), (800, 250), (150, 250))
    assert first.baseline == ((150, 240), (800, 240))
    assert first.region_reading_order == 0


def test_revision_and_anchor_hashes_verify() -> None:
    revision = _revision()
    assert transcription_sha256(revision) == revision.sha256
    validate_revision(revision)
    validate_anchor(revision.lines[2].anchor, revision)


def test_corrected_coordinates_leave_text_identity_and_anchors_intact() -> None:
    """A layout correction that flips the derived side must not touch identity.

    The two fixtures carry the same ids and the same text and differ only in
    their polygons, swapped so that every line lands on the other half of the
    spread.
    """

    original = _revision()
    corrected = _revision("page-shifted-coordinates.xml")

    assert [line.anchor.side for line in original.lines] == [
        Side.LEFT,
        Side.LEFT,
        Side.RIGHT,
    ]
    assert [line.anchor.side for line in corrected.lines] == [
        Side.RIGHT,
        Side.RIGHT,
        Side.LEFT,
    ]
    assert [line.text for line in corrected.lines] == [
        line.text for line in original.lines
    ]
    assert [line.id for line in corrected.lines] == [line.id for line in original.lines]
    assert corrected.sha256 == original.sha256
    assert corrected.lines[0].line_polygon != original.lines[0].line_polygon

    for line in original.lines:
        validate_anchor(line.anchor, corrected)


def test_changed_quote_is_rejected_against_revision() -> None:
    revision = _revision()
    original = revision.lines[0].anchor
    changed = SourceAnchor.model_validate(
        {
            **original.model_dump(mode="json", by_alias=True),
            "end": 4,
            "quote": "Hans",
        }
    )
    with pytest.raises(ValueError, match="quote does not match"):
        validate_anchor(changed, revision)
