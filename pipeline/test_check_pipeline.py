"""Tests for the pipeline healthcheck, runnable with pytest or plain python.

The clean case runs against the real repository, because that is what the check is for.
The two failure cases work on a copy in a temporary directory with the module constants
pointed at it, so nothing in the working tree is touched.

Usage:
  python test_check_pipeline.py
  pytest pipeline/test_check_pipeline.py
"""

import contextlib
import io
import json
import shutil
import sys
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
