# /// script
# requires-python = ">=3.11"
# dependencies = ["requests"]
# ///
"""Entity extraction with line anchors over human-corrected transcriptions.

Every entity carries a line anchor, which is what makes deterministic TEI
encoding possible: the model sees every line with its id, has to name the id it
read an entity in, and every returned entity is re-checked against that line
before it is kept.

Two facts about the Transkribus export drive the design. Region ids restart on
every page, so a bare line id ("r2l3") is ambiguous inside a document and the
prompt therefore uses the page-qualified form ("p1_r2l3"), which is split back
into pageNr and lineId on write. And a minority of lines carry combining
diacritics, so the verbatim check matches in NFC space but stores the raw
substring taken from the line, which keeps the stored surface form byte-identical
to the transcription.

Provenance: source "llm", with model, prompt id, prompt hash and date in every
output file. No confidence field anywhere; the evidence of an entity is its line
id plus its verbatim surface form.

Data flow (network only for the Gemini API):
  docs/data/transcriptions/<docId>.json   Transkribus export: pages, regions, lines
  pipeline/pages/<docId>.json             page register, for a document whose text
                                          DoCTA transcribed itself (no export)
  pipeline/prompts/entities_it01.md       frozen system prompt (first code block)
  -> docs/data/entities/<docId>.json      entities plus the rejected list

Which layer a document's text comes from is decided in build_register.py and not
here. Where it is a DoCTA transcription, the output records that in the
provenance, because the extraction then rests on unrevised machine output and
the run ids it rests on have to stay readable.

The API call goes through requests rather than urllib, for its retry and
timeout handling.

Usage:
  python extract_entities.py             # all three documents, skip existing
  python extract_entities.py --force     # re-run and overwrite
  python extract_entities.py --doc 11328300
"""

import argparse
import hashlib
import json
import re
import sys
import time
import unicodedata
from datetime import date

import build_register as br
import requests
from io_paths import DATA, PIPELINE_DIR, REPO_ROOT, fenced_block, load_json

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

TRANSCRIPTIONS = DATA / "transcriptions"
OUT_DIR = DATA / "entities"

MODEL = "gemini-3.7-flash"
API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
TEMPERATURE = 0.0
TIMEOUT = 300
PROMPT_ID = "entities_it01"

# Documents whose transcription layer is human-corrected in Transkribus and
# therefore validated ground for an extraction with line anchors.
DOC_IDS = (11328300, 11330019, 11330020)

# Documents DoCTA transcribed itself. The line ids are the synthetic ids of the
# edition run, and the anchors sit in unrevised machine output, which the output
# file records in its provenance instead of leaving it to be inferred.
VLM_DOC_IDS = (12593450,)

TYPES = ("person", "place", "object", "time")
ID_PREFIX = {"person": "p", "place": "pl", "object": "o", "time": "t"}

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "lineId": {"type": "string"},
                    "text": {"type": "string"},
                    "normalized": {"type": "string"},
                    "type": {"type": "string", "enum": list(TYPES)},
                    "role": {"type": "string"},
                },
                "required": ["lineId", "text", "normalized", "type"],
            },
        },
    },
    "required": ["entities"],
}


def load_api_key() -> str:
    env = REPO_ROOT / ".env"
    if not env.exists():
        sys.exit("FEHLER: .env nicht gefunden")
    for line in env.read_text(encoding="utf-8").splitlines():
        if line.startswith("GEMINI_API_KEY="):
            return line.split("=", 1)[1].strip()
    sys.exit("FEHLER: GEMINI_API_KEY nicht in .env gefunden")


def load_lines(doc: dict) -> dict[str, dict]:
    """Page-qualified line index, in document order.

    Key is the page-qualified line id; the value keeps pageNr, the native
    lineId, the raw text and the running order used for the derived entity ids.
    """
    index: dict[str, dict] = {}
    order = 0
    for page in doc["pages"]:
        for line in br.iter_lines(page):
            key = br.line_key(page["pageNr"], line["id"])
            if key in index:
                sys.exit(f"FEHLER: doppelte Zeilen-ID {key} in Dokument {doc['docId']}")
            index[key] = {
                "pageNr": page["pageNr"],
                "lineId": line["id"],
                "text": line["text"],
                "order": order,
            }
            order += 1
    return index


