"""Import one Inventaria PAGE XML document into a private annotation snapshot.

This flat pipeline script retrieves one explicitly named published document or
accepts its complete local PAGE XML export. It preserves page, region, and line
identifiers, XML attributes, raw ``custom`` strings, and parsed annotation
attributes. Annotation offsets are validated against the line Unicode text. The
output is restricted to ``tmp/inventaria`` because the rights decision in
``docs/knowledge/data.md`` permits a private research copy but not publication
of the annotation collection.

Usage: ``uv run python scripts/import_inventaria.py --doc-id ID --output
tmp/inventaria/ID.json``. Add ``--input-dir DIR`` for a local export and pass
``--expected-pages`` when it has no manifest with an ``expectedPages`` field.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
PRIVATE_ROOT = (ROOT / "tmp" / "inventaria").resolve()
CUSTOM_BLOCK = re.compile(r"(?P<type>[\w.-]+)\s*\{(?P<body>[^{}]*)\}")
PAGES_API = "https://api-sites.transkribus.eu/search/documents/{doc_id}/pages"
FILES_PREFIX = "https://files.transkribus.eu/Get?id="
USER_AGENT = (
    "DoCTA-research-import/1.0 (https://github.com/DigitalHumanitiesCraft/DoCTA)"
)


def _parse_custom(raw: str, text: str, location: str) -> list[dict[str, Any]]:
    annotations = []
    consumed = []
    for match in CUSTOM_BLOCK.finditer(raw):
        consumed.append(match.span())
        attributes: dict[str, str] = {}
        for field in match.group("body").split(";"):
            field = field.strip()
            if not field:
                continue
            if ":" not in field:
                raise ValueError(f"{location}: malformed custom field {field!r}")
            key, value = field.split(":", 1)
            key = key.strip()
            if not key or key in attributes:
                raise ValueError(f"{location}: invalid duplicate or empty custom key")
            attributes[key] = value.strip()

        annotation: dict[str, Any] = {
            "type": match.group("type"),
            "attributes": attributes,
            "raw": match.group(0),
        }
        has_offset = "offset" in attributes
        has_length = "length" in attributes
        if has_offset != has_length:
            raise ValueError(f"{location}: annotation needs both offset and length")
        if has_offset:
            try:
                offset = int(attributes["offset"])
                length = int(attributes["length"])
            except ValueError as error:
                raise ValueError(
                    f"{location}: offset and length must be integers"
                ) from error
            if offset < 0 or length < 0 or offset + length > len(text):
                raise ValueError(
                    f"{location}: annotation span {offset}:{offset + length} "
                    f"exceeds line length {len(text)}"
                )
            annotation.update(
                {
                    "offset": offset,
                    "length": length,
                    "text": text[offset : offset + length],
                }
            )
        if "prov" in attributes:
            annotation["provenance"] = attributes["prov"]
        annotations.append(annotation)

    remainder = raw
    for start, end in reversed(consumed):
        remainder = remainder[:start] + remainder[end:]
    if remainder.strip():
        raise ValueError(f"{location}: unparsed custom content {remainder.strip()!r}")
    return annotations


def _attributes(element: etree._Element) -> dict[str, str]:
    return {str(key): value for key, value in sorted(element.attrib.items())}


def _custom(element: etree._Element, text: str, location: str) -> dict[str, Any]:
    raw = element.get("custom", "")
    return {"raw": raw, "annotations": _parse_custom(raw, text, location)}


def parse_page(path: Path) -> dict[str, Any]:
    """Parse one strict PAGE file without network or entity resolution."""
    parser = etree.XMLParser(
        resolve_entities=False, no_network=True, recover=False, huge_tree=False
    )
    try:
        root = etree.parse(path, parser).getroot()
    except etree.XMLSyntaxError as error:
        raise ValueError(f"{path.name}: invalid XML: {error}") from error
    namespace = etree.QName(root).namespace
    if (
        etree.QName(root).localname != "PcGts"
        or not namespace
        or "PAGE/gts" not in namespace
    ):
        raise ValueError(f"{path.name}: root is not a PAGE PcGts element")
    page_ns = {"page": namespace}
    page = root.find("page:Page", page_ns)
    if page is None:
        raise ValueError(f"{path.name}: PAGE Page element is missing")

    regions = []
    seen_region_ids: set[str] = set()
    seen_line_ids: set[str] = set()
    for region in page.findall("page:TextRegion", page_ns):
        region_id = region.get("id")
        if not region_id or region_id in seen_region_ids:
            raise ValueError(
                f"{path.name}: missing or duplicate region id {region_id!r}"
            )
        seen_region_ids.add(region_id)
        lines = []
        for line in region.findall("page:TextLine", page_ns):
            line_id = line.get("id")
            if not line_id or line_id in seen_line_ids:
                raise ValueError(
                    f"{path.name}: missing or duplicate line id {line_id!r}"
                )
            seen_line_ids.add(line_id)
            unicode_node = line.find("page:TextEquiv/page:Unicode", page_ns)
            text = (
                ""
                if unicode_node is None or unicode_node.text is None
                else unicode_node.text
            )
            lines.append(
                {
                    "id": line_id,
                    "attributes": _attributes(line),
                    "text": text,
                    "custom": _custom(line, text, f"{path.name}/{region_id}/{line_id}"),
                }
            )
        regions.append(
            {
                "id": region_id,
                "attributes": _attributes(region),
                "custom": _custom(region, "", f"{path.name}/{region_id}"),
                "lines": lines,
            }
        )
    return {
        "sourceFile": path.name,
        "id": page.get("id"),
        "attributes": _attributes(page),
        "custom": _custom(page, "", path.name),
        "regions": regions,
    }


def _expected_pages(input_dir: Path, cli_value: int | None) -> int:
    manifest_path = input_dir / "manifest.json"
    manifest_value = None
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_value = manifest.get("expectedPages")
        if not isinstance(manifest_value, int) or manifest_value < 1:
            raise ValueError("manifest.json: expectedPages must be a positive integer")
    if (
        cli_value is not None
        and manifest_value is not None
        and cli_value != manifest_value
    ):
        raise ValueError("--expected-pages disagrees with manifest.json")
    expected = cli_value if cli_value is not None else manifest_value
    if expected is None or expected < 1:
        raise ValueError("completeness requires --expected-pages or manifest.json")
    return expected


def _private_output(path: Path) -> Path:
    resolved = path.resolve()
    if resolved != PRIVATE_ROOT and PRIVATE_ROOT not in resolved.parents:
        raise ValueError(f"output must stay under {PRIVATE_ROOT}")
    return resolved


def _write_json(path: Path, payload: dict[str, Any], force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"{path} exists; pass --force to replace it")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _request(url: str, data: bytes | None = None) -> bytes:
    headers = {"User-Agent": USER_AGENT}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def _write_bytes(path: Path, content: bytes) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_bytes(content)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def fetch_public_export(doc_id: int, force: bool) -> Path:
    """Cache every published page exposed by the Sites document endpoint."""
    cache = PRIVATE_ROOT / "cache" / str(doc_id)
    cache.mkdir(parents=True, exist_ok=True)
    limit = 50
    offset = 0
    total = None
    items: list[dict[str, Any]] = []
    while total is None or offset < total:
        body = json.dumps(
            {
                "id": doc_id,
                "collections": [1979152],
                "url": "inventaria",
                "offset": offset,
                "limit": limit,
            }
        ).encode()
        payload = json.loads(_request(PAGES_API.format(doc_id=doc_id), body))
        if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
            raise ValueError("public pages response has no items array")
        response_total = payload.get("total")
        if not isinstance(response_total, int) or response_total < 1:
            raise ValueError("public pages response has no positive total")
        if total is not None and response_total != total:
            raise ValueError("public page total changed during pagination")
        total = response_total
        batch = payload["items"]
        if not batch:
            raise ValueError(f"public pagination stopped at offset {offset} of {total}")
        items.extend(batch)
        offset += len(batch)
        if offset < total:
            time.sleep(0.2)
    if len(items) != total:
        raise ValueError(f"public pagination returned {len(items)} of {total} pages")

    numbers: set[int] = set()
    for item in items:
        number = item.get("number")
        xml_url = item.get("xmlKey")
        if not isinstance(number, int) or number < 1 or number in numbers:
            raise ValueError(
                f"public pages response has invalid page number {number!r}"
            )
        if not isinstance(xml_url, str) or not xml_url.startswith(FILES_PREFIX):
            raise ValueError(f"page {number} has an invalid PAGE XML URL")
        numbers.add(number)
        target = cache / f"{number:06d}.xml"
        if target.exists() and not force:
            continue
        _write_bytes(target, _request(xml_url))
        time.sleep(0.2)
    expected_numbers = set(range(1, total + 1))
    if numbers != expected_numbers:
        raise ValueError(
            "published page numbers are not contiguous from one through total"
        )
    (cache / "manifest.json").write_text(
        json.dumps({"expectedPages": total}) + "\n", encoding="utf-8", newline="\n"
    )
    return cache


def build(
    doc_id: int, input_dir: Path, output: Path, expected_pages: int | None, force: bool
) -> None:
    if not input_dir.is_dir():
        raise ValueError(f"input directory does not exist: {input_dir}")
    paths = sorted(input_dir.glob("*.xml"), key=lambda path: path.name.casefold())
    expected = _expected_pages(input_dir, expected_pages)
    if len(paths) != expected:
        raise ValueError(
            f"incomplete export: expected {expected} PAGE files, found {len(paths)}"
        )
    pages = [parse_page(path) for path in paths]
    payload = {
        "docId": doc_id,
        "provenance": {
            "source": "Inventaria published PAGE XML local research copy",
            "generator": "scripts/import_inventaria.py",
            "publication": "private research copy; not cleared for republication",
        },
        "completeness": {
            "expectedPages": expected,
            "importedPages": len(pages),
            "complete": True,
        },
        "pages": pages,
    }
    _write_json(_private_output(output), payload, force)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--doc-id", type=int, required=True)
    parser.add_argument(
        "--input-dir",
        type=Path,
        help="complete local PAGE export; omit to retrieve this document from its public site",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-pages", type=int)
    parser.add_argument("--force", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        input_dir = args.input_dir or fetch_public_export(args.doc_id, args.force)
        build(args.doc_id, input_dir, args.output, args.expected_pages, args.force)
    except (OSError, ValueError, json.JSONDecodeError, urllib.error.URLError) as error:
        print(f"FEHLER {error}", file=sys.stderr)
        return 1
    print(f"OK private Inventaria snapshot written to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
