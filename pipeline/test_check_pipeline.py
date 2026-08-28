"""Tests for the pipeline healthcheck.

The clean case runs against the real repository, because that is what the check is for.
The failure cases work on a copy in a temporary directory with the module constants
pointed at it, so nothing in the working tree is touched.

Usage:
  pytest pipeline/test_check_pipeline.py
"""

import contextlib
import io
import json
import shutil
import tempfile
from pathlib import Path

import check_pipeline as cp
import pytest


def _run(argv: list[str]) -> tuple[int, str]:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = cp.main(argv)
    return code, buffer.getvalue()


@pytest.mark.slow
def test_clean_run_exits_zero() -> None:
    """The working tree passes every check; INFO findings do not change the exit.

    Slow by design: it measures the state of the working tree, including the
    full rebuild, and runs via the pre-commit hook or pytest -m slow.
    """
    code, report = _run([])
    assert code == 0, f"healthcheck failed on the real repo:\n{report}"


def test_broken_register_vocabulary_is_caught() -> None:
    """A content_class outside the register vocabulary must not pass the contract."""
    with tempfile.TemporaryDirectory() as td:
        register = Path(td) / "pages"
        shutil.copytree(cp.REGISTER, register)
        path = sorted(register.glob("*.json"))[0]
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["pages"][0]["content_class"] = "geschwaerzt"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        original = cp.REGISTER
        cp.REGISTER = register
        try:
            findings = cp.check_contract()
        finally:
            cp.REGISTER = original

    hits = [f for f in findings if f.check == "contract.content-class"]
    assert hits, f"the broken vocabulary went unnoticed: {findings}"
    assert all(f.severity == cp.FAIL for f in hits), hits
    assert "geschwaerzt" in hits[0].message


def test_confidence_field_in_an_entity_file_is_caught() -> None:
    """A confidence value is a self-assessment of the agent and never edition data."""
    with tempfile.TemporaryDirectory() as td:
        entities = Path(td) / "entities"
        shutil.copytree(cp.ENTITY_DIR, entities)
        path = sorted(entities.glob("*.json"))[0]
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["entities"][0]["confidence"] = 0.87
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        original = cp.ENTITY_DIR
        cp.ENTITY_DIR = entities
        try:
            findings = cp.check_provenance()
        finally:
            cp.ENTITY_DIR = original

    hits = [f for f in findings if f.check == "provenance.confidence"]
    assert hits, f"the confidence field went unnoticed: {findings}"
    assert all(f.severity == cp.FAIL for f in hits), hits


def test_a_malformed_review_export_is_a_finding_and_not_a_crash() -> None:
    """A broken export file must be reported, so the rest of the run survives it."""
    with tempfile.TemporaryDirectory() as td:
        reviews = Path(td) / "reviews"
        reviews.mkdir()
        (reviews / "broken.json").write_text('{"docId":', encoding="utf-8")

        original = cp.REVIEWS
        cp.REVIEWS = reviews
        try:
            findings = cp._check_reviews()
        finally:
            cp.REVIEWS = original

    hits = [f for f in findings if f.check == "json.review-parse"]
    assert hits, f"the malformed export went unnoticed: {findings}"
    assert all(f.severity == cp.FAIL for f in hits), hits
    assert "broken.json" in hits[0].message


def test_a_crashing_check_becomes_a_finding_and_the_run_continues() -> None:
    """One unreadable input must not take the whole report down with it."""

    def exploding() -> list[cp.Finding]:
        raise RuntimeError("unreadable input")

    original = cp.CHECKS
    cp.CHECKS = (("boom", exploding), ("coverage", cp.check_coverage))
    try:
        code, report = _run([])
    finally:
        cp.CHECKS = original

    assert code == 1, report
    assert "FAIL boom.crashed: RuntimeError: unreadable input" in report
    assert "OK   coverage" in report, "the checks after the crash did not run"
