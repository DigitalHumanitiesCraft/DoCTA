"""Validate DoCTA accounting TEI against TEI P5 and the pilot profile.

The validator is offline and read-only. It first applies the vendored TEI P5
Relax NG schema, then the narrow accounting Relax NG schema, and finally the
accounting Schematron rules. The three stages remain separate because they
answer different questions and produce different remediation paths.

Usage:
    python pipeline/accounts/validate_tei.py FILE_OR_DIRECTORY [...]
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from lxml import etree, isoschematron

ROOT = Path(__file__).resolve().parent
TEI_SCHEMA = ROOT.parent / "schema" / "tei_all.rng"
PROFILE_SCHEMA = ROOT / "schema" / "docta-accounts.rng"
SCHEMATRON_SCHEMA = ROOT / "schema" / "docta-accounts.sch"
SVRL_NS = {"svrl": "http://purl.oclc.org/dsdl/svrl"}


@dataclass(frozen=True)
class Finding:
    """One validation failure tied to a stage and, where available, a line."""

    path: Path
    stage: str
    message: str
    line: int | None = None

    def __str__(self) -> str:
        location = f":{self.line}" if self.line else ""
        return f"{self.path}{location}: {self.stage}: {self.message}"


@cache
def _relaxng(schema_path: str) -> etree.RelaxNG:
    return etree.RelaxNG(etree.parse(schema_path))


@cache
def _schematron(schema_path: str) -> isoschematron.Schematron:
    return isoschematron.Schematron(
        etree.parse(schema_path),
        store_report=True,
    )


def _rng_findings(
    document: etree._ElementTree,
    path: Path,
    stage: str,
    schema_path: Path,
) -> list[Finding]:
    validator = _relaxng(str(schema_path.resolve()))
    if validator.validate(document):
        return []
    return [
        Finding(path, stage, entry.message, entry.line or None)
        for entry in validator.error_log
    ]


def _schematron_findings(
    document: etree._ElementTree,
    path: Path,
    schema_path: Path,
) -> list[Finding]:
    validator = _schematron(str(schema_path.resolve()))
    if validator.validate(document):
        return []
    report = validator.validation_report
    if report is None:
        return [
            Finding(path, "Schematron", "Validation failed without an SVRL report.")
        ]
    findings: list[Finding] = []
    for failed in report.xpath("//svrl:failed-assert", namespaces=SVRL_NS):
        message = " ".join(
            failed.xpath("string(svrl:text)", namespaces=SVRL_NS).split()
        )
        location = failed.get("location") or "unknown location"
        findings.append(Finding(path, "Schematron", f"{message} [{location}]"))
    return findings


def validate_file(
    path: Path,
    *,
    tei_schema: Path = TEI_SCHEMA,
    profile_schema: Path = PROFILE_SCHEMA,
    schematron_schema: Path = SCHEMATRON_SCHEMA,
) -> list[Finding]:
    """Return every formal finding for one generated accounting TEI file."""

    try:
        document = etree.parse(str(path))
    except (OSError, etree.XMLSyntaxError) as exc:
        line = exc.position[0] if isinstance(exc, etree.XMLSyntaxError) else None
        return [Finding(path, "XML", str(exc), line)]

    findings = _rng_findings(document, path, "TEI P5", tei_schema)
    findings += _rng_findings(document, path, "DoCTA account profile", profile_schema)
    findings += _schematron_findings(document, path, schematron_schema)
    return findings


def collect_files(targets: list[Path]) -> list[Path]:
    """Expand files and directories without silently accepting an empty target."""

    files: set[Path] = set()
    for target in targets:
        if target.is_file():
            files.add(target)
        elif target.is_dir():
            files.update(target.rglob("*.xml"))
        else:
            raise FileNotFoundError(f"TEI target does not exist: {target}")
    return sorted(files)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("targets", nargs="+", type=Path)
    parser.add_argument("--tei-schema", type=Path, default=TEI_SCHEMA)
    parser.add_argument("--profile-schema", type=Path, default=PROFILE_SCHEMA)
    parser.add_argument("--schematron", type=Path, default=SCHEMATRON_SCHEMA)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    for schema in (args.tei_schema, args.profile_schema, args.schematron):
        if not schema.is_file():
            print(f"FEHLER schema missing: {schema}", file=sys.stderr)
            return 2
    try:
        files = collect_files(args.targets)
    except FileNotFoundError as exc:
        print(f"FEHLER {exc}", file=sys.stderr)
        return 2
    if not files:
        print("FEHLER no XML files found", file=sys.stderr)
        return 2

    findings: list[Finding] = []
    for path in files:
        findings += validate_file(
            path,
            tei_schema=args.tei_schema,
            profile_schema=args.profile_schema,
            schematron_schema=args.schematron,
        )
    for finding in findings:
        print(f"FEHLER {finding}", file=sys.stderr)
    print(
        f"{'FEHLER' if findings else 'OK'} {len(files)} file(s), {len(findings)} finding(s)"
    )
    return 1 if findings else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(main())
