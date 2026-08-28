"""Tests for the TEI builder, runnable with pytest or plain python.

Integration tests against the real repo data; the TEI stage has no fixtures of
its own, its input is the Transkribus export in the repository.

Usage:
  python test_build_tei.py
  pytest pipeline/test_build_tei.py
"""

import json
import re
import sys
import tempfile
from pathlib import Path
from xml.etree import ElementTree

import apply_review as ar
import build_register as br
import build_tei as bt
import entity_index as ei

TEI = "{http://www.tei-c.org/ns/1.0}"

# two documents of different size, read from the export for the count checks
SAMPLES = (11327963, 11328042)

# every page marked DONE in Transkribus; these carry the human-corrected wording
FULLY_CORRECTED = (11328300, 11330019, 11330020)
MACHINE_SAMPLE = 11327963

# a document of the Inventaria campaign with no page marked done in Transkribus,
# and the one attributed document the edition-link harvest found no entry for
ATTRIBUTED_MACHINE = 11327963
ATTRIBUTED_WITHOUT_LINK = 11329439

# the document carrying the prototype entity extraction, and one without any
DEMO_DOC = 11328300
NON_DEMO_DOC = 11327963

# the document the review fixture is written against, and one of its lines
REVIEW_DOC = 11327963
REVIEW_PAGE = 2
REVIEW_LINE = "r2l1"
REVIEW_TEXT = "Auf dem klainen estrich"
REVIEWER = "XY"
REVIEW_DATE = "2026-09-03"

XML_ID = "{http://www.w3.org/XML/1998/namespace}id"


def _built() -> dict[int, str]:
    with tempfile.TemporaryDirectory() as td:
        return bt.build(Path(td))


def _has_entities(doc_id: int) -> bool:
    return bt._entity_data(doc_id) is not None


def _export(doc_id: int) -> dict:
    path = bt.DATA / "transcriptions" / f"{doc_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ unit tests
# The pure functions of the generator, checked against written-out literals; the
# corpus exercises only the values it happens to carry.

# Archival dating strings and the origDate the normalisation has to produce.
ORIGDATE_CASES = (
    (
        {"raw": "1471.09.25", "start": 1471, "end": 1471},
        '<origDate when="1471-09-25">1471.09.25</origDate>',
    ),
    (
        {"raw": "1471", "start": 1471, "end": 1471},
        '<origDate when="1471">1471</origDate>',
    ),
    ({"raw": "  1471  ", "start": 1471}, '<origDate when="1471">1471</origDate>'),
    (
        {"raw": "1471-1475", "start": 1471, "end": 1475},
        '<origDate from="1471" to="1475">1471-1475</origDate>',
    ),
    (
        {"raw": "um 1471", "start": 1466, "end": 1476, "circa": True},
        '<origDate notBefore="1466" notAfter="1476">um 1471</origDate>',
    ),
    (
        {"raw": "nach 1471", "start": 1471, "end": None, "circa": True},
        '<origDate notBefore="1471">nach 1471</origDate>',
    ),
    (
        {"raw": "vor 1471", "start": None, "end": 1471, "circa": True},
        '<origDate notAfter="1471">vor 1471</origDate>',
    ),
    ({"raw": "ohne Datum", "circa": True}, "<origDate>ohne Datum</origDate>"),
    # an unparsable raw value keeps its content and claims no normalisation
    ({"raw": "15. Jahrhundert"}, "<origDate>15. Jahrhundert</origDate>"),
    ({"raw": "1471.9.25"}, "<origDate>1471.9.25</origDate>"),
    ({"raw": "1471 & 1475"}, "<origDate>1471 &amp; 1475</origDate>"),
    ({"raw": "", "start": 1471}, None),
    ({"raw": "   "}, None),
    ({"raw": None}, None),
    ({}, None),
)


def test_origdate_normalises_only_as_far_as_the_raw_value_allows() -> None:
    for dating, expected in ORIGDATE_CASES:
        assert bt._origdate(dating) == expected, f"_origdate on {dating}"


# raw text, element content, attribute value
ESCAPE_CASES = (
    ("Hanns & Ruprecht", "Hanns &amp; Ruprecht", "Hanns &amp; Ruprecht"),
    ("<lb/>", "&lt;lb/&gt;", "&lt;lb/&gt;"),
    ("&amp;", "&amp;amp;", "&amp;amp;"),
    ('sagt "ja"', 'sagt "ja"', "sagt &quot;ja&quot;"),
    ("a\x00b\x07c\x1fd", "abcd", "abcd"),
    ("zeile\tund\nzeile\r", "zeile\tund\nzeile\r", "zeile\tund\nzeile\r"),
    ("", "", ""),
)


def test_escaping_strips_control_characters_and_quotes_only_in_attributes() -> None:
    for raw, content, attribute in ESCAPE_CASES:
        assert bt._esc(raw) == content, f"_esc on {raw!r}"
        assert bt._att(raw) == attribute, f"_att on {raw!r}"


# done pages, pages, correction state
CORRECTION_CASES = (
    (10, 10, bt.CORRECTED),
    (11, 10, bt.CORRECTED),
    (5, 10, bt.PARTLY),
    (1, 10, bt.PARTLY),
    (0, 10, bt.MACHINE),
    (None, 10, bt.MACHINE),
    (10, None, bt.MACHINE),
    (10, 0, bt.MACHINE),
    (None, None, bt.MACHINE),
)


def test_correction_state_from_the_done_page_count() -> None:
    """The partly-corrected branch has no document in the corpus, so this table
    is the only place it is exercised at all."""
    for done, pages, expected in CORRECTION_CASES:
        assert bt._correction(done, pages) == expected, f"_correction({done}, {pages})"


# ----------------------------------------------------------- integration tests


def test_every_document_parses() -> None:
    built = _built()
    assert built, "no TEI documents built"
    for doc_id, xml in built.items():
        root = ElementTree.fromstring(xml)
        assert root.tag == f"{TEI}TEI", f"unexpected root in {doc_id}"


def test_line_counts_match_the_export() -> None:
    """Every exported line is either an lb or a folio milestone, never dropped.

    The expectation is counted off the export JSON, so the check does not go
    through the same line iteration the generator uses.
    """
    built = _built()
    for doc_id in SAMPLES:
        exported = sum(
            len(region.get("lines") or [])
            for page in _export(doc_id)["pages"]
            for region in page.get("regions") or []
        )
        root = ElementTree.fromstring(built[doc_id])
        body = root.find(f"{TEI}text")
        encoded = sum(1 for _ in body.iter(f"{TEI}lb"))
        milestones = sum(1 for _ in body.iter(f"{TEI}milestone"))
        assert exported, f"empty export for {doc_id}"
        assert encoded + milestones == exported, f"line count differs in {doc_id}"


