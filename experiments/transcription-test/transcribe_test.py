# /// script
# requires-python = ">=3.11"
# dependencies = ["requests", "pillow"]
# ///
"""VLM transcription test case: 5 images x 5 prompt variants with Gemini Flash.

Test set: 4 Raitbuch 2 double-page spreads (untranscribed, Early New High German
cursive) + 1 inventory page from Thaur A 49.9 with scholarly Transkribus ground
truth as CER anchor. Few-shot example is drawn from a DIFFERENT inventory
(A 49.5) to avoid contamination of the GT evaluation.

Variants:
  v1_baseline   minimal prompt, plain text output
  v2_structured diplomatic rules + hard JSON schema with uncertain_words field
  v3_fewshot    v2 + one image/GT pair from another inventory as in-context example
  v4_split      v2 on left/right folio halves separately (higher effective resolution)
  v5_repeat     v2 re-run, measures self-consistency (VLM nondeterminism)

Design decisions ported from szd-htr (knowledge/verification-concept.md there):
full-resolution images (capped only by API limits), mandatory uncertain_words
field instead of inline [?] markers, provenance in every output, skip-if-exists.

Usage:
  uv run transcribe_test.py            # fetch images, run all missing variants
  uv run transcribe_test.py --force    # re-run everything
  uv run transcribe_test.py --eval     # only recompute evaluation + viewer data
"""

import base64
import io
import json
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import requests
from PIL import Image, ImageOps

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent
REPO = ROOT.parent.parent
IMAGES = ROOT / "images"
RESULTS = ROOT / "results"

MODEL_CANDIDATES = ["gemini-3.7-flash", "gemini-flash-latest"]
API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
MAX_SIDE = 3500  # px cap for API payload; crops in v4 keep more effective detail
TEMPERATURE = 0.0  # per published best practice for diplomatic transcription
TIMEOUT = 300

# Raitbuch 2 spreads by pageNr in data/raitbuch2_pages.json
RAITBUCH_PAGES = [2, 3, 40, 90]
GT_DOC, GT_PAGE = "11327963", 2        # Thaur A 49.9, CER anchor
FEWSHOT_DOC, FEWSHOT_PAGE = "11327964", 2  # Thaur A 49.5, in-context example

SYSTEM_PROMPT = """\
Du bist Experte für die diplomatische Transkription spätmittelalterlicher \
deutschsprachiger Handschriften (Kurrent/Bastarda des 15. Jahrhunderts, \
Frühneuhochdeutsch, Tiroler Verwaltungsschriftgut: Rechnungsbücher und Inventare).

Regeln:
1. Diplomatisch transkribieren: historische Orthographie exakt beibehalten, \
keine Normalisierung (u/v, i/j, Vokalzeichen wie ů ö ä genau wiedergeben).
2. Abkürzungen, die du sicher auflösen kannst, in runden Klammern auflösen \
(od(er), It(em), Sum(m)a); unsichere Kürzel unaufgelöst belassen. \
Das entspricht der Transkribus-Konvention dieses Bestands.
3. Zeilengetreu arbeiten: eine Ausgabezeile pro Handschriftzeile, \
Zeilenreihenfolge der Seite folgen (Spalte für Spalte, oben nach unten).
4. Zahlzeichen exakt wiedergeben (römische und arabische Zahlen wie geschrieben, \
Währungskürzel wie geschrieben).
5. Nichts erfinden. Unleserliche Zeichen als [...] wiedergeben. Jedes Wort, \
bei dem du nicht sicher bist, MUSS zusätzlich im Feld uncertain aufgeführt werden. \
Lieber zu viele Wörter als unsicher markieren als zu wenige.
6. Durchgestrichenes in ~~...~~, nachträglich Eingefügtes in {...}.
7. Keinen durchscheinenden Text der Rückseite (Bleed-Through) transkribieren.
8. Leere Seiten oder Seitenteile explizit als leer melden, nichts erfinden. \
In Rechnungsbüchern ist die linke Seite (verso) häufig leer oder zeigt nur \
durchscheinende Schrift der Folgeseite.
9. Beträge stehen meist am Zeilenende, oft nach einem Füllstrich, als römische \
Zahlen mit hochgestellten Multiplikatoren und Währungskürzeln (gld, lb/tt, ß, d, kr); \
exakt wie geschrieben wiedergeben, Füllstriche als "——", Hochstellungen mit ^ \
(z.B. iiij^C = 400).\
"""

