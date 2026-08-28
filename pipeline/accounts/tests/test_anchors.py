"""PAGE import and exact source-anchor tests."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from pipeline.accounts.anchors import (
    _safe_id_part,
    import_page_xml,
    qualified_line_id,
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


# PAGE is a trust boundary: a document that breaks line identity or geometry is
# refused on import rather than carried into anchors that cannot be resolved.

PAGE_NS = "http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15"
PAGE_ATTRS = 'imageWidth="2000" imageHeight="1200"'

REGION_LEFT = (
    '<TextRegion id="r-left">'
    '<Coords points="100,100 900,100 900,1000 100,1000"/>'
    '<TextLine id="l-left-1">'
    '<Coords points="150,200 800,200 800,250 150,250"/>'
    "<TextEquiv><Unicode>Hanns</Unicode></TextEquiv>"
    "</TextLine>"
    "</TextRegion>"
)
REGION_UNLISTED = (
    '<TextRegion id="r-unlisted">'
    '<Coords points="100,100 900,100 900,1000 100,1000"/>'
    '<TextLine id="l-unlisted-1">'
    "<TextEquiv><Unicode>ohne Eintrag im Leseweg</Unicode></TextEquiv>"
    "</TextLine>"
    "</TextRegion>"
)
REGION_LISTED = (
    '<TextRegion id="r-listed">'
    '<Coords points="1100,100 1900,100 1900,1000 1100,1000"/>'
    '<TextLine id="l-listed-1">'
    "<TextEquiv><Unicode>im Leseweg</Unicode></TextEquiv>"
    "</TextLine>"
    "</TextRegion>"
)


def _page_document(body: str, attrs: str = PAGE_ATTRS) -> str:
    return (
        f'<PcGts xmlns="{PAGE_NS}">'
        f'<Page imageFilename="synthetic.jpg" {attrs}>{body}</Page>'
        "</PcGts>"
    )


def _reading_order(*entries: str) -> str:
    return (
        '<ReadingOrder><OrderedGroup id="reading-order">'
        + "".join(entries)
        + "</OrderedGroup></ReadingOrder>"
    )


IMPORT_ERRORS = (
    (
        "missing imageWidth",
        _page_document(REGION_LEFT, 'imageHeight="1200"'),
        "integer imageWidth",
    ),
    (
        "non-numeric imageWidth",
        _page_document(REGION_LEFT, 'imageWidth="breit" imageHeight="1200"'),
        "integer imageWidth",
    ),
    (
        "non-positive imageWidth",
        _page_document(REGION_LEFT, 'imageWidth="0" imageHeight="1200"'),
        "imageWidth must be positive",
    ),
    (
        "TextRegion without id",
        _page_document('<TextRegion><Coords points="100,100 900,100"/></TextRegion>'),
        "TextRegion without id",
    ),
    (
        "TextLine without id",
        _page_document(
            '<TextRegion id="r-left"><TextLine>'
            '<Coords points="150,200 800,200"/>'
            "</TextLine></TextRegion>"
        ),
        "TextLine without id in region r-left",
    ),
    (
        "duplicate line id in one region",
        _page_document(
            '<TextRegion id="r-left">'
            '<TextLine id="l-1"/><TextLine id="l-1"/>'
            "</TextRegion>"
        ),
        "duplicate PAGE line id in region: r-left/l-1",
    ),
    (
        "duplicate region reference in the reading order",
        _page_document(
            _reading_order(
                '<RegionRefIndexed index="0" regionRef="r-left"/>',
                '<RegionRefIndexed index="1" regionRef="r-left"/>',
            )
            + REGION_LEFT
        ),
        "duplicate PAGE region reference in reading order",
    ),
    (
        "invalid reading-order index",
        _page_document(
            _reading_order('<RegionRefIndexed index="erste" regionRef="r-left"/>')
            + REGION_LEFT
        ),
        "invalid PAGE reading-order index",
    ),
    (
        "invalid point",
        _page_document(
            '<TextRegion id="r-left"><Coords points="100,100 neun,zehn"/></TextRegion>'
        ),
        "invalid PAGE point",
    ),
)


@pytest.mark.parametrize(
    ("xml", "message"),
    [(xml, message) for _, xml, message in IMPORT_ERRORS],
    ids=[name for name, _, _ in IMPORT_ERRORS],
)
def test_a_broken_page_document_is_refused_on_import(xml: str, message: str) -> None:
    with pytest.raises(ValueError, match=re.escape(message)):
        import_page_xml(xml, document_id=1, scan_number=1, revision_id="tr-1")


def test_a_region_outside_the_reading_order_follows_the_listed_ones() -> None:
    """An incomplete ReadingOrder orders what it names and keeps the rest in
    document order behind it, so no region is dropped for lack of an entry."""
    xml = _page_document(
        _reading_order('<RegionRefIndexed index="0" regionRef="r-listed"/>')
        + REGION_UNLISTED
        + REGION_LISTED
    )
    revision = import_page_xml(xml, document_id=1, scan_number=1, revision_id="tr-1")
    assert [line.text for line in revision.lines] == [
        "im Leseweg",
        "ohne Eintrag im Leseweg",
    ]
    # the fallback order counts from behind the listed entries and off the
    # sorted position, so it leaves a gap and stays strictly increasing
    assert [line.region_reading_order for line in revision.lines] == [0, 2]


def test_a_single_page_scan_carries_no_side_of_an_opening() -> None:
    """Side is descriptive layout data and stays out of the text identity, so
    reading the same page as a single scan leaves the hash and the ids alone."""
    xml = (FIXTURES / "page.xml").read_text(encoding="utf-8")
    single = import_page_xml(
        xml,
        document_id=12514730,
        scan_number=1,
        revision_id="tr-rb2-001",
        spread=False,
    )
    spread = _revision()
    assert [line.anchor.side for line in single.lines] == [Side.SINGLE] * 3
    assert [line.id for line in single.lines] == [line.id for line in spread.lines]
    assert single.sha256 == spread.sha256


SAFE_ID_CASES = (
    ("r-left", "r-left"),
    ("a.b_c-1", "a.b_c-1"),
    ("  r 1  ", "r-1"),
    ("region:1", "region-1"),
    ("--x--", "x"),
    ("Zeile 1 / Region 2", "Zeile-1-Region-2"),
)


def test_page_ids_are_reduced_to_xml_id_characters() -> None:
    for raw, expected in SAFE_ID_CASES:
        assert _safe_id_part(raw) == expected, f"_safe_id_part({raw!r})"
    for raw in ("", "   ", "###"):
        with pytest.raises(ValueError, match="at least one XML-id character"):
            _safe_id_part(raw)
    assert qualified_line_id(1, 2, "region 3", "line:4") == "line-1-2-region-3-line-4"
