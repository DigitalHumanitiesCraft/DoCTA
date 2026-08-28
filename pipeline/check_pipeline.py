"""Healthcheck over the whole pipeline: run it before every commit.

One run, one findings list, exit 0 only when nothing failed. The checks are the contracts
the pipeline scripts assume about each other and that no single script can verify on its
own, so they live here rather than in the generators: the register against the export, the
document sets against each other, the JSON side files against their contracts, the
provenance rules against the data, the cross-references against their targets, the
evaluation metrics against their value ranges, the TEI against both schemas, and the
generators against themselves through a rebuild.

A finding is FAIL or INFO. INFO is a fact worth seeing that is not a defect of the
pipeline, such as a page whose reference transcription is degenerate; only FAIL decides the
exit code.

Usage:
  python check_pipeline.py            # every check
  python check_pipeline.py --skip idempotence   # leave out the slow rebuild
  python check_pipeline.py --list     # the check ids
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import re
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import apply_review as ar
import build_graph as bg
import build_register as br
import build_tei as bt
import validate_tei as vt
from io_paths import DATA, PIPELINE_DIR, REPO_ROOT, fenced_block, load_json, write_json

TEI_DIR = DATA / "tei"
ENTITY_DIR = DATA / "entities"
GRAPH = DATA / "graph.jsonld"
TRANSCRIPTIONS = DATA / "transcriptions"
REGISTER = PIPELINE_DIR / "pages"
DOCUMENTS = PIPELINE_DIR / "documents.json"
REVIEWS = PIPELINE_DIR / "reviews"
PROMPTS = PIPELINE_DIR / "prompts"
SUMMARY = DATA / "pipeline" / "register_summary.json"
SITE_TRANSCRIPTIONS = DATA / "pipeline" / "transcriptions"
EVALUATION = REPO_ROOT / "evaluation"

TEI_NS = "{http://www.tei-c.org/ns/1.0}"
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"

RUN_SOURCES = ("transkribus", "vlm", "human")

# Documents that appear in one set and not in another for a reason already settled in the
# data, so their absence is not a coverage gap:
#   12514730            Raitbuch 2, paired in build_register.py itself because the
#                       CSV-to-Transkribus matcher covers the inventories only
KNOWN_ORPHANS = (br.RAITBUCH2_DOC,)

# Evaluation run records are numerous and uniform; a sample proves the shape.
RUN_SAMPLE = 20
RUN_KEYS = (
    "page",
    "iteration",
    "repeat",
    "model",
    "prompt_hash",
    "timestamp",
    "lines",
    "parsed",
)

# Line-count spread between the repeats of one page above which a third run is worth
# having; a report, not a defect.
REPEAT_DIVERGENCE = 5

FAIL, INFO = "FAIL", "INFO"


@dataclass(frozen=True)
class Finding:
    check: str
    severity: str
    message: str

    def __str__(self) -> str:
        return f"{self.severity} {self.check}: {self.message}"


def _fail(check: str, message: str) -> Finding:
    return Finding(check, FAIL, message)


def _info(check: str, message: str) -> Finding:
    return Finding(check, INFO, message)


def _register_files() -> list[Path]:
    return sorted(REGISTER.glob("*.json"))


# ================================== contract =================================


def check_contract() -> list[Finding]:
    """The register against the export and against its own vocabularies."""
    out: list[Finding] = []
    seen_runs: dict[str, str] = {}
    for path in _register_files():
        payload = load_json(path)
        doc_id = payload["docId"]
        page_nrs = [p["pageNr"] for p in payload["pages"]]
        for nr, count in _counts(page_nrs).items():
            if count > 1:
                out.append(
                    _fail(
                        "contract.page-duplicate",
                        f"document {doc_id} page {nr} appears {count} times"
                        " in the register",
                    )
                )
        export = TRANSCRIPTIONS / f"{doc_id}.json"
        if export.exists():
            exported = {p["pageNr"] for p in load_json(export)["pages"]}
            missing = sorted(exported - set(page_nrs))
            if missing:
                out.append(
                    _fail(
                        "contract.page-missing",
                        f"document {doc_id} export pages not in the register:"
                        f" {missing}",
                    )
                )
        out += _check_pages(doc_id, payload["pages"], seen_runs)
    return out


def _counts(values: list[Any]) -> dict[Any, int]:
    counts: dict[Any, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


def _check_pages(
    doc_id: int, pages: list[dict], seen_runs: dict[str, str]
) -> list[Finding]:
    out: list[Finding] = []
    for page in pages:
        where = f"document {doc_id} page {page['pageNr']}"
        if page["content_class"] not in br.CONTENT_CLASSES:
            out.append(
                _fail(
                    "contract.content-class",
                    f"{where}: content_class {page['content_class']!r}",
                )
            )
        status = (page.get("verification") or {}).get("status")
        if status not in br.VERIFICATION_STATUS:
            out.append(
                _fail(
                    "contract.verification-status",
                    f"{where}: verification status {status!r}",
                )
            )
        ids_here: set[str] = set()
        for run in page.get("runs") or []:
            run_id = run.get("id")
            if run.get("source") not in RUN_SOURCES:
                out.append(
                    _fail(
                        "contract.run-source",
                        f"{where}, run {run_id}: source {run.get('source')!r}",
                    )
                )
            if run_id in ids_here:
                out.append(
                    _fail(
                        "contract.run-duplicate",
                        f"{where}: run id {run_id!r} twice on one page",
                    )
                )
            ids_here.add(run_id)
            # "transkribus" is the export run of every page and is unique per page;
            # every other run id names one evaluation or review record corpus-wide.
            if run_id != "transkribus":
                if run_id in seen_runs:
                    out.append(
                        _fail(
                            "contract.run-duplicate",
                            f"run id {run_id!r} in {where} and in {seen_runs[run_id]}",
                        )
                    )
                seen_runs[run_id] = where
            for line in run.get("lines") or []:
                if set(line) != {"id", "text"}:
                    out.append(
                        _fail(
                            "contract.run-lines",
                            f"{where}, run {run_id}: line keys {sorted(line)}",
                        )
                    )
                    break
    return out


# ================================== coverage =================================


def check_coverage() -> list[Finding]:
    """The three document sets against each other, orphans reported in each direction."""
    sources = {
        doc["doc_id"]
        for entry in load_json(DATA / "sources.json")
        for doc in entry.get("transkribus_docs") or ()
    }
    mapping = {
        entry["transkribus_id"]
        for entry in load_json(DATA / "source_mapping.json")["matched"]
    }
    register = {doc["docId"] for doc in load_json(DOCUMENTS)}

    out: list[Finding] = []
    pairs = (
        ("sources", sources, "mapping", mapping),
        ("mapping", mapping, "sources", sources),
        ("mapping", mapping, "register", register),
        ("register", register, "mapping", mapping),
    )
    for left_name, left, right_name, right in pairs:
        for doc_id in sorted(left - right):
            severity = _info if doc_id in KNOWN_ORPHANS else _fail
            out.append(
                severity(
                    "coverage.orphan",
                    f"document {doc_id} is in {left_name} and not in {right_name}",
                )
            )
    return out


# ================================ json contracts =============================


def check_json() -> list[Finding]:
    """Entity files, review exports and evaluation runs against their contracts."""
    return _check_entities() + _check_reviews() + _check_runs()


def _check_entities() -> list[Finding]:
    out: list[Finding] = []
    for path in sorted(ENTITY_DIR.glob("*.json")):
        data = load_json(path)
        doc_id = data.get("docId")
        prov = data.get("provenance") or {}
        for field in ("source", "model", "prompt", "prompt_hash", "date"):
            if not prov.get(field):
                out.append(
                    _fail(
                        "json.entity-provenance",
                        f"{path.name}: provenance field {field} missing",
                    )
                )
        lines = _transcription_lines(doc_id)
        if lines is None:
            out.append(
                _fail(
                    "json.entity-doc",
                    f"{path.name}: no transcription for document {doc_id}",
                )
            )
            continue
        for entity in data.get("entities") or []:
            missing = [
                f
                for f in ("id", "text", "normalized", "type", "pageNr", "lineId")
                if entity.get(f) in (None, "")
            ]
            if missing:
                out.append(
                    _fail(
                        "json.entity-fields",
                        f"{path.name}, entity {entity.get('id')}: fields"
                        f" {missing} missing",
                    )
                )
                continue
            key = br.line_key(entity["pageNr"], entity["lineId"])
            line = lines.get(key)
            if line is None:
                out.append(
                    _fail(
                        "json.entity-anchor",
                        f"{path.name}, entity {entity['id']}: line {key} is"
                        " not in the transcription",
                    )
                )
            elif entity["text"] not in line:
                out.append(
                    _fail(
                        "json.entity-verbatim",
                        f"{path.name}, entity {entity['id']}:"
                        f" {entity['text']!r} not verbatim in line {key}",
                    )
                )
    return out


def _transcription_lines(doc_id: Any) -> dict[str, str] | None:
    """Page-qualified line index of one document, the key entity anchors use.

    Whichever layer carries the text, the export or the DoCTA edition runs; the
    same function answers that for the extraction, so the check anchors on the
    text the extraction actually read.
    """
    doc = br.transcription_of(doc_id, REGISTER)
    if doc is None:
        return None
    return {
        br.line_key(page["pageNr"], line["id"]): line["text"]
        for page in doc["pages"]
        for line in br.iter_lines(page)
    }


def _check_reviews() -> list[Finding]:
    if not REVIEWS.is_dir():
        return []
    out: list[Finding] = []
    for path in sorted(REVIEWS.glob("*.json")):
        try:
            data = load_json(path)
        except json.JSONDecodeError as exc:
            out.append(_fail("json.review-parse", f"{path.name}: {exc}"))
            continue
        try:
            ar.validate(data, path.name)
        except ar.ReviewError as exc:
            out.append(_fail("json.review-contract", str(exc)))
    return out


def _evaluation_runs() -> list[Path]:
    return sorted(
        p
        for cohort in ("benchmark", "pilot", "pilot2", br.EDITION)
        for p in (EVALUATION / cohort / "runs").glob("*.json")
    )


def _check_runs() -> list[Finding]:
    files = _evaluation_runs()
    if not files:
        return []
    # deterministic spread over the cohorts rather than the first n of one of them
    step = max(1, len(files) // RUN_SAMPLE)
    out: list[Finding] = []
    for path in files[::step][:RUN_SAMPLE]:
        try:
            record = load_json(path)
        except json.JSONDecodeError as exc:
            out.append(_fail("json.run-parse", f"{path.name}: {exc}"))
            continue
        missing = [k for k in RUN_KEYS if k not in record]
        if missing:
            out.append(_fail("json.run-shape", f"{path.name}: keys {missing} missing"))
    return out


# ============================ provenance regression ==========================


def check_provenance() -> list[Finding]:
    """No confidence value anywhere and no certainty attribute in the TEI.

    A confidence the extracting agent reports is a self-assessment and not evidence about
    the source, so it must not travel into the edition data in any form.
    """
    out: list[Finding] = []
    for folder in (ENTITY_DIR, TEI_DIR):
        for path in sorted(folder.glob("*")):
            if path.is_file() and "confidence" in path.read_text(encoding="utf-8"):
                out.append(
                    _fail(
                        "provenance.confidence",
                        f"{path.name}: carries the string 'confidence'",
                    )
                )
    from lxml import etree

    for path in sorted(TEI_DIR.glob("*.xml")):
        for element in etree.parse(str(path)).getroot().iter():
            bare = {name.rsplit("}", 1)[-1] for name in element.attrib}
            if "cert" in bare:
                out.append(
                    _fail(
                        "provenance.cert",
                        f"{path.name}: {etree.QName(element).localname} carries @cert",
                    )
                )
    for path in _register_files():
        payload = load_json(path)
        for page in payload["pages"]:
            for run in page.get("runs") or []:
                if not run.get("source"):
                    out.append(
                        _fail(
                            "provenance.run-source",
                            f"document {payload['docId']} page"
                            f" {page['pageNr']}: run {run.get('id')!r}"
                            " carries no source",
                        )
                    )
    return out


# ================================= referential ===============================


def check_referential() -> list[Finding]:
    """Every pointer resolves: TEI @facs and @ref, thumbnails, prompt hashes."""
    return (
        _check_facs()
        + _check_entity_refs()
        + _check_thumbs()
        + _check_tei_flag()
        + _check_prompt_hashes()
    )


def _check_tei_flag() -> list[Finding]:
    """has_tei of the projection against the TEI directory, in both directions.

    The projection derives the flag from the register, build_tei.py iterates the
    source mapping; a document paired outside that mapping would carry the flag
    with no file behind it, and the site would offer a TEI view that 404s.
    """
    if not SUMMARY.exists():
        return [_fail("referential.projection", f"{SUMMARY.name} is missing")]
    out: list[Finding] = []
    for entry in load_json(SUMMARY)["documents"]:
        exists = (TEI_DIR / f"{entry['docId']}.xml").exists()
        if entry["has_tei"] != exists:
            out.append(
                _fail(
                    "referential.has-tei",
                    f"document {entry['docId']}: has_tei is {entry['has_tei']}"
                    f" and the TEI file {'exists' if exists else 'is missing'}",
                )
            )
    return out


def _check_facs() -> list[Finding]:
    from lxml import etree

    out: list[Finding] = []
    for path in sorted(TEI_DIR.glob("*.xml")):
        root = etree.parse(str(path)).getroot()
        ids = {el.get(XML_ID) for el in root.iter() if el.get(XML_ID)}
        for element in root.iter():
            facs = element.get("facs")
            if facs and facs.lstrip("#") not in ids:
                out.append(
                    _fail(
                        "referential.facs",
                        f"{path.name}: {etree.QName(element).localname}"
                        f" @facs {facs} resolves to nothing",
                    )
                )
    return out


def _graph_entity_ids() -> set[str] | None:
    """Entity node ids of the JSON-LD graph, without the namespace prefix."""
    if not GRAPH.exists():
        return None
    classes = set(bg.TYPE_CLASS.values())
    return {
        node["@id"].split(":", 1)[-1]
        for node in load_json(GRAPH)["@graph"]
        if node.get("@type") in classes
    }


def _check_entity_refs() -> list[Finding]:
    """The entity register against the documents that point into it.

    A dangling @ref is a defect. An entry no document points at is not: an
    entity whose anchor could not be placed deterministically stays unencoded in
    the text and keeps its register entry, which is where the extraction remains
    readable. The register and the JSON-LD graph must name the same entities,
    because both take their ids from entity_index.py.
    """
    from lxml import etree

    register = TEI_DIR / bt.REGISTER_FILE
    if not register.exists():
        return [_fail("referential.register", f"{bt.REGISTER_FILE} is missing")]
    root = etree.parse(str(register)).getroot()
    # entries only; the responsibility ids and the file id of the register are
    # not entities and are no target of an entity @ref
    ids = {
        el.get(XML_ID)
        for tag in ("person", "place", "item")
        for el in root.iter(f"{TEI_NS}{tag}")
        if el.get(XML_ID)
    }

    out: list[Finding] = []
    used: set[str] = set()
    for path in sorted(TEI_DIR.glob("*.xml")):
        if path.name == bt.REGISTER_FILE:
            continue
        for element in etree.parse(str(path)).getroot().iter():
            # A marked entity is what points into the register, and the entity
            # responsibility is what identifies one; the header carries @ref of
            # its own, on the name of an attributed project, which addresses
            # that project and not a register entry.
            if element.get("resp") != f"#{bt.RESP_ENTITY}":
                continue
            ref = element.get("ref")
            if not ref:
                continue
            target = ref.split("#", 1)[-1]
            used.add(target)
            if target not in ids:
                out.append(
                    _fail(
                        "referential.entity-ref",
                        f"{path.name}: @ref {ref} resolves to nothing in"
                        f" {bt.REGISTER_FILE}",
                    )
                )
    graph_ids = _graph_entity_ids()
    if graph_ids is None:
        out.append(_fail("referential.entity-graph", f"{GRAPH.name} is missing"))
    else:
        for entity_id in sorted(ids - graph_ids):
            out.append(
                _fail(
                    "referential.entity-graph",
                    f"{entity_id} is in {bt.REGISTER_FILE} and not in {GRAPH.name}",
                )
            )
        for entity_id in sorted(graph_ids - ids):
            out.append(
                _fail(
                    "referential.entity-graph",
                    f"{entity_id} is in {GRAPH.name} and not in {bt.REGISTER_FILE}",
                )
            )
    if unused := sorted(ids - used):
        out.append(
            _info(
                "referential.entity-unused",
                f"{len(unused)} register entries no document points at, their"
                f" anchors were not placeable, first: {unused[:3]}",
            )
        )
    return out


def _check_thumbs() -> list[Finding]:
    if not SUMMARY.exists():
        return [_fail("referential.projection", f"{SUMMARY.name} is missing")]
    out: list[Finding] = []
    for entry in load_json(SUMMARY)["documents"]:
        doc_id = entry["docId"]
        if entry["thumb"] is None and entry["thumb_page"] is None:
            continue
        path = REGISTER / f"{doc_id}.json"
        if not path.exists():
            out.append(
                _fail(
                    "referential.thumb",
                    f"document {doc_id}: no register file for the thumbnail",
                )
            )
            continue
        page = next(
            (p for p in load_json(path)["pages"] if p["pageNr"] == entry["thumb_page"]),
            None,
        )
        if page is None:
            out.append(
                _fail(
                    "referential.thumb",
                    f"document {doc_id}: thumb_page {entry['thumb_page']}"
                    " is not a page of the register",
                )
            )
        elif page["iiif"] != entry["thumb"]:
            out.append(
                _fail(
                    "referential.thumb",
                    f"document {doc_id} page {entry['thumb_page']}: thumb URL"
                    " differs from the register",
                )
            )
    return out


def _prompt_hash(prompt_id: str) -> str | None:
    """sha256-12 of the frozen prompt, which is the first fenced block of its document.

    None where the prompt has no frozen file at all, which covers a document
    without a fenced block as well; the finding below names both cases.
    """
    path = PROMPTS / f"{prompt_id}.md"
    if not path.exists():
        return None
    try:
        block = fenced_block(path)
    except ValueError:
        return None
    return hashlib.sha256(block.encode()).hexdigest()[:12]


def _check_prompt_hashes() -> list[Finding]:
    out: list[Finding] = []
    for path in sorted(ENTITY_DIR.glob("*.json")):
        prov = load_json(path).get("provenance") or {}
        prompt_id = prov.get("prompt")
        expected = _prompt_hash(prompt_id) if prompt_id else None
        if expected is None:
            out.append(
                _fail(
                    "referential.prompt",
                    f"{path.name}: prompt {prompt_id!r} has no frozen file",
                )
            )
        elif expected != prov.get("prompt_hash"):
            out.append(
                _fail(
                    "referential.prompt-hash",
                    f"{path.name}: prompt_hash {prov.get('prompt_hash')!r}"
                    f" does not match {prompt_id} ({expected})",
                )
            )
    return out


# =================================== metrics =================================


def check_metrics() -> list[Finding]:
    """Value ranges of the evaluation summaries, plus two reportable states."""
    out: list[Finding] = []
    for cohort, name in (
        ("pilot", "pilot_summary.json"),
        ("pilot2", "pilot2_summary.json"),
    ):
        path = EVALUATION / cohort / name
        if not path.exists():
            out.append(_fail("metrics.summary", f"{name} is missing"))
            continue
        for page_id, page in load_json(path)["pages"].items():
            out += _check_metric_page(cohort, page_id, page)
    return out


def _check_metric_page(cohort: str, page_id: str, page: dict) -> list[Finding]:
    out: list[Finding] = []
    for field in ("consistency_words", "consistency_numbers"):
        value = page.get(field)
        if value is not None and not 0.0 <= value <= 1.0:
            out.append(
                _fail("metrics.consistency", f"{cohort} {page_id}: {field} is {value}")
            )
    for value in page.get("cer_fair_vs_working") or []:
        if value > 1:
            # a CER above one means the reference is shorter than the edit distance,
            # which says something about the reference and not about the run
            out.append(
                _info(
                    "metrics.degenerate-reference",
                    f"{cohort} {page_id}: cer_fair_vs_working {value}",
                )
            )
            break
    lines = page.get("lines") or []
    if len(lines) > 1 and max(lines) - min(lines) > REPEAT_DIVERGENCE:
        out.append(
            _info(
                "metrics.repeat-divergence",
                f"{cohort} {page_id}: repeats report {lines} lines,"
                " a third run would decide",
            )
        )
    return out


# ==================================== schema =================================


def check_schema() -> list[Finding]:
    """Both validation stages of validate_tei.py, reported as one finding on failure."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = vt.main(["--tei-dir", str(TEI_DIR)])
    if code == 0:
        return []
    report = "; ".join(line for line in buffer.getvalue().splitlines() if line.strip())
    return [_fail("schema.validate", f"validate_tei.py exit {code}: {report}")]


