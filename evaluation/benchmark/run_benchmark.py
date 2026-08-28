# /// script
# requires-python = ">=3.11"
# dependencies = ["requests", "pillow"]
# ///
"""HTR prompt benchmark runner: fixed page set, versioned prompt iterations.

The measurement rests on three properties. A run is split into two requests only
on a real double-page spread, consistency is measured positionwise rather than
as set overlap, and every record carries prompt provenance, meaning the
iteration id plus the SHA-256 of the exact prompt text.

Iterations:
  it01  frozen test-day config (v2_structured equivalent): it01 system prompt,
        full spread image, no few-shot. Baseline.
  it02  core + text-type prompt module, folio-split for raitbuch spreads,
        amount object in the schema, reworked few-shot for inventories
        (example answer shows non-empty uncertain fields and kind variety).
        The example marks words carrying a combining diacritic; where the page
        has none, as the configured one does, the longest word of the three
        longest-worded entry lines is marked instead, because an all-empty
        uncertain field was measured to suppress markers in the answer.

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
import difflib
import hashlib
import io
import json
import os
import re
import sys
import threading
import time
import unicodedata
from datetime import UTC, datetime
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
ATTEMPTS = 4
# A 49.5, inventar few-shot example. The document is in neither pages.json nor
# the page sets of pilot and pilot2, so no measured page has seen its own text.
FEWSHOT_DOC, FEWSHOT_PAGE = "11327964", 2

# Version id of the measuring instrument, written into every summary. A change to
# normalize(), to the token classification or to the agreement formula raises the
# version of every profile it touches, because summaries of different versions are
# not comparable. Frozen prompts and runs are unaffected by such a change.
# v2: numeral classification before the v/u collapse, all folio-marker spellings
# stripped, symmetric agreement (2026-08-28).
NORMALISATION_PROFILE = {"fair": "docta-fair-v2", "strict": "docta-strict-v2"}

# A fair-normalised reference below this length is a cover-label export of a page
# whose image carries a full text: every edit distance exceeds it and the CER then
# measures the reference, not the run. The threshold sits in a gap of an order of
# magnitude, the two flagged pages normalise to 30 and 38 characters and the
# shortest informative reference of the set to 1006.
DEGENERATE_REF_CHARS = 100

# Frozen it01 instruction; a change to the wording is a new iteration.
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
                        "lines": {
                            "type": "array",
                            "items": LINE_SCHEMA_AMOUNT
                            if with_amount
                            else LINE_SCHEMA_BASE,
                        },
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
        "it01": {
            "raitbuch2": it01,
            "inventar": it01,
            "instruction": IT01_INSTRUCTION,
            "amount": False,
        },
        "it02": {
            "raitbuch2": kern + "\n\n" + rb,
            "inventar": kern + "\n\n" + inv,
            "instruction": IT02_INSTRUCTION,
            "amount": True,
        },
    }


def resolve_pages() -> list[dict]:
    spec = json.loads((ROOT / "pages.json").read_text(encoding="utf-8"))["pages"]
    rb = {
        p["pageNr"]: p
        for p in json.loads(
            (REPO / "docs" / "data" / "raitbuch2_pages.json").read_text(
                encoding="utf-8"
            )
        )
    }
    docs: dict[str, dict] = {}
    for page in spec:
        if page["source"] == "raitbuch2":
            page["iiif"] = rb[page["pageNr"]]["iiif_url"]
            page["spread"] = True
        else:
            doc = docs.setdefault(
                page["docId"],
                json.loads(
                    (
                        REPO
                        / "docs"
                        / "data"
                        / "transcriptions"
                        / f"{page['docId']}.json"
                    ).read_text(encoding="utf-8")
                ),
            )
            p = next(x for x in doc["pages"] if x["pageNr"] == page["pageNr"])
            page["iiif"] = p["iiif"]
            page["spread"] = False
            if page.get("gt"):
                page["gt_lines"] = [
                    ln["text"] for r in p["regions"] for ln in r["lines"]
                ]
    return spec


def fewshot_example() -> dict:
    """Inventar few-shot example: kind heuristics plus uncertain markers on the
    diacritic-carrying words, so the example never demonstrates empty uncertainty."""
    doc = json.loads(
        (REPO / "docs" / "data" / "transcriptions" / f"{FEWSHOT_DOC}.json").read_text(
            encoding="utf-8"
        )
    )
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
            unc = [
                w
                for w in t.split()
                if any(
                    unicodedata.combining(c) for c in unicodedata.normalize("NFD", w)
                )
                or any(ch in w for ch in "ůẘ")
            ][:2]
            lines.append({"text": t, "kind": kind, "uncertain": unc})
    # The example must demonstrate a non-empty uncertain field (an empty one was
    # measured to suppress markers by ~60%); fall back to the rarest lexemes.
    if not any(ln["uncertain"] for ln in lines):
        entries = [
            ln for ln in lines if ln["kind"] == "entry" and len(ln["text"].split()) > 1
        ]
        for ln in sorted(
            entries, key=lambda x: -max(len(w) for w in x["text"].split())
        )[:3]:
            ln["uncertain"] = [max(ln["text"].split(), key=len)]
    answer = {
        "pages": [{"label": f"Seite {FEWSHOT_PAGE}", "empty": False, "lines": lines}],
        "notes": "Fachwissenschaftliche Referenztranskription (Transkribus).",
    }
    return {
        "iiif": p["iiif"],
        "answer": answer,
        "image_id": f"fewshot_{FEWSHOT_DOC}_p{FEWSHOT_PAGE}",
    }


def fewshot_hash(fs: dict) -> str:
    """Digest of the few-shot answer exactly as it goes into the request.

    The block is assembled at runtime from the Transkribus export instead of being
    frozen in a prompt document, so `prompt_hash` does not cover it; a run that
    used it pins it here.
    """
    payload = json.dumps(fs["answer"], ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


_fetch_lock = threading.Lock()


def fetch_image(image_id: str, url: str) -> Path:
    """Thread-safe: workers race on the same page image (repeats), so the
    download runs under a lock and the tmp name is unique per thread."""
    IMAGES.mkdir(exist_ok=True)
    path = IMAGES / f"{image_id}.jpg"
    with _fetch_lock:
        if path.exists():
            return path
        r = requests.get(
            url,
            timeout=180,
            headers={"User-Agent": "DoCTA-benchmark (office@dhcraft.org)"},
        )
        r.raise_for_status()
        tmp = path.with_suffix(f".tmp{os.getpid()}_{threading.get_ident()}")
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
    return (
        {
            "inline_data": {
                "mime_type": "image/jpeg",
                "data": base64.b64encode(buf.getvalue()).decode(),
            }
        },
        {"source_px": list(orig), "sent_px": list(img.size), "crop": crop},
    )


def call_gemini(key: str, system: str, contents: list, with_amount: bool) -> dict:
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": contents,
        "generationConfig": {
            "temperature": TEMPERATURE,
            "maxOutputTokens": 32768,
            "responseMimeType": "application/json",
            "responseSchema": response_schema(with_amount),
        },
    }
    last_reason = "keine Antwort"
    for attempt in range(ATTEMPTS):
        # backoff only between attempts; after the last one the caller gives up anyway
        backoff = 2 ** (attempt + 2) if attempt < ATTEMPTS - 1 else 0
        r = requests.post(
            f"{API_BASE}/{MODEL}:generateContent",
            headers={"x-goog-api-key": key, "Content-Type": "application/json"},
            json=body,
            timeout=TIMEOUT,
        )
        if r.status_code in (429, 500, 503):
            last_reason = f"HTTP {r.status_code}"
            time.sleep(backoff)
            continue
        r.raise_for_status()
        data = r.json()
        cands = data.get("candidates")
        if not cands:
            last_reason = data.get("promptFeedback", {}).get(
                "blockReason", "no candidates"
            )
            time.sleep(backoff)
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


def run_one(
    key: str, page: dict, iteration: str, prompts: dict, repeat: int, fs: dict
) -> str:
    out = RUNS / f"{page['id']}__{iteration}__r{repeat}.json"
    if out.exists():
        return f"SKIP {out.name}"
    cfg = prompts[iteration]
    system = cfg[page["source"]]
    uses_fewshot = iteration == "it02" and page["source"] == "inventar"
    img_path = fetch_image(page["id"], page["iiif"])
    t0 = time.time()
    parsed_pages, infos = [], []
    # it02 default: one folio per request on real spreads (smaller field of view wins)
    crops = ("left", "right") if (iteration == "it02" and page["spread"]) else (None,)
    for crop in crops:
        part, info = image_part(img_path, crop=crop)
        label = {
            "left": " Dies ist die LINKE Hälfte einer Doppelseite (verso).",
            "right": " Dies ist die RECHTE Hälfte einer Doppelseite (recto).",
        }.get(crop, "")
        contents = []
        if uses_fewshot:
            ex_part, _ = image_part(fetch_image(fs["image_id"], fs["iiif"]))
            contents += [
                {"role": "user", "parts": [ex_part, {"text": cfg["instruction"]}]},
                {
                    "role": "model",
                    "parts": [{"text": json.dumps(fs["answer"], ensure_ascii=False)}],
                },
            ]
        contents.append(
            {"role": "user", "parts": [part, {"text": cfg["instruction"] + label}]}
        )
        parsed = call_gemini(key, system, contents, cfg["amount"])
        parsed_pages += parsed.get("pages", [])
        infos.append(info)
    merged = {"pages": parsed_pages}
    record = {
        "page": page["id"],
        "iteration": iteration,
        "repeat": repeat,
        "model": MODEL,
        "temperature": TEMPERATURE,
        "prompt_hash": hashlib.sha256(
            (system + cfg["instruction"]).encode()
        ).hexdigest()[:16],
        "fewshot": uses_fewshot,
        "fewshot_hash": fewshot_hash(fs) if uses_fewshot else None,
        "image_info": infos,
        "duration_s": round(time.time() - t0, 1),
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        "parsed": merged,
        "lines": [ln["text"] for pg in parsed_pages for ln in pg.get("lines", [])],
    }
    RUNS.mkdir(exist_ok=True)
    # process- and thread-unique tmp name, and a last existence check, so a
    # concurrent runner never replaces a finished run with a half-written one
    tmp = out.with_suffix(f".tmp{os.getpid()}_{threading.get_ident()}")
    tmp.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
    if out.exists():
        tmp.unlink()
        return f"SKIP {out.name}"
    tmp.replace(out)
    return f"OK {out.name} ({record['duration_s']}s, {len(record['lines'])} Zeilen)"


# ---------- Evaluation ----------

UNITS = {
    "gld",
    "rhgld",
    "lb",
    "tt",
    "ß",
    "d",
    "kr",
    "hl",
    "m",
    "marck",
    "mark",
    "fl",
    "pfd",
}


# Every folio-marker spelling the exports carry. Beside the long [fol.1r] the
# Inventaria transcriptions use the short [1r]/[1v] and, once mid-reference in
# inv_11328300_p2, the malformed 2[r] with the leaf number outside the bracket.
# All of them are page furniture and are stripped from reference and hypothesis
# alike; a marker left in on one side alone is counted as a transcription error.
# The alternatives are narrow on purpose: [...] and [---], which mark content a
# run lost, and a bracketed expansion inside a word (sup[r]a, unnse[r], It[em])
# must survive untouched, so the two short forms have to stand as their own
# whitespace-delimited token.
FOLIO_MARKER = (
    r"\[\s*fol\.?[^\]]*\]"  # [fol.1r], [fol. 7r], [fol.]
    r"|(?<!\S)\[\s*\d+\s*[rv]?\s*\](?!\S)"  # [1r], [12v], [3]
    r"|(?<!\S)\d+\s*\[\s*[rv]\s*\](?!\S)"  # 2[r], leaf number outside the bracket
)
FOLIO_MARKER_RE = re.compile(FOLIO_MARKER, re.IGNORECASE)
FOLIO_LINE_RE = re.compile(rf"^\s*(?:{FOLIO_MARKER})\s*$", re.IGNORECASE)


def normalize(text: str, profile: str) -> str:
    """Three profiles. `strict` keeps the characters as transcribed, `fair`
    additionally collapses v/u and j/i for the CER, and `fair-raw` stops right
    before that collapse. `fair-raw` exists for token classification, because the
    collapse turns every Roman numeral carrying a v or j (vij, xxv) into a letter
    string no numeral pattern matches. Both fair variants split into the same
    tokens, the collapse maps letter to letter and touches no whitespace.

    Folio markers are removed in every profile, before the branch, so the two CER
    profiles see the same page furniture removed."""
    lines = [ln for ln in text.splitlines() if not FOLIO_LINE_RE.match(ln)]
    text = " ".join(lines) if lines else text
    text = FOLIO_MARKER_RE.sub("", text).replace("¬", "")
    text = unicodedata.normalize("NFC", text)
    if profile == "strict":
        return re.sub(r"\s+", " ", text).strip()
    text = "".join(
        c for c in unicodedata.normalize("NFD", text) if not unicodedata.combining(c)
    )
    text = re.sub(r"\(([^)]*)\)", r"\1", text).lower()
    text = re.sub(r"~~|\{|\}|\[\.*\]|\[---\]|\[|\]", "", text)
    if profile == "fair":
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
    """Expects a `fair-raw` token, where `j` is still the final-`i` variant of a
    Roman numeral and `v` is still `v`."""
    t = tok.lower().strip("^°")
    return bool(re.fullmatch(r"[ivxlcdmj]+|\d+", t)) or t in UNITS or "^" in tok


def positionwise(
    a: list[str], b: list[str], a_raw: list[str], b_raw: list[str]
) -> tuple[float | None, float | None]:
    """Symmetric aligned token agreement, split word vs number/currency.

    Agreement per class is 2*matches/(|a| + |b|) over the tokens of that class,
    the Dice form, so agreement(a, b) equals agreement(b, a). Taking both
    denominators from the first repeat, as this did before 2026-08-28, made the
    value a recall against whichever repeat happened to come first.

    Alignment runs on the fair tokens `a` and `b`, classification on `a_raw` and
    `b_raw`, the same tokens before the v/u collapse; positions correspond,
    each pair comes from one text. A matched pair counts for a class only where
    both sides carry that class, so no numerator can exceed its denominator. A
    class with no tokens on either side yields None rather than zero, because a
    page carrying no numeral is not a page whose numerals disagree; two empty
    repeats agree.
    """
    # Equal denominators are not enough for symmetry: difflib picks one of several
    # equally long alignments and the choice depends on argument order, which moves
    # matched positions between the two classes. Orienting the pair deterministically
    # before alignment is what makes agreement(a, b) and agreement(b, a) one value.
    if (len(a), a) > (len(b), b):
        a, b, a_raw, b_raw = b, a, b_raw, a_raw
    num_a = [is_numberish(tok) for tok in a_raw]
    num_b = [is_numberish(tok) for tok in b_raw]
    tot_n = sum(num_a) + sum(num_b)
    tot_w = (len(num_a) - sum(num_a)) + (len(num_b) - sum(num_b))
    eq_w = eq_n = 0
    for blk in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_matching_blocks():
        for k in range(blk.size):
            hit_a, hit_b = num_a[blk.a + k], num_b[blk.b + k]
            if hit_a and hit_b:
                eq_n += 1
            elif not hit_a and not hit_b:
                eq_w += 1
    # two empty repeats agree; any other class without tokens has nothing to say
    words = round(2 * eq_w / tot_w, 3) if tot_w else (1.0 if not a and not b else None)
    return (words, round(2 * eq_n / tot_n, 3) if tot_n else None)


def mean_defined(values: list[float | None]) -> float | None:
    """Mean over the pairs where the metric is defined, None where none is."""
    seen = [v for v in values if v is not None]
    return round(sum(seen) / len(seen), 3) if seen else None


def evaluate(pages: list[dict], iterations: list[str]) -> dict:
    summary = {
        "generated": datetime.now(UTC).isoformat(timespec="seconds"),
        "model": MODEL,
        "temperature": TEMPERATURE,
        "normalisation_profile": NORMALISATION_PROFILE,
        "pages": {},
    }
    for page in pages:
        reference = "\n".join(page.get("gt_lines") or [])
        entry: dict = {
            "folio": page["folio"],
            "phenomena": page["phenomena"],
            "source": page["source"],
            "iiif": page["iiif"],
            "spread": page["spread"],
            # what the page is measured against at all: a formal Transkribus-DONE
            # transcription, or nothing but the agreement of its own repeats
            "reference_class": "transkribus-done"
            if page.get("gt_lines")
            else "self-consistency",
            "iterations": {},
        }
        if page.get("gt_lines"):
            entry["gt_lines"] = page["gt_lines"]
            # the criterion of the exclusion, persisted beside its input, so a
            # consumer excludes by this property and never by a measured CER
            entry["reference_chars"] = len(normalize(reference, "fair"))
            entry["reference_degenerate"] = (
                entry["reference_chars"] < DEGENERATE_REF_CHARS
            )
        for it in iterations:
            runs = sorted(
                RUNS.glob(f"{page['id']}__{it}__r*.json"),
                key=lambda p: int(p.stem.rsplit("__r", 1)[1]),
            )
            if not runs:
                continue
            recs = [json.loads(f.read_text(encoding="utf-8")) for f in runs]
            texts = ["\n".join(r["lines"]) for r in recs]
            e: dict = {
                "k": len(recs),
                "runs": [f.name for f in runs],
                "lines": [len(r["lines"]) for r in recs],
                # one flag per image part, so a spread reports verso and recto
                "empty_parts": [
                    [pg.get("empty") is True for pg in r["parsed"]["pages"]]
                    for r in recs
                ],
                "empty": [
                    bool(r["parsed"]["pages"])
                    and all(pg.get("empty") is True for pg in r["parsed"]["pages"])
                    for r in recs
                ],
                "uncertain": [
                    sum(
                        len(ln.get("uncertain", []) or [])
                        for pg in r["parsed"]["pages"]
                        for ln in pg.get("lines", [])
                    )
                    for r in recs
                ],
            }
            if page.get("gt_lines"):
                # dist and ref_len travel with the rate, so a reader can see what
                # a CER above one rests on without recomputing the normalisation
                for field, profile in (("cer_fair", "fair"), ("cer_strict", "strict")):
                    ref_norm = normalize(reference, profile)
                    dist = [levenshtein(normalize(t, profile), ref_norm) for t in texts]
                    rates = [round(d / max(len(ref_norm), 1), 4) for d in dist]
                    e[field] = {
                        "mean": round(sum(rates) / len(rates), 4),
                        "min": min(rates),
                        "max": max(rates),
                        "dist": dist,
                        "ref_len": len(ref_norm),
                    }
            toks = [normalize(t, "fair").split() for t in texts]
            raw = [normalize(t, "fair-raw").split() for t in texts]
            pairs = [(i, j) for i in range(len(toks)) for j in range(i + 1, len(toks))]
            if pairs:
                agr = [positionwise(toks[i], toks[j], raw[i], raw[j]) for i, j in pairs]
                e["consistency_words"] = mean_defined([w for w, _ in agr])
                e["consistency_numbers"] = mean_defined([n for _, n in agr])
            entry["iterations"][it] = e
        summary["pages"][page["id"]] = entry
    (ROOT / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return summary


def newest_run_timestamp() -> str | None:
    """Timestamp of the newest run record on disk. Artifacts are dated from the
    data, never from the clock, so a rewrite without new runs stays identical."""
    stamps = [
        json.loads(path.read_text(encoding="utf-8")).get("timestamp")
        for path in RUNS.glob("*.json")
    ]
    return max((s for s in stamps if s), default=None)


def parse_only(argv: list[str], known: list[str]) -> str | None:
    """Iteration named by `--only`, exiting when the value is missing or unknown."""
    if "--only" not in argv:
        return None
    index = argv.index("--only") + 1
    if index >= len(argv):
        sys.exit(f"FEHLER: --only braucht eine Iteration ({', '.join(known)})")
    name = argv[index]
    if name not in known:
        sys.exit(f"FEHLER: unbekannte Iteration {name!r} (bekannt: {', '.join(known)})")
    return name


def main() -> None:
    eval_only = "--eval" in sys.argv
    prompts = build_prompts()
    only = parse_only(sys.argv, list(prompts))
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
            futs = {
                ex.submit(run_one, key, p, it, prompts, r, fs): (p["id"], it, r)
                for p, it, r in jobs
            }
            for fut in concurrent.futures.as_completed(futs):
                pid, it, r = futs[fut]
                try:
                    print(fut.result())
                except Exception as e:
                    print(f"FEHLER {pid}/{it}/r{r}: {e}", file=sys.stderr)
                    errors.append(
                        {"page": pid, "iteration": it, "repeat": r, "error": str(e)}
                    )
        # always written, so a blockage cleared by a later fill does not linger
        stamp = newest_run_timestamp()
        report: dict = {}
        if stamp is not None:
            report["run_timestamp"] = stamp
        report["errors"] = errors
        (ROOT / "errors.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8"
        )
    # --only limits which runs are produced; the summary always covers every
    # iteration, otherwise a partial fill would drop the others from summary.json
    summary = evaluate(pages, list(prompts))
    print("\n== Zusammenfassung (GT-Seiten) ==")
    for pid, e in summary["pages"].items():
        for it, m in e["iterations"].items():
            if "cer_fair" in m:
                print(
                    f"{pid} {it}: fair {m['cer_fair']['mean']} ({m['cer_fair']['min']}-{m['cer_fair']['max']}) "
                    f"konsistenz w={m.get('consistency_words')} n={m.get('consistency_numbers')}"
                )
    print("\n== Konsistenz (Seiten ohne GT) ==")
    for pid, e in summary["pages"].items():
        for it, m in e["iterations"].items():
            if "cer_fair" not in m:
                print(
                    f"{pid} {it}: w={m.get('consistency_words')} n={m.get('consistency_numbers')} "
                    f"zeilen={m['lines']} uncertain={m['uncertain']}"
                )


if __name__ == "__main__":
    main()
