"""Mutation tests for the two-stage TEI validation.

Stage two exists to refuse what the generator never emits, so its rejection power
is tested by mutation rather than by asserting that valid files are valid. A real
generated file is the control; each test alters a copy of it in memory into
something outside the DoCTA encoding contract and requires stage two to refuse it.

The mutated file stays well-formed TEI in every case, which is checked, because a
broken parse would fail the stage for the wrong reason and prove nothing about the
grammar.

The module name carries the suffix because pipeline/accounts/tests/ holds a
test_validate_tei.py of its own for the account-book stack, and pytest imports
both directories as top-level modules.

Usage:
  pytest pipeline/test_validate_tei_stages.py
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
import validate_tei as vt
from lxml import etree

TEI = {"tei": "http://www.tei-c.org/ns/1.0"}
NS = "{http://www.tei-c.org/ns/1.0}"
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"

# A real generated file that carries an entity layer and folio milestones, so
# every mutation below has something in the document to attach to.
SOURCE = vt.DEFAULT_TEI_DIR / "11328300.xml"

Mutation = Callable[[etree._ElementTree], None]


def _cert_on_a_persname(document: etree._ElementTree) -> None:
    document.find(".//tei:text//tei:persName", TEI).set("cert", "high")


def _cert_on_an_ab(document: etree._ElementTree) -> None:
    document.find(".//tei:ab", TEI).set("cert", "high")


def _certainty_element(document: etree._ElementTree) -> None:
    ab = document.find(".//tei:ab", TEI)
    element = etree.SubElement(ab, f"{NS}certainty")
    element.set("locus", "value")
    element.set("degree", "0.8")


def _unknown_responsibility(document: etree._ElementTree) -> None:
    document.find(".//tei:respStmt", TEI).set(XML_ID, "resp-scholarly-edition")


def _unknown_milestone_unit(document: etree._ElementTree) -> None:
    milestone = document.find(".//tei:milestone", TEI)
    milestone.set("unit", "section")
    milestone.set("n", "2")


def _unknown_stream_status(document: etree._ElementTree) -> None:
    change = document.find(".//tei:change[@n='transcription-summary']", TEI)
    change.set("status", "scholarly-edition")


def _element_outside_the_grammar(document: etree._ElementTree) -> None:
    ab = document.find(".//tei:ab", TEI)
    etree.SubElement(ab, f"{NS}seg").text = "an editorial segment"


MUTATIONS: tuple[tuple[str, Mutation], ...] = (
    ("cert on a persName", _cert_on_a_persname),
    ("cert on an ab", _cert_on_an_ab),
    ("certainty element", _certainty_element),
    ("unknown respStmt id", _unknown_responsibility),
    ("unknown milestone unit", _unknown_milestone_unit),
    ("unknown stream status", _unknown_stream_status),
    ("element outside the grammar", _element_outside_the_grammar),
)


def _mutated(tmp_path: Path, mutate: Mutation) -> Path:
    document = etree.parse(str(SOURCE))
    mutate(document)
    path = tmp_path / "mutated.xml"
    document.write(str(path), encoding="utf-8", xml_declaration=True)
    etree.parse(str(path))  # the mutation must leave well-formed XML behind
    return path


def _invalid(paths: list[Path], schema: Path) -> list[Path]:
    return vt.validate_with_lxml(paths, schema, vt.DEFAULT_MAX_ERRORS)


def test_the_control_file_exists_and_passes_the_project_schema() -> None:
    """Without a passing control every rejection below would be meaningless."""
    assert SOURCE.is_file(), f"generated TEI file missing: {SOURCE}"
    assert _invalid([SOURCE], vt.DOCTA_SCHEMA) == []


@pytest.mark.parametrize(
    "mutate", [m for _, m in MUTATIONS], ids=[name for name, _ in MUTATIONS]
)
def test_the_project_schema_refuses_what_the_generator_never_emits(
    tmp_path: Path, mutate: Mutation
) -> None:
    path = _mutated(tmp_path, mutate)
    assert _invalid([path], vt.DOCTA_SCHEMA) == [path]


@pytest.mark.slow
def test_a_certainty_claim_is_valid_tei_and_still_refused(tmp_path: Path) -> None:
    """The two stages answer different questions, which is why both exist.

    Marked slow because loading tei_all.rng costs seconds; the pre-commit hook
    runs the slow marker, the ordinary test run stays fast.
    """
    path = _mutated(tmp_path, _cert_on_a_persname)
    assert _invalid([SOURCE, path], vt.TEI_SCHEMA) == []
    assert _invalid([path], vt.DOCTA_SCHEMA) == [path]


def test_both_schema_stages_are_present() -> None:
    for _, schema in vt.STAGES:
        assert schema.is_file(), f"schema missing: {schema}"
