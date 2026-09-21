"""Retrieve or import image references for one explicit Transkribus document.

The script reads only metadata. With credentials in the environment it obtains
an authenticated ``fulldoc`` response. Without them, ``--export-request`` writes
a private request descriptor that can accompany a manually exported response;
``--input`` then validates that response and emits a proposed merge. It never
changes ``docs/data/edition_pages.json``.

Usage: ``uv run python scripts/fetch_edition_pages.py --doc-id 12647153
--pages 2-6 --output tmp/inventaria/edition-pages.json --export-request``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PRIVATE_ROOT = (ROOT / "tmp" / "inventaria").resolve()
TOKEN_URL = (
    "https://account.readcoop.eu/auth/realms/readcoop/protocol/openid-connect/token"
)
API_BASE = "https://transkribus.eu/TrpServer/rest"
COLLECTION_ID = 2197991
USER_AGENT = (
    "DoCTA-edition-metadata/1.0 (https://github.com/DigitalHumanitiesCraft/DoCTA)"
)


def _parse_pages(value: str) -> tuple[int, ...]:
    match = value.split("-", 1)
    try:
        start = int(match[0])
        end = int(match[-1])
    except ValueError as error:
        raise argparse.ArgumentTypeError("pages must be N or N-M") from error
    if start < 1 or end < start:
        raise argparse.ArgumentTypeError("page range must be positive and ascending")
    return tuple(range(start, end + 1))


def _private_output(path: Path) -> Path:
    resolved = path.resolve()
    if resolved != PRIVATE_ROOT and PRIVATE_ROOT not in resolved.parents:
        raise ValueError(f"output must stay under {PRIVATE_ROOT}")
    return resolved


def _request_json(
    url: str, *, data: bytes | None = None, token: str | None = None
) -> Any:
    headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    if data is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def _authenticated_fulldoc(doc_id: int) -> dict[str, Any]:
    username = os.environ.get("TRANSKRIBUS_USER")
    password = os.environ.get("TRANSKRIBUS_PASS") or os.environ.get(
        "TRANSKRIBUS_PASSWORD"
    )
    if not username or not password:
        raise ValueError("Transkribus credentials are absent")
    form = urllib.parse.urlencode(
        {
            "grant_type": "password",
            "client_id": "transkribus-api-client",
            "username": username,
            "password": password,
        }
    ).encode()
    token_payload = _request_json(TOKEN_URL, data=form)
    token = token_payload.get("access_token")
    if not isinstance(token, str) or not token:
        raise ValueError("authentication response has no access token")
    result = _request_json(
        f"{API_BASE}/collections/{COLLECTION_ID}/{doc_id}/fulldoc", token=token
    )
    if not isinstance(result, dict):
        raise ValueError("fulldoc response is not an object")
    return result


def _page_list(payload: dict[str, Any]) -> list[dict[str, Any]]:
    page_list = payload.get("pageList")
    if not isinstance(page_list, dict) or not isinstance(page_list.get("pages"), list):
        raise ValueError("input has no pageList.pages array")
    return page_list["pages"]


def build_merge(
    doc_id: int, requested: tuple[int, ...], payload: dict[str, Any]
) -> dict[str, Any]:
    selected = []
    by_number: dict[int, dict[str, Any]] = {}
    for page in _page_list(payload):
        if not isinstance(page, dict) or not isinstance(page.get("pageNr"), int):
            raise ValueError("fulldoc contains a page without integer pageNr")
        number = page["pageNr"]
        if number in by_number:
            raise ValueError(f"fulldoc contains duplicate pageNr {number}")
        by_number[number] = page
    missing = [number for number in requested if number not in by_number]
    if missing:
        raise ValueError(f"fulldoc lacks requested pages {missing}")
    for number in requested:
        page = by_number[number]
        key = page.get("key")
        if not isinstance(key, str) or not key:
            raise ValueError(f"page {number} has no image key")
        selected.append(
            {
                "docId": doc_id,
                "pageNr": number,
                "imgKey": key,
                "iiif": f"https://files.transkribus.eu/iiif/2/{key}/full/max/0/default.jpg",
                "origin": f"authenticated fulldoc, collection {COLLECTION_ID}, document {doc_id}",
            }
        )
    return {
        "target": "docs/data/edition_pages.json",
        "approvalRequired": True,
        "docId": doc_id,
        "requestedPages": list(requested),
        "pages": selected,
    }


def _write(path: Path, payload: dict[str, Any], force: bool) -> None:
    path = _private_output(path)
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


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--doc-id", type=int, required=True)
    parser.add_argument("--pages", type=_parse_pages, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--export-request", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.input:
            payload = json.loads(args.input.read_text(encoding="utf-8"))
            result = build_merge(args.doc_id, args.pages, payload)
        elif args.export_request:
            result = {
                "status": "metadata-export-required",
                "method": "GET",
                "endpoint": f"{API_BASE}/collections/{COLLECTION_ID}/{args.doc_id}/fulldoc",
                "docId": args.doc_id,
                "requestedPages": list(args.pages),
                "nextCommand": (
                    f"uv run python scripts/fetch_edition_pages.py --doc-id {args.doc_id} "
                    f"--pages {args.pages[0]}-{args.pages[-1]} --input FULldoc.json "
                    f"--output {args.output} --force"
                ),
            }
        else:
            result = build_merge(
                args.doc_id, args.pages, _authenticated_fulldoc(args.doc_id)
            )
        _write(args.output, result, args.force)
    except (OSError, ValueError, json.JSONDecodeError, urllib.error.URLError) as error:
        print(f"FEHLER {error}", file=sys.stderr)
        return 1
    print(f"OK private metadata result written to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