JSON_INSTRUCTION = """\
Transkribiere das Bild vollständig. Antworte als JSON nach dem Schema. \
Bei einer Doppelseite zuerst die linke Seite (verso), dann die rechte (recto), \
als getrennte Einträge in "pages". "kind" pro Zeile: "rubric" für rubrizierte \
Überschriften/Namen, "entry" für Posten- und Fließtextzeilen, "amount" für reine \
Zahlen-/Betragszeilen, "sum" für Summenzeilen, "marginal" für Marginalien, \
"foliation" für Blattzählung.\
"""

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "pages": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string", "description": "z.B. 'links (verso)' oder 'fol. 2r'"},
                    "empty": {"type": "boolean"},
                    "lines": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "text": {"type": "string"},
                                "kind": {"type": "string"},
                                "uncertain": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["text", "kind"],
                        },
                    },
                },
                "required": ["label", "lines"],
            },
        },
        "notes": {"type": "string"},
    },
    "required": ["pages"],
}

BASELINE_PROMPT = (
    "Transkribiere diese historische Handschrift diplomatisch und zeilengetreu. "
    "Gib nur den transkribierten Text aus, eine Zeile pro Handschriftzeile."
)


def load_api_key() -> str:
    env = REPO / ".env"
    if not env.exists():
        sys.exit("FEHLER: .env fehlt im Repo-Root (GEMINI_API_KEY=...)")
    for line in env.read_text(encoding="utf-8").splitlines():
        if line.startswith("GEMINI_API_KEY="):
            return line.split("=", 1)[1].strip()
    sys.exit("FEHLER: GEMINI_API_KEY nicht in .env gefunden")


def build_test_set() -> list[dict]:
    """Assemble the 5 test items from repo data files."""
    rb = json.loads((REPO / "docs" / "data" / "raitbuch2_pages.json").read_text(encoding="utf-8"))
    by_nr = {p["pageNr"]: p for p in rb}
    items = []
    for nr in RAITBUCH_PAGES:
        p = by_nr[nr]
        items.append({
            "id": f"rb2_p{nr:03d}",
            "title": p["imgFileName"].replace(".jpg", ""),
            "iiif": p["iiif_url"],
            "gt": None,
            "spread": True,
        })
    gt_doc = json.loads(
        (REPO / "docs" / "data" / "transcriptions" / f"{GT_DOC}.json").read_text(encoding="utf-8")
    )
    page = next(p for p in gt_doc["pages"] if p["pageNr"] == GT_PAGE)
    gt_lines = [ln["text"] for r in page["regions"] for ln in r["lines"]]
    items.append({
        "id": f"inv_{GT_DOC}_p{GT_PAGE}",
        "title": f"{gt_doc['title']} Seite {GT_PAGE} (Ground Truth)",
        "iiif": page["iiif"],
        "gt": gt_lines,
        "spread": False,
    })
    return items


def fewshot_example() -> dict:
    doc = json.loads(
        (REPO / "docs" / "data" / "transcriptions" / f"{FEWSHOT_DOC}.json").read_text(encoding="utf-8")
    )
    page = next(p for p in doc["pages"] if p["pageNr"] == FEWSHOT_PAGE)
    lines = [ln["text"] for r in page["regions"] for ln in r["lines"]]
    answer = {
        "pages": [{
            "label": f"Seite {FEWSHOT_PAGE}",
            "empty": False,
            "lines": [{"text": t, "kind": "entry", "uncertain": []} for t in lines],
        }],
        "notes": "Fachwissenschaftliche Referenztranskription (Transkribus).",
    }
    return {"iiif": page["iiif"], "answer": answer, "image_id": f"fewshot_{FEWSHOT_DOC}_p{FEWSHOT_PAGE}"}


