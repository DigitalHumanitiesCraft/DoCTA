"""Fetch the PAGE-XML transcription of every Transkribus document with text.

Converts it to simplified JSON: lines with coordinates and text.
Output: docs/data/transcriptions/{doc_id}.json
"""

import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

TOKEN_URL = (
    "https://account.readcoop.eu/auth/realms/readcoop/protocol/openid-connect/token"
)
API_BASE = "https://transkribus.eu/TrpServer/rest"
COLLECTION_ID = "2197991"
from pathlib import Path

BASE = str(Path(__file__).resolve().parents[1])


def get_token():
    params = {
        "grant_type": "password",
        "client_id": "transkribus-api-client",
        "username": os.environ["TRANSKRIBUS_USER"],
        "password": os.environ["TRANSKRIBUS_PASS"],
    }
    data = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))["access_token"]


def api_get(token, path):
    url = f"{API_BASE}{path}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/json")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_xml(token, url):
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode("utf-8")


def parse_page_xml(xml):
    """Parse PAGE-XML into simplified structure."""
    regions = []
    for region_match in re.finditer(
        r'<TextRegion[^>]*id="([^"]*)"[^>]*(?:type="([^"]*)")?[^>]*>(.*?)</TextRegion>',
        xml,
        re.DOTALL,
    ):
        region_id = region_match.group(1)
        region_type = region_match.group(2) or ""
        region_body = region_match.group(3)

        coords_m = re.search(r'<Coords points="([^"]*)"', region_body)
        region_coords = coords_m.group(1) if coords_m else ""

        lines = []
        for line_match in re.finditer(
            r'<TextLine[^>]*id="([^"]*)"[^>]*>(.*?)</TextLine>', region_body, re.DOTALL
        ):
            line_id = line_match.group(1)
            line_body = line_match.group(2)

            lc = re.search(r'<Coords points="([^"]*)"', line_body)
            line_coords = lc.group(1) if lc else ""

            bl = re.search(r'<Baseline points="([^"]*)"', line_body)
            baseline = bl.group(1) if bl else ""

            text_m = re.search(r"<Unicode>(.*?)</Unicode>", line_body, re.DOTALL)
            text = text_m.group(1).strip() if text_m else ""

            if text:  # Only include lines with text
                lines.append(
                    {
                        "id": line_id,
                        "text": text,
                        "coords": line_coords,
                        "baseline": baseline,
                    }
                )

        if lines:
            regions.append(
                {
                    "id": region_id,
                    "type": region_type,
                    "coords": region_coords,
                    "lines": lines,
                }
            )

    return regions


def main():
    token = get_token()
    print("Auth OK\n")

    with open(f"{BASE}/docs/data/transkribus_status.json", encoding="utf-8") as f:
        all_docs = json.load(f)

    with open(f"{BASE}/docs/data/source_mapping.json", encoding="utf-8") as f:
        mapping = json.load(f)

    mapping_by_id = {m["transkribus_id"]: m for m in mapping["matched"]}

    docs_with_text = [d for d in all_docs if d.get("has_text")]
    print(f"Processing {len(docs_with_text)} documents with transcription text...\n")

    os.makedirs(f"{BASE}/docs/data/transcriptions", exist_ok=True)

    total_pages = 0
    total_lines = 0
    total_words = 0
    auth_counter = 0

    for i, doc in enumerate(docs_with_text):
        doc_id = doc["id"]
        title = doc["title"]
        print(
            f"  [{i + 1}/{len(docs_with_text)}] {title} (ID {doc_id})...",
            end=" ",
            flush=True,
        )

        # The access token expires after 300s, so re-authenticate periodically.
        auth_counter += 1
        if auth_counter > 40:
            token = get_token()
            auth_counter = 0

        try:
            fulldoc = api_get(token, f"/collections/{COLLECTION_ID}/{doc_id}/fulldoc")
            pages = fulldoc.get("pageList", {}).get("pages", [])

            doc_pages = []
            doc_lines = 0
            doc_words = 0

            for p in pages:
                page_nr = p.get("pageNr", 0)
                key = p.get("key", "")
                img_filename = p.get("imgFileName", "")
                ts = p.get("tsList", {}).get("transcripts", [])

                if not ts:
                    continue

                t = ts[0]
                xml_key = t.get("key", "")

                if not xml_key or (t.get("nrOfTranscribedLines", 0) or 0) == 0:
                    # No text on this page; the entry stays for the image reference.
                    doc_pages.append(
                        {
                            "pageNr": page_nr,
                            "imgKey": key,
                            "imgFileName": img_filename,
                            "iiif": f"https://files.transkribus.eu/iiif/2/{key}/full/max/0/default.jpg",
                            "regions": [],
                        }
                    )
                    continue

                xml_url = f"https://files.transkribus.eu/Get?id={xml_key}"
                xml = fetch_xml(token, xml_url)
                regions = parse_page_xml(xml)

                page_lines = sum(len(r["lines"]) for r in regions)
                page_words = sum(
                    len(line["text"].split()) for r in regions for line in r["lines"]
                )
                doc_lines += page_lines
                doc_words += page_words

                doc_pages.append(
                    {
                        "pageNr": page_nr,
                        "imgKey": key,
                        "imgFileName": img_filename,
                        "iiif": f"https://files.transkribus.eu/iiif/2/{key}/full/max/0/default.jpg",
                        "regions": regions,
                    }
                )

                time.sleep(0.1)  # rate limit

            csv_meta = mapping_by_id.get(doc_id, {})
            output = {
                "docId": doc_id,
                "title": title,
                "csvSignatur": csv_meta.get("csv_signatur", ""),
                "csvTitel": csv_meta.get("csv_titel", ""),
                "csvKategorie": csv_meta.get("csv_kategorie", ""),
                "totalPages": len(doc_pages),
                "totalLines": doc_lines,
                "totalWords": doc_words,
                "pages": doc_pages,
            }

            with open(
                f"{BASE}/docs/data/transcriptions/{doc_id}.json", "w", encoding="utf-8"
            ) as f:
                json.dump(output, f, ensure_ascii=False, indent=2)

            total_pages += len(doc_pages)
            total_lines += doc_lines
            total_words += doc_words

            print(f"{len(doc_pages)}p, {doc_lines}L, {doc_words}W")

        except Exception as e:
            print(f"ERROR: {e}")

    print("\n=== DONE ===")
    print(f"Documents: {len(docs_with_text)}")
    print(f"Pages: {total_pages}")
    print(f"Lines: {total_lines}")
    print(f"Words: {total_words}")
    print("Output: docs/data/transcriptions/*.json")


if __name__ == "__main__":
    main()
