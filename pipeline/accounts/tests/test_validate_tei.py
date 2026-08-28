"""Tests for the formal accounting TEI validation stack.

The source file is a synthetic software fixture. Mutations create isolated
negative cases and do not claim readings of historical material.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from lxml import etree

ACCOUNTS = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "validation"
VALID = FIXTURES / "valid-account.xml"
TEI = {"tei": "http://www.tei-c.org/ns/1.0"}


def _load_validator():
    path = ACCOUNTS / "validate_tei.py"
    spec = importlib.util.spec_from_file_location("docta_account_validate_tei", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


validator = _load_validator()


def _mutated(tmp_path: Path, mutate) -> Path:
    document = etree.parse(str(VALID))
    mutate(document)
    path = tmp_path / "mutated.xml"
    document.write(path, encoding="utf-8", xml_declaration=True)
    return path


def _messages(path: Path) -> list[str]:
    return [finding.message for finding in validator.validate_file(path)]


def test_valid_fixture_passes_tei_profile_and_schematron() -> None:
    assert validator.validate_file(VALID) == []
    text = VALID.read_text(encoding="utf-8")
    assert "Technical test data" in text
    assert "no scholarly verification" in text


def test_unresolved_entity_reference_is_rejected(tmp_path: Path) -> None:
    def mutate(document) -> None:
        name = document.find(".//tei:text//tei:persName", TEI)
        name.set("ref", "#person-missing")

    messages = _messages(_mutated(tmp_path, mutate))
    assert any("local ref" in message for message in messages)
    assert any("listPerson" in message for message in messages)


def test_entry_transaction_transfer_context_is_rejected(tmp_path: Path) -> None:
    def mutate(document) -> None:
        entry = document.find(".//tei:seg[@ana='bk:Entry']", TEI)
        transaction = entry.find("tei:seg[@ana='bk:Transaction']", TEI)
        entry.getparent().append(transaction)

    messages = _messages(_mutated(tmp_path, mutate))
    assert any("Transaction must be a direct child" in message for message in messages)
    assert any(
        "Entry must contain at least one Transaction" in message for message in messages
    )


def test_unit_and_taxonomy_links_are_rejected(tmp_path: Path) -> None:
    def mutate(document) -> None:
        entry = document.find(".//tei:seg[@ana='bk:Entry']", TEI)
        entry.set("type", "rubric-missing")
        entry.set("subtype", "account-missing")
        measure = document.find(".//tei:measure[@ana='bk:EconomicGood']", TEI)
        measure.set("unitRef", "#unit-missing")
        measure.set("commodity", "good-missing")

    messages = _messages(_mutated(tmp_path, mutate))
    assert any("unitRef" in message for message in messages)
    assert any("source-rubrics taxonomy" in message for message in messages)
    assert any("account-categories taxonomy" in message for message in messages)
    assert any("goods taxonomy" in message for message in messages)


def test_transfer_without_resource_is_rejected(tmp_path: Path) -> None:
    def mutate(document) -> None:
        transfer = document.find(".//tei:seg[@ana='bk:Transfer']", TEI)
        measure = transfer.find("tei:measure", TEI)
        transfer.remove(measure)

    messages = _messages(_mutated(tmp_path, mutate))
    assert any("Transfer must contain a resource" in message for message in messages)


def test_missing_target_is_a_usage_error() -> None:
    assert validator.main([str(FIXTURES / "missing.xml")]) == 2


@pytest.mark.parametrize(
    "schema",
    [
        validator.TEI_SCHEMA,
        validator.PROFILE_SCHEMA,
        validator.SCHEMATRON_SCHEMA,
    ],
)
def test_schema_artifacts_exist(schema: Path) -> None:
    assert schema.is_file()
