"""Tests for SHACL validation and deterministic RDF comparison.

All graphs are synthetic software fixtures and carry no scholarly verification.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from rdflib import RDF, Graph, Namespace

ACCOUNTS = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "validation"


def _load_validator():
    path = ACCOUNTS / "validate_rdf.py"
    spec = importlib.util.spec_from_file_location("docta_account_validate_rdf", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


validator = _load_validator()
BK = Namespace("https://gams.uni-graz.at/o:depcha.bookkeeping#")
EX = Namespace("https://dhcraft.org/DoCTA/id/fixture/")
pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


def _validate(name: str):
    return validator.validate_file(FIXTURES / name)


def test_valid_graph_conforms_without_findings() -> None:
    conforms, findings = _validate("valid-account.ttl")
    assert conforms
    assert findings == []


@pytest.mark.parametrize(
    ("fixture", "message"),
    [
        ("invalid-missing-transfer.ttl", "at least one Transfer"),
        ("invalid-missing-source-anchor.ttl", "requires a source anchor"),
        ("invalid-missing-resource.ttl", "at least one resource"),
        ("invalid-missing-parties.ttl", "at least one source-attested party"),
    ],
)
def test_release_violations_are_rejected(fixture: str, message: str) -> None:
    conforms, findings = _validate(fixture)
    assert not conforms
    violations = [finding for finding in findings if finding.severity == "Violation"]
    assert any(message in finding.message for finding in violations)


def test_one_unknown_party_is_a_non_blocking_warning() -> None:
    conforms, findings = _validate("warning-one-party.ttl")
    assert conforms
    assert [finding.severity for finding in findings] == ["Warning"]
    assert "to-agent" in findings[0].message


def test_unsupported_resource_class_is_rejected() -> None:
    path = FIXTURES / "valid-account.ttl"
    graph = validator.load_graph(path)
    graph.remove((EX["money-1"], RDF.type, BK.Money))
    graph.add((EX["money-1"], RDF.type, EX.UnsupportedResource))
    conforms, findings = validator.validate_graph(graph, path=path)
    assert not conforms
    assert any("supported bookkeeping class" in finding.message for finding in findings)


def test_graph_comparison_ignores_order_and_prefixes() -> None:
    left = validator.load_graph(FIXTURES / "valid-account.ttl")
    right = validator.load_graph(FIXTURES / "equivalent-valid-account.ttl")
    assert validator.graphs_equal(left, right)
    assert validator.sorted_ntriples(left) == validator.sorted_ntriples(right)


def test_sorted_ntriples_refuses_blank_nodes() -> None:
    graph = Graph().parse(
        data="[] <https://example.invalid/p> <https://example.invalid/o> .",
        format="turtle",
    )
    with pytest.raises(ValueError, match="blank nodes"):
        validator.sorted_ntriples(graph)


def test_strict_warning_cli_turns_warning_into_failure() -> None:
    path = FIXTURES / "warning-one-party.ttl"
    assert validator.main([str(path)]) == 0
    assert validator.main([str(path), "--strict-warnings"]) == 1