# The mark forms of the corpus with the value the generator has to read off each
# one, plus the neighbouring forms that are ordinary text: the dominant
# "[fol.2r]", the spaced and the bare variant, the endpaper marks, the lacuna
# "[- - -]" and a line that carries a mark beside other words.
FOLIO_CASES = (
    ("[fol.2r]", "2r"),
    ("[fol. 2r]", "2r"),
    ("[fol.12v]", "12v"),
    ("[1r]", "1r"),
    ("[3]", "3"),
    ("[- - -]", None),
    ("[us_vorne_r]", None),
    ("[fol.3v] item ain kessel", None),
    ("item [fol.3v]", None),
    ("fol.3v", None),
    ("[fol.3v]x", None),
    ("", None),
)

COVER_CASES = (
    ("[us_vorne_r]", "us_vorne_r"),
    ("[us_hinten_v]", "us_hinten_v"),
    ("[fol.2r]", None),
    ("[- - -]", None),
    ("[us_vorne_r] item ain kessel", None),
    ("[us_Vorne_r]", None),
    ("", None),
)


def test_a_mark_is_read_off_a_whole_line_only() -> None:
    for text, expected in FOLIO_CASES:
        m = bt.FOLIO_LINE.match(text)
        assert (m.group(1) if m else None) == expected, f"FOLIO_LINE on {text!r}"
    for text, expected in COVER_CASES:
        m = bt.COVER_LINE.match(text)
        assert (m.group(1) if m else None) == expected, f"COVER_LINE on {text!r}"


# Independent re-statement of the mark forms, so the corpus check does not borrow
# the generator's own regexes. It matches anywhere in a line, because a mark that
# survived would sit inside the text of one.
MARK_IN_TEXT = re.compile(r"\[(?:fol\.?\s*)?[0-9]+[rv]?\]|\[us_[a-z]+_[rv]\]")


def test_no_mark_is_left_in_the_body_text() -> None:
    """A mark line is a reference point of the transcription and becomes a
    milestone; none of them survives as text of the source."""
    milestones = 0
    for doc_id, xml in _built().items():
        root = ElementTree.fromstring(xml)
        text = "".join(root.find(f"{TEI}text").itertext())
        marks = MARK_IN_TEXT.findall(text)
        assert not marks, f"marks left in the text of {doc_id}: {marks[:3]}"
        for milestone in root.iter(f"{TEI}milestone"):
            milestones += 1
            assert milestone.get("unit") in ("folio", "cover"), (
                f"unknown milestone unit in {doc_id}"
            )
            assert milestone.get("n"), f"milestone without n in {doc_id}"
            assert milestone.get("facs") is None, (
                f"milestone bound to a zone in {doc_id}"
            )
    assert milestones, "no milestone in the corpus, the check proves nothing"


def test_one_pb_and_one_surface_per_page() -> None:
    built = _built()
    for doc_id, xml in built.items():
        source = br.transcription_of(doc_id, bt.REGISTER)
        page_numbers = [str(p["pageNr"]) for p in source["pages"]]
        root = ElementTree.fromstring(xml)
        pbs = [pb.get("n") for pb in root.iter(f"{TEI}pb")]
        surfaces = [s.get("n") for s in root.iter(f"{TEI}surface")]
        graphics = [g.get("url") for g in root.iter(f"{TEI}graphic")]
        assert pbs == sorted(page_numbers, key=int), f"pb set differs in {doc_id}"
        assert surfaces == pbs, f"surface set differs in {doc_id}"
        assert len(graphics) == len(surfaces) and all(graphics), (
            f"missing graphic url in {doc_id}"
        )
        for pb in root.iter(f"{TEI}pb"):
            assert pb.get("facs") == f"#surface-{doc_id}-{pb.get('n')}"


def test_one_ab_per_text_region() -> None:
    """Regions of the export survive as blocks; nothing is flattened away."""
    built = _built()
    for doc_id in SAMPLES:
        export = bt._load(bt.DATA / "transcriptions" / f"{doc_id}.json")
        expected = [
            f"ab-{doc_id}-{page['pageNr']}-{region['id']}"
            for page in sorted(export["pages"], key=lambda p: p["pageNr"])
            for region in page.get("regions") or []
        ]
        root = ElementTree.fromstring(built[doc_id])
        assert [ab.get(XML_ID) for ab in root.iter(f"{TEI}ab")] == expected, (
            f"ab set differs in {doc_id}"
        )
        div = root.find(f".//{TEI}div")
        # the pb of a page stands beside the blocks of that page, not inside one
        assert [c.tag for c in div].count(f"{TEI}pb") == len(export["pages"])
        for ab in root.iter(f"{TEI}ab"):
            assert ab.find(f"{TEI}pb") is None, f"pb inside an ab in {doc_id}"


def test_header_carries_the_archival_identity() -> None:
    built = _built()
    docs = {d["docId"]: d for d in bt._documents()}
    for doc_id, xml in built.items():
        root = ElementTree.fromstring(xml)
        titles = {t.get("type"): t.text for t in root.iter(f"{TEI}title")}
        assert titles.get("shelfmark") == docs[doc_id]["shelfmark"]
        assert root.find(f".//{TEI}repository").text == bt.REPOSITORY
        assert root.find(f".//{TEI}altIdentifier/{TEI}idno").text == str(doc_id)
        change = root.find(f".//{TEI}change")
        assert change.get("when") == bt.GENERATION_DATE
        assert (
            root.find(f"{TEI}text").get("{http://www.w3.org/XML/1998/namespace}lang")
            == bt.TEXT_LANG
        )
        raw = (docs[doc_id]["dating"] or {}).get("raw")
        origdate = root.find(f".//{TEI}origDate")
        if raw:
            assert origdate is not None and origdate.text == raw
        else:
            assert origdate is None, f"origDate invented in {doc_id}"


# Independent re-statement of the folio and cover mark forms from the corpus
# ("[fol.2r]", "[fol. 2r]", bare "[1r]", "[us_vorne_r]"), written out here so
# the test does not borrow the generator's own regexes.
MARK_LINE = re.compile(r"^\[(?:fol\.\s*)?[0-9]+[rv]?\]$|^\[us_[a-z]+_[rv]\]$")


