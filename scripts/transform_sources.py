"""Transform the CSV source catalog into clean JSON for the prototype.

Input: sources/quellen-katalog.csv, which carries ghost columns and inconsistent dates
Output: docs/data/sources.json, with Transkribus links and availability tiers

Two figures per source that used to be one. `catalogue_extent` is the archival
statement of the finding aid, in an explicit unit; `digital_images` is the number
of scans the Transkribus documents of the shelfmark hold. They are different
units and were mixed under the old `seiten` field.

`--migrate` rewrites an existing docs/data/sources.json into the current schema
without reading the CSV, which is project-internal and absent from the public
clone. Both paths run through the same schema code, which is why the mode lives
here instead of in a second script.
"""

import csv
import io
import json
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from pathlib import Path

BASE = str(Path(__file__).resolve().parents[1])


def normalize_date(raw):
    """Normalize date strings to consistent format.

    Handles: '1487-1594', '1495 (ca.)', '15. Jh.', '-1564', '1479',
             '1470-1479', '1490 (ca.)', etc.
    Returns: {'raw': original, 'start': int|None, 'end': int|None, 'circa': bool}
    """
    if not raw or not raw.strip():
        return {"raw": "", "start": None, "end": None, "circa": False}

    raw = raw.strip()
    # Normalize dashes (en-dash → hyphen)
    raw_norm = raw.replace("\u2013", "-").replace("\u2014", "-")
    circa = "ca." in raw_norm or "ca" in raw_norm

    # Try range: 1487-1594
    m = re.match(r"(-?\d{4})\s*-\s*(\d{4})", raw_norm)
    if m:
        return {
            "raw": raw,
            "start": int(m.group(1)),
            "end": int(m.group(2)),
            "circa": circa,
        }

    # Try single year with optional prefix/suffix: 1479, -1564, 1495 (ca.)
    m = re.search(r"(-?\d{4})", raw_norm)
    if m:
        year = int(m.group(1))
        return {"raw": raw, "start": year, "end": year, "circa": circa}

    # Century: "15. Jh."
    m = re.search(r"(\d+)\.\s*Jh", raw_norm)
    if m:
        century = int(m.group(1))
        return {
            "raw": raw,
            "start": (century - 1) * 100 + 1,
            "end": century * 100,
            "circa": True,
        }

    return {"raw": raw, "start": None, "end": None, "circa": False}


def parse_pages(digitalisiert):
    """Extract the catalogue extent from the Digitalisiert column.

    The column contains an extent, not a boolean, e.g. '123', '45 S.'. What that
    extent counts is not stated in the column, which is why the value is wrapped
    by catalogue_extent() with an explicit unit. The first integer of a free-text
    cell can be an artifact of the cell rather than an extent (A 194.1 yields 1
    for a document of 40 scans), so the raw cell travels with the value.
    """
    if not digitalisiert or not digitalisiert.strip():
        return None
    m = re.search(r"(\d+)", digitalisiert.strip())
    if m:
        return int(m.group(1))
    return None


# Shelfmark families whose catalogue unit the source audit settled.
ACCOUNT_BOOK = re.compile(r"^TLA Raitbuch \d+$")
SIDE_COUNTING = re.compile(r"Inventare A 0(?:06|24)\.")


def catalogue_unit(signatur, value, digital_images):
    """The unit of a catalogue extent: written sides, images, or undecided.

    Account-book volumes: the catalogue figure equals the counted scans of the
    Transkribus volume for 22 of 25 entries, so the catalogue counts openings,
    which are one image each.
    A 006 and A 024 personal inventories: an even figure of roughly twice the
    images counts written sides, two per opening.
    Everywhere else the evidence does not decide and the unit stays unknown; the
    figure is then an archival statement of unnamed unit and nothing more.
    """
    if ACCOUNT_BOOK.match(signatur):
        return "bilder"
    if (
        SIDE_COUNTING.search(signatur)
        and value % 2 == 0
        and digital_images > 0
        and 1.5 * digital_images <= value <= 2.5 * digital_images
    ):
        return "seiten"
    return "unbekannt"


def catalogue_extent(signatur, value, raw, digital_images):
    """The archival extent with its unit named, or None where the catalogue is silent."""
    if value is None:
        return None
    return {
        "value": value,
        "unit": catalogue_unit(signatur, value, digital_images),
        "raw": raw,
    }


def transkribus_docs(signatur, matched, images_by_doc):
    """Every Transkribus document of a shelfmark, in the order of the mapping.

    Two catalogue rows pair two shelfmarks and carry two documents each
    (A 125.3-4, A 142.1-2). Keying by shelfmark into a dict dropped one of the
    two silently, so the mapping is filtered rather than indexed.
    """
    docs = []
    for m in matched:
        if m["csv_signatur"] != signatur:
            continue
        doc_id = m["transkribus_id"]
        docs.append(
            {
                "doc_id": doc_id,
                "title": m["transkribus_title"],
                # Scans of the document, from the collection metadata where it
                # knows the document, otherwise from the mapping record.
                "pages": images_by_doc.get(doc_id, m["pages"]),
                "lines": m["lines"],
                "words": m["words"],
                "has_text": m["has_text"],
            }
        )
    return docs


