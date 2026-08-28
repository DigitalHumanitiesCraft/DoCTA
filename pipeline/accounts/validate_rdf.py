"""Validate DoCTA accounting RDF with the project SHACL Core shapes.

The default release gate treats SHACL Violations as failures and retains SHACL
Warnings as visible findings. It also exposes semantic graph comparison and a
stable sorted N-Triples representation for deterministic fixture tests.

Usage:
    python pipeline/accounts/validate_rdf.py FILE_OR_DIRECTORY [...]
    python pipeline/accounts/validate_rdf.py FILE --compare EXPECTED_FILE
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from pyshacl import validate
from rdflib import BNode, Graph, Namespace
from rdflib.compare import to_isomorphic

ROOT = Path(__file__).resolve().parent
SHAPES = ROOT / "shapes" / "docta-accounts.ttl"
SH = Namespace("http://www.w3.org/ns/shacl#")
RDF_EXTENSIONS = {".ttl", ".nt", ".rdf", ".xml", ".jsonld", ".json-ld"}


@dataclass(frozen=True)
class Finding:
    """One SHACL result with its severity and focus node."""

    path: Path
    severity: str
    message: str
    focus_node: str = ""
    result_path: str = ""

    def __str__(self) -> str:
        focus = f" focus={self.focus_node}" if self.focus_node else ""
        predicate = f" path={self.result_path}" if self.result_path else ""
        return f"{self.path}: {self.severity}: {self.message}{focus}{predicate}"


def load_graph(path: Path) -> Graph:
    """Parse one RDF graph, failing at the file boundary with its path intact."""

    graph = Graph()
    graph.parse(path)
    return graph


def _local_name(value: object) -> str:
    text = str(value)
    return text.rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def validate_graph(
    graph: Graph,
    *,
    path: Path,
    shapes_path: Path = SHAPES,
) -> tuple[bool, list[Finding]]:
    """Apply SHACL Core and return release conformance plus all result records."""

    conforms, report_graph, _ = validate(
        data_graph=graph,
        shacl_graph=str(shapes_path),
        inference="none",
        abort_on_first=False,
        allow_infos=True,
        allow_warnings=True,
        meta_shacl=False,
        advanced=False,
    )
    findings: list[Finding] = []
    for result in report_graph.subjects(predicate=None, object=SH.ValidationResult):
        severity = report_graph.value(result, SH.resultSeverity)
        message = report_graph.value(result, SH.resultMessage)
        focus = report_graph.value(result, SH.focusNode)
        result_path = report_graph.value(result, SH.resultPath)
        findings.append(
            Finding(
                path=path,
                severity=_local_name(severity) if severity else "Violation",
                message=str(message or "SHACL constraint failed."),
                focus_node=str(focus or ""),
                result_path=str(result_path or ""),
            )
        )
    findings.sort(
        key=lambda item: (
            item.severity,
            item.focus_node,
            item.result_path,
            item.message,
        )
    )
    has_violation = any(item.severity == "Violation" for item in findings)
    return bool(conforms) and not has_violation, findings


def validate_file(
    path: Path,
    *,
    shapes_path: Path = SHAPES,
) -> tuple[bool, list[Finding]]:
    graph = load_graph(path)
    return validate_graph(graph, path=path, shapes_path=shapes_path)


def graphs_equal(left: Graph, right: Graph) -> bool:
    """Compare RDF meaning rather than serialisation order or prefix choices."""

    return to_isomorphic(left) == to_isomorphic(right)


def sorted_ntriples(graph: Graph) -> str:
    """Return stable N-Triples for graphs whose published nodes are all named."""

    if any(isinstance(term, BNode) for triple in graph for term in triple):
        raise ValueError("Stable N-Triples require a graph without blank nodes.")
    lines = [
        f"{subject.n3()} {predicate.n3()} {obj.n3()} ."
        for subject, predicate, obj in graph
    ]
    return "\n".join(sorted(lines)) + ("\n" if lines else "")


def collect_files(targets: list[Path]) -> list[Path]:
    files: set[Path] = set()
    for target in targets:
        if target.is_file():
            files.add(target)
        elif target.is_dir():
            files.update(
                path
                for path in target.rglob("*")
                if path.suffix.lower() in RDF_EXTENSIONS
            )
        else:
            raise FileNotFoundError(f"RDF target does not exist: {target}")
    return sorted(files)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("targets", nargs="+", type=Path)
    parser.add_argument("--shapes", type=Path, default=SHAPES)
    parser.add_argument("--compare", type=Path)
    parser.add_argument("--strict-warnings", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.shapes.is_file():
        print(f"FEHLER shapes missing: {args.shapes}", file=sys.stderr)
        return 2
    try:
        files = collect_files(args.targets)
    except FileNotFoundError as exc:
        print(f"FEHLER {exc}", file=sys.stderr)
        return 2
    if not files:
        print("FEHLER no RDF files found", file=sys.stderr)
        return 2

    findings: list[Finding] = []
    failed = False
    graphs: list[Graph] = []
    for path in files:
        try:
            graph = load_graph(path)
        except Exception as exc:  # rdflib exposes parser-specific exception types
            print(f"FEHLER {path}: RDF parse: {exc}", file=sys.stderr)
            failed = True
            continue
        graphs.append(graph)
        conforms, result = validate_graph(graph, path=path, shapes_path=args.shapes)
        findings += result
        failed = failed or not conforms

    if args.compare:
        if len(graphs) != 1:
            print(
                "FEHLER --compare requires exactly one parsed input graph",
                file=sys.stderr,
            )
            return 2
        try:
            expected = load_graph(args.compare)
        except Exception as exc:  # rdflib exposes parser-specific exception types
            print(f"FEHLER {args.compare}: RDF parse: {exc}", file=sys.stderr)
            return 2
        if not graphs_equal(graphs[0], expected):
            print(
                "FEHLER RDF graph differs semantically from expected graph",
                file=sys.stderr,
            )
            failed = True

    for finding in findings:
        stream = sys.stderr if finding.severity == "Violation" else sys.stdout
        print(f"{finding.severity.upper()} {finding}", file=stream)
    if args.strict_warnings and any(item.severity == "Warning" for item in findings):
        failed = True
    print(
        f"{'FEHLER' if failed else 'OK'} {len(files)} file(s), {len(findings)} finding(s)"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(main())
