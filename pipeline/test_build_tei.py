"""Tests for the TEI builder, runnable with pytest or plain python.

Integration tests against the real repo data; the TEI stage has no fixtures of
its own, its input is the Transkribus export in the repository.

Usage:
  python test_build_tei.py
  pytest pipeline/test_build_tei.py
"""

import re
import sys
import tempfile
from pathlib import Path
from xml.etree import ElementTree

import build_tei as bt

TEI = "{http://www.tei-c.org/ns/1.0}"

# two documents of different size, read from the export for the count checks
SAMPLES = (11327963, 11328042)

# every page marked DONE in Transkribus; these carry the human-corrected wording
FULLY_CORRECTED = (11328300, 11330019, 11330020)
MACHINE_SAMPLE = 11327963


def _built() -> dict[int, str]:
    with tempfile.TemporaryDirectory() as td:
        return bt.build(Path(td))


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


def _resp_ids(root: ElementTree.Element) -> list[str]:
    xml_id = "{http://www.w3.org/XML/1998/namespace}id"
    return [r.get(xml_id) for r in root.iter(f"{TEI}respStmt")]


def _changes(root: ElementTree.Element) -> dict[str, ElementTree.Element]:
    return {c.get("n"): c for c in root.iter(f"{TEI}change") if c.get("n")}


def test_every_document_declares_its_work_steps() -> None:
    """Each file names the two steps that ran, and claims no verification step."""
    built = _built()
    for doc_id, xml in built.items():
        root = ElementTree.fromstring(xml)
        assert _resp_ids(root) == [bt.RESP_TRANSKRIBUS, bt.RESP_GENERATION], \
            f"respStmt ids differ in {doc_id}"
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