def compute_availability_tier(row, tb_mapping):
    """Compute data availability tier 1-4.

    Tier 1: Transkription vorhanden (in Transkribus mit Text)
    Tier 2: Digitalisiert (in Transkribus, aber kein Text)
    Tier 3: Im Archiv bekannt, nicht digitalisiert
    Tier 4: Unsicher/fraglich
    """
    signatur = row.get("Signatur", "").strip()

    for m in tb_mapping.get("matched", []):
        if m["csv_signatur"] == signatur:
            if m["has_text"]:
                return 1
            else:
                return 2

    # Transkribiert column says "Inventaria"
    if row.get("Transkribiert", "").strip():
        return 1

    # Has page count in Digitalisiert column → likely digitized
    pages = parse_pages(row.get("Digitalisiert", ""))
    if pages and pages > 0:
        return 2

    return 3


OUT_PATH = f"{BASE}/docs/data/sources.json"


def load_json(name):
    with open(f"{BASE}/docs/data/{name}", encoding="utf-8") as f:
        return json.load(f)


def build_source(signatur, base, extent_value, extent_raw, matched, images_by_doc):
    """One source entry: archival metadata, catalogue extent, Transkribus documents."""
    docs = transkribus_docs(signatur, matched, images_by_doc)
    return {
        "signatur": signatur,
        "kategorie": base["kategorie"],
        "titel": base["titel"],
        "datierung": base["datierung"],
        "art": base["art"],
        "projekt": base["projekt"],
        "catalogue_extent": catalogue_extent(
            signatur, extent_value, extent_raw, sum(d["pages"] for d in docs)
        ),
        "transkribiert": base["transkribiert"],
        "tier": base["tier"],
        "transkribus_docs": docs,
        "digital_images": sum(d["pages"] for d in docs),
    }


def from_csv(matched, images_by_doc, tb_mapping):
    rows = []
    with open(f"{BASE}/sources/quellen-katalog.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    print(f"Loaded {len(rows)} CSV rows")

    sources = []
    for row in rows:
        signatur = row.get("Signatur", "").strip()
        # An empty trailing row of the CSV carries no signature.
        if not signatur:
            continue
        digitalisiert = row.get("Digitalisiert", "").strip()
        base = {
            "kategorie": row.get("Kategorie", "").strip(),
            "titel": row.get("Titel", "").strip(),
            "datierung": normalize_date(row.get("Datierung", "").strip()),
            "art": row.get("Art", "").strip(),
            "projekt": row.get("Projekt", "").strip(),
            "transkribiert": row.get("Transkribiert", "").strip(),
            "tier": compute_availability_tier(row, tb_mapping),
        }
        sources.append(
            build_source(
                signatur,
                base,
                parse_pages(digitalisiert),
                digitalisiert or None,
                matched,
                images_by_doc,
            )
        )
    return sources


def from_existing(matched, images_by_doc):
    """Rewrite the existing sources.json into the current schema, without the CSV."""
    sources = []
    for entry in load_json("sources.json"):
        base = {
            k: entry[k]
            for k in (
                "kategorie",
                "titel",
                "datierung",
                "art",
                "projekt",
                "transkribiert",
                "tier",
            )
        }
        old = entry.get("catalogue_extent")
        value = old["value"] if old else entry.get("seiten")
        # The catalogue cell the value was parsed from cannot be recovered here:
        # sources/quellen-katalog.csv is project-internal and absent from this
        # clone. raw stays null until a run with the CSV present fills it.
        raw = old["raw"] if old else None
        sources.append(
            build_source(entry["signatur"], base, value, raw, matched, images_by_doc)
        )
    return sources


def main():
    migrate = "--migrate" in sys.argv
    tb_mapping = load_json("source_mapping.json")
    matched = tb_mapping.get("matched", [])
    images_by_doc = {
        c["docId"]: c["nrOfPages"] for c in load_json("transkribus_collection.json")
    }

    sources = (
        from_existing(matched, images_by_doc)
        if migrate
        else from_csv(matched, images_by_doc, tb_mapping)
    )

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(sources, f, ensure_ascii=False, indent=1)

    print(f"\nSaved {len(sources)} sources to {OUT_PATH}")
    print("\nCategories:")
    categories = {}
    for s in sources:
        categories[s["kategorie"]] = categories.get(s["kategorie"], 0) + 1
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat:<30} {count:>4}")

    print("\nTiers:")
    tier_counts = {}
    for s in sources:
        tier_counts[s["tier"]] = tier_counts.get(s["tier"], 0) + 1
    for tier in sorted(tier_counts):
        labels = {1: "Transkription", 2: "Digitalisiert", 3: "Im Archiv", 4: "Unsicher"}
        print(f"  Tier {tier} ({labels.get(tier, '?')}): {tier_counts[tier]}")

    linked = [s for s in sources if s["transkribus_docs"]]
    print(
        f"\nWith Transkribus documents: {len(linked)} rows, "
        f"{sum(len(s['transkribus_docs']) for s in linked)} documents, "
        f"{sum(s['digital_images'] for s in linked)} images"
    )
    units = {}
    for s in sources:
        if s["catalogue_extent"]:
            u = s["catalogue_extent"]["unit"]
            units[u] = units.get(u, 0) + 1
    print(
        "Catalogue extent units: "
        + ", ".join(f"{u}={n}" for u, n in sorted(units.items()))
    )


if __name__ == "__main__":
    main()
