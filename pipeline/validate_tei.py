"""Validate the generated TEI files in two stages.

Stage 1 is TEI conformance against the vendored TEI P5 RelaxNG (`tei_all.rng`), stage 2 the
DoCTA encoding contract against the hand-written project schema (`docta.rng`). The two
answer different questions, so they are reported separately per stage: a file may be
perfectly good TEI and still carry something the pipeline never emits.

Usage:
    python pipeline/validate_tei.py [--tei-dir DIR] [--max-errors N]
    python pipeline/validate_tei.py --schema PATH      # single-schema run

Exit code 0 only when every file parses and validates in every stage that ran.

Requires lxml (pinned in this environment: lxml 5.3.0, libxml2 2.11.7). Without lxml the
script falls back to the `jing` CLI if it is on PATH, and otherwise exits with a message
naming what to install.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

SCHEMA_DIR = Path(__file__).resolve().parent / "schema"
DEFAULT_TEI_DIR = Path(__file__).resolve().parent.parent / "docs" / "data" / "tei"
TEI_SCHEMA = SCHEMA_DIR / "tei_all.rng"
DOCTA_SCHEMA = SCHEMA_DIR / "docta.rng"
DEFAULT_MAX_ERRORS = 3

# Stage label to schema; the label is what the report and the healthcheck name.
STAGES = (("TEI conformance", TEI_SCHEMA), ("DoCTA contract", DOCTA_SCHEMA))

MISSING_TOOLS_MESSAGE = (
    "No RelaxNG validator available. Install lxml (`pip install lxml`) or put the "
    "`jing` CLI on PATH."
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tei-dir", type=Path, default=DEFAULT_TEI_DIR)
    parser.add_argument(
        "--schema",
        type=Path,
        default=None,
        help="validate against this schema only, instead of both stages",
    )
    parser.add_argument(
        "--max-errors",
        type=int,
        default=DEFAULT_MAX_ERRORS,
        help="errors reported per invalid file",
    )
    return parser.parse_args(argv)


def collect_files(tei_dir: Path) -> list[Path]:
    return sorted(tei_dir.glob("*.xml"))


def validate_with_lxml(
    files: list[Path], schema_path: Path, max_errors: int
) -> list[Path]:
    from lxml import etree

    relaxng = etree.RelaxNG(etree.parse(str(schema_path)))
    invalid: list[Path] = []
    for path in files:
        try:
            doc = etree.parse(str(path))
        except etree.XMLSyntaxError as exc:
            invalid.append(path)
            print(f"{path.name}: XML not well-formed: {exc}")
            continue
        if relaxng.validate(doc):
            continue
        invalid.append(path)
        entries = list(relaxng.error_log)
        for entry in entries[:max_errors]:
            print(f"{path.name}:{entry.line}: {entry.message}")
        if len(entries) > max_errors:
            print(f"{path.name}: ... {len(entries) - max_errors} further error(s)")
    return invalid


def validate_with_jing(
    files: list[Path], schema_path: Path, max_errors: int
) -> list[Path]:
    invalid: list[Path] = []
    for path in files:
        result = subprocess.run(
            ["jing", str(schema_path), str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            continue
        invalid.append(path)
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        for line in lines[:max_errors]:
            print(line)
        if len(lines) > max_errors:
            print(f"{path.name}: ... {len(lines) - max_errors} further error(s)")
    return invalid


def _validator():
    """The available RelaxNG validator, or None when neither lxml nor jing is there."""
    try:
        import lxml  # noqa: F401
    except ImportError:
        return validate_with_jing if shutil.which("jing") else None
    return validate_with_lxml


def run_stage(
    label: str, files: list[Path], schema_path: Path, max_errors: int
) -> list[Path]:
    """One validation stage, reported on its own line. Returns the invalid files."""
    validate = _validator()
    if validate is None:  # pragma: no cover - guarded in main
        raise RuntimeError(MISSING_TOOLS_MESSAGE)
    invalid = validate(files, schema_path, max_errors)
    print(
        f"{label}: {len(files) - len(invalid)}/{len(files)} files valid"
        f" against {schema_path.name}"
    )
    return invalid


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    stages = [("Schema", args.schema)] if args.schema else list(STAGES)
    for _, schema in stages:
        if not schema.is_file():
            print(f"Schema not found: {schema}", file=sys.stderr)
            return 2
    if not args.tei_dir.is_dir():
        print(f"TEI directory not found: {args.tei_dir}", file=sys.stderr)
        return 2

    files = collect_files(args.tei_dir)
    if not files:
        print(f"No TEI files found in {args.tei_dir}", file=sys.stderr)
        return 2

    if _validator() is None:
        print(MISSING_TOOLS_MESSAGE, file=sys.stderr)
        return 2

    failed = 0
    for label, schema in stages:
        failed += len(run_stage(label, files, schema, args.max_errors))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
