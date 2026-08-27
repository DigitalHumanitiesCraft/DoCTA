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

TEI = "{http://www.tei-c.org/ns/1.0}"

# two documents of different size, read from the export for the count checks
SAMPLES = (11327963, 11328042)

# every page marked DONE in Transkribus; these carry the human-corrected wording
FULLY_CORRECTED = (11328300, 11330019, 11330020)
MACHINE_SAMPLE = 11327963

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


def _export_lines(doc_id: int) -> list[str]:
    export = bt._load(bt.DATA / "transcriptions" / f"{doc_id}.json")
    return [line for page in export["pages"] for line in bt._lines(page)]


def test_every_document_parses() -> None:
    built = _built()
    assert built, "no TEI documents built"
    for doc_id, xml in built.items():
        root = ElementTree.fromstring(xml)
        assert root.tag == f"{TEI}TEI", f"unexpected root in {doc_id}"


def test_line_counts_match_the_export() -> None:
    """Every exported line is either an lb or a folio milestone, never dropped."""
    built = _built()
    for doc_id in SAMPLES:
        root = ElementTree.fromstring(built[doc_id])
        body = root.find(f"{TEI}text")
        encoded = sum(1 for _ in body.iter(f"{TEI}lb"))
        milestones = sum(1 for _ in body.iter(f"{TEI}milestone"))
        assert encoded + milestones == len(_export_lines(doc_id)), \
            f"line count differs in {doc_id}"


def test_folio_marks_became_milestones() -> None:
    built = _built()
    for doc_id, xml in built.items():
        expected = []
        for t in _export_lines(doc_id):
            if m := bt.FOLIO_LINE.match(t):
                expected.append(("folio", m.group(1)))
            elif m := bt.COVER_LINE.match(t):
                expected.append(("cover", m.group(1)))
        root = ElementTree.fromstring(xml)
        encoded = [(m.get("unit"), m.get("n"))
                   for m in root.iter(f"{TEI}milestone")]
        assert all(u in ("folio", "cover") for u, _ in encoded)
        assert encoded == expected, f"folio milestones differ in {doc_id}"
        text = "".join(root.find(f"{TEI}text").itertext())
        assert not re.search(r"\[fol\.\s*\d+[rv]?\]", text), \
            f"folio mark left in the text of {doc_id}"


def test_one_pb_and_one_surface_per_page() -> None:
    built = _built()
    for doc_id, xml in built.items():
        export = bt._load(bt.DATA / "transcriptions" / f"{doc_id}.json")
        page_numbers = [str(p["pageNr"]) for p in export["pages"]]
        root = ElementTree.fromstring(xml)
        pbs = [pb.get("n") for pb in root.iter(f"{TEI}pb")]
        surfaces = [s.get("n") for s in root.iter(f"{TEI}surface")]
        graphics = [g.get("url") for g in root.iter(f"{TEI}graphic")]
        assert pbs == sorted(page_numbers, key=int), f"pb set differs in {doc_id}"
        assert surfaces == pbs, f"surface set differs in {doc_id}"
        assert len(graphics) == len(surfaces) and all(graphics), \
            f"missing graphic url in {doc_id}"
        for pb in root.iter(f"{TEI}pb"):
            assert pb.get("facs") == f"#surface-{doc_id}-{pb.get('n')}"


def test_one_ab_per_text_region() -> None:
    """Regions of the export survive as blocks; nothing is flattened away."""
    built = _built()
    for doc_id in SAMPLES:
        export = bt._load(bt.DATA / "transcriptions" / f"{doc_id}.json")
        expected = [f"ab-{doc_id}-{page['pageNr']}-{region['id']}"
                    for page in sorted(export["pages"], key=lambda p: p["pageNr"])
                    for region in page.get("regions") or []]
        root = ElementTree.fromstring(built[doc_id])
        assert [ab.get(XML_ID) for ab in root.iter(f"{TEI}ab")] == expected, \
            f"ab set differs in {doc_id}"
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
        assert root.find(f"{TEI}text").get("{http://www.w3.org/XML/1998/namespace}lang") \
            == bt.TEXT_LANG
        raw = (docs[doc_id]["dating"] or {}).get("raw")
        origdate = root.find(f".//{TEI}origDate")
        if raw:
            assert origdate is not None and origdate.text == raw
        else:
            assert origdate is None, f"origDate invented in {doc_id}"