def fetch_image(image_id: str, url: str) -> Path:
    IMAGES.mkdir(exist_ok=True)
    path = IMAGES / f"{image_id}.jpg"
    if path.exists():
        return path
    print(f"  lade {image_id} ...")
    r = requests.get(url, timeout=180, headers={"User-Agent": "DoCTA-pipeline-test (office@dhcraft.org)"})
    r.raise_for_status()
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(r.content)
    tmp.replace(path)
    return path


def image_part(path: Path, crop: str | None = None, enhance: bool = False) -> tuple[dict, dict]:
    """Return (API part, provenance info). crop: None | 'left' | 'right'.

    enhance: grayscale + autocontrast for faded ink (e.g. rb2 fol. 40r,
    where the recto is nearly invisible at native contrast).
    """
    img = Image.open(path)
    orig = img.size
    if crop == "left":
        img = img.crop((0, 0, img.width // 2, img.height))
    elif crop == "right":
        img = img.crop((img.width // 2, 0, img.width, img.height))
    if enhance:
        img = ImageOps.autocontrast(ImageOps.grayscale(img), cutoff=1)
    if max(img.size) > MAX_SIDE:
        scale = MAX_SIDE / max(img.size)
        img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=90)
    info = {"source_px": list(orig), "sent_px": list(img.size), "crop": crop, "enhanced": enhance}
    return {"inline_data": {"mime_type": "image/jpeg",
                            "data": base64.b64encode(buf.getvalue()).decode()}}, info


def call_gemini(key: str, contents: list, json_mode: bool) -> tuple[dict, str]:
    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": contents,
        "generationConfig": {"temperature": TEMPERATURE, "maxOutputTokens": 32768},
    }
    if json_mode:
        body["generationConfig"]["responseMimeType"] = "application/json"
        body["generationConfig"]["responseSchema"] = RESPONSE_SCHEMA
    last_err = ""
    for model in MODEL_CANDIDATES:
        for attempt in range(4):
            r = requests.post(
                f"{API_BASE}/{model}:generateContent",
                headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                json=body, timeout=TIMEOUT,
            )
            if r.status_code == 404:
                last_err = f"{model}: 404"
                break  # try next model name
            if r.status_code in (429, 500, 503):
                wait = 2 ** (attempt + 2)
                print(f"  WARNUNG: {r.status_code}, Retry in {wait}s", file=sys.stderr)
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json(), model
    sys.exit(f"FEHLER: kein Modell erreichbar ({last_err})")


def extract_text(response: dict) -> str:
    cand = response["candidates"][0]
    parts = cand.get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts)
    if not text:
        raise ValueError(f"leere Antwort, finishReason={cand.get('finishReason')}")
    return text


def parse_json_output(text: str) -> dict:
    text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    return json.loads(text)


def flatten_lines(parsed: dict) -> list[str]:
    return [ln["text"] for pg in parsed.get("pages", []) for ln in pg.get("lines", [])]


def run_variant(key: str, item: dict, variant: str, fewshot: dict | None, force: bool) -> None:
    out = RESULTS / f"{item['id']}__{variant}.json"
    if out.exists() and not force:
        print(f"SKIP {out.name} (vorhanden)")
        return
    img_path = fetch_image(item["id"], item["iiif"])
    t0 = time.time()

    if variant == "v1_baseline":
        part, info = image_part(img_path)
        resp, model = call_gemini(key, [{"role": "user", "parts": [part, {"text": BASELINE_PROMPT}]}], json_mode=False)
        raw = extract_text(resp)
        record = {"raw_text": raw, "lines": [l for l in raw.splitlines() if l.strip()],
                  "parsed": None, "image_info": [info]}

    elif variant in ("v2_structured", "v5_repeat"):
        part, info = image_part(img_path)
        resp, model = call_gemini(key, [{"role": "user", "parts": [part, {"text": JSON_INSTRUCTION}]}], json_mode=True)
        parsed = parse_json_output(extract_text(resp))
        record = {"raw_text": None, "lines": flatten_lines(parsed), "parsed": parsed, "image_info": [info]}

    elif variant == "v3_fewshot":
        ex_path = fetch_image(fewshot["image_id"], fewshot["iiif"])
        ex_part, ex_info = image_part(ex_path)
        part, info = image_part(img_path)
        contents = [
            {"role": "user", "parts": [ex_part, {"text": JSON_INSTRUCTION}]},
            {"role": "model", "parts": [{"text": json.dumps(fewshot["answer"], ensure_ascii=False)}]},
            {"role": "user", "parts": [part, {"text": JSON_INSTRUCTION + " Folge exakt den Transkriptionskonventionen des Beispiels."}]},
        ]
        resp, model = call_gemini(key, contents, json_mode=True)
        parsed = parse_json_output(extract_text(resp))
        record = {"raw_text": None, "lines": flatten_lines(parsed), "parsed": parsed,
                  "image_info": [ex_info, info], "fewshot_source": fewshot["image_id"]}

    elif variant == "v6_enhanced":
        part, info = image_part(img_path, enhance=True)
        resp, model = call_gemini(key, [{"role": "user", "parts": [part, {"text": JSON_INSTRUCTION}]}], json_mode=True)
        parsed = parse_json_output(extract_text(resp))
        record = {"raw_text": None, "lines": flatten_lines(parsed), "parsed": parsed, "image_info": [info]}

    elif variant == "v4_split":
        halves, infos, models = [], [], []
        crops = ("left", "right") if item["spread"] else (None,)
        for crop in crops:
            part, info = image_part(img_path, crop=crop)
            label = {"left": " Dies ist die LINKE Hälfte einer Doppelseite.",
                     "right": " Dies ist die RECHTE Hälfte einer Doppelseite."}.get(crop, "")
            resp, model = call_gemini(key, [{"role": "user", "parts": [part, {"text": JSON_INSTRUCTION + label}]}], json_mode=True)
            halves.append(parse_json_output(extract_text(resp)))
            infos.append(info)
            models.append(model)
        merged = {"pages": [pg for h in halves for pg in h.get("pages", [])],
                  "notes": " | ".join(h.get("notes", "") for h in halves)}
        model = models[0]
        record = {"raw_text": None, "lines": flatten_lines(merged), "parsed": merged, "image_info": infos}
    else:
        raise ValueError(variant)

    record.update({
        "item": item["id"], "variant": variant, "model": model,
        "temperature": TEMPERATURE, "duration_s": round(time.time() - t0, 1),
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })
    RESULTS.mkdir(exist_ok=True)
    tmp = out.with_suffix(".tmp")
    tmp.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(out)
    print(f"OK {out.name} ({record['duration_s']}s, {len(record['lines'])} Zeilen, {model})")


def normalize(text: str, profile: str) -> str:
    """Symmetric normalization applied to hypothesis AND reference.

    Corpus-specific (Transkribus GT findings): drop [fol.Xr] foliation lines,
    merge the line-break marker U+00AC, unwrap (...) abbreviation expansions,
    and for 'fair' strip combining diacritics (GT is not NFC-normalized and
    carries U+0306/U+0303/U+0311 etc. no VLM reproduces reliably).
    """
    lines = [ln for ln in text.splitlines() if not re.match(r"^\s*\[fol\.?[^\]]*\]\s*$", ln)]
    text = " ".join(lines) if lines else text
    text = re.sub(r"\[fol\.?[^\]]*\]", "", text)
    text = text.replace("¬", "")
    text = unicodedata.normalize("NFC", text)
    if profile == "strict":
        return re.sub(r"\s+", " ", text).strip()
    # "fair": strip combining marks, unwrap (...), case-fold, u/v i/j collapse
    text = "".join(c for c in unicodedata.normalize("NFD", text) if not unicodedata.combining(c))
    text = re.sub(r"\(([^)]*)\)", r"\1", text)
    text = text.lower()
    text = re.sub(r"~~|\{|\}|\[\.*\]|\[---\]|\[|\]", "", text)
    text = text.replace("v", "u").replace("j", "i")
    text = re.sub(r"[^\w\s]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def cer(hyp: str, ref: str) -> float:
    return round(levenshtein(hyp, ref) / max(len(ref), 1), 4)


def word_overlap(hyp: str, ref: str) -> float:
    h, r = set(hyp.split()), set(ref.split())
    return round(len(h & r) / max(len(h | r), 1), 4)


def evaluate(items: list[dict]) -> dict:
    """CER vs GT where available; pairwise divergence between variants everywhere."""
    variants = ["v1_baseline", "v2_structured", "v3_fewshot", "v4_split", "v5_repeat", "v6_enhanced"]
    summary = {"items": {}, "generated": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    for item in items:
        texts = {}
        for v in variants:
            f = RESULTS / f"{item['id']}__{v}.json"
            if f.exists():
                texts[v] = "\n".join(json.loads(f.read_text(encoding="utf-8"))["lines"])
        entry = {"title": item["title"], "gt_lines": len(item["gt"]) if item["gt"] else None,
                 "cer": {}, "divergence": {}}
        if item["gt"]:
            ref = "\n".join(item["gt"])
            for v, hyp in texts.items():
                entry["cer"][v] = {
                    "strict": cer(normalize(hyp, "strict"), normalize(ref, "strict")),
                    "fair": cer(normalize(hyp, "fair"), normalize(ref, "fair")),
                    "word_overlap": word_overlap(normalize(hyp, "fair"), normalize(ref, "fair")),
                }
        pairs = [("v2_structured", "v5_repeat"), ("v2_structured", "v3_fewshot"), ("v2_structured", "v6_enhanced"),
                 ("v2_structured", "v4_split"), ("v1_baseline", "v2_structured")]
        for a, b in pairs:
            if a in texts and b in texts:
                entry["divergence"][f"{a}~{b}"] = {
                    "cer": cer(normalize(texts[a], "fair"), normalize(texts[b], "fair")),
                    "word_overlap": word_overlap(normalize(texts[a], "fair"), normalize(texts[b], "fair")),
                }
        summary["items"][item["id"]] = entry
    (RESULTS / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    return summary


def build_viewer_data(items: list[dict], summary: dict) -> None:
    """Bundle everything into results.js so viewer.html works from file://."""
    variants = ["v1_baseline", "v2_structured", "v3_fewshot", "v4_split", "v5_repeat", "v6_enhanced"]
    data = {"items": [], "summary": summary["items"], "generated": summary["generated"]}
    for item in items:
        rec = {"id": item["id"], "title": item["title"], "iiif": item["iiif"],
               "gt": item["gt"], "variants": {}}
        for v in variants:
            f = RESULTS / f"{item['id']}__{v}.json"
            if f.exists():
                d = json.loads(f.read_text(encoding="utf-8"))
                rec["variants"][v] = {"lines": d["lines"], "parsed": d["parsed"],
                                      "model": d["model"], "duration_s": d["duration_s"],
                                      "timestamp": d["timestamp"]}
        data["items"].append(rec)
    js = "window.RESULTS = " + json.dumps(data, ensure_ascii=False) + ";\n"
    (ROOT / "results.js").write_text(js, encoding="utf-8")
    print(f"OK results.js ({len(data['items'])} Items)")


def main() -> None:
    force = "--force" in sys.argv
    eval_only = "--eval" in sys.argv
    items = build_test_set()
    if "--fetch" in sys.argv:
        fs = fewshot_example()
        for item in items:
            fetch_image(item["id"], item["iiif"])
        fetch_image(fs["image_id"], fs["iiif"])
        print("OK alle Bilder geladen")
        return
    if not eval_only:
        key = load_api_key()
        fs = fewshot_example()
        errors = []
        for item in items:
            for variant in ["v1_baseline", "v2_structured", "v3_fewshot", "v4_split", "v5_repeat", "v6_enhanced"]:
                try:
                    run_variant(key, item, variant, fs, force)
                except Exception as e:  # skip-and-log-and-collect per item
                    print(f"FEHLER {item['id']}/{variant}: {e}", file=sys.stderr)
                    errors.append({"item": item["id"], "variant": variant, "error": str(e)})
        if errors:
            (RESULTS / "errors.json").write_text(json.dumps(errors, ensure_ascii=False, indent=1), encoding="utf-8")
    summary = evaluate(items)
    build_viewer_data(items, summary)
    for iid, e in summary["items"].items():
        if e["cer"]:
            print(f"\nCER {iid}:")
            for v, m in sorted(e["cer"].items()):
                print(f"  {v}: strict={m['strict']} fair={m['fair']} overlap={m['word_overlap']}")
    if not eval_only and errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
