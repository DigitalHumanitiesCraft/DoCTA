"""Map DoCTA documents to their published Inventaria edition on Transkribus Sites.

Queries the public sites API for the Inventaria hierarchy (every published
page with its image key) and matches those image keys against the IIIF keys
in the page register. The result docs/data/inventaria_mapping.json lets the
site link every attributed document straight to its published edition.

This is a harvester, so unlike the builders it talks to the network and
stamps its fetch time; the mapping file is input data, reviewed and committed
like any other source snapshot.
"""

import json
import re
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES_DIR = ROOT / "pipeline" / "pages"
OUT_FILE = ROOT / "docs" / "data" / "inventaria_mapping.json"

API = "https://api-sites.transkribus.eu/search/hierarchy"
COLLECTION = 1979152
SITE_URL = "https://app.transkribus.org/en/sites/inventaria"


def fetch_site_pages() -> dict[str, int]:
    """imgKey -> site docId for every published Inventaria page."""
    body = json.dumps(
        {
            "collections": [COLLECTION],
            "url": "inventaria",
            "hierarchyLevels": [f"h_{i}" for i in range(10)],
            "hierarchyPath": [],
            "includeDocs": True,
        }
    ).encode()
    req = urllib.request.Request(
        API, data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    keys: dict[str, int] = {}

    def walk(node):
        if isinstance(node, dict):
            if "imgKey" in node and "docId" in node:
                keys.setdefault(node["imgKey"], node["docId"])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(data)
    return keys


def match(site_keys: dict[str, int]) -> tuple[list[dict], list[int]]:
    """Pair register documents with site documents over shared image keys."""
    matched: dict[int, set[int]] = {}
    for path in sorted(PAGES_DIR.glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        for page in doc.get("pages", []):
            found = re.search(r"/iiif/2/([A-Z]+)/", page.get("iiif") or "")
            if found and found.group(1) in site_keys:
                matched.setdefault(int(path.stem), set()).add(site_keys[found.group(1)])
    documents, ambiguous = [], []
    for doc_id, site_ids in sorted(matched.items()):
        if len(site_ids) != 1:
            ambiguous.append(doc_id)
            continue
        site_id = site_ids.pop()
        documents.append(
            {
                "docId": doc_id,
                "siteDocId": site_id,
                "url": f"{SITE_URL}/doc/{site_id}/detail",
            }
        )
    return documents, ambiguous


def main() -> int:
    site_keys = fetch_site_pages()
    documents, ambiguous = match(site_keys)
    payload = {
        "provenance": {
            "source": "workflow",
            "generator": "scripts/harvest_inventaria_mapping.py",
            "endpoint": API,
            "method": "IIIF image keys shared between the page register and "
            "the published site identify the same document",
            "fetched": datetime.now(UTC).isoformat(timespec="seconds"),
        },
        "site": SITE_URL,
        "documents": documents,
    }
    OUT_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"OK {len(documents)} documents mapped -> {OUT_FILE}")
    if ambiguous:
        print(f"ambiguous, left out: {ambiguous}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
