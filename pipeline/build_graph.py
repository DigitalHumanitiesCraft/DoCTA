"""Aggregated research data of the entity layer as JSON-LD.

Derives docs/data/graph.jsonld from the per-document entity extractions: one
node per entity-index entry and per extracted document, plus the line
co-occurrences between entities. Everything in the file is derivable from the
inputs; the builder reads no clock and makes no network calls, so the output
is byte-identical on every rebuild.

Typed relations between entities (who hands over to whom) are deliberately
absent, because no pipeline step establishes them yet. When a relation
extraction with full provenance exists, its output joins this graph as
further link resources.
"""

from __future__ import annotations

import itertools
import json
import re
import sys
from pathlib import Path

import build_register as br
import entity_index as ei

ROOT = Path(__file__).resolve().parent.parent
GRAPH_FILE = ROOT / "docs" / "data" / "graph.jsonld"

NS = "docta:"
TYPE_CLASS = {
    "person": "docta:Person",
    "place": "docta:Place",
    "object": "docta:Object",
}

CONTEXT = {
    "@version": 1.1,
    "docta": "https://dhcraft.org/DoCTA/ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "label": {"@id": "rdfs:label"},
    "attestedForm": {"@id": "docta:attestedForm", "@container": "@set"},
    "role": {"@id": "docta:role", "@container": "@set"},
    "attestedIn": {"@id": "docta:attestedIn", "@type": "@id", "@container": "@set"},
    "attestation": {"@id": "docta:attestation", "@type": "@json"},
    "member": {"@id": "docta:member", "@type": "@id", "@container": "@set"},
    "count": {"@id": "docta:count"},
    "transkribusDocId": {"@id": "docta:transkribusDocId"},
    "transcriptionBy": {"@id": "docta:transcriptionBy"},
    "tei": {"@id": "docta:tei"},
    "provenance": {"@id": "docta:provenance", "@type": "@json"},
}


def _document_label(extraction: dict) -> str:
    """Readable label from the extraction title, raw title as the fallback."""
    title = extraction.get("title") or str(extraction.get("docId"))
    match = re.fullmatch(r"([^_]+)_(.+)_(\d{4})", title)
    if match:
        return f"{match.group(1)}, {match.group(2)} ({match.group(3)})"
    return title


def _transcription_attribution() -> set[int]:
    """Documents whose transcription was made by the Inventaria project.

    The attribution must reach every consumer of the graph, so it is carried
    on the document nodes rather than left to a client-side join.
    """
    mapping_path = ROOT / "docs" / "data" / "source_mapping.json"
    if not mapping_path.exists():
        return set()
    data = json.loads(mapping_path.read_text(encoding="utf-8"))
    return {
        m["transkribus_id"]
        for m in data.get("matched", [])
        if m.get("csv_transkribiert") == "Inventaria"
    }


def _document_nodes(extractions: list[dict]) -> list[dict]:
    inventaria = _transcription_attribution()
    nodes = []
    for ex in extractions:
        node = {
            "@id": f"{NS}doc-{ex['docId']}",
            "@type": "docta:Document",
            "label": _document_label(ex),
            "transkribusDocId": ex["docId"],
            "tei": f"tei/{ex['docId']}.xml",
        }
        if ex["docId"] in inventaria:
            node["transcriptionBy"] = "Inventaria"
        nodes.append(node)
    return nodes


def _entity_nodes(entries: list[dict]) -> list[dict]:
    nodes = []
    for entry in entries:
        node: dict = {
            "@id": NS + entry["id"],
            "@type": TYPE_CLASS[entry["type"]],
            "label": entry["normalized"],
            "attestedForm": entry["forms"],
        }
        if entry["roles"]:
            node["role"] = entry["roles"]
        node["attestedIn"] = sorted(
            {f"{NS}doc-{a['docId']}" for a in entry["attestations"]}
        )
        node["attestation"] = entry["attestations"]
        nodes.append(node)
    return nodes


def _cooccurrences(entries: list[dict]) -> list[dict]:
    """One link resource per entity pair attested in the same line."""
    by_locus: dict[tuple, set[str]] = {}
    for entry in entries:
        for a in entry["attestations"]:
            if a["line"] is None:
                continue
            by_locus.setdefault((a["docId"], a["page"], a["line"]), set()).add(
                entry["id"]
            )
    pairs: dict[tuple[str, str], set[tuple]] = {}
    for locus, ids in by_locus.items():
        for a, b in itertools.combinations(sorted(ids), 2):
            pairs.setdefault((a, b), set()).add(locus)
    return [
        {
            "@id": f"{NS}cooc-{a}--{b}",
            "@type": "docta:LineCoOccurrence",
            "member": [NS + a, NS + b],
            "count": len(loci),
            "attestation": [
                {"docId": d, "page": p, "line": line}
                for d, p, line in sorted(
                    loci, key=lambda x: (x[0], x[1], ei._line_sort_key(x[2]))
                )
            ],
        }
        for (a, b), loci in sorted(pairs.items())
    ]


def build(entity_dir: Path = ei.ENTITY_DIR) -> dict:
    extractions = ei.load_extractions(entity_dir)
    entries = ei.build_index(extractions)
    provenance = {
        # Who identified the entities: the extraction runs, carried verbatim.
        "identification": [
            dict(ex.get("provenance") or {}, docId=ex.get("docId"))
            for ex in extractions
        ],
        # Who built the graph: a deterministic aggregation, no model involved.
        "aggregation": {
            "source": "workflow",
            "generator": "pipeline/build_graph.py",
            "method": "entities merged by type and normalized form; links are "
            "attestation in a document and co-occurrence in a transcription line",
        },
    }
    return {
        "@context": CONTEXT,
        "@id": "docta:graph",
        "label": "DoCTA entity graph over the extracted inventory transcriptions",
        "provenance": provenance,
        "@graph": _document_nodes(extractions)
        + _entity_nodes(entries)
        + _cooccurrences(entries),
    }


def main() -> int:
    payload = build()
    br._write(GRAPH_FILE, payload)
    graph = payload["@graph"]
    print(f"graph.jsonld: {len(graph)} resources")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