def test_zone_per_line_with_coordinates() -> None:
    """Every exported line with coordinates gets one zone under its surface."""
    built = _built()
    for doc_id in SAMPLES:
        export = bt._load(bt.DATA / "transcriptions" / f"{doc_id}.json")
        expected = [(page["pageNr"], line["id"], line["coords"])
                    for page in sorted(export["pages"], key=lambda p: p["pageNr"])
                    if page.get("iiif")
                    for line in bt._line_records(page)
                    if (line.get("coords") or "").strip()]
        root = ElementTree.fromstring(built[doc_id])
        zones = [(z.get(XML_ID), z.get("points"))
                 for z in root.iter(f"{TEI}zone")]
        assert zones == [(f"zone-{doc_id}-{nr}-{lid}", coords)
                         for nr, lid, coords in expected], \
            f"zone set differs in {doc_id}"


def test_every_lb_facs_resolves_to_a_zone() -> None:
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
            assert facs.startswith("#") and facs[1:] in ids, \
                f"dangling lb facs {facs} in {doc_id}"
        assert bound, f"no lb bound to a zone in {doc_id}"


def test_entity_layer_only_where_an_extraction_exists() -> None:
    built = _built()
    assert _has_entities(DEMO_DOC), "the prototype extraction disappeared"
    for doc_id, xml in built.items():
        if not _has_entities(doc_id):
            continue
        root = ElementTree.fromstring(xml)
        assert bt.RESP_ENTITY in _resp_ids(root), f"entity respStmt missing in {doc_id}"
        names = [pn for pn in root.iter(f"{TEI}persName")
                 if pn.get("resp") == f"#{bt.RESP_ENTITY}"]
        assert names, f"no persName bound to the entity responsibility in {doc_id}"
        assert all(pn.get("key") and pn.text for pn in names), \
            f"persName without key or content in {doc_id}"
        decl = "".join(root.find(f".//{TEI}editorialDecl").itertext())
        assert "unverified extraction by an LLM agent" in decl

    assert not _has_entities(NON_DEMO_DOC), "the counter-example acquired entities"
    other = ElementTree.fromstring(built[NON_DEMO_DOC])
    assert bt.RESP_ENTITY not in _resp_ids(other), "entity respStmt leaked"
    assert bt.RESP_ENTITY not in built[NON_DEMO_DOC]
    for tag in ("persName", "placeName", "objectName"):
        assert not list(other.iter(f"{TEI}{tag}")), f"{tag} leaked into {NON_DEMO_DOC}"


def test_no_certainty_attribute_anywhere() -> None:
    """The extraction reports a confidence; the encoding must not repeat it."""
    built = _built()
    for doc_id, xml in built.items():
        root = ElementTree.fromstring(xml)
        for element in root.iter():
            assert "cert" not in element.attrib, \
                f"cert on {element.tag} in {doc_id}"
        assert "<certainty" not in xml, f"certainty element in {doc_id}"


def _resp_ids(root: ElementTree.Element) -> list[str]:
    return [r.get(XML_ID) for r in root.iter(f"{TEI}respStmt")]


def _changes(root: ElementTree.Element) -> dict[str, ElementTree.Element]:
    return {c.get("n"): c for c in root.iter(f"{TEI}change") if c.get("n")}


def test_every_document_declares_its_work_steps() -> None:
    """Each file names the two steps that ran, and claims no verification step."""
    built = _built()
    for doc_id, xml in built.items():
        root = ElementTree.fromstring(xml)
        expected = [bt.RESP_TRANSKRIBUS, bt.RESP_GENERATION]
        if _has_entities(doc_id):
            expected.append(bt.RESP_ENTITY)
        assert _resp_ids(root) == expected, f"respStmt ids differ in {doc_id}"
        assert "resp-expert-verification" not in xml, \
            f"verification claimed in {doc_id}"
        names = [n.text for n in root.iter(f"{TEI}name")]
        assert f"pipeline/build_tei.py (sha256 {bt.script_digest()})" in names, \
            f"script digest missing in {doc_id}"


