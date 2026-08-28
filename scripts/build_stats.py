"""Precompute the entry counts of the SiCProD exports into one small file.

The counting runs offline so that no page has to load several megabytes of
entity data to read their lengths. No page of the site loads the output; the
site computes its figures from sources.json and the register summary.

Sources of the numbers:
  persons        len(data/persons.json)
  relations      len(data/relations.json)
  places         len(data/places.json)
  sources        len(data/sources.json)
  functions      len(data/functions.json)
  transcriptions data/source_mapping.json -> matched[] entries with has_text

Input:  data/persons.json, data/relations.json, data/places.json,
        data/sources.json, data/functions.json, data/source_mapping.json
Output: docs/data/stats.json

Re-run after any change to those input files.
"""

import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(name):
    with open(f"{BASE}/docs/data/{name}", encoding="utf-8") as f:
        return json.load(f)


def main():
    mapping = load("source_mapping.json")
    stats = {
        "persons": len(load("persons.json")),
        "relations": len(load("relations.json")),
        "places": len(load("places.json")),
        "sources": len(load("sources.json")),
        "functions": len(load("functions.json")),
        "transcriptions": sum(
            1 for m in mapping.get("matched", []) if m.get("has_text")
        ),
    }

    out_path = f"{BASE}/docs/data/stats.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
        f.write("\n")

    for key, value in stats.items():
        print(f"{key:15} {value}")
    print(f"\nWritten: {out_path}")


if __name__ == "__main__":
    main()
