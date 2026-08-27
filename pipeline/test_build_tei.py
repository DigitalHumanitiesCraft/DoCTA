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
        expected = [bt.FOLIO_LINE.match(t) for t in _export_lines(doc_id)]
        folios = [m.group(1) for m in expected if m]
        root = ElementTree.fromstring(xml)
        encoded = [m.get("n") for m in root.iter(f"{TEI}milestone")]
        assert all(m.get("unit") == "folio" for m in root.iter(f"{TEI}milestone"))
        assert encoded == folios, f"folio milestones differ in {doc_id}"
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


def test_rebuild_is_byte_identical() -> None:
    """A rebuild without input changes must leave no diff in the repository."""
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
    assert '<change when="2026-09-01">' in xml
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
