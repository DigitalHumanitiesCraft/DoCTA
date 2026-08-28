"""Build one baseline TEI P5 document per transcribed source.

This is the first cut of the TEI stage of the agentic edition pipeline. It turns
the Transkribus export into a diplomatic, line-faithful TEI file per document,
honest about the fact that the text is unrevised machine transcription.

Data flow (repo-local only, no network):
  docs/data/source_mapping.json      matched CSV entry <-> Transkribus doc
  docs/data/sources.json             archival metadata (shelfmark, title, dating)
  docs/data/transkribus_status.json  page-status distribution (DONE = corrected)
  docs/data/transcriptions/*.json    Transkribus export: pages, IIIF, lines
  docs/data/demo/thaur_entities.json prototype named entities of one document
  docs/data/entities/<docId>.json    named entities of a document, same schema
  pipeline/pages/<docId>.json        page register: verification and review runs

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
  The page and the text region are the structural units the export gives, so the
  body is one <ab> per region under a <pb> per page and carries no paragraph or
  section structure; <ab> avoids claiming a <p> the source has not been read for.
  A region keeps its export id in the xml:id of its <ab>, so a block of the TEI
  and a block of the layout analysis stay addressable in both directions.
  The text of a page comes from the review layer where one exists. A page that a
  reviewer marked gesichtet or abgenommen in the viewer and corrected there
  carries the lines of its newest review run instead of the raw export; the
  layout data of the export still carries zones and lb bindings, because a
  correction changes a reading and not the position of a line on the image.
  Every line of a page becomes a <zone> under the surface of that page, and the
  <lb> of the line points at it, so text and image region stay bound. Zones and
  lb come from the same iteration over the export, which keeps them in step.
  The entity layer exists for the one demo document that has a prototype
  extraction. It is encoded only where the anchor is deterministic, meaning the
  entity names its line and its surface form occurs there verbatim exactly once;
  everything else is reported as unencoded instead of being placed by guesswork.
  The layer carries its own responsibility statement and no certainty attribute,
  because a confidence value of the extracting agent is not evidence.
  Nothing is invented: an element whose data is absent is omitted rather than
  filled with a placeholder.
  Every file carries its work-step provenance in the header, following the ZBZ
  pattern: one respStmt per step that actually happened, a digest pinning the
  generating script version, and per-stream status entries in revisionDesc. A
  responsibility is never declared for a step that did not run.

Usage:
  python build_tei.py                  # write docs/data/tei/
  python build_tei.py --out DIR        # write elsewhere
  python build_tei.py --date 2026-09-01
  python build_tei.py --register DIR   # read the register elsewhere
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import build_register as br

ROOT = Path(__file__).parent
REPO = ROOT.parent
DATA = REPO / "docs" / "data"
TEI_OUT = DATA / "tei"
REGISTER = ROOT / "pages"

GENERATION_DATE = "2026-08-28"

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
# Corpus forms: "[fol.2r]" (dominant), "[fol. 2r]", bare "[1r]", and the
# endpaper marks "[us_vorne_r]" etc.; "[- - -]" stays ordinary text.
FOLIO_LINE = re.compile(r"^\[(?:fol\.\s*)?([0-9]+[rv]?)\]$")
COVER_LINE = re.compile(r"^\[(us_[a-z]+_[rv])\]$")

FULL_DATE = re.compile(r"^(\d{4})\.(\d{2})\.(\d{2})$")
YEAR = re.compile(r"^(\d{4})$")
YEAR_RANGE = re.compile(r"^(\d{4})-(\d{4})$")

# XML 1.0 permits only these characters; the export is a trust boundary and may
# carry control characters from the OCR stage.
VALID_XML = re.compile(
    "[^\t\n\r\x20-\ud7ff\ue000-\ufffd\U00010000-\U0010ffff]")


# Correction state of the transcription stream, derived from the DONE page count
# in Transkribus. The values are written verbatim into change/@status.
CORRECTED, PARTLY, MACHINE = (
    "human-corrected", "partly-corrected", "machine-unrevised")

# Review states of the transcription stream. They outrank the Transkribus states
# above, because a page reviewed in DoCTA has been read against the scan here.
REVIEWED, APPROVED = "partly-reviewed", "approved"

# Register verification states from which the review layer becomes the text of a
# page; the machine states of the register assert no reading of the scan.
REVIEWED_STATUS = ("gesichtet", "abgenommen")

# A responsibility is declared only for a step that actually ran; the
# verification statement therefore appears only in a file with a review layer.
RESP_TRANSKRIBUS = "resp-transkribus-layer"
RESP_GENERATION = "resp-tei-generation"
RESP_VERIFICATION = "resp-expert-verification"
RESP_ENTITY = "resp-entity-llm"

# Prototype named entities of a single document. The file names the docId it
# belongs to, so no other document can pick the layer up by accident.
ENTITY_FILE = DATA / "demo" / "thaur_entities.json"

# Per-document entity files of the running extraction, same schema as the
# prototype file; a document without one keeps no entity layer.
ENTITY_DIR = DATA / "entities"

# Entity types the encoding covers; a type outside this map stays unencoded
# rather than being forced into an element that does not fit it.
ENTITY_ELEMENTS = {
    "person": "persName", "place": "placeName", "object": "objectName"}


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


def script_digest() -> str:
    """First 12 hex of the sha256 over this script, pinning the code version.

    The digest travels in the header, so a file states which generator version
    produced it. Changing build_tei.py therefore changes every output file; that
    is the point, and it is stable for an unchanged script.
    """
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:12]


def _correction(done_pages: int | None, pages: int | None) -> str:
    if not pages or not done_pages:
        return MACHINE
    return CORRECTED if done_pages >= pages else PARTLY


def _resp_stmts(doc: dict, indent: str, entities: bool = False,
                reviewed: bool = False) -> list[str]:
    """One respStmt per work step that actually happened for this document."""
    state = doc["correction"]
    if state == CORRECTED:
        layer = ("Transcription corrected page by page and marked done in"
                 " Transkribus (human-corrected layer)")
        # The DONE marks were set by the editors of the Transkribus collection,
        # not by DoCTA; the neutral role avoids a false attribution.
        actor = "Editors of the Transkribus collection"
    elif state == PARTLY:
        layer = ("Transcription corrected page by page and marked done in"
                 f" Transkribus for {doc['done_pages']} of {doc['pages']} pages"
                 " (human-corrected layer); the remaining pages carry the"
                 " unrevised automated recognition layer")
        actor = "Editors of the Transkribus collection and Transkribus"
    else:
        layer = "Automated text recognition layer from Transkribus, unrevised"
        actor = "Transkribus"
    generation = ("Deterministic TEI generation from the Transkribus export,"
                  " without editorial judgment")
    steps = [(RESP_TRANSKRIBUS, layer, actor),
             (RESP_GENERATION, generation,
              f"pipeline/build_tei.py (sha256 {script_digest()})")]
    if reviewed:
        steps.append((RESP_VERIFICATION,
                      "Page-level scholarly review and correction in the DoCTA"
                      " viewer",
                      "DoCTA reviewer (initials in the revision log)"))
    if entities:
        steps.append((RESP_ENTITY,
                      "Named-entity extraction by an LLM agent in the prototype"
                      " phase, informally reviewed, not verified by a scholar",
                      "DoCTA prototype extraction"))
    out = []
    for resp_id, resp, name in steps:
        out += [f'{indent}<respStmt xml:id="{resp_id}">',
                f"{indent}  <resp>{_esc(resp)}</resp>",
                f"{indent}  <name>{_esc(name)}</name>",
                f"{indent}</respStmt>"]
    return out


# What the pages without a DoCTA review carry, per Transkribus state; appended
# to the partly-reviewed declaration so it never contradicts the stream status.
_REMAINDER = {
    MACHINE: ("The pages without a review carry unrevised machine"
              " transcription and every reading there is provisional."),
    PARTLY: ("The pages without a review carry the Transkribus layer,"
             " corrected for part of them and unrevised machine transcription"
             " for the rest."),
    CORRECTED: ("The pages without a review carry the transcription corrected"
                " and marked done in Transkribus."),
}


def _editorial_decl(state: str, indent: str, entities: bool = False,
                    review: dict | None = None) -> list[str]:
    """Stream-dependent editorial declaration; never asserts a step that did
    not run and never contradicts the transcription-summary status."""
    reviewed = bool(review and review["pages"])
    if reviewed and review["complete"]:
        first = ("Every page of this file has been read against the scan in"
                 " the DoCTA viewer and accepted as edition text; the"
                 " corrections made there are part of the text. The TEI"
                 " encoding is machine-generated.")
    elif reviewed:
        first = ("Part of the pages of this file has been read against the"
                 " scan in the DoCTA viewer and marked gesichtet or abgenommen"
                 " there; the revision log names those pages one by one, and"
                 " the corrections made there are part of the text of those"
                 f" pages. {_REMAINDER[state]} The file is not yet a citable"
                 " edition text.")
    elif state == MACHINE:
        first = ("The text of this file is unrevised machine transcription."
                 " It was produced by automated text recognition and has not"
                 " been reviewed, so every reading is provisional and the file"
                 " is not a citable edition text.")
    elif state == PARTLY:
        first = ("The transcription of this file is corrected in Transkribus"
                 " for part of its pages and unrevised machine transcription"
                 " for the rest; which pages are corrected is recorded in the"
                 " page register. The TEI encoding is machine-generated and"
                 " scholarly review within DoCTA is still pending, so the file"
                 " is not yet a citable edition text.")
    else:
        first = ("The transcription of this file was corrected page by page in"
                 " Transkribus and marked done there. The TEI encoding is"
                 " machine-generated and scholarly review within DoCTA is still"
                 " pending, so the file is not yet a citable edition text.")
    second = ("Transcription is diplomatic: the wording and spelling of the"
              " source are kept, nothing is normalised, expanded or corrected,"
              " and lineation follows the source, one lb per written line.")
    out = [f"{indent}<editorialDecl>",
           f"{indent}  <p>{_esc(first)} {second}</p>"]
    if entities:
        out.append(f"{indent}  <p>The named entities marked in this file are an"
                   " unverified extraction by an LLM agent from the prototype"
                   " phase; they have not been checked against the source by a"
                   " scholar and carry no claim of correctness.</p>")
    out.append(f"{indent}</editorialDecl>")
    return out


def _review(doc_id: int, register_dir: Path) -> dict:
    """The review layer of a document, read from the page register.

    Returns the reviewed pages in page order and, per page that carries a review
    run, the corrected line texts by line id. A page counts as reviewed on its
    register verification alone; the run is what supplies a changed reading, and
    a page reviewed without a correction simply keeps the export text.
    """
    path = register_dir / f"{doc_id}.json"
    if not path.exists():
        return {"pages": [], "texts": {}, "complete": False}
    register = _load(path)["pages"]
    pages, texts = [], {}
    for page in register:
        verification = page.get("verification") or {}
        if verification.get("status") not in REVIEWED_STATUS:
            continue
        pages.append({"pageNr": page["pageNr"],
                      "status": verification["status"],
                      "reviewer": verification.get("reviewer"),
                      "date": verification.get("date")})
        if latest := br.newest_review_run(page):
            texts[page["pageNr"]] = {line["id"]: line["text"]
                                     for line in latest["lines"]
                                     if line.get("id")}
    complete = bool(register) and len(pages) == len(register) and \
        all(p["status"] == "abgenommen" for p in pages)
    return {"pages": pages, "texts": texts, "complete": complete}


def _stream_status(doc: dict, review: dict) -> str:
    """State of the transcription stream, review layer first."""
    if review["complete"]:
        return APPROVED
    if review["pages"]:
        return REVIEWED
    return doc["correction"]


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


def _header(doc: dict, date: str, entities: bool = False,
            review: dict | None = None) -> list[str]:
    review = review or {"pages": [], "texts": {}, "complete": False}
    reviewed = bool(review["pages"])
    title = (doc.get("title") or "").strip()
    signatur = doc["shelfmark"]
    category = (doc.get("category") or "").strip()
    origdate = _origdate(doc.get("dating") or {})

    out = ["  <teiHeader>", "    <fileDesc>", "      <titleStmt>"]
    if title:
        out.append(f'        <title type="main">{_esc(title)}</title>')
    out.append(f'        <title type="shelfmark">{_esc(signatur)}</title>')
    out += _resp_stmts(doc, "        ", entities, reviewed)
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
            "      </projectDesc>"]
    out += _editorial_decl(doc["correction"], "      ", entities, review)
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
    stream = _stream_status(doc, review)
    out += ["    </profileDesc>",
            "    <revisionDesc>",
            f'      <change when="{_att(date)}" who="#{RESP_GENERATION}">Generated'
            " from the Transkribus export by the DoCTA pipeline.</change>"]
    for page in review["pages"]:
        when = f' when="{_att(page["date"])}"' if page.get("date") else ""
        initials = page.get("reviewer") or "unnamed"
        out.append(f'      <change{when} who="#{RESP_VERIFICATION}" n="review">Page'
                   f' {page["pageNr"]} reviewed in the DoCTA viewer by'
                   f" {_esc(initials)} (state): {page['status']}</change>")
    out += [f'      <change n="transcription-summary" status="{stream}">'
            f"Transcription stream (state): {stream}</change>",
            '      <change n="tei-summary" status="machine-generated">TEI stream'
            " (state): machine-generated</change>",
            "    </revisionDesc>",
            "  </teiHeader>"]
    return out


def _facsimile(pages: list[dict], doc_id: int,
               review_texts: dict | None = None) -> list[str]:
    review_texts = review_texts or {}
    surfaces = [p for p in pages if p.get("iiif")]
    if not surfaces:
        return []
    out = ["  <facsimile>"]
    for page in surfaces:
        out += [f'    <surface xml:id="{_att(_surface_id(doc_id, page))}"'
                f' n="{page["pageNr"]}">',
                f'      <graphic url="{_att(page["iiif"])}"/>']
        for line in _line_records(page):
            # A folio or cover line becomes a milestone without facs in the
            # body, so its zone would reference nothing; the effective text
            # decides, because a review can turn a line into or out of a mark.
            text = _line_text(line, review_texts.get(page["pageNr"]))
            if FOLIO_LINE.match(text) or COVER_LINE.match(text):
                continue
            if points := (line.get("coords") or "").strip():
                zone = _zone_id(doc_id, page["pageNr"], line["id"])
                out.append(f'      <zone xml:id="{_att(zone)}"'
                           f' points="{_att(points)}"/>')
        out.append("    </surface>")
    out.append("  </facsimile>")
    return out


def _surface_id(doc_id: int, page: dict) -> str:
    return f"surface-{doc_id}-{page['pageNr']}"


def _zone_id(doc_id: int, page_nr: int, line_id: str) -> str:
    return f"zone-{doc_id}-{page_nr}-{line_id}"


def _page_body(page: dict, doc_id: int, anchors: dict,
               review_texts: dict | None = None) -> list[str]:
    """One pb per page and one ab per text region of the export."""
    page_nr = page["pageNr"]
    pb = f'<pb n="{page_nr}"'
    has_surface = bool(page.get("iiif"))
    if has_surface:
        pb += f' facs="#{_att(_surface_id(doc_id, page))}"'
    out = [f"      {pb}/>"]
    for region in page.get("regions") or []:
        out.append(f'      <ab xml:id="{_att(_ab_id(doc_id, page_nr, region))}">')
        for line in region.get("lines") or []:
            text = _line_text(line, review_texts)
            if m := FOLIO_LINE.match(text):
                out.append(f'        <milestone unit="folio"'
                           f' n="{_att(m.group(1))}"/>')
            elif m := COVER_LINE.match(text):
                out.append(f'        <milestone unit="cover"'
                           f' n="{_att(m.group(1))}"/>')
            else:
                # The lb points at a zone only where that zone was actually
                # emitted, which needs both a surface for the page and
                # coordinates for the line; a dangling facs reference is worse
                # than none.
                lb = "<lb/>"
                if has_surface and (line.get("coords") or "").strip():
                    zone = _zone_id(doc_id, page_nr, line["id"])
                    lb = f'<lb facs="#{_att(zone)}"/>'
                content = _line_content(text, anchors.get(line["id"]) or [])
                out.append(f"        {lb}{content}")
        out.append("      </ab>")
    return out


def _ab_id(doc_id: int, page_nr: int, region: dict) -> str:
    return f"ab-{doc_id}-{page_nr}-{region['id']}"


def _line_records(page: dict) -> list[dict]:
    """Line records of a page in export order, across its regions.

    Single source of the page-to-line iteration, so zone, lb and entity anchor
    are derived from the same order and cannot drift apart.
    """
    return [line
            for region in page.get("regions") or []
            for line in region.get("lines") or []]


def _line_text(line: dict, review_texts: dict | None = None) -> str:
    """Effective text of a line: the reviewed reading where one exists."""
    if review_texts and line.get("id") in review_texts:
        return review_texts[line["id"]].strip()
    return (line.get("text") or "").strip()


def _lines(page: dict, review_texts: dict | None = None) -> list[str]:
    """Line texts of a page in export order, across its regions."""
    return [_line_text(line, review_texts) for line in _line_records(page)]


def _line_content(text: str, anchors: list[dict]) -> str:
    """Line text with the entity anchors of that line wrapped inline.

    Escaping is safe by construction: every substring of the raw line passes
    through _esc before it enters the output, the key through _att, and the
    element names come from ENTITY_ELEMENTS, so no raw character can escape
    into markup. Anchors are applied left to right and an anchor overlapping an
    already consumed span is dropped, which keeps the result deterministic.
    """
    if not anchors:
        return _esc(text)
    out, pos = [], 0
    for anchor in sorted(anchors, key=lambda a: a["start"]):
        if anchor["start"] < pos:
            continue
        element = anchor["element"]
        out += [_esc(text[pos:anchor["start"]]),
                f'<{element} resp="#{RESP_ENTITY}" key="{_att(anchor["key"])}">',
                _esc(text[anchor["start"]:anchor["end"]]),
                f"</{element}>"]
        pos = anchor["end"]
    out.append(_esc(text[pos:]))
    return "".join(out)


def _entity_data(doc_id: int) -> dict | None:
    """The entity extraction of this document, from the per-document file first.

    Both sources carry the same schema and name the docId they belong to, so no
    document can pick a layer up by accident. A document with neither file has
    no entity layer, which is the normal case.
    """
    path = ENTITY_DIR / f"{doc_id}.json"
    if not path.exists():
        path = ENTITY_FILE
        if not path.exists():
            return None
    data = _load(path)
    return data if data.get("docId") == doc_id else None


def _entity_anchors(doc_id: int, pages: list[dict],
                    review_texts: dict | None = None
                    ) -> tuple[dict[int, dict[str, list[dict]]],
                               list[tuple[str, str]]]:
    """Deterministic inline anchors for the prototype entity layer.

    Returns the anchors per page and line, plus the entities that were not
    encoded with the reason each one failed. An entity is encoded only when it
    names a line of this document and its surface form occurs in that line
    verbatim exactly once; a second occurrence makes the position ambiguous and
    guessing one would assert a reading that was never established.
    """
    data = _entity_data(doc_id)
    if data is None:
        return {}, []
    # Anchors are cut against the text the file will carry, so a corrected line
    # is matched on its reviewed reading and never on the superseded one.
    review_texts = review_texts or {}
    texts = {(page["pageNr"], line["id"]):
             _line_text(line, review_texts.get(page["pageNr"]))
             for page in pages for line in _line_records(page)}
    anchors: dict[int, dict[str, list[dict]]] = {}
    skipped: list[tuple[str, str]] = []
    for entity in data.get("entities") or []:
        line_id = entity.get("lineId")
        page_nr = entity.get("pageNr")
        element = ENTITY_ELEMENTS.get(entity.get("type"))
        surface = entity.get("text") or ""
        text = texts.get((page_nr, line_id))
        if not line_id:
            skipped.append((entity["id"], "no line reference"))
        elif element is None:
            skipped.append((entity["id"],
                            f"type not encoded ({entity.get('type')})"))
        elif text is None:
            skipped.append((entity["id"], "line reference not in the export"))
        elif not surface or text.count(surface) != 1:
            skipped.append((entity["id"],
                            "surface form not exactly once in the line"))
        else:
            start = text.index(surface)
            anchors.setdefault(page_nr, {}).setdefault(line_id, []).append(
                {"start": start, "end": start + len(surface),
                 "element": element,
                 "key": entity.get("normalized") or surface,
                 "entity_id": entity["id"]})
    # An anchor inside a span an earlier anchor already consumed cannot be
    # placed; it is dropped here, where it can be reported with its reason,
    # rather than silently at render time.
    for lines in anchors.values():
        for line_id, items in lines.items():
            items.sort(key=lambda a: (a["start"], a["end"]))
            kept: list[dict] = []
            consumed = 0
            for anchor in items:
                if anchor["start"] < consumed:
                    skipped.append((anchor["entity_id"],
                                    "overlaps an earlier entity in the line"))
                else:
                    kept.append(anchor)
                    consumed = anchor["end"]
            lines[line_id] = kept
    return anchors, skipped


def document_xml(doc: dict, pages: list[dict], date: str,
                 anchors: dict | None = None, review: dict | None = None) -> str:
    doc_id = doc["docId"]
    anchors = anchors or {}
    review = review or {"pages": [], "texts": {}, "complete": False}
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<TEI xmlns="http://www.tei-c.org/ns/1.0"'
           f' xml:id="docta-{doc_id}">']
    out += _header(doc, date, bool(anchors), review)
    out += _facsimile(pages, doc_id, review["texts"])
    out += [f'  <text xml:lang="{TEXT_LANG}">', "    <body>",
            '      <div type="transcription">']
    for page in pages:
        page_anchors = anchors.get(page["pageNr"]) or {}
        texts = review["texts"].get(page["pageNr"])
        out += ["  " + line
                for line in _page_body(page, doc_id, page_anchors, texts)]
    out += ["      </div>", "    </body>", "  </text>", "</TEI>", ""]
    return "\n".join(out)


def _documents() -> list[dict]:
    """Documents with a Transkribus export, joined to their archival metadata."""
    mapping = _load(DATA / "source_mapping.json")["matched"]
    by_signatur = {s["signatur"]: s
                   for s in _load(DATA / "sources.json")}
    # Same source as build_register.py: a DONE page is human-corrected in
    # Transkribus, everything else is the automated recognition layer.
    status_by_id = {d["id"]: d for d in _load(DATA / "transkribus_status.json")}
    docs: list[dict] = []
    for entry in mapping:
        if not entry.get("has_text"):
            continue
        source = by_signatur.get(entry["csv_signatur"]) or {}
        status = status_by_id.get(entry["transkribus_id"]) or {}
        done, pages = status.get("done_pages"), status.get("pages")
        docs.append({
            "docId": entry["transkribus_id"],
            "shelfmark": entry["csv_signatur"],
            "title": source.get("titel"),
            "category": source.get("kategorie"),
            "dating": source.get("datierung") or {},
            "done_pages": done,
            "pages": pages,
            "correction": _correction(done, pages),
        })
    docs.sort(key=lambda d: d["docId"])
    return docs


def build(out_dir: Path, date: str = GENERATION_DATE,
          register_dir: Path = REGISTER) -> dict[int, str]:
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
        review = _review(doc_id, register_dir)
        anchors, skipped = _entity_anchors(doc_id, pages, review["texts"])
        if skipped:
            print(f"ENTITIES {doc_id}: {len(skipped)} nicht kodiert", file=sys.stderr)
            for entity_id, reason in skipped:
                print(f"  {entity_id}: {reason}", file=sys.stderr)
        xml = document_xml(doc, pages, date, anchors, review)
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
    ap.add_argument("--register", type=Path, default=REGISTER,
                    help="register page directory (default: pipeline/pages/)")
    args = ap.parse_args()

    built = build(args.out, args.date, args.register)
    print(f"OK TEI: {len(built)} Dokumente -> {args.out}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