def serialize(doc: dict) -> str:
    """The transcription as the model sees it: page headers plus id-tagged lines."""
    out: list[str] = [f"DOKUMENT: {doc['title']}"]
    for page in doc["pages"]:
        out.append(f"\n== Seite {page['pageNr']} ==")
        for line in br.iter_lines(page):
            out.append(f"{br.line_key(page['pageNr'], line['id'])}\t{line['text']}")
    return "\n".join(out)


def call_gemini(key: str, system: str, user: str) -> dict:
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {
            "temperature": TEMPERATURE,
            "candidateCount": 1,
            "maxOutputTokens": 32768,
            "responseMimeType": "application/json",
            "responseSchema": RESPONSE_SCHEMA,
        },
    }
    last_reason = "HTTP"
    for attempt in range(4):
        r = requests.post(
            f"{API_BASE}/{MODEL}:generateContent",
            headers={"x-goog-api-key": key, "Content-Type": "application/json"},
            json=body,
            timeout=TIMEOUT,
        )
        if r.status_code in (429, 500, 503):
            time.sleep(2 ** (attempt + 2))
            continue
        r.raise_for_status()
        data = r.json()
        cands = data.get("candidates")
        if not cands:
            last_reason = data.get("promptFeedback", {}).get(
                "blockReason", "no candidates"
            )
            time.sleep(2 ** (attempt + 2))
            continue
        cand = cands[0]
        text = "".join(
            p.get("text", "") for p in cand.get("content", {}).get("parts", [])
        )
        if not text:
            raise ValueError(f"leere Antwort, finishReason={cand.get('finishReason')}")
        return json.loads(
            re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
        )
    raise RuntimeError(f"Retries erschöpft ({last_reason})")


def locate(line: str, surface: str) -> str | None:
    """The raw substring of `line` that equals `surface`, or None.

    Direct match first; the NFC fallback catches the lines whose combining
    diacritics the model reproduced in precomposed form. Scanning the offsets
    returns the raw substring, so the stored surface stays byte-identical to the
    transcription. Lines are short, so the quadratic scan is irrelevant here.
    """
    if not surface:
        return None
    if surface in line:
        return surface
    target = unicodedata.normalize("NFC", surface)
    for i in range(len(line)):
        for j in range(i + 1, len(line) + 1):
            if unicodedata.normalize("NFC", line[i:j]) == target:
                return line[i:j]
    return None


def validate(raw: list[dict], index: dict[str, dict]) -> tuple[list[dict], list[dict]]:
    """Deterministic post-validation: keep only entities proven by their line.

    Rejection reasons are kept verbatim in the output file, so the failure modes
    of an iteration stay inspectable without a re-run.
    """
    kept: list[dict] = []
    rejected: list[dict] = []
    seen: set[tuple] = set()
    for item in raw:
        key = str(item.get("lineId", "")).strip()
        surface = str(item.get("text", "")).strip()
        etype = str(item.get("type", "")).strip()
        record = {
            "lineId": key,
            "text": surface,
            "normalized": item.get("normalized", ""),
            "type": etype,
            "role": item.get("role", ""),
        }
        if etype not in TYPES:
            rejected.append({**record, "reason": "type_invalid"})
            continue
        if key not in index:
            rejected.append({**record, "reason": "line_unknown"})
            continue
        line = index[key]
        found = locate(line["text"], surface)
        if found is None:
            rejected.append(
                {**record, "reason": "not_verbatim", "lineText": line["text"]}
            )
            continue
        dedupe = (key, found, etype)
        if dedupe in seen:
            rejected.append({**record, "reason": "duplicate"})
            continue
        seen.add(dedupe)
        kept.append(
            {
                "text": found,
                "normalized": str(item.get("normalized", "")).strip() or found,
                "type": etype,
                "pageNr": line["pageNr"],
                "lineId": line["lineId"],
                "role": str(item.get("role", "")).strip(),
                "_order": (line["order"], line["text"].index(found)),
            }
        )
    kept.sort(key=lambda e: e["_order"])
    counters: dict[str, int] = {}
    out: list[dict] = []
    for entity in kept:
        prefix = ID_PREFIX[entity["type"]]
        counters[prefix] = counters.get(prefix, 0) + 1
        out.append(
            {
                "id": f"{prefix}{counters[prefix]}",
                "text": entity["text"],
                "normalized": entity["normalized"],
                "type": entity["type"],
                "pageNr": entity["pageNr"],
                "lineId": entity["lineId"],
                "role": entity["role"],
            }
        )
    return out, rejected


