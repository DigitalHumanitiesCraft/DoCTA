"""Build one baseline TEI P5 document per transcribed source.

This is the first cut of the TEI stage of the agentic edition pipeline. It turns
the Transkribus export into a diplomatic, line-faithful TEI file per document,
honest about the fact that the text is unrevised machine transcription.

Data flow (repo-local only, no network):
  docs/data/source_mapping.json      matched CSV entry <-> Transkribus doc
  docs/data/sources.json             archival metadata (shelfmark, title, dating)
  docs/data/transcriptions/*.json    Transkribus export: pages, IIIF, lines

Writes:
  docs/data/tei/<docId>.xml          one file per document with has_text

Design decisions:
  The TEI is written as a hand-built string template rather than through an XML
  library, because the output must be byte-stable and readable as a diff; every
  file is re-parsed before it is written, so well-formedness is still checked by
  a parser and not by the template.
  Generation is deterministic. The date in publicationStmt and revisionDesc comes
  from --date and never from the clock, so a rebuild without input changes leaves
  no diff.
  The page is the only structural unit the export gives, so the body is one <ab>
  per page and carries no paragraph or section structure; <ab> avoids claiming a
  <p> the source has not been read for. Transkribus text regions are flattened in
  this baseline (lines in reading order of the export); preserving them would mean
  one <ab> per region and is the upgrade path once region types are curated.
  Nothing is invented: an element whose data is absent is omitted rather than
  filled with a placeholder.

Usage:
  python build_tei.py                  # write docs/data/tei/
  python build_tei.py --out DIR        # write elsewhere
  python build_tei.py --date 2026-09-01
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

ROOT = Path(__file__).parent
REPO = ROOT.parent
DATA = REPO / "docs" / "data"
TEI_OUT = DATA / "tei"

GENERATION_DATE = "2026-08-27"

REPOSITORY = "Tiroler Landesarchiv"
PUBLISHER = "Digital Humanities Craft OG"
LICENCE_URL = "https://creativecommons.org/licenses/by/4.0/"
LICENCE_NAME = "Creative Commons Attribution 4.0 International (CC BY 4.0)"

# ISO 639-3 registers no code for Fruehneuhochdeutsch; gmh (Middle High German,
# 1050-1500) is the nearest registered historical German code and covers the
# dating of this corpus. The approximation is declared in langUsage rather than
# hidden in the attribute.
TEXT_LANG = "gmh"

# A line that is nothing but a folio mark is an editorial reference point of the
# Transkribus transcription, not text of the source, and becomes a milestone.
FOLIO_LINE = re.compile(r"^\[fol\.\s*([0-9]+[rv]?)\]$")

FULL_DATE = re.compile(r"^(\d{4})\.(\d{2})\.(\d{2})$")
YEAR = re.compile(r"^(\d{4})$")
YEAR_RANGE = re.compile(r"^(\d{4})-(\d{4})$")

# XML 1.0 permits only these characters; the export is a trust boundary and may
# carry control characters from the OCR stage.
VALID_XML = re.compile(
    "[^\t\n\r\x20-\ud7ff\ue000-\ufffd\U00010000-\U0010ffff]")


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _esc(text: str) -> str:
    """Escape for element content and strip characters XML cannot carry."""
    clean = VALID_XML.sub("", text)
    return clean.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _att(text: str) -> str:
    return _esc(text).replace('"', "&quot;")


def _origdate(dating: dict) -> str | None:
    """origDate for the archival dating, as precise as the raw value allows.

    A circa dating becomes notBefore/notAfter, an exact day when, a span
    from/to. The raw string stays as the element content, so nothing of the
    archival statement is lost to the normalisation.
    """
    raw = (dating.get("raw") or "").strip()
    if not raw:
        return None
    start, end = dating.get("start"), dating.get("end")
    if dating.get("circa"):
        attrs = ""
        if start:
            attrs += f' notBefore="{start:04d}"'
        if end:
            attrs += f' notAfter="{end:04d}"'
    elif m := FULL_DATE.match(raw):
        attrs = f' when="{m.group(1)}-{m.group(2)}-{m.group(3)}"'
    elif m := YEAR.match(raw):
        attrs = f' when="{m.group(1)}"'
    elif m := YEAR_RANGE.match(raw):
        attrs = f' from="{m.group(1)}" to="{m.group(2)}"'
    else:
        attrs = ""
    return f"<origDate{attrs}>{_esc(raw)}</origDate>"


def _ms_identifier(signatur: str, doc_id: int, indent: str) -> list[str]:
    collection, _, idno = signatur.partition(" - ")
    if not idno:
        collection, idno = "", signatur
    out = [f"{indent}<msIdentifier>",
           f"{indent}  <repository>{_esc(REPOSITORY)}</repository>"]
    if collection:
        out.append(f"{indent}  <collection>{_esc(collection)}</collection>")
    out.append(f"{indent}  <idno>{_esc(idno)}</idno>")
    out.append(f'{indent}  <altIdentifier type="transkribus">')
    out.append(f"{indent}    <idno>{doc_id}</idno>")
    out.append(f"{indent}  </altIdentifier>")
    out.append(f"{indent}</msIdentifier>")
    return out


def _header(doc: dict, date: str) -> list[str]:
    title = (doc.get("title") or "").strip()
    signatur = doc["shelfmark"]
    category = (doc.get("category") or "").strip()
    origdate = _origdate(doc.get("dating") or {})

    out = ["  <teiHeader>", "    <fileDesc>", "      <titleStmt>"]
    if title:
        out.append(f'        <title type="main">{_esc(title)}</title>')
    out.append(f'        <title type="shelfmark">{_esc(signatur)}</title>')
    out += ["      </titleStmt>",
            "      <publicationStmt>",
            f"        <publisher>{_esc(PUBLISHER)}</publisher>",
            f'        <date when="{_att(date)}">{_esc(date)}</date>',
            '        <availability status="free">',
            f'          <licence target="{LICENCE_URL}">{_esc(LICENCE_NAME)}</licence>',
            "          <p>The licence covers the encoded transcription. The"
            " facsimile images are held by the archive and are referenced by"
            " IIIF URL, not redistributed here.</p>",
            "        </availability>",
            "      </publicationStmt>",
            "      <sourceDesc>",
            "        <msDesc>"]
    out += _ms_identifier(signatur, doc["docId"], "          ")
    if origdate:
        out += ["          <history>",
                f"            <origin>{origdate}</origin>",
                "          </history>"]
    out += ["        </msDesc>", "      </sourceDesc>", "    </fileDesc>",
            "    <encodingDesc>",
            "      <projectDesc>",
            "        <p>DoCTA edits the inventories and account books of the"
            " Tyrolean territorial administration; this file is produced by the"
            " project's agentic edition pipeline from the Transkribus export.</p>",
            "      </projectDesc>",
            "      <editorialDecl>",
            "        <p>The text of this file is unrevised machine transcription."
            " It was produced by a vision-language model reading the Transkribus"
            " facsimiles and has not been reviewed by an editor, so every reading"
            " is provisional and the file is not a citable edition text."
            " Transcription is diplomatic: the wording and spelling of the source"
            " are kept, nothing is normalised, expanded or corrected, and"
            " lineation follows the source, one lb per written line.</p>",
            "      </editorialDecl>"]
    if category:
        out += ['      <classDecl>',
                '        <taxonomy xml:id="docta-category">',
                "          <desc>Archival category of the source, taken from the"
                " DoCTA source register.</desc>",
                "        </taxonomy>",
                "      </classDecl>"]
    out.append("    </encodingDesc>")

    out += ["    <profileDesc>",
            "      <langUsage>",
            f'        <language ident="{TEXT_LANG}">Early New High German,'
            " tagged with the Middle High German code as the nearest registered"
            " approximation.</language>",
            "      </langUsage>"]
    if category:
        out += ["      <textClass>",
                '        <keywords scheme="#docta-category">',
                f"          <term>{_esc(category)}</term>",
                "        </keywords>",
                "      </textClass>"]
    out += ["    </profileDesc>",
            "    <revisionDesc>",
            f'      <change when="{_att(date)}">Generated from the Transkribus'
            " export; unrevised.</change>",
            "    </revisionDesc>",
            "  </teiHeader>"]
    return out


def _facsimile(pages: list[dict], doc_id: int) -> list[str]:
    surfaces = [p for p in pages if p.get("iiif")]
    if not surfaces:
        return []
    out = ["  <facsimile>"]
    for page in surfaces:
        out += [f'    <surface xml:id="{_att(_surface_id(doc_id, page))}"'
                f' n="{page["pageNr"]}">',
                f'      <graphic url="{_att(page["iiif"])}"/>',
                "    </surface>"]
    out.append("  </facsimile>")
    return out


def _surface_id(doc_id: int, page: dict) -> str:
    return f"surface-{doc_id}-{page['pageNr']}"


def _page_body(page: dict, doc_id: int) -> list[str]:
    pb = f'<pb n="{page["pageNr"]}"'
    if page.get("iiif"):
        pb += f' facs="#{_att(_surface_id(doc_id, page))}"'
    out = ["      <ab>", f"        {pb}/>"]
    for text in _lines(page):
        if m := FOLIO_LINE.match(text):
            out.append(f'        <milestone unit="folio" n="{_att(m.group(1))}"/>')
        else:
            out.append(f"        <lb/>{_esc(text)}")
    out.append("      </ab>")
    return out


def _lines(page: dict) -> list[str]:
    """Line texts of a page in export order; regions are flattened."""
    return [(line.get("text") or "").strip()
            for region in page.get("regions") or []
            for line in region.get("lines") or []]


def document_xml(doc: dict, pages: list[dict], date: str) -> str:
    doc_id = doc["docId"]
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<TEI xmlns="http://www.tei-c.org/ns/1.0"'
           f' xml:id="docta-{doc_id}">']
    out += _header(doc, date)
    out += _facsimile(pages, doc_id)
    out += [f'  <text xml:lang="{TEXT_LANG}">', "    <body>",
            '      <div type="transcription">']
    for page in pages:
        out += ["  " + line for line in _page_body(page, doc_id)]
    out += ["      </div>", "    </body>", "  </text>", "</TEI>", ""]
    return "\n".join(out)


def _documents() -> list[dict]:
    """Documents with a Transkribus export, joined to their archival metadata."""
    mapping = _load(DATA / "source_mapping.json")["matched"]
    by_signatur = {s["signatur"]: s
                   for s in _load(DATA / "sources.json")}
    docs: list[dict] = []
    for entry in mapping:
        if not entry.get("has_text"):
            continue
        source = by_signatur.get(entry["csv_signatur"]) or {}
        docs.append({
            "docId": entry["transkribus_id"],
            "shelfmark": entry["csv_signatur"],
            "title": source.get("titel"),
            "category": source.get("kategorie"),
            "dating": source.get("datierung") or {},
        })
    docs.sort(key=lambda d: d["docId"])
    return docs


def build(out_dir: Path, date: str = GENERATION_DATE) -> dict[int, str]:
    """Build one TEI file per transcribed document. Deterministic and re-runnable.

    Every document is re-parsed before it is written; a malformed result is a
    contract violation of the generator and fails the whole run rather than
    leaving a broken file on disk.
    """
    result: dict[int, str] = {}
    for doc in _documents():
        doc_id = doc["docId"]
        export = DATA / "transcriptions" / f"{doc_id}.json"
        if not export.exists():
            print(f"SKIP {doc_id}: kein Export unter {export.name}",
                  file=sys.stderr)
            continue
        pages = sorted(_load(export)["pages"], key=lambda p: p["pageNr"])
        xml = document_xml(doc, pages, date)
        ElementTree.fromstring(xml)  # fail fast on a malformed template result
        result[doc_id] = xml
    for doc_id, xml in result.items():
        _write(out_dir / f"{doc_id}.xml", xml)
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=TEI_OUT,
                    help="target directory (default: docs/data/tei/)")
    ap.add_argument("--date", default=GENERATION_DATE,
                    help="generation date written into the header"
                         f" (default: {GENERATION_DATE})")
    args = ap.parse_args()

    built = build(args.out, args.date)
    print(f"OK TEI: {len(built)} Dokumente -> {args.out}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