def test_zone_per_line_with_coordinates() -> None:
    """Every exported line with coordinates gets one zone under its surface;
    folio and cover lines become milestones without facs and get none."""
    built = _built()
    for doc_id in SAMPLES:
        export = bt._load(bt.DATA / "transcriptions" / f"{doc_id}.json")
        expected = [
            (page["pageNr"], line["id"], line["coords"])
            for page in sorted(export["pages"], key=lambda p: p["pageNr"])
            if page.get("iiif")
            for region in page.get("regions") or []
            for line in region.get("lines") or []
            if (line.get("coords") or "").strip()
            and not MARK_LINE.match((line.get("text") or "").strip())
        ]
        root = ElementTree.fromstring(built[doc_id])
        zones = [(z.get(XML_ID), z.get("points")) for z in root.iter(f"{TEI}zone")]
        assert zones == [
            (f"zone-{doc_id}-{nr}-{lid}", coords) for nr, lid, coords in expected
        ], f"zone set differs in {doc_id}"


def test_every_zone_is_referenced_by_an_lb() -> None:
    """No zone is dead layout data: each one is the target of exactly one lb."""
    built = _built()
    for doc_id, xml in built.items():
        root = ElementTree.fromstring(xml)
        zone_ids = {z.get(XML_ID) for z in root.iter(f"{TEI}zone")}
        referenced = {
            lb.get("facs")[1:] for lb in root.iter(f"{TEI}lb") if lb.get("facs")
        }
        assert zone_ids == referenced, f"orphan or dangling zones in {doc_id}"


def test_every_lb_facs_resolves_to_a_zone() -> None:
    """An lb points at a zone or at nothing, never at a missing one.

    A document whose text DoCTA transcribed itself has no layout analysis and
    therefore no zone at all, so its lines are unbound by construction; every
    document that has zones must bind lines to them.
    """
    built = _built()
    for doc_id, xml in built.items():
        root = ElementTree.fromstring(xml)
        ids = {z.get(XML_ID) for z in root.iter(f"{TEI}zone")}
        bound = 0
        for lb in root.iter(f"{TEI}lb"):
            facs = lb.get("facs")
            if facs is None:
                continue
            bound += 1
            assert facs.startswith("#") and facs[1:] in ids, (
                f"dangling lb facs {facs} in {doc_id}"
            )
        assert bool(bound) == bool(ids), f"zones and bound lines disagree in {doc_id}"


def _marked_entities(root: ElementTree.Element) -> list[ElementTree.Element]:
    """Elements bound to the entity responsibility, whatever their tag.

    Tag alone would not do it: <term> also carries the archival category in the
    header, so the responsibility is what separates a marked entity from it.
    """
    return [el for el in root.iter() if el.get("resp") == f"#{bt.RESP_ENTITY}"]


def test_entity_layer_only_where_an_extraction_exists() -> None:
    built = _built()
    assert _has_entities(DEMO_DOC), "the prototype extraction disappeared"
    for doc_id, xml in built.items():
        if not _has_entities(doc_id):
            continue
        root = ElementTree.fromstring(xml)
        assert bt.RESP_ENTITY in _resp_ids(root), f"entity respStmt missing in {doc_id}"
        marked = _marked_entities(root)
        assert marked, f"no entity bound to the entity responsibility in {doc_id}"
        assert {el.tag for el in marked} <= {
            f"{TEI}persName",
            f"{TEI}placeName",
            f"{TEI}term",
        }, f"entity element outside the encoding in {doc_id}"
        assert all(el.get("key") is None for el in marked), (
            f"a normalised form written onto the entity in {doc_id}"
        )
        assert all(
            el.text and (el.get("ref") or "").startswith(f"{bt.REGISTER_FILE}#")
            for el in marked
        ), f"entity without a register reference or content in {doc_id}"
        decl = "".join(root.find(f".//{TEI}editorialDecl").itertext())
        assert "unverified extraction by an LLM agent" in decl

    assert not _has_entities(NON_DEMO_DOC), "the counter-example acquired entities"
    other = ElementTree.fromstring(built[NON_DEMO_DOC])
    assert bt.RESP_ENTITY not in _resp_ids(other), "entity respStmt leaked"
    assert bt.RESP_ENTITY not in built[NON_DEMO_DOC]
    assert not _marked_entities(other), f"entity leaked into {NON_DEMO_DOC}"
    for tag in ("persName", "placeName", "objectName"):
        assert not list(other.iter(f"{TEI}{tag}")), f"{tag} leaked into {NON_DEMO_DOC}"


# ------------------------------------------------------------------- register


def _register(tmp: Path) -> ElementTree.Element:
    return ElementTree.fromstring((tmp / bt.REGISTER_FILE).read_text(encoding="utf-8"))


def test_the_register_carries_the_ids_of_the_entity_index() -> None:
    """The register, the document refs and graph.jsonld share one id space, so
    the register must hold exactly what entity_index.py produces."""
    entries = ei.build_index(ei.load_extractions())
    assert entries, "the entity index is empty, the check proves nothing"
    root = ElementTree.fromstring(bt.register_xml(entries, "2026-08-28"))

    got = {}
    for tag in ("person", "place", "item"):
        for el in root.iter(f"{TEI}{tag}"):
            names = list(el)
            got[el.get(XML_ID)] = (
                names[0].text,
                [n.text for n in names[1:]],
            )
            assert names[0].get("type") is None, "normalised form marked attested"
            assert all(n.get("type") == "attested" for n in names[1:]), (
                f"unmarked spelling in {el.get(XML_ID)}"
            )
    assert got == {
        entry["id"]: (entry["normalized"], entry["forms"]) for entry in entries
    }
    assert root.get(XML_ID) == bt.REGISTER_ID
    assert root.find(f"{TEI}standOff") is not None, "the entries are not standOff"


def test_every_document_reference_resolves_in_the_register() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        built = bt.build(tmp)
        register = _register(tmp)
    ids = {
        el.get(XML_ID)
        for tag in ("person", "place", "item")
        for el in register.iter(f"{TEI}{tag}")
    }
    refs = 0
    for doc_id, xml in built.items():
        root = ElementTree.fromstring(xml)
        for element in _marked_entities(root):
            ref = element.get("ref")
            refs += 1
            file_name, _, target = ref.partition("#")
            assert file_name == bt.REGISTER_FILE, f"foreign register in {doc_id}"
            assert target in ids, f"dangling @ref {ref} in {doc_id}"
    assert refs, "no entity reference in the corpus, the check proves nothing"