def test_correction_state_decides_wording_and_status() -> None:
    built = _built()
    for doc_id in FULLY_CORRECTED:
        root = ElementTree.fromstring(built[doc_id])
        resp = root.find(f".//{TEI}respStmt/{TEI}resp").text
        assert "corrected page by page" in resp, f"wrong layer resp in {doc_id}"
        decl = "".join(root.find(f".//{TEI}editorialDecl").itertext())
        assert "corrected page by page in Transkribus" in decl
        assert "unrevised machine transcription" not in decl
        assert _changes(root)["transcription-summary"].get("status") == \
            bt.CORRECTED, f"wrong status in {doc_id}"

    root = ElementTree.fromstring(built[MACHINE_SAMPLE])
    resp = root.find(f".//{TEI}respStmt/{TEI}resp").text
    assert resp == "Automated text recognition layer from Transkribus, unrevised"
    decl = "".join(root.find(f".//{TEI}editorialDecl").itertext())
    assert "unrevised machine transcription" in decl
    assert _changes(root)["transcription-summary"].get("status") == bt.MACHINE


def test_revision_desc_carries_both_stream_summaries() -> None:
    built = _built()
    states = {bt.CORRECTED, bt.PARTLY, bt.MACHINE}
    for doc_id, xml in built.items():
        root = ElementTree.fromstring(xml)
        generation = root.find(f".//{TEI}change")
        assert generation.get("who") == f"#{bt.RESP_GENERATION}", \
            f"generation change without responsibility in {doc_id}"
        changes = _changes(root)
        assert set(changes) == {"transcription-summary", "tei-summary"}, \
            f"stream summaries differ in {doc_id}"
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
    path.write_text(json.dumps(
        {"docId": REVIEW_DOC, "reviewer": REVIEWER, "pages": pages,
         "exported": f"{REVIEW_DATE}T10:15:00Z", "source": "docta-viewer"},
        ensure_ascii=False), encoding="utf-8")
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
        before, after = _review_build(tmp, {str(REVIEW_PAGE): {
            "status": "gesichtet", "date": REVIEW_DATE,
            "lines": [{"id": REVIEW_LINE, "original": original,
                       "corrected": REVIEW_TEXT}]}})

    assert original != REVIEW_TEXT, "the fixture must change something"
    assert REVIEW_TEXT not in before[REVIEW_DOC], "reviewed text before the review"
    assert REVIEW_TEXT in after[REVIEW_DOC], "reviewed text missing after"

    root = ElementTree.fromstring(after[REVIEW_DOC])
    assert bt.RESP_VERIFICATION in _resp_ids(root), "verification not declared"
    resp = [r for r in root.iter(f"{TEI}respStmt")
            if r.get(XML_ID) == bt.RESP_VERIFICATION][0]
    assert resp.find(f"{TEI}resp").text == \
        "Page-level scholarly review and correction in the DoCTA viewer"
    assert resp.find(f"{TEI}name").text == \
        "DoCTA reviewer (initials in the revision log)"

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
    assert bt.RESP_VERIFICATION not in _resp_ids(other), \
        "verification claimed without a review"


def test_a_fully_accepted_document_reports_approval() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        br.build(tmp)
        count = len(br._load(tmp / "pages" / f"{REVIEW_DOC}.json")["pages"])
        _, after = _review_build(tmp, {
            str(nr): {"status": "abgenommen", "date": REVIEW_DATE, "lines": []}
            for nr in range(1, count + 1)})
    root = ElementTree.fromstring(after[REVIEW_DOC])
    assert _changes(root)["transcription-summary"].get("status") == bt.APPROVED
    assert len([c for c in root.iter(f"{TEI}change")
                if c.get("n") == "review"]) == count
    decl = "".join(root.find(f".//{TEI}editorialDecl").itertext())
    assert "Every page of this file has been read against the scan" in decl


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
