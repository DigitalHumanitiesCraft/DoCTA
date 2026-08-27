# /// script
# requires-python = ">=3.11"
# dependencies = ["requests", "pillow"]
# ///
"""HTR prompt benchmark runner: fixed page set, versioned prompt iterations.

Ports the API/image/normalization core from ../transcription-test/transcribe_test.py
and fixes its three known defects: split runs only on real double-page spreads,
consistency is measured positionwise (not set-Jaccard), and every record carries
prompt provenance (iteration id + SHA-256 of the exact prompt text).

Iterations:
  it01  frozen test-day config (v2_structured equivalent): it01 system prompt,
        full spread image, no few-shot. Baseline.
  it02  core + text-type prompt module, folio-split for raitbuch spreads,
        amount object in the schema, reworked few-shot for inventories
        (example answer shows non-empty uncertain fields and kind variety;
        uncertain in the example = words carrying combining diacritics).

Repeats: k=5 on pages with formal Transkribus-DONE ground truth, k=3 otherwise
(identical requests at temperature 0 were measured to spread by 5.5 CER points).
Runs are never overwritten; delete nothing, add iterations instead.

Usage:
  python run_benchmark.py            # run all missing (page x iteration x repeat)
  python run_benchmark.py --eval     # only recompute evaluation
  python run_benchmark.py --only it02  # limit to one iteration
"""

import base64
import concurrent.futures
import hashlib
import io
import json
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import requests
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent
REPO = ROOT.parent.parent
IMAGES = ROOT / "images"
RUNS = ROOT / "runs"

MODEL = "gemini-3.7-flash"
API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
MAX_SIDE = 3500
TEMPERATURE = 0.0
TIMEOUT = 300
WORKERS = 4
FEWSHOT_DOC, FEWSHOT_PAGE = "11327964", 2  # A 49.5, inventar few-shot example

# Frozen it01 instruction (identical to the 2026-08-26 test run).
IT01_INSTRUCTION = (
    "Transkribiere das Bild vollständig. Antworte als JSON nach dem Schema. "
    "Bei einer Doppelseite zuerst die linke Seite (verso), dann die rechte (recto), "
    'als getrennte Einträge in "pages". "kind" pro Zeile: "rubric" für rubrizierte '
    'Überschriften/Namen, "entry" für Posten- und Fließtextzeilen, "amount" für reine '
    'Zahlen-/Betragszeilen, "sum" für Summenzeilen, "marginal" für Marginalien, '
    '"foliation" für Blattzählung.'
)
IT02_INSTRUCTION = (
    "Transkribiere das Bild vollständig. Antworte als JSON nach dem Schema. "
    'Jede Handschriftzeile ein Eintrag in "lines". "kind" pro Zeile: "rubric" '
    '(Auszeichnungsschrift/Überschrift), "entry", "amount", "sum", "marginal", '
    '"foliation". Zeilen mit Geldbetrag füllen zusätzlich das "amount"-Objekt.'
)

LINE_SCHEMA_BASE = {
    "type": "object",
    "properties": {
        "text": {"type": "string"},
        "kind": {"type": "string"},
        "uncertain": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["text", "kind"],
}
LINE_SCHEMA_AMOUNT = {
    "type": "object",
    "properties": {
        **LINE_SCHEMA_BASE["properties"],
        "amount": {
            "type": "object",
            "properties": {
                "multiplier": {"type": "string"},
                "numeral": {"type": "string"},
                "unit": {"type": "string"},
            },
        },
    },
    "required": ["text", "kind"],
}


def response_schema(with_amount: bool) -> dict:
    return {
        "type": "object",
        "properties": {
            "pages": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string"},
                        "empty": {"type": "boolean"},
                        "lines": {"type": "array",
                                  "items": LINE_SCHEMA_AMOUNT if with_amount else LINE_SCHEMA_BASE},
                    },
                    "required": ["label", "lines"],
                },
            },
            "notes": {"type": "string"},
        },
        "required": ["pages"],
    }


def load_api_key() -> str:
    env = REPO / ".env"
    for line in env.read_text(encoding="utf-8").splitlines():
        if line.startswith("GEMINI_API_KEY="):
            return line.split("=", 1)[1].strip()
    sys.exit("FEHLER: GEMINI_API_KEY nicht in .env gefunden")


def extract_prompt(md_path: Path) -> str:
    """A prompt document's payload is its first fenced code block."""
    m = re.search(r"```\n(.*?)\n```", md_path.read_text(encoding="utf-8"), re.DOTALL)
    if not m:
        sys.exit(f"FEHLER: kein Codeblock in {md_path.name}")
    return m.group(1)