def test_the_register_is_byte_identical_on_a_rebuild() -> None:
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        bt.build(Path(a))
        bt.build(Path(b))
        first, second = Path(a) / bt.REGISTER_FILE, Path(b) / bt.REGISTER_FILE
        assert first.is_file(), "no register written"
        assert first.read_bytes() == second.read_bytes(), "register drift"


def test_an_anchored_entity_without_an_index_entry_fails_the_build() -> None:
    """Both sides read the same extraction files, so this cannot happen; a
    silent drop would leave an entity encoded that points at nothing."""
    entities = [_entity("p1", "person", "Hannsen Ramung", "Hans Ramung", 1, "r1l1")]
    original = bt._entity_data
    bt._entity_data = lambda doc_id: {"docId": doc_id, "entities": entities}
    try:
        bt._entity_anchors(MINI_DOC, MINI_PAGES, None, {})
    except ValueError as exc:
        assert "entity index" in str(exc), f"unhelpful error: {exc}"
    else:
        raise AssertionError("an entity without an index entry was encoded")
    finally:
        bt._entity_data = original


# A hand-built export standing in for two pages of two regions. No document of
# the corpus carries all anchor cases at once, and the offsets an anchor has to
# produce can only be checked against written-out numbers.
MINI_DOC = 99999999
MINI_PAGES = [
    {
        "pageNr": 1,
        "iiif": "https://example.org/iiif/1",
        "regions": [
            {
                "id": "r1",
                "lines": [
                    {
                        "id": "r1l1",
                        "text": "Hannsen Ramung ze Thawr",
                        "coords": "1,1 2,2",
                    },
                    {
                        "id": "r1l2",
                        "text": "item ain kessel und ain kessel",
                        "coords": "3,3 4,4",
                    },
                ],
            },
            {
                "id": "r2",
                "lines": [{"id": "r2l1", "text": "sloss Thawr", "coords": "5,5 6,6"}],
            },
        ],
    },
    # the second page repeats the line id of the first, so a page-blind lookup
    # would anchor against the wrong text
    {
        "pageNr": 2,
        "iiif": None,
        "regions": [
            {
                "id": "r1",
                "lines": [
                    {"id": "r1l1", "text": "Burkharten von Knoringen", "coords": ""}
                ],
            }
        ],
    },
]


def _entity(
    entity_id: str,
    kind: str,
    text: str,
    normalized: str | None,
    page_nr: int | None,
    line_id: str | None,
) -> dict:
    """One record in the shape docs/data/entities/<docId>.json carries."""
    return {
        "id": entity_id,
        "type": kind,
        "text": text,
        "normalized": normalized,
        "pageNr": page_nr,
        "lineId": line_id,
    }


# Register ids of the synthetic layer, in the shape entity_index.py produces
# them; the anchor step looks an entity up by (type, normalised form).
MINI_SLUGS = {
    ("person", "Hans Ramung"): "per-hans-ramung",
    ("person", "Ramung"): "per-ramung",
    ("person", "Burkharten von Knoringen"): "per-burkharten-von-knoringen",
    ("place", "Thaur"): "pl-thaur",
    ("place", "Schloss Thaur"): "pl-schloss-thaur",
    ("object", "Kessel"): "obj-kessel",
    ("object", "Napf"): "obj-napf",
}


def _ref(slug: str) -> str:
    return f"{bt.REGISTER_FILE}#{slug}"


def _anchors(
    entities: list[dict], review_texts: dict | None = None
) -> tuple[dict, list[tuple[str, str]]]:
    """Run the anchor step over the mini export with a synthetic entity layer.

    The layer is normally read from disk by _entity_data; swapping that one
    function keeps the test off the repository's entity files and needs no
    fixture, so the plain-python runner keeps working.
    """
    original = bt._entity_data
    bt._entity_data = lambda doc_id: {"docId": doc_id, "entities": entities}
    try:
        return bt._entity_anchors(MINI_DOC, MINI_PAGES, review_texts, MINI_SLUGS)
    finally:
        bt._entity_data = original


def test_an_entity_anchors_where_its_form_sits_once_in_the_named_line() -> None:
    anchors, skipped = _anchors(
        [
            _entity("p1", "person", "Hannsen Ramung", "Hans Ramung", 1, "r1l1"),
            _entity("pl1", "place", "Thawr", "Thaur", 1, "r1l1"),
            _entity("pl2", "place", "sloss Thawr", "Schloss Thaur", 1, "r2l1"),
            _entity("o1", "object", "kessel und ain kessel", "Kessel", 1, "r1l2"),
            _entity("p2", "person", "Burkharten von Knoringen", None, 2, "r1l1"),
        ]
    )
    assert skipped == []
    assert anchors == {
        1: {
            "r1l1": [
                {
                    "start": 0,
                    "end": 14,
                    "element": "persName",
                    "ref": _ref("per-hans-ramung"),
                    "entity_id": "p1",
                },
                {
                    "start": 18,
                    "end": 23,
                    "element": "placeName",
                    "ref": _ref("pl-thaur"),
                    "entity_id": "pl1",
                },
            ],
            "r1l2": [
                {
                    "start": 9,
                    "end": 30,
                    "element": "term",
                    "ref": _ref("obj-kessel"),
                    "entity_id": "o1",
                }
            ],
            "r2l1": [
                {
                    "start": 0,
                    "end": 11,
                    "element": "placeName",
                    "ref": _ref("pl-schloss-thaur"),
                    "entity_id": "pl2",
                }
            ],
        },
        # no normalised form: the surface form itself identifies the entry
        2: {
            "r1l1": [
                {
                    "start": 0,
                    "end": 24,
                    "element": "persName",
                    "ref": _ref("per-burkharten-von-knoringen"),
                    "entity_id": "p2",
                }
            ]
        },
    }


