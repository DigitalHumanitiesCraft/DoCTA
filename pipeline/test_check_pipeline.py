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


def _benchmark_page(cer_mean: float, degenerate: bool | None) -> dict:
    page: dict = {
        "reference_class": "transkribus-done",
        "reference_chars": 38,
        "iterations": {
            "it02": {
                "k": 2,
                "lines": [8, 8],
                "cer_fair": {"mean": cer_mean},
                "consistency_words": 0.5,
                "consistency_numbers": 0.5,
            }
        },
    }
    if degenerate is not None:
        page["reference_degenerate"] = degenerate
    return page


def test_a_degenerate_reference_without_its_flag_is_caught() -> None:
    """The exclusion is a data property. A page the flag misses would have to be
    excluded by its measured rate again, which is what the flag replaces."""
    summary = {"pages": {"inv_x_p1": _benchmark_page(1.4, None)}}
    findings = cp._check_benchmark_metrics(summary)
    hits = [f for f in findings if f.check == "metrics.degenerate-unflagged"]
    assert hits, f"the unflagged degenerate reference went unnoticed: {findings}"
    assert all(f.severity == cp.FAIL for f in hits), hits


def test_a_flagged_degenerate_reference_is_reported_and_does_not_fail() -> None:
    findings = cp._check_benchmark_metrics(
        {"pages": {"inv_x_p1": _benchmark_page(1.4, True)}}
    )
    assert [f.check for f in findings] == ["metrics.degenerate-reference"]
    assert findings[0].severity == cp.INFO


def test_a_consistency_outside_its_range_is_caught_in_the_benchmark() -> None:
    page = _benchmark_page(0.3, False)
    page["iterations"]["it02"]["consistency_numbers"] = 1.4
    findings = cp._check_benchmark_metrics({"pages": {"inv_x_p1": page}})
    hits = [f for f in findings if f.check == "metrics.consistency"]
    assert hits, f"the out-of-range value went unnoticed: {findings}"
    assert all(f.severity == cp.FAIL for f in hits), hits


def test_a_drifted_site_copy_of_the_benchmark_summary_is_caught() -> None:
    """docs/data/benchmark/summary.json is copied by hand, so only this check
    keeps the published figures and the measured ones the same."""
    with tempfile.TemporaryDirectory() as td:
        stale = Path(td) / "summary.json"
        stale.write_text('{"pages": {}}', encoding="utf-8")
        original = cp.SITE_BENCHMARK_SUMMARY
        cp.SITE_BENCHMARK_SUMMARY = stale
        try:
            findings = cp._check_benchmark_copy()
        finally:
            cp.SITE_BENCHMARK_SUMMARY = original

    assert [f.check for f in findings] == ["metrics.benchmark-copy"], findings
    assert findings[0].severity == cp.FAIL


def test_the_committed_site_copy_matches_its_source() -> None:
    assert cp._check_benchmark_copy() == []


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