def build_prompts() -> dict:
    it01 = extract_prompt(ROOT / "prompts" / "it01_system.md")
    kern = extract_prompt(ROOT / "prompts" / "it02_kern.md")
    rb = extract_prompt(ROOT / "prompts" / "it02_raitbuch.md")
    inv = extract_prompt(ROOT / "prompts" / "it02_inventar.md")
    return {
        "it01": {"raitbuch2": it01, "inventar": it01, "instruction": IT01_INSTRUCTION, "amount": False},
        "it02": {"raitbuch2": kern + "\n\n" + rb, "inventar": kern + "\n\n" + inv,
                 "instruction": IT02_INSTRUCTION, "amount": True},
    }


def resolve_pages() -> list[dict]:
    spec = json.loads((ROOT / "pages.json").read_text(encoding="utf-8"))["pages"]
    rb = {p["pageNr"]: p for p in json.loads(
        (REPO / "docs" / "data" / "raitbuch2_pages.json").read_text(encoding="utf-8"))}
    docs: dict[str, dict] = {}
    for page in spec:
        if page["source"] == "raitbuch2":
            page["iiif"] = rb[page["pageNr"]]["iiif_url"]
            page["spread"] = True
        else:
            doc = docs.setdefault(page["docId"], json.loads(
                (REPO / "docs" / "data" / "transcriptions" / f"{page['docId']}.json").read_text(encoding="utf-8")))
            p = next(x for x in doc["pages"] if x["pageNr"] == page["pageNr"])
            page["iiif"] = p["iiif"]
            page["spread"] = False
            if page.get("gt"):
                page["gt_lines"] = [ln["text"] for r in p["regions"] for ln in r["lines"]]
    return spec


def fewshot_example() -> dict:
    """Reworked inventar example: kind heuristics + uncertain for diacritic-carrying
    words, so the example demonstrates non-empty uncertainty instead of silencing it."""
    doc = json.loads((REPO / "docs" / "data" / "transcriptions" / f"{FEWSHOT_DOC}.json").read_text(encoding="utf-8"))
    p = next(x for x in doc["pages"] if x["pageNr"] == FEWSHOT_PAGE)
    lines = []
    for r in p["regions"]:
        for ln in r["lines"]:
            t = ln["text"]
            if re.match(r"^\s*\[fol", t):
                kind = "foliation"
            elif re.match(r"^\s*(In |Auf |An |Vor )", t) and len(t.split()) <= 6:
                kind = "rubric"
            else:
                kind = "entry"
            unc = [w for w in t.split()
                   if any(unicodedata.combining(c) for c in unicodedata.normalize("NFD", w))
                   or any(ch in w for ch in "ůw̋ẘ")][:2]
            lines.append({"text": t, "kind": kind, "uncertain": unc})
    # The example must demonstrate a non-empty uncertain field (an empty one was
    # measured to suppress markers by ~60%); fall back to the rarest lexemes.
    if not any(ln["uncertain"] for ln in lines):
        entries = [ln for ln in lines if ln["kind"] == "entry" and len(ln["text"].split()) > 1]
        for ln in sorted(entries, key=lambda x: -max(len(w) for w in x["text"].split()))[:3]:
            ln["uncertain"] = [max(ln["text"].split(), key=len)]
    answer = {"pages": [{"label": f"Seite {FEWSHOT_PAGE}", "empty": False, "lines": lines}],
              "notes": "Fachwissenschaftliche Referenztranskription (Transkribus)."}
    return {"iiif": p["iiif"], "answer": answer, "image_id": f"fewshot_{FEWSHOT_DOC}_p{FEWSHOT_PAGE}"}


_fetch_lock = __import__("threading").Lock()


def fetch_image(image_id: str, url: str) -> Path:
    """Thread-safe: workers race on the same page image (repeats), so the
    download runs under a lock and the tmp name is unique per thread."""
    IMAGES.mkdir(exist_ok=True)
    path = IMAGES / f"{image_id}.jpg"
    with _fetch_lock:
        if path.exists():
            return path
        r = requests.get(url, timeout=180, headers={"User-Agent": "DoCTA-benchmark (office@dhcraft.org)"})
        r.raise_for_status()
        tmp = path.with_suffix(f".tmp{__import__('threading').get_ident()}")
        tmp.write_bytes(r.content)
        tmp.replace(path)
    return path