def test_an_entity_that_cannot_be_placed_is_reported_with_its_reason() -> None:
    """Placing it would assert a reading that was never established."""
    anchors, skipped = _anchors(
        [
            _entity("e1", "person", "Hannsen Ramung", "Hans Ramung", 1, None),
            _entity("e2", "time", "Sand Michels tag", "Sankt Michaelstag", 1, "r1l1"),
            _entity("e3", "person", "Hannsen Ramung", "Hans Ramung", 1, "r9l9"),
            _entity("e4", "person", "Hannsen Ramung", "Hans Ramung", 3, "r1l1"),
            # twice in its line, absent from it, and without a surface form at all
            _entity("e5", "object", "kessel", "Kessel", 1, "r1l2"),
            _entity("e6", "object", "napf", "Napf", 1, "r1l2"),
            _entity("e7", "object", "", "Kessel", 1, "r1l2"),
        ]
    )
    assert anchors == {}
    assert skipped == [
        ("e1", "no line reference"),
        ("e2", "type not encoded (time)"),
        ("e3", "line reference not in the export"),
        ("e4", "line reference not in the export"),
        ("e5", "surface form not exactly once in the line"),
        ("e6", "surface form not exactly once in the line"),
        ("e7", "surface form not exactly once in the line"),
    ]


def test_two_overlapping_entities_keep_the_first_and_report_the_second() -> None:
    """The encoding admits no nesting, so the second one is dropped, and it is
    reported with its reason instead of vanishing at render time."""
    anchors, skipped = _anchors(
        [
            _entity("p2", "person", "Ramung ze", "Ramung", 1, "r1l1"),
            _entity("p1", "person", "Hannsen Ramung", "Hans Ramung", 1, "r1l1"),
        ]
    )
    assert anchors == {
        1: {
            "r1l1": [
                {
                    "start": 0,
                    "end": 14,
                    "element": "persName",
                    "ref": _ref("per-hans-ramung"),
                    "entity_id": "p1",
                }
            ]
        }
    }
    assert skipped == [("p2", "overlaps an earlier entity in the line")]


def test_an_anchor_is_cut_against_the_reviewed_text() -> None:
    """A corrected line is matched on its reviewed reading, never on the
    superseded one; both the match and the offset follow the review."""
    person = _entity("p1", "person", "Hannsen Ramung", "Hans Ramung", 1, "r1l1")
    # "Thaur" is the reviewed spelling; the export line reads "Thawr"
    place = _entity("pl1", "place", "Thaur", "Thaur", 1, "r1l1")

    anchors, skipped = _anchors([person, place])
    assert anchors == {
        1: {
            "r1l1": [
                {
                    "start": 0,
                    "end": 14,
                    "element": "persName",
                    "ref": _ref("per-hans-ramung"),
                    "entity_id": "p1",
                }
            ]
        }
    }
    assert skipped == [("pl1", "surface form not exactly once in the line")]

    reviewed, skipped = _anchors(
        [person, place], {1: {"r1l1": "item Hannsen Ramung ze Thaur"}}
    )
    assert skipped == []
    assert reviewed == {
        1: {
            "r1l1": [
                {
                    "start": 5,
                    "end": 19,
                    "element": "persName",
                    "ref": _ref("per-hans-ramung"),
                    "entity_id": "p1",
                },
                {
                    "start": 23,
                    "end": 28,
                    "element": "placeName",
                    "ref": _ref("pl-thaur"),
                    "entity_id": "pl1",
                },
            ]
        }
    }


def test_line_content_wraps_the_anchors_and_escapes_everything_else() -> None:
    text = "Hannsen Ramung & Thawr"
    anchors = [
        {"start": 0, "end": 14, "element": "persName", "ref": _ref("per-hans-ramung")},
        {"start": 17, "end": 22, "element": "placeName", "ref": _ref("pl-thaur")},
    ]
    assert bt._line_content(text, anchors) == (
        '<persName resp="#resp-entity-llm" ref="register.xml#per-hans-ramung">'
        "Hannsen Ramung</persName>"
        " &amp; "
        '<placeName resp="#resp-entity-llm" ref="register.xml#pl-thaur">'
        "Thawr</placeName>"
    )
    assert bt._line_content(text, []) == "Hannsen Ramung &amp; Thawr"


def test_no_certainty_attribute_anywhere() -> None:
    """The extraction reports a confidence; the encoding must not repeat it.

    Attribute names are compared with their namespace stripped, because an exact
    key comparison against "cert" sees neither a prefixed form nor @certainty.
    """
    built = _built()
    for doc_id, xml in built.items():
        root = ElementTree.fromstring(xml)
        for element in root.iter():
            bare = {name.rsplit("}", 1)[-1] for name in element.attrib}
            assert not bare & {"cert", "certainty"}, (
                f"certainty attribute on {element.tag} in {doc_id}"
            )
        assert "<certainty" not in xml, f"certainty element in {doc_id}"


def _resp_ids(root: ElementTree.Element) -> list[str]:
    return [r.get(XML_ID) for r in root.iter(f"{TEI}respStmt")]


def _changes(root: ElementTree.Element) -> dict[str, ElementTree.Element]:
    return {c.get("n"): c for c in root.iter(f"{TEI}change") if c.get("n")}


def test_every_document_declares_its_work_steps() -> None:
    """Each file names the two steps that ran, and claims no verification step.

    Which transcription step that is depends on the layer: the Transkribus one
    where an export carries the text, DoCTA's own where the pipeline produced it.
    """
    built = _built()
    layers = {d["docId"]: d["layer"] for d in bt._documents()}
    attributed = {d["docId"]: bool(d["inventaria"]) for d in bt._documents()}
    for doc_id, xml in built.items():
        root = ElementTree.fromstring(xml)
        transcription = (
            bt.RESP_VLM if layers[doc_id] == bt.VLM_LAYER else bt.RESP_TRANSKRIBUS
        )
        expected = [transcription]
        if attributed[doc_id]:
            expected.append(bt.RESP_INVENTARIA)
        expected.append(bt.RESP_GENERATION)
        if _has_entities(doc_id):
            expected.append(bt.RESP_ENTITY)
        assert _resp_ids(root) == expected, f"respStmt ids differ in {doc_id}"
        assert "resp-expert-verification" not in xml, (
            f"verification claimed in {doc_id}"
        )
        names = [n.text for n in root.iter(f"{TEI}name")]
        assert f"pipeline/build_tei.py (sha256 {bt.script_digest()})" in names, (
            f"script digest missing in {doc_id}"
        )


