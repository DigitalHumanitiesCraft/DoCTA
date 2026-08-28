"""Corpus-wide entity index over the pipeline entity extractions.

One entry per distinct (type, normalized) pair across all extracted documents,
under a deterministic slug id. Every consumer of the extraction layer, the
JSON-LD graph now and the TEI entity register next, names an entity by the
same id, so the index is built here once and imported everywhere.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENTITY_DIR = ROOT / "docs" / "data" / "entities"

# Types that become index entries. Time stays out by decision: the extraction
# resolves no calendar dates yet, and an unresolved date is not an entity entry.
TYPE_PREFIX = {"person": "per", "place": "pl", "object": "obj"}

_TRANSLIT = str.maketrans(
    {"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "ae", "Ö": "oe", "Ü": "ue", "ß": "ss"}
)


def slugify(text: str) -> str:
    """ASCII slug of a normalized form, with the German umlaut convention."""
    text = text.translate(_TRANSLIT)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "x"


def _line_sort_key(line_id: str | None) -> tuple:
    match = re.fullmatch(r"r(\d+)l(\d+)", line_id or "")
    if match:
        return (0, int(match.group(1)), int(match.group(2)), "")
    return (1, 0, 0, line_id or "")


def load_extractions(entity_dir: Path = ENTITY_DIR) -> list[dict]:
    """The per-document extraction files, in stable docId order."""
    files = sorted(entity_dir.glob("*.json"))
    extractions = [json.loads(p.read_text(encoding="utf-8")) for p in files]
    return sorted(extractions, key=lambda ex: ex.get("docId") or 0)


def build_index(extractions: list[dict]) -> list[dict]:
    """Merged entries with slug ids, sorted by (type, normalized).

    A slug collision between two distinct normalized forms gets a numeric
    suffix in that same sort order, so ids stay stable as long as the colliding
    forms themselves do.
    """
    merged: dict[tuple[str, str], dict] = {}
    for extraction in extractions:
        doc_id = extraction.get("docId")
        for entity in extraction.get("entities") or []:
            etype = entity.get("type")
            if etype not in TYPE_PREFIX:
                continue
            normalized = entity.get("normalized") or entity.get("text") or ""
            if not normalized:
                continue
            entry = merged.setdefault(
                (etype, normalized),
                {
                    "type": etype,
                    "normalized": normalized,
                    "forms": set(),
                    "roles": set(),
                    "attestations": [],
                },
            )
            form = entity.get("text") or normalized
            entry["forms"].add(form)
            role = (entity.get("role") or "").strip()
            if role:
                entry["roles"].add(role)
            entry["attestations"].append(
                {
                    "docId": doc_id,
                    "page": entity.get("pageNr"),
                    "line": entity.get("lineId"),
                    "form": form,
                }
            )

    entries = []
    taken: set[str] = set()
    for (etype, normalized), entry in sorted(merged.items()):
        base = f"{TYPE_PREFIX[etype]}-{slugify(normalized)}"
        slug, n = base, 1
        while slug in taken:
            n += 1
            slug = f"{base}-{n}"
        taken.add(slug)
        entries.append(
            {
                "id": slug,
                "type": etype,
                "normalized": normalized,
                "forms": sorted(entry["forms"]),
                "roles": sorted(entry["roles"]),
                "attestations": sorted(
                    entry["attestations"],
                    key=lambda a: (
                        a["docId"] or 0,
                        a["page"] or 0,
                        _line_sort_key(a["line"]),
                    ),
                ),
            }
        )
    return entries