def image_part(path: Path, crop: str | None = None) -> tuple[dict, dict]:
    img = Image.open(path)
    orig = img.size
    if crop == "left":
        img = img.crop((0, 0, img.width // 2, img.height))
    elif crop == "right":
        img = img.crop((img.width // 2, 0, img.width, img.height))
    if max(img.size) > MAX_SIDE:
        s = MAX_SIDE / max(img.size)
        img = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=90)
    return ({"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(buf.getvalue()).decode()}},
            {"source_px": list(orig), "sent_px": list(img.size), "crop": crop})


def call_gemini(key: str, system: str, contents: list, with_amount: bool) -> dict:
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": contents,
        "generationConfig": {"temperature": TEMPERATURE, "maxOutputTokens": 32768,
                             "responseMimeType": "application/json",
                             "responseSchema": response_schema(with_amount)},
    }
    last_reason = "HTTP"
    for attempt in range(4):
        r = requests.post(f"{API_BASE}/{MODEL}:generateContent",
                          headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                          json=body, timeout=TIMEOUT)
        if r.status_code in (429, 500, 503):
            time.sleep(2 ** (attempt + 2))
            continue
        r.raise_for_status()
        data = r.json()
        cands = data.get("candidates")
        if not cands:
            # No candidate at all (e.g. prompt blocked or transient empty response); retry.
            last_reason = data.get("promptFeedback", {}).get("blockReason", "no candidates")
            time.sleep(2 ** (attempt + 2))
            continue
        cand = cands[0]
        text = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []))
        if not text:
            raise ValueError(f"leere Antwort, finishReason={cand.get('finishReason')}")
        return json.loads(re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip())
    raise RuntimeError(f"Retries erschöpft ({last_reason})")


def run_one(key: str, page: dict, iteration: str, prompts: dict, repeat: int, fs: dict) -> str:
    out = RUNS / f"{page['id']}__{iteration}__r{repeat}.json"
    if out.exists():
        return f"SKIP {out.name}"
    cfg = prompts[iteration]
    system = cfg[page["source"]]
    img_path = fetch_image(page["id"], page["iiif"])
    t0 = time.time()
    parsed_pages, infos = [], []
    # it02 default: one folio per request on real spreads (smaller field of view wins)
    crops = ("left", "right") if (iteration == "it02" and page["spread"]) else (None,)
    for crop in crops:
        part, info = image_part(img_path, crop=crop)
        label = {"left": " Dies ist die LINKE Hälfte einer Doppelseite (verso).",
                 "right": " Dies ist die RECHTE Hälfte einer Doppelseite (recto)."}.get(crop, "")
        contents = []
        if iteration == "it02" and page["source"] == "inventar":
            ex_part, _ = image_part(fetch_image(fs["image_id"], fs["iiif"]))
            contents += [{"role": "user", "parts": [ex_part, {"text": cfg["instruction"]}]},
                         {"role": "model", "parts": [{"text": json.dumps(fs["answer"], ensure_ascii=False)}]}]
        contents.append({"role": "user", "parts": [part, {"text": cfg["instruction"] + label}]})
        parsed = call_gemini(key, system, contents, cfg["amount"])
        parsed_pages += parsed.get("pages", [])
        infos.append(info)
    merged = {"pages": parsed_pages}
    record = {
        "page": page["id"], "iteration": iteration, "repeat": repeat,
        "model": MODEL, "temperature": TEMPERATURE,
        "prompt_hash": hashlib.sha256((system + cfg["instruction"]).encode()).hexdigest()[:16],
        "fewshot": iteration == "it02" and page["source"] == "inventar",
        "image_info": infos, "duration_s": round(time.time() - t0, 1),
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "parsed": merged,
        "lines": [ln["text"] for pg in parsed_pages for ln in pg.get("lines", [])],
    }
    RUNS.mkdir(exist_ok=True)
    tmp = out.with_suffix(".tmp")
    tmp.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(out)
    return f"OK {out.name} ({record['duration_s']}s, {len(record['lines'])} Zeilen)"


# ---------- Evaluation ----------

UNITS = {"gld", "rhgld", "lb", "tt", "ß", "d", "kr", "hl", "m", "marck", "mark", "fl", "pfd"}


def normalize(text: str, profile: str) -> str:
    lines = [ln for ln in text.splitlines() if not re.match(r"^\s*\[fol\.?[^\]]*\]\s*$", ln)]
    text = " ".join(lines) if lines else text
    text = re.sub(r"\[fol\.?[^\]]*\]", "", text).replace("¬", "")
    text = unicodedata.normalize("NFC", text)
    if profile == "strict":
        return re.sub(r"\s+", " ", text).strip()
    text = "".join(c for c in unicodedata.normalize("NFD", text) if not unicodedata.combining(c))
    text = re.sub(r"\(([^)]*)\)", r"\1", text).lower()
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


def is_numberish(tok: str) -> bool:
    t = tok.lower().strip("^°")
    return bool(re.fullmatch(r"[ivxlcdm]+|\d+", t)) or t in UNITS or "^" in tok


def positionwise(a: list[str], b: list[str]) -> tuple[float, float]:
    """Aligned token agreement via SequenceMatcher, split word vs number/currency."""
    import difflib
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    eq_w = eq_n = tot_w = tot_n = 0
    for tok in a:
        if is_numberish(tok):
            tot_n += 1
        else:
            tot_w += 1
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            tok = a[blk.a + k]
            if is_numberish(tok):
                eq_n += 1
            else:
                eq_w += 1
    return (round(eq_w / max(tot_w, 1), 3), round(eq_n / max(tot_n, 1), 3))


def evaluate(pages: list[dict], iterations: list[str]) -> dict:
    summary = {"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "model": MODEL, "pages": {}}
    for page in pages:
        entry: dict = {"folio": page["folio"], "phenomena": page["phenomena"],
                       "source": page["source"], "iiif": page["iiif"], "spread": page["spread"],
                       "iterations": {}}
        if page.get("gt_lines"):
            entry["gt_lines"] = page["gt_lines"]
        for it in iterations:
            runs = sorted(RUNS.glob(f"{page['id']}__{it}__r*.json"))
            if not runs:
                continue
            recs = [json.loads(f.read_text(encoding="utf-8")) for f in runs]
            texts = ["\n".join(r["lines"]) for r in recs]
            e: dict = {"k": len(recs), "runs": [f.name for f in runs],
                       "lines": [len(r["lines"]) for r in recs],
                       "uncertain": [sum(len(ln.get("uncertain", []) or [])
                                          for pg in r["parsed"]["pages"] for ln in pg.get("lines", []))
                                      for r in recs]}
            if page.get("gt_lines"):
                ref = "\n".join(page["gt_lines"])
                fair = [cer(normalize(t, "fair"), normalize(ref, "fair")) for t in texts]
                strict = [cer(normalize(t, "strict"), normalize(ref, "strict")) for t in texts]
                e["cer_fair"] = {"mean": round(sum(fair) / len(fair), 4), "min": min(fair), "max": max(fair)}
                e["cer_strict"] = {"mean": round(sum(strict) / len(strict), 4), "min": min(strict), "max": max(strict)}
            toks = [normalize(t, "fair").split() for t in texts]
            pairs = [(i, j) for i in range(len(toks)) for j in range(i + 1, len(toks))]
            if pairs:
                agr = [positionwise(toks[i], toks[j]) for i, j in pairs]
                e["consistency_words"] = round(sum(a for a, _ in agr) / len(agr), 3)
                e["consistency_numbers"] = round(sum(b for _, b in agr) / len(agr), 3)
            entry["iterations"][it] = e
        summary["pages"][page["id"]] = entry
    (ROOT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    return summary


def main() -> None:
    eval_only = "--eval" in sys.argv
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    prompts = build_prompts()
    iterations = [only] if only else list(prompts)
    pages = resolve_pages()
    if not eval_only:
        key = load_api_key()
        fs = fewshot_example()
        jobs = []
        for page in pages:
            k = 5 if page.get("gt") else 3
            for it in iterations:
                for r in range(1, k + 1):
                    jobs.append((page, it, r))
        print(f"{len(jobs)} Läufe geplant ({len(pages)} Seiten × {iterations} × k)")
        errors = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
            futs = {ex.submit(run_one, key, p, it, prompts, r, fs): (p["id"], it, r) for p, it, r in jobs}
            for fut in concurrent.futures.as_completed(futs):
                pid, it, r = futs[fut]
                try:
                    print(fut.result())
                except Exception as e:  # skip-and-log-and-collect
                    print(f"FEHLER {pid}/{it}/r{r}: {e}", file=sys.stderr)
                    errors.append({"page": pid, "iteration": it, "repeat": r, "error": str(e)})
        if errors:
            (ROOT / "errors.json").write_text(json.dumps(errors, ensure_ascii=False, indent=1), encoding="utf-8")
    summary = evaluate(pages, ["it01", "it02"])
    print("\n== Zusammenfassung (GT-Seiten) ==")
    for pid, e in summary["pages"].items():
        for it, m in e["iterations"].items():
            if "cer_fair" in m:
                print(f"{pid} {it}: fair {m['cer_fair']['mean']} ({m['cer_fair']['min']}-{m['cer_fair']['max']}) "
                      f"konsistenz w={m.get('consistency_words')} n={m.get('consistency_numbers')}")
    print("\n== Konsistenz (Seiten ohne GT) ==")
    for pid, e in summary["pages"].items():
        for it, m in e["iterations"].items():
            if "cer_fair" not in m:
                print(f"{pid} {it}: w={m.get('consistency_words')} n={m.get('consistency_numbers')} "
                      f"zeilen={m['lines']} uncertain={m['uncertain']}")


if __name__ == "__main__":
    main()
