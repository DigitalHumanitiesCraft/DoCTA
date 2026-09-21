"""Integration tests for the bounded account-book pre-release build."""

from __future__ import annotations

import json
from pathlib import Path
from xml.etree import ElementTree

import pytest

from pipeline.accounts.build_edition import build

ROOT = Path(__file__).resolve().parents[2]
REAL_RUN = ROOT / "evaluation" / "pilot" / "runs" / "pilot_rb2_p002__it02__r1.json"
SOURCE_MANIFEST = ROOT / "docs" / "data" / "raitbuch2_pages.json"
PAGE_NS = "http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15"


def _page_for_real_run(path: Path) -> None:
    run = json.loads(REAL_RUN.read_text(encoding="utf-8"))
    root = ElementTree.Element(f"{{{PAGE_NS}}}PcGts")
    page = ElementTree.SubElement(
        root,
        f"{{{PAGE_NS}}}Page",
        imageWidth="3813",
        imageHeight="2622",
        imageFilename="OÖKAM Raitbuch 2, fol. 1v-2r.jpg",
    )
    region = ElementTree.SubElement(page, f"{{{PAGE_NS}}}TextRegion", id="machine-run")
    ElementTree.SubElement(
        region, f"{{{PAGE_NS}}}Coords", points="1910,0 3813,0 3813,2622 1910,2622"
    )
    for index, text in enumerate(run["lines"], start=1):
        line = ElementTree.SubElement(region, f"{{{PAGE_NS}}}TextLine", id=f"l{index}")
        ElementTree.SubElement(
            line,
            f"{{{PAGE_NS}}}Coords",
            points=f"1950,{index * 50} 3700,{index * 50} 3700,{index * 50 + 30} 1950,{index * 50 + 30}",
        )
        equivalent = ElementTree.SubElement(line, f"{{{PAGE_NS}}}TextEquiv")
        ElementTree.SubElement(equivalent, f"{{{PAGE_NS}}}Unicode").text = text
    ElementTree.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def test_real_raitbuch_run_builds_deterministic_anchored_prerelease(
    tmp_path: Path,
) -> None:
    page_xml = tmp_path / "page.xml"
    _page_for_real_run(page_xml)
    first = tmp_path / "first"
    second = tmp_path / "second"

    result = build(REAL_RUN, page_xml, first, source_manifest_path=SOURCE_MANIFEST)
    build(REAL_RUN, page_xml, second, source_manifest_path=SOURCE_MANIFEST)

    manifest = result["manifest"]
    revision = result["revision"]
    assert manifest["releaseEligible"] is False
    assert manifest["artifacts"]["tei"] is None
    assert manifest["artifacts"]["rdf"] is None
    assert (
        manifest["artifacts"]["transcriptionRevision"]["editorialLabel"]
        == "machine-unrevised"
    )
    assert revision["verification"] == "unreviewed"
    assert revision["publication"] == "unpublished"
    assert revision["lines"][0]["text"] == "2"
    assert revision["lines"][0]["anchor"]["side"] == "right"
    assert revision["lines"][0]["anchor"]["quote"] == "2"
    assert (first / "transcription-revision.json").read_bytes() == (
        second / "transcription-revision.json"
    ).read_bytes()
    assert (first / "edition-build-manifest.json").read_bytes() == (
        second / "edition-build-manifest.json"
    ).read_bytes()


def test_page_text_mismatch_fails_before_output(tmp_path: Path) -> None:
    page_xml = tmp_path / "page.xml"
    _page_for_real_run(page_xml)
    tree = ElementTree.parse(page_xml)
    unicode_node = next(node for node in tree.iter() if node.tag.endswith("Unicode"))
    unicode_node.text = "changed"
    tree.write(page_xml, encoding="utf-8", xml_declaration=True)
    output = tmp_path / "output"

    with pytest.raises(ValueError, match="PAGE line text does not match"):
        build(REAL_RUN, page_xml, output, source_manifest_path=SOURCE_MANIFEST)

    assert not output.exists()


def test_missing_page_xml_is_an_explicit_input_error(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="required PAGE XML"):
        build(
            REAL_RUN,
            tmp_path / "missing.xml",
            tmp_path / "output",
            source_manifest_path=SOURCE_MANIFEST,
        )