# ================================= idempotence ===============================


def _tei_date() -> str:
    """Generation date of the committed TEI, so the rebuild compares against
    the date the files actually carry instead of the script constant."""
    for path in sorted(TEI_DIR.glob("*.xml")):
        m = re.search(
            r'<date when="(\d{4}-\d{2}-\d{2})">', path.read_text(encoding="utf-8")
        )
        if m:
            return m.group(1)
    return bt.GENERATION_DATE


def check_idempotence() -> list[Finding]:
    """A rebuild of register, TEI and graph must reproduce the working tree byte
    for byte, and the working tree must hold nothing the rebuild does not produce."""
    out: list[Finding] = []
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        with contextlib.redirect_stderr(io.StringIO()):
            # The ingested review state is the one part of the register the
            # builder cannot derive from its inputs, so the rebuild into the
            # empty temp directory is pointed at the working tree for it;
            # without that it would reproduce a register nobody has reviewed.
            docs, pages_by_doc = br.build(tmp, carry_from=PIPELINE_DIR)
            br.project(docs, pages_by_doc, tmp / "register_summary.json")
            bt.build(tmp / "tei", _tei_date())
            write_json(tmp / GRAPH.name, bg.build())
        out += _compare(DOCUMENTS, tmp / "documents.json")
        out += _compare(SUMMARY, tmp / "register_summary.json")
        out += _compare(GRAPH, tmp / GRAPH.name)
        for path in sorted((tmp / "pages").glob("*.json")):
            out += _compare(REGISTER / path.name, path)
        # The site transcriptions of the documents DoCTA transcribed itself are
        # part of the projection and are compared in both directions like the
        # TEI, so a stale one is found as well as a drifted one.
        rebuilt_site = {p.name for p in (tmp / "transcriptions").glob("*.json")}
        for name in sorted(rebuilt_site):
            out += _compare(SITE_TRANSCRIPTIONS / name, tmp / "transcriptions" / name)
        for name in sorted(
            {p.name for p in SITE_TRANSCRIPTIONS.glob("*.json")} - rebuilt_site
        ):
            out.append(
                _fail(
                    "idempotence.orphan",
                    f"pipeline/transcriptions/{name}: the working tree has it,"
                    " the rebuild does not produce it",
                )
            )
        # The TEI side is compared over the glob rather than over the returned
        # document ids, so register.xml is covered like any other file and an
        # orphan is found in both directions.
        rebuilt_tei = {p.name for p in (tmp / "tei").glob("*.xml")}
        current_tei = {p.name for p in TEI_DIR.glob("*.xml")}
        for name in sorted(rebuilt_tei):
            out += _compare(TEI_DIR / name, tmp / "tei" / name)
        rebuilt_pages = {p.name for p in (tmp / "pages").glob("*.json")}
        for name in sorted({p.name for p in REGISTER.glob("*.json")} - rebuilt_pages):
            out.append(
                _fail(
                    "idempotence.orphan",
                    f"pages/{name}: the working tree has it, the"
                    " rebuild does not produce it",
                )
            )
        for name in sorted(current_tei - rebuilt_tei):
            out.append(
                _fail(
                    "idempotence.orphan",
                    f"tei/{name}: the working tree has it, the"
                    " rebuild does not produce it",
                )
            )
    return out