def test_correction_state_decides_wording_and_status() -> None:
    built = _built()
    for doc_id in FULLY_CORRECTED:
        root = ElementTree.fromstring(built[doc_id])
        resp = root.find(f".//{TEI}respStmt/{TEI}resp").text
        assert "corrected page by page" in resp, f"wrong layer resp in {doc_id}"
        decl = "".join(root.find(f".//{TEI}editorialDecl").itertext())
        assert "corrected page by page in Transkribus" in decl
        assert "unrevised machine transcription" not in decl
        assert _changes(root)["transcription-summary"].get("status") == bt.CORRECTED, (
            f"wrong status in {doc_id}"
        )

    root = ElementTree.fromstring(built[MACHINE_SAMPLE])
    resp = root.find(f".//{TEI}respStmt/{TEI}resp").text
    assert resp == "Automated text recognition layer from Transkribus, unrevised"
    decl = "".join(root.find(f".//{TEI}editorialDecl").itertext())
    assert "unrevised machine transcription" in decl
    assert _changes(root)["transcription-summary"].get("status") == bt.MACHINE


# ------------------------------------------------- Inventaria attribution
# 57 of the transcribed documents carry a transcription the Inventaria project
# made in Transkribus. The header has to name that project and, where the
# harvest found one, link the published edition.


def _resp_of(root: ElementTree.Element, resp_id: str) -> ElementTree.Element | None:
    return next(
        (r for r in root.iter(f"{TEI}respStmt") if r.get(XML_ID) == resp_id), None
    )


def _decl(root: ElementTree.Element) -> str:
    return "".join(root.find(f".//{TEI}editorialDecl").itertext())


def test_the_attribution_reads_the_source_mapping_and_the_edition_links() -> None:
    """Same two sources as the site projection in build_register.py, so the TEI
    and the site cannot disagree about who made a transcription."""
    mapping = bt._load(bt.DATA / "source_mapping.json")["matched"]
    expected = {
        m["transkribus_id"]
        for m in mapping
        if m.get("csv_transkribiert") == "Inventaria"
    }
    links = {
        d["docId"]: d["url"]
        for d in bt._load(bt.DATA / "inventaria_mapping.json")["documents"]
    }
    assert expected, "no attributed document in the mapping, the check proves nothing"

    docs = bt._documents()
    for doc in docs:
        # a text DoCTA produced itself is never an Inventaria transcription,
        # whatever the mapping says about the source
        attributed = doc["docId"] in expected and doc["layer"] == bt.TRANSKRIBUS_LAYER
        assert doc["inventaria"] == attributed, f"wrong attribution on {doc['docId']}"
        assert doc["edition_url"] == (
            links.get(doc["docId"]) if attributed else None
        ), f"wrong edition link on {doc['docId']}"
    assert any(d["inventaria"] for d in docs)
    assert any(not d["inventaria"] for d in docs), "no unattributed counter-example"
    # a flagged document without a harvested entry stays attributed and links to
    # nothing, rather than losing its attribution with the link
    without = next(d for d in docs if d["docId"] == ATTRIBUTED_WITHOUT_LINK)
    assert without["inventaria"] and without["edition_url"] is None


def test_an_attributed_document_names_the_inventaria_project() -> None:
    """The attribution stands beside the Transkribus layer it qualifies and
    weakens none of the responsibilities already declared."""
    built = _built()
    docs = {d["docId"]: d for d in bt._documents()}
    seen = 0
    for doc_id, xml in built.items():
        root = ElementTree.fromstring(xml)
        resp = _resp_of(root, bt.RESP_INVENTARIA)
        if not docs[doc_id]["inventaria"]:
            assert resp is None, f"attribution invented in {doc_id}"
            continue
        seen += 1
        ids = _resp_ids(root)
        assert ids.index(bt.RESP_INVENTARIA) == ids.index(bt.RESP_TRANSKRIBUS) + 1, (
            f"attribution not beside the transkribus layer in {doc_id}"
        )
        name = resp.find(f"{TEI}name")
        assert name.text == "Inventaria project", f"wrong name in {doc_id}"
        assert name.get("ref") == bt.INVENTARIA_URL, f"wrong name ref in {doc_id}"
        assert "Inventaria project" in resp.find(f"{TEI}resp").text
    assert seen, "no attributed document in the corpus, the check proves nothing"


def test_a_fully_done_attributed_document_is_not_called_unrevised() -> None:
    """A document the Inventaria project corrected page by page must not be
    presented as unrevised machine output, and DoCTA must not claim the
    verification the done status is not."""
    built = _built()
    docs = {d["docId"]: d for d in bt._documents()}
    for doc_id in FULLY_CORRECTED:
        assert docs[doc_id]["inventaria"], f"{doc_id} lost its attribution"
        root = ElementTree.fromstring(built[doc_id])
        resp = _resp_of(root, bt.RESP_INVENTARIA).find(f"{TEI}resp").text
        assert "produced and corrected by the Inventaria project" in resp
        assert "marked done in Transkribus" in resp
        assert "pages" not in resp, f"page split claimed on a full document: {resp}"

        decl = _decl(root)
        assert "unrevised machine transcription" not in decl, doc_id
        assert "Automated text recognition" not in decl, doc_id
        assert "produced by the Inventaria project" in decl, doc_id
        # the two status axes stay separate
        assert "workflow status of Transkribus" in decl, doc_id
        assert "DoCTA has not independently verified" in decl, doc_id


def test_an_attributed_document_without_a_done_page_says_so() -> None:
    """No page marked done means the campaign produced the text and no one
    corrected it; the file keeps saying that it is machine transcription."""
    built = _built()
    root = ElementTree.fromstring(built[ATTRIBUTED_MACHINE])
    resp = _resp_of(root, bt.RESP_INVENTARIA).find(f"{TEI}resp").text
    assert resp == (
        "Transcription campaign of the Inventaria project in Transkribus,"
        " no page marked done there"
    )
    decl = _decl(root)
    assert "transcription campaign of the Inventaria project" in decl
    assert "no page of it is marked done" in decl
    assert "unrevised machine transcription" in decl
    assert _changes(root)["transcription-summary"].get("status") == bt.MACHINE


# A document corrected for part of its pages, which the corpus does not have;
# the split wording can only be exercised against a written-out case.
PARTLY_DOC = {
    "docId": 99999999,
    "correction": bt.PARTLY,
    "done_pages": 3,
    "pages": 8,
    "layer": bt.TRANSKRIBUS_LAYER,
    "inventaria": True,
    "edition_url": "https://app.transkribus.org/en/sites/inventaria/doc/1/detail",
}


