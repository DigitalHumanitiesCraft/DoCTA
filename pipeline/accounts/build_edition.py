"""Build a deterministic pre-release bundle for one DoCTA account-book scan.

The flat script-pipeline stage joins one existing machine transcription run to
one PAGE document whose line text must match it exactly. It writes the anchored
``TranscriptionRevision`` and an Edition Build Manifest with checksums and
provenance. The manifest deliberately records that TEI and RDF release remain
blocked until an editorially accepted Annotation Set exists. It never turns
machine output into accepted accounting data.

Usage:
    python pipeline/accounts/build_edition.py RUN.json PAGE.xml OUTPUT_DIR
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from hashlib import sha256
from pathlib import Path
from typing import Any

from pipeline.accounts.anchors import import_page_xml
from pipeline.accounts.models import model_payload, write_model_atomic

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE_MANIFEST = ROOT / "docs" / "data" / "raitbuch2_pages.json"
DOCUMENT_ID = 12514730
BUILD_SPECIFICATION = "docta-accounts-edition-build"
BUILD_SPECIFICATION_VERSION = "0.1.0"


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_json(path: Path) -> Any:
    if not path.is_file():
        raise FileNotFoundError(f"required input does not exist: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _page_number(run: dict[str, Any]) -> int:
    page_id = run.get("page")
    if not isinstance(page_id, str) or "_p" not in page_id:
        raise ValueError("run needs a page id ending in _p<scan number>")
    try:
        number = int(page_id.rsplit("_p", 1)[1])
    except ValueError as exc:
        raise ValueError("run page id has no integer scan number") from exc
    if number <= 0:
        raise ValueError("run scan number must be positive")
    return number


def _run_lines(run: dict[str, Any]) -> tuple[str, ...]:
    lines = run.get("lines")
    if not isinstance(lines, list) or not all(isinstance(line, str) for line in lines):
        raise ValueError("run needs a string array named lines")
    if not lines:
        raise ValueError("run has no transcription lines")
    return tuple(lines)


def _source_page(source_manifest: Any, scan_number: int) -> dict[str, Any]:
    if not isinstance(source_manifest, list):
        raise ValueError("source manifest must be an array")
    matches = [
        page
        for page in source_manifest
        if isinstance(page, dict) and page.get("pageNr") == scan_number
    ]
    if len(matches) != 1:
        raise ValueError(
            f"source manifest needs exactly one pageNr {scan_number}, got {len(matches)}"
        )
    page = matches[0]
    for key in ("key", "imgFileName", "iiif_url"):
        if not isinstance(page.get(key), str) or not page[key]:
            raise ValueError(f"source page {scan_number} needs {key}")
    return page


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    encoded = (
        json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    ).encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() == encoded:
            return
        raise FileExistsError(f"artifact already exists with different content: {path}")
    handle, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def build(
    run_path: Path,
    page_xml_path: Path,
    output_dir: Path,
    *,
    source_manifest_path: Path = DEFAULT_SOURCE_MANIFEST,
    document_id: int = DOCUMENT_ID,
) -> dict[str, Any]:
    """Build an anchored machine-text bundle without asserting semantics."""

    run = _load_json(run_path)
    if not isinstance(run, dict):
        raise ValueError("run must be a JSON object")
    scan_number = _page_number(run)
    expected_lines = _run_lines(run)
    source_manifest = _load_json(source_manifest_path)
    source_page = _source_page(source_manifest, scan_number)
    if not page_xml_path.is_file():
        raise FileNotFoundError(f"required PAGE XML does not exist: {page_xml_path}")

    revision_id = f"tr-{run['page']}-{run.get('iteration', 'unknown')}-r{run.get('repeat', 'unknown')}"
    revision = import_page_xml(
        page_xml_path.read_bytes(),
        document_id=document_id,
        scan_number=scan_number,
        revision_id=revision_id,
    )
    actual_lines = tuple(line.text for line in revision.lines)
    if actual_lines != expected_lines:
        raise ValueError(
            "PAGE line text does not match the selected machine run; "
            f"PAGE has {len(actual_lines)} lines and run has {len(expected_lines)}"
        )

    revision_path = output_dir / "transcription-revision.json"
    manifest_path = output_dir / "edition-build-manifest.json"
    manifest = {
        "specification": BUILD_SPECIFICATION,
        "specificationVersion": BUILD_SPECIFICATION_VERSION,
        "releaseEligible": False,
        "releaseBlockers": [
            "No editorially accepted Annotation Set was supplied; accounting TEI and RDF were not generated."
        ],
        "artifacts": {
            "transcriptionRevision": {
                "path": revision_path.name,
                "transcriptionSha256": revision.sha256,
                "verification": revision.verification.value,
                "publication": revision.publication.value,
                "editorialLabel": "machine-unrevised",
            },
            "tei": None,
            "rdf": None,
        },
        "inputs": {
            "machineRun": {
                "path": run_path.as_posix(),
                "sha256": _file_sha256(run_path),
                "page": run["page"],
                "iteration": run.get("iteration"),
                "repeat": run.get("repeat"),
                "model": run.get("model"),
                "promptHash": run.get("prompt_hash"),
            },
            "pageXml": {
                "path": page_xml_path.as_posix(),
                "sha256": _file_sha256(page_xml_path),
            },
            "sourceManifest": {
                "path": source_manifest_path.as_posix(),
                "sha256": _file_sha256(source_manifest_path),
                "page": {
                    "pageNr": source_page["pageNr"],
                    "key": source_page["key"],
                    "imgFileName": source_page["imgFileName"],
                    "iiifUrl": source_page["iiif_url"],
                },
            },
        },
        "generator": {
            "path": Path(__file__).resolve().as_posix(),
            "sha256": _file_sha256(Path(__file__).resolve()),
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    write_model_atomic(revision_path, revision)
    manifest["artifacts"]["transcriptionRevision"]["fileSha256"] = _file_sha256(
        revision_path
    )
    _write_json_atomic(manifest_path, manifest)
    return {"manifest": manifest, "revision": model_payload(revision)}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("page_xml", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--source-manifest", type=Path, default=DEFAULT_SOURCE_MANIFEST)
    parser.add_argument("--document-id", type=int, default=DOCUMENT_ID)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = build(
            args.run,
            args.page_xml,
            args.output_dir,
            source_manifest_path=args.source_manifest,
            document_id=args.document_id,
        )
    except (
        FileNotFoundError,
        FileExistsError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"FEHLER {exc}", file=sys.stderr)
        return 1
    revision = result["revision"]
    print(
        f"OK anchored {len(revision['lines'])} machine-unrevised lines; "
        "TEI/RDF blocked without accepted annotations"
    )
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(main())