def assert_verbatim(entities: list[dict], index: dict[str, dict]) -> None:
    """Definition of Done: every kept entity occurs verbatim in its named line.

    Raises instead of asserting, so the check also holds under python -O.
    """
    for e in entities:
        line = index[br.line_key(e["pageNr"], e["lineId"])]
        if e["text"] not in line["text"]:
            raise ValueError(f"{e['id']}: {e['text']!r} nicht in {line['lineId']}")
        if "confidence" in e:
            raise ValueError(f"{e['id']}: Konfidenzfeld in der Ausgabe")


def _title(doc_id: int) -> str | None:
    """Archival title of a document, for a transcription that carries none.

    The Transkribus export brings its own title; a transcription assembled from
    the register takes it from the document index, so the extraction file and
    the graph label the document the way the source register does.
    """
    path = PIPELINE_DIR / "documents.json"
    if not path.exists():
        return None
    doc = next((d for d in load_json(path) if d["docId"] == doc_id), None)
    return (doc or {}).get("title")


def run_one(key: str, doc_id: int, system: str, prompt_hash: str, force: bool) -> dict:
    out_path = OUT_DIR / f"{doc_id}.json"
    if out_path.exists() and not force:
        print(f"SKIP {out_path.name} (existiert, --force zum Neuladen)")
        return load_json(out_path)
    doc = br.transcription_of(doc_id, title=_title(doc_id))
    if doc is None:
        sys.exit(f"FEHLER: keine Transkription fuer Dokument {doc_id}")
    index = load_lines(doc)
    parsed = call_gemini(key, system, serialize(doc))
    entities, rejected = validate(parsed.get("entities", []), index)
    assert_verbatim(entities, index)
    provenance = {
        "source": "llm",
        "model": MODEL,
        "prompt": PROMPT_ID,
        "prompt_hash": prompt_hash,
        "date": date.today().isoformat(),
    }
    # What the extraction read. Named only where that is a DoCTA transcription,
    # because there the anchors sit in unrevised machine output and the runs
    # they rest on have to stay identifiable.
    if basis := (doc.get("provenance") or {}).get("runs"):
        provenance["basis"] = {
            "transcription": "vlm",
            "state": "machine-unrevised",
            "runs": basis,
        }
    result = {
        "docId": doc_id,
        "title": doc["title"],
        "provenance": provenance,
        "entities": entities,
        "rejected": rejected,
    }
    # Written here rather than through io_paths.write_json: an extraction file is
    # research data the committed corpus already holds in this serialisation, and
    # the shared writer would rewrite every one of them on the next run.
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(out_path)
    print(f"OK {out_path.name}: {len(entities)} Entitäten, {len(rejected)} verworfen")
    return result


def report(result: dict) -> None:
    by_type: dict[str, int] = {}
    for e in result["entities"]:
        by_type[e["type"]] = by_type.get(e["type"], 0) + 1
    reasons: dict[str, int] = {}
    for r in result["rejected"]:
        reasons[r["reason"]] = reasons.get(r["reason"], 0) + 1
    types = " ".join(f"{t}={by_type.get(t, 0)}" for t in TYPES)
    worst = max(reasons.items(), key=lambda kv: kv[1])[0] if reasons else "-"
    print(f"{result['docId']} {result['title']}")
    print(f"  gehalten {len(result['entities'])} ({types})")
    print(f"  verworfen {len(result['rejected'])} {reasons or ''} dominant={worst}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--doc", type=int, action="append", help="nur diese docId (mehrfach möglich)"
    )
    ap.add_argument(
        "--force", action="store_true", help="bestehende Ausgabe überschreiben"
    )
    args = ap.parse_args()
    doc_ids = args.doc or list(DOC_IDS + VLM_DOC_IDS)
    system = fenced_block(PIPELINE_DIR / "prompts" / f"{PROMPT_ID}.md")
    prompt_hash = hashlib.sha256(system.encode()).hexdigest()[:12]
    key = load_api_key()
    errors = []
    results = []
    for doc_id in doc_ids:
        try:
            results.append(run_one(key, doc_id, system, prompt_hash, args.force))
        except Exception as e:
            print(f"FEHLER {doc_id}: {e}", file=sys.stderr)
            errors.append({"docId": doc_id, "error": str(e)})
    print(f"\n== Bericht (prompt {PROMPT_ID}, hash {prompt_hash}) ==")
    for result in results:
        report(result)
    if errors:
        print(f"\n{len(errors)} Dokument(e) fehlgeschlagen", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