def test_a_partly_done_attributed_document_states_the_split() -> None:
    resp = "\n".join(bt._resp_stmts(PARTLY_DOC, ""))
    assert "resp-inventaria-transcription" in resp
    assert "marked done in Transkribus for 3 of 8 pages" in resp
    # the pre-existing Transkribus responsibility keeps its own split wording
    assert "for 3 of 8 pages (human-corrected layer)" in resp

    decl = "\n".join(bt._editorial_decl(PARTLY_DOC, ""))
    assert "3 of its 8 pages are corrected and marked done" in decl
    assert "unrevised automated recognition layer" in decl
    assert "workflow status of Transkribus" in decl
    assert "DoCTA has not independently verified" in decl


def test_the_published_edition_travels_as_a_bibl() -> None:
    """Where the harvest found the published edition, the source description
    links it; a document without a link carries no empty bibl."""
    built = _built()
    docs = {d["docId"]: d for d in bt._documents()}
    linked = 0
    for doc_id, xml in built.items():
        root = ElementTree.fromstring(xml)
        source = root.find(f".//{TEI}sourceDesc")
        bibl = source.find(f"{TEI}bibl")
        url = docs[doc_id]["edition_url"]
        if url is None:
            assert bibl is None, f"bibl without an edition link in {doc_id}"
            continue
        linked += 1
        ref = bibl.find(f"{TEI}ref")
        assert ref.get("target") == url, f"wrong edition target in {doc_id}"
        assert "Inventaria project" in ref.text and "edition" in ref.text
        # the archival description stays first and is not displaced by the link
        assert [el.tag for el in source] == [f"{TEI}msDesc", f"{TEI}bibl"]
    assert linked, "no edition link in the corpus, the check proves nothing"
    assert (
        ElementTree.fromstring(built[ATTRIBUTED_WITHOUT_LINK]).find(f".//{TEI}bibl")
        is None
    )


def test_an_unattributed_document_keeps_its_own_wording() -> None:
    built = _built()
    docs = [d for d in bt._documents() if not d["inventaria"]]
    assert docs, "no unattributed document, the check proves nothing"
    for doc in docs:
        xml = built[doc["docId"]]
        root = ElementTree.fromstring(xml)
        assert bt.RESP_INVENTARIA not in xml, f"attribution leaked into {doc['docId']}"
        assert "Inventaria" not in xml, f"Inventaria named in {doc['docId']}"
        assert root.find(f".//{TEI}bibl") is None
        assert "unrevised machine transcription" in _decl(root)


def test_a_docta_transcription_declares_its_own_step_and_no_layout() -> None:
    """A document Transkribus holds no text for carries DoCTA's own layer.

    Its responsibility names the model instead of Transkribus, its declaration
    says the reading is the model's own, and it asserts no image region, because
    no layout analysis ran on the page.
    """
    built = _built()
    doc = next(d for d in bt._documents() if d["layer"] == bt.VLM_LAYER)
    doc_id = doc["docId"]
    root = ElementTree.fromstring(built[doc_id])

    ids = _resp_ids(root)
    assert bt.RESP_VLM in ids and bt.RESP_TRANSKRIBUS not in ids
    resp = root.find(f".//{TEI}respStmt/{TEI}resp").text
    assert resp.startswith("Vision-language model transcription")
    name = root.find(f".//{TEI}respStmt/{TEI}name").text
    assert doc["model"] in name and doc["prompt"] in name

    decl = "".join(root.find(f".//{TEI}editorialDecl").itertext())
    assert "Transkribus holds no transcription of this source" in decl
    assert "unrevised machine transcription" in decl
    assert _changes(root)["transcription-summary"].get("status") == bt.MACHINE

    assert not list(root.iter(f"{TEI}zone")), "zones without a layout analysis"
    assert all(lb.get("facs") is None for lb in root.iter(f"{TEI}lb"))
    # The page image is referenced all the same; it is what was transcribed.
    assert [g.get("url") for g in root.iter(f"{TEI}graphic")], "no facsimile"

    register = br.transcription_of(doc_id, bt.REGISTER)
    for page in register["pages"]:
        block = f"ab-{doc_id}-{page['pageNr']}-{br.VLM_REGION}"
        assert root.find(f'.//{TEI}ab[@{XML_ID}="{block}"]') is not None, block
    expected = sum(len(r["lines"]) for p in register["pages"] for r in p["regions"])
    assert sum(1 for _ in root.iter(f"{TEI}lb")) == expected, "line count differs"


def test_a_partly_transcribed_document_says_how_much_it_covers() -> None:
    """A file carrying part of its source states the ratio, a complete one does not.

    Without the sentence the file reads as the whole document, since a source
    without an export has no page list to compare its page count against.
    """
    built = _built()
    for doc in bt._documents():
        if doc["layer"] != bt.VLM_LAYER:
            continue
        pages = br.transcription_of(doc["docId"], bt.REGISTER)["pages"]
        root = ElementTree.fromstring(built[doc["docId"]])
        decl = "".join(root.find(f".//{TEI}editorialDecl").itertext())
        covered, total = len(pages), doc["pages"]
        if covered < total:
            assert f"It covers {covered} of the {total} pages" in decl, doc["docId"]
        else:
            assert "It covers" not in decl, doc["docId"]


def test_revision_desc_carries_both_stream_summaries() -> None:
    built = _built()
    states = {bt.CORRECTED, bt.PARTLY, bt.MACHINE}
    for doc_id, xml in built.items():
        root = ElementTree.fromstring(xml)
        generation = root.find(f".//{TEI}change")
        assert generation.get("who") == f"#{bt.RESP_GENERATION}", (
            f"generation change without responsibility in {doc_id}"
        )
        changes = _changes(root)
        assert set(changes) == {"transcription-summary", "tei-summary"}, (
            f"stream summaries differ in {doc_id}"
        )
        assert changes["transcription-summary"].get("status") in states
        assert changes["tei-summary"].get("status") == "machine-generated"


def test_rebuild_is_byte_identical() -> None:
    """A rebuild without input changes must leave no diff in the repository.

    Both builds run the same script version, so the digest in the header is the
    same constant; editing build_tei.py is meant to change the output.
    """
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        bt.build(Path(a))
        bt.build(Path(a))  # rebuild over the existing output
        bt.build(Path(b))
        first = sorted(Path(a).glob("*.xml"))
        assert first, "nothing written"
        for path in first:
            other = Path(b) / path.name
            assert path.read_bytes() == other.read_bytes(), f"drift in {path.name}"