def _compare(current: Path, rebuilt: Path) -> list[Finding]:
    if not current.exists():
        return [
            _fail(
                "idempotence.missing",
                f"{current.name}: the rebuild writes it, the working tree has it not",
            )
        ]
    if current.read_bytes() == rebuilt.read_bytes():
        return []
    return [
        _fail(
            "idempotence.drift",
            f"{current.name}: the rebuild does not reproduce the working tree",
        )
    ]


# ==================================== runner =================================

CHECKS: tuple[tuple[str, Callable[[], list[Finding]]], ...] = (
    ("contract", check_contract),
    ("coverage", check_coverage),
    ("json", check_json),
    ("provenance", check_provenance),
    ("referential", check_referential),
    ("metrics", check_metrics),
    ("schema", check_schema),
    ("idempotence", check_idempotence),
)


def run(skip: set[str] | None = None) -> list[Finding]:
    """Every check that was not skipped, in order. Returns the findings."""
    skip = skip or set()
    findings: list[Finding] = []
    for name, check in CHECKS:
        if name in skip:
            print(f"SKIP {name}")
            continue
        try:
            result = check()
        except Exception as exc:
            # One malformed input must not take the whole report down; the
            # crash is itself a finding and still decides the exit code.
            result = [_fail(f"{name}.crashed", f"{type(exc).__name__}: {exc}")]
        for finding in result:
            print(finding)
        failures = sum(1 for f in result if f.severity == FAIL)
        if not failures:
            print(f"OK   {name}" + (f" ({len(result)} INFO)" if result else ""))
        findings += result
    return findings


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--skip", action="append", default=[], help="check id to leave out, repeatable"
    )
    ap.add_argument("--list", action="store_true", help="print the check ids and exit")
    args = ap.parse_args(argv)

    if args.list:
        for name, check in CHECKS:
            print(f"{name}: {(check.__doc__ or '').splitlines()[0]}")
        return 0

    findings = run(set(args.skip))
    failures = [f for f in findings if f.severity == FAIL]
    infos = [f for f in findings if f.severity == INFO]
    print(f"\n{len(failures)} FAIL, {len(infos)} INFO")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
