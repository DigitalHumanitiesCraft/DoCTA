"""Boundary checks for private PAGE annotation and image-reference imports."""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _load(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


inventaria = _load("import_inventaria")
edition_pages = _load("fetch_edition_pages")


def test_page_import_preserves_custom_annotation(tmp_path: Path) -> None:
    source = ROOT / "pipeline" / "accounts" / "tests" / "fixtures" / "core" / "page.xml"
    xml = source.read_text(encoding="utf-8").replace(
        '<TextLine id="l-left-1">',
        '<TextLine id="l-left-1" custom="inv_person {offset:0;length:5;prov:inventaria;}">',
    )
    path = tmp_path / "page.xml"
    path.write_text(xml, encoding="utf-8")

    page = inventaria.parse_page(path)

    annotation = page["regions"][1]["lines"][0]["custom"]["annotations"][0]
    assert annotation == {
        "type": "inv_person",
        "attributes": {"length": "5", "offset": "0", "prov": "inventaria"},
        "raw": "inv_person {offset:0;length:5;prov:inventaria;}",
        "offset": 0,
        "length": 5,
        "text": "Hanns",
        "provenance": "inventaria",
    }


def test_page_import_rejects_annotation_outside_line(tmp_path: Path) -> None:
    source = ROOT / "pipeline" / "accounts" / "tests" / "fixtures" / "core" / "page.xml"
    xml = source.read_text(encoding="utf-8").replace(
        '<TextLine id="l-left-1">',
        '<TextLine id="l-left-1" custom="inv_person {offset:4;length:2;}">',
    )
    path = tmp_path / "page.xml"
    path.write_text(xml, encoding="utf-8")

    with pytest.raises(ValueError, match="exceeds line length"):
        inventaria.parse_page(path)


def test_image_merge_selects_only_requested_pages() -> None:
    payload = {
        "pageList": {
            "pages": [
                {"pageNr": 1, "key": "ISMVDKARQUBRQTZVDEQSWVHR"},
                {"pageNr": 2, "key": "GVSKSVEKBGNWJKNAKRHAOAUB"},
                {"pageNr": 3, "key": "NZLKHSGPPSRNYJOODRHTOBER"},
            ]
        }
    }

    result = edition_pages.build_merge(12647153, (2, 3), payload)

    assert [page["imgKey"] for page in result["pages"]] == [
        "GVSKSVEKBGNWJKNAKRHAOAUB",
        "NZLKHSGPPSRNYJOODRHTOBER",
    ]
    assert result["approvalRequired"] is True


def test_image_merge_rejects_missing_page() -> None:
    payload = {
        "pageList": {"pages": [{"pageNr": 2, "key": "GVSKSVEKBGNWJKNAKRHAOAUB"}]}
    }

    with pytest.raises(ValueError, match="lacks requested pages"):
        edition_pages.build_merge(12647153, (2, 3), payload)