def _review_build(tmp: Path, pages: dict) -> tuple[dict[int, str], dict[int, str]]:
    """Build the corpus twice off one register copy, before and after a review.

    Both builds run the same code version against the same inputs, so every
    difference between them is the review and nothing else.
    """
    br.build(tmp)
    pages_dir = tmp / "pages"
    before = bt.build(tmp / "before", register_dir=pages_dir)
    path = tmp / f"review-{REVIEW_DOC}.json"
    path.write_text(
        json.dumps(
            {
                "docId": REVIEW_DOC,
                "reviewer": REVIEWER,
                "pages": pages,
                "exported": f"{REVIEW_DATE}T10:15:00Z",
                "source": "docta-viewer",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    ar.ingest([path], pages_dir)
    return before, bt.build(tmp / "after", register_dir=pages_dir)


def _base_text(tmp: Path, page_nr: int, line_id: str) -> str:
    payload = br._load(tmp / "pages" / f"{REVIEW_DOC}.json")
    page = next(p for p in payload["pages"] if p["pageNr"] == page_nr)
    run = next(r for r in page["runs"] if r["source"] == "transkribus")
    return next(ln["text"] for ln in run["lines"] if ln["id"] == line_id)


def test_a_reviewed_page_carries_the_reviewed_text() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        br.build(tmp)
        original = _base_text(tmp, REVIEW_PAGE, REVIEW_LINE)
        before, after = _review_build(
            tmp,
            {
                str(REVIEW_PAGE): {
                    "status": "gesichtet",
                    "date": REVIEW_DATE,
                    "lines": [
                        {
                            "id": REVIEW_LINE,
                            "original": original,
                            "corrected": REVIEW_TEXT,
                        }
                    ],
                }
            },
        )

    assert original != REVIEW_TEXT, "the fixture must change something"
    assert REVIEW_TEXT not in before[REVIEW_DOC], "reviewed text before the review"
    assert REVIEW_TEXT in after[REVIEW_DOC], "reviewed text missing after"

    root = ElementTree.fromstring(after[REVIEW_DOC])
    assert bt.RESP_VERIFICATION in _resp_ids(root), "verification not declared"
    resp = next(
        r for r in root.iter(f"{TEI}respStmt") if r.get(XML_ID) == bt.RESP_VERIFICATION
    )
    assert (
        resp.find(f"{TEI}resp").text
        == "Page-level scholarly review and correction in the DoCTA viewer"
    )
    assert (
        resp.find(f"{TEI}name").text == "DoCTA reviewer (initials in the revision log)"
    )

    decl = "".join(root.find(f".//{TEI}editorialDecl").itertext())
    assert "Part of the pages of this file has been read" in decl
    assert "The text of this file is unrevised machine transcription." not in decl, (
        "editorialDecl contradicts the partly-reviewed stream"
    )

    changes = [c for c in root.iter(f"{TEI}change") if c.get("n") == "review"]
    assert len(changes) == 1, "expected one review entry per reviewed page"
    change = changes[0]
    assert change.get("when") == REVIEW_DATE
    assert change.get("who") == f"#{bt.RESP_VERIFICATION}"
    assert f"Page {REVIEW_PAGE}" in change.text and REVIEWER in change.text
    assert _changes(root)["transcription-summary"].get("status") == bt.REVIEWED

    # a review touches the document it names and nothing else in the corpus
    for doc_id, xml in before.items():
        if doc_id != REVIEW_DOC:
            assert after[doc_id] == xml, f"review leaked into {doc_id}"

    other = ElementTree.fromstring(before[REVIEW_DOC])
    assert bt.RESP_VERIFICATION not in _resp_ids(other), (
        "verification claimed without a review"
    )


def test_a_fully_accepted_document_reports_approval() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        br.build(tmp)
        count = len(br._load(tmp / "pages" / f"{REVIEW_DOC}.json")["pages"])
        _, after = _review_build(
            tmp,
            {
                str(nr): {"status": "abgenommen", "date": REVIEW_DATE, "lines": []}
                for nr in range(1, count + 1)
            },
        )
    root = ElementTree.fromstring(after[REVIEW_DOC])
    assert _changes(root)["transcription-summary"].get("status") == bt.APPROVED
    assert (
        len([c for c in root.iter(f"{TEI}change") if c.get("n") == "review"]) == count
    )
    decl = "".join(root.find(f".//{TEI}editorialDecl").itertext())
    assert "Every page of this file has been read against the scan" in decl
    assert "unrevised machine transcription" not in decl, (
        "editorialDecl contradicts the approved stream"
    )


def test_a_document_reviewed_in_mixed_states_stays_partly_reviewed() -> None:
    """Approval is a statement about every page. One page merely gesichtet keeps
    the document off the approved state, even with no page left unreviewed."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        br.build(tmp)
        count = len(br._load(tmp / "pages" / f"{REVIEW_DOC}.json")["pages"])
        _, after = _review_build(
            tmp,
            {
                str(nr): {
                    "status": "gesichtet" if nr == 1 else "abgenommen",
                    "date": REVIEW_DATE,
                    "lines": [],
                }
                for nr in range(1, count + 1)
            },
        )
    root = ElementTree.fromstring(after[REVIEW_DOC])
    assert count > 1, "the fixture needs more than one page to mix states"
    assert _changes(root)["transcription-summary"].get("status") == bt.REVIEWED
    assert (
        len([c for c in root.iter(f"{TEI}change") if c.get("n") == "review"]) == count
    )
    decl = "".join(root.find(f".//{TEI}editorialDecl").itertext())
    assert "Part of the pages of this file has been read" in decl
    assert "Every page of this file has been read against the scan" not in decl


def test_generation_date_comes_from_the_argument() -> None:
    with tempfile.TemporaryDirectory() as td:
        built = bt.build(Path(td), "2026-09-01")
    xml = next(iter(built.values()))
    assert f'<change when="2026-09-01" who="#{bt.RESP_GENERATION}">' in xml
    assert '<date when="2026-09-01">' in xml


def main() -> int:
    failed = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_"):
            continue
        try:
            fn()
            print(f"OK   {name}")
        except AssertionError as exc:
            failed += 1
            print(f"FEHLER {name}: {exc}", file=sys.stderr)
    print(f"{'FEHLER' if failed else 'OK'}: {failed} fehlgeschlagen")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
