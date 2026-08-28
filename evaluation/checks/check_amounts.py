# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Deterministic arithmetic validation of Raitbuch transcriptions.

An account book carries its own referenceless quality signal: the item amounts of a
block must add up to the block's Summa line. Where one repeat's arithmetic goes
through and the other's does not, the arithmetic points at the better run without any
ground truth. The visual referee review (evaluation/pilot2/review/raitbuch.md)
verified two such cases by image, 300+700+694=1694 on p025 verso and 1220+67=1287 on
p030 recto, and in both the arithmetic picked the run the image confirms.

This module parses the amount notation of the Early New High German account book,
groups a page's amount lines into blocks, and checks each block against its Summa.

Supported notation
------------------
Values are lowercase Roman numerals with `j` as the final-`i` variant, written
additively as well as subtractively: `iiij` = 4, `xl` = 40, `lxxxxiiij` = 94,
`cccc xxvij` = 427. Consecutive Roman tokens accumulate additively (`c l iiij` = 154).

Two multiplier marks scale the immediately preceding Roman group:

* `C`, `c`, `ᶜ`, `^C` and forms attached to the group (`iiijC`, `vjc`, `ij^c`)
  multiply by one hundred: `iij C` = 300, `xij C xx` = 1220.
* `m` multiplies by one thousand: `m vj C lxxxxiiij` = 1694, `vij m ij c xv` = 7215.

An attached mark is detached from its group except where the token reads as a
subtractive numeral, `xc` = 90 and `ixc` = 89, which is the one form in which `c`
follows a group without multiplying it.

A mark that follows no Roman group contributes its own Roman value instead, so a
leading `c` is 100 and a leading `m` is 1000.

Denominations close a value and open the next one:
`gld` (also `Rh gld`, `Rhgld`, `gl`, `guld`), `duc` (also `dut`, `ducat`, `ducatn`),
`m` for the mark (also `m̄`, `m̅`, `m̃`, `mr`, `mrk`, `mark`), `lb`, `ß` (also `s`),
`d`, `hl`. So `xxxviij m viij lb ij d` is 38 mark, 8 pound, 2 pfennig.

Three letters are ambiguous and are resolved by position, which is the one place
where this parser makes an assumption rather than reading a symbol:

* `m` is the thousand multiplier when a hundred mark still follows in the same
  amount, and the mark denomination otherwise. `m vj C lxxxxiiij` is 1694,
  `xxxviij m viij lb ij d` is 38 mark. The barred forms (`m̄`, `mr`) are always the
  denomination.
* `c` is the hundred multiplier when a Roman group directly precedes it, and the
  Roman digit 100 otherwise.
* a standalone `d` is the pfennig denomination, never the Roman digit 500; inside a
  longer Roman group (`cd`) it keeps its Roman value.

The it02 schema splits an amount into `multiplier`, `numeral` and `unit`, and the
numeral usually carries its own marks. Where it does not, the mark from the
`multiplier` field is inserted, and the line text decides its position, since both
`C lxxij` = 172 and `viijC liij` = 853 occur. Without a text witness the mark goes
behind the first group.

Not supported, and never guessed: German number words (`dreizehn`), the ellipsis
`...` that a run writes where it lost content, misread unit letters (`tt`, `t`, `w`,
`f`, `pw`), weight units of the silver accounts (`lot`, `mrcz`), and `halb`
notations, which do not occur in this corpus. Every such token is reported as
"unparsed" and never turned into a value. A value left over at the end of an amount
after at least one denomination was assigned goes to the pseudo-denomination `?`,
because the ß/d/hl chain at the line end is exactly where the model drops marks.

Block model
-----------
A block is the run of amount-bearing lines up to the next Summa head, plus the value
of that head. Amount lines are recognized by their `amount` object, which the it02
schema also attaches to `entry` and `sum` lines, not only to lines of kind `amount`.
A Summa head is a line of kind `sum` or a line whose text starts with a Summa
spelling (`Summa`, `Suma`, `Sm̃a`, `Sūma`, ...); its value sits either on the head
line itself or on the amount lines directly following it. A `rubric` or `foliation`
line closes the running block, because it opens a new account section.

Verdicts are per denomination and assume no conversion between denominations:

* `exact-match`: the denominations of items and Summa are the same set and every one
  of them adds up exactly.
* `mismatch`: same set, at least one denomination off. Both totals are reported.
* `unverifiable`: an unparsed token in the block, no Summa value, a single item
  (where the check is trivial), or item and Summa denominations that differ, which an
  unknown conversion could explain.

A mismatching block additionally reports `subset_exact` when exactly one proper
subset of at least two items adds up to the Summa. That is the p030 recto case: a
descriptive line carries an amount that is not an addend of the block.

Usage:
  python check_amounts.py           # all Raitbuch runs of pilot and pilot2
  python check_amounts.py --runs DIR [--runs DIR] --out DIR
"""

import argparse
import itertools
import json
import re
import sys
import unicodedata
from collections.abc import Iterable
from pathlib import Path
from typing import NamedTuple

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent
REPO = ROOT.parent.parent
DEFAULT_RUN_DIRS = (
    REPO / "evaluation" / "pilot" / "runs",
    REPO / "evaluation" / "pilot2" / "runs",
)
RUN_GLOB = "*rb2*.json"

# Denomination normalization. Keys are matched on a lowercased, NFC-normalized token.
# `m` and `c` are deliberately absent: they are resolved positionally (see docstring).
UNIT_MAP = {
    "gld": "gld",
    "gl": "gld",
    "guld": "gld",
    "gulden": "gld",
    "rhgld": "gld",
    "rhgl": "gld",
    "duc": "duc",
    "dut": "duc",
    "ducat": "duc",
    "ducatn": "duc",
    "ducaten": "duc",
    "m̄": "m",
    "m̅": "m",
    "m̃": "m",
    "mr": "m",
    "mrk": "m",
    "mark": "m",
    "marck": "m",
    "lb": "lb",
    "ß": "ß",
    "s": "ß",
    "d": "d",
    "hl": "hl",
}
# Multi-token unit spellings, joined before tokenization.
UNIT_PHRASES = (("rh", "gld"), ("rh", "guld"), ("rh", "gl"))

HUNDRED_MARKS = {"c", "ᶜ"}
THOUSAND_MARK = "m"
SEPARATORS = {".", "/", "·", ",", ";", "-", "—", "——", "–", "+", "|", "*", "&"}
LOST_MARKERS = ("[...]", "[…]", "[---]", "...", "…")
LOST_TOKEN = "␦"  # sentinel: survives tokenization, marks content the run lost
ROMAN_VALUES = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}
ROMAN_RE = re.compile(r"^[ivxlcdm]+$")
DIGIT_RE = re.compile(r"^\d+$")
# A Summa spelling as its own token, or a longer spelling glued to what follows.
# The bare `sm` is deliberately absent from the second alternative: without a word
# boundary it would make a Summa head of every line starting with those letters.
SUM_HEAD_RE = re.compile(r"^(summa|suma|sma|smha|sm|sum)\b|^(summa|suma|sma|smha)")
SUBTRACTIVE_BEFORE = {"c": "x", "m": "c"}  # digit a subtractive form puts before a mark
MAX_SUBSET_ITEMS = 12  # bounds the 2**n subset search of a mismatching block


class Amount(NamedTuple):
    """A parsed amount: denomination totals plus the tokens that could not be read."""

    values: dict[str, int]
    unparsed: list[str]

    @property
    def parsed(self) -> bool:
        return not self.unparsed


def strip_marks(text: str) -> str:
    """Casefold and drop combining marks, for matching Summa spellings only."""
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()


def roman_value(token: str) -> int | None:
    """Additive-and-subtractive Roman value; `j` is the final-`i` variant."""
    token = token.replace("j", "i")
    if not ROMAN_RE.match(token):
        return None
    total, prev = 0, 0
    for char in reversed(token):
        value = ROMAN_VALUES[char]
        total = total - value if value < prev else total + value
        prev = max(prev, value)
    return total


def _detach_mark(match: re.Match[str]) -> str:
    """Split a trailing multiplier mark off its group, unless the token is a
    subtractive numeral, where the mark is a Roman digit: `xc` is 90 and not
    10 x 100, `vjc` stays 6 x 100.
    """
    group, mark = match.group(1), match.group(2)
    if group[-1:].lower() == SUBTRACTIVE_BEFORE[mark.lower()]:
        return match.group(0)
    return f"{group} {mark}"


def tokenize(text: str) -> list[str]:
    """Split an amount string into value, mark, denomination and residual tokens."""
    text = unicodedata.normalize("NFC", text)
    text = text.replace("^c", " c ").replace("^C", " c ").replace("ᶜ", " c ")
    for marker in LOST_MARKERS:
        text = text.replace(marker, f" {LOST_TOKEN} ")
    text = re.sub(r"[{}()\[\]]", " ", text)
    # Detach a trailing multiplier mark from its group (`vjc`, `iiijC`, `iijm`), but
    # leave a group that is Roman hundreds or thousands itself (`cccc`) intact.
    text = re.sub(r"\b([ivxlj]+)([cCmM])\b", _detach_mark, text)
    raw = [t for t in re.split(r"[\s.·/,;|]+", text) if t]
    tokens: list[str] = []
    index = 0
    while index < len(raw):
        pair = (
            raw[index].lower(),
            raw[index + 1].lower() if index + 1 < len(raw) else "",
        )
        if pair in UNIT_PHRASES:
            tokens.append(pair[1])
            index += 2
            continue
        tokens.append(raw[index])
        index += 1
    return tokens


def parse_amount(
    numeral: str, multiplier: str = "", unit: str = "", text: str = ""
) -> Amount:
    """Parse the amount object of a line into denomination totals.

    `multiplier` marks that the numeral does not already carry are inserted into it;
    the line `text` decides whether such a mark stands before or after the first Roman
    group, since both occur (`C lxxij` = 172 against `viij C liij` = 853). `unit` is
    used only when the numeral assigns no denomination of its own.
    """
    numeral = _apply_multiplier(numeral or "", multiplier or "", text or "")
    tokens = tokenize(numeral)
    values: dict[str, int] = {}
    unparsed: list[str] = []
    group = 0  # Roman tokens accumulated since the last mark or denomination
    running = 0  # scaled groups since the last denomination
    assigned = False

    def flush(denomination: str) -> None:
        nonlocal group, running, assigned
        total = running + group
        group, running = 0, 0
        if total:
            values[denomination] = values.get(denomination, 0) + total
            assigned = True

    lowered = [t.lower() for t in tokens]
    for position, token in enumerate(lowered):
        if token in SEPARATORS:
            continue
        if token == LOST_TOKEN:
            unparsed.append("...")
            continue
        if token in UNIT_MAP:
            flush(UNIT_MAP[token])
            continue
        if token in HUNDRED_MARKS:
            running += (group or 1) * 100
            group = 0
            continue
        if token == THOUSAND_MARK:
            if group and not any(
                later in HUNDRED_MARKS for later in lowered[position + 1 :]
            ):
                flush("m")
            else:
                running += (group or 1) * 1000
                group = 0
            continue
        value = roman_value(token)
        if value is None and DIGIT_RE.match(token):
            value = int(token)
        if value is None:
            unparsed.append(token)
            continue
        group += value

    rest = running + group
    if rest:
        fallback = None
        if not assigned:
            candidates = {
                UNIT_MAP[t.lower()]
                for t in tokenize(unit or "")
                if t.lower() in UNIT_MAP
            }
            fallback = candidates.pop() if len(candidates) == 1 else None
        values["?" if fallback is None else fallback] = (
            values.get("?" if fallback is None else fallback, 0) + rest
        )
    return Amount(values=values, unparsed=unparsed)


def _flatten(text: str) -> str:
    return text.replace("ᶜ", "c").replace("^", "").lower()


def _apply_multiplier(numeral: str, multiplier: str, text: str = "") -> str:
    """Insert multiplier marks that the numeral string does not already carry."""
    if not multiplier.strip():
        return numeral
    normalized = _flatten(numeral)
    missing = []
    for part in re.split(r"[\s./]+", multiplier.replace("ᶜ", "c").replace("^", "")):
        part = part.strip()
        if part and part.lower() not in normalized:
            missing.append(part)
    if not missing:
        return numeral
    if not numeral.strip():
        return " ".join(missing)
    # A multiplier that carries its own Roman group (`ijC`) opens the amount. A bare
    # mark goes where the line text shows it, and behind the first group by default.
    head, _, tail = numeral.strip().partition(" ")
    leading = [m for m in missing if m.rstrip("cCmM")]
    bare = [m for m in missing if not m.rstrip("cCmM")]
    flat_text = _flatten(text)
    before = [
        m
        for m in bare
        if re.search(
            rf"(^|\s){m.lower()}\s+{re.escape(_flatten(head))}(\s|$)", flat_text
        )
    ]
    after = [m for m in bare if m not in before]
    return " ".join([*leading, *before, head, *after, tail]).strip()


# ---------- Block detection ----------


class Line(NamedTuple):
    index: int
    text: str
    kind: str
    amount: Amount | None
    unreadable: bool  # kind `amount` without a parsable amount object


class Block(NamedTuple):
    page_label: str
    items: list[Line]
    head: Line | None
    total_lines: list[Line]


def line_amount(line: dict) -> tuple[Amount | None, bool]:
    obj = line.get("amount")
    if isinstance(obj, dict) and (obj.get("numeral") or obj.get("multiplier")):
        return parse_amount(
            obj.get("numeral", ""),
            obj.get("multiplier", ""),
            obj.get("unit", ""),
            line.get("text", ""),
        ), False
    return None, line.get("kind") == "amount"


def read_lines(page: dict) -> list[Line]:
    lines = []
    for index, raw in enumerate(page.get("lines") or []):
        amount, unreadable = line_amount(raw)
        lines.append(
            Line(
                index=index,
                text=raw.get("text", ""),
                kind=raw.get("kind", ""),
                amount=amount,
                unreadable=unreadable,
            )
        )
    return lines


def is_sum_head(line: Line) -> bool:
    if line.kind == "sum":
        return True
    return bool(SUM_HEAD_RE.match(strip_marks(line.text).lstrip("~ ")))


def find_blocks(page: dict) -> list[Block]:
    """Group a page's lines into item runs terminated by a Summa head."""
    label = page.get("label", "")
    lines = read_lines(page)
    blocks: list[Block] = []
    items: list[Line] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if is_sum_head(line):
            totals, index = collect_total(lines, index)
            blocks.append(
                Block(page_label=label, items=items, head=line, total_lines=totals)
            )
            items = []
            continue
        if line.kind in {"rubric", "foliation"} and items:
            blocks.append(
                Block(page_label=label, items=items, head=None, total_lines=[])
            )
            items = []
        if line.amount is not None or line.unreadable:
            items.append(line)
        index += 1
    if items:
        blocks.append(Block(page_label=label, items=items, head=None, total_lines=[]))
    return blocks


def collect_total(lines: list[Line], head_index: int) -> tuple[list[Line], int]:
    """Value lines of a Summa: the head itself, or the amount lines right after it.

    The window after the head is three lines wide, because a Summa is written over up
    to two text lines before its value, and its value can run over two amount lines
    when the minor denominations sit on their own line.
    """
    head = lines[head_index]
    if head.amount is not None:
        return [head], head_index + 1
    totals: list[Line] = []
    index = head_index + 1
    while index < len(lines) and index <= head_index + 3:
        line = lines[index]
        if line.amount is not None or line.unreadable:
            totals.append(line)
            index += 1
            continue
        if totals or line.kind not in {"sum", "entry"}:
            break
        index += 1
    return totals, index


# ---------- Verdicts ----------


def merge(amounts: Iterable[Amount]) -> Amount:
    values: dict[str, int] = {}
    unparsed: list[str] = []
    for amount in amounts:
        for denomination, value in amount.values.items():
            values[denomination] = values.get(denomination, 0) + value
        unparsed.extend(amount.unparsed)
    return Amount(values=values, unparsed=unparsed)


def named(values: dict[str, int]) -> dict[str, int]:
    """Denominations that were actually read, without the `?` residual."""
    return {k: v for k, v in values.items() if k != "?" and v}


def subset_exact(items: list[Amount], target: dict[str, int]) -> list[int] | None:
    """The one proper subset of at least two items that adds up to the Summa."""
    if not 2 < len(items) <= MAX_SUBSET_ITEMS:
        return None
    hits = []
    for size in range(2, len(items)):
        for combination in itertools.combinations(range(len(items)), size):
            if named(merge(items[i] for i in combination).values) == target:
                hits.append(list(combination))
    return hits[0] if len(hits) == 1 else None


def judge(block: Block) -> dict:
    """Verdict for one block, with both totals and the reason where it does not decide."""
    item_amounts = [line.amount for line in block.items if line.amount is not None]
    total_amounts = [
        line.amount for line in block.total_lines if line.amount is not None
    ]
    items = merge(item_amounts)
    total = merge(total_amounts)
    result: dict = {
        "page_label": block.page_label,
        "head_text": block.head.text if block.head else "",
        "head_line": block.head.index if block.head else None,
        "item_lines": [line.index for line in block.items],
        "item_texts": [line.text for line in block.items],
        "total_texts": [line.text for line in block.total_lines],
        "items_total": dict(sorted(items.values.items())),
        "sum_total": dict(sorted(total.values.items())),
        "unparsed": sorted(set(items.unparsed) | set(total.unparsed)),
    }
    unreadable = [
        line.text for line in (*block.items, *block.total_lines) if line.unreadable
    ]

    def undecided(reason: str) -> dict:
        return {**result, "verdict": "unverifiable", "reason": reason}

    if block.head is None:
        return undecided("no Summa line closes this run of amounts")
    if not total_amounts:
        return undecided("Summa line carries no readable amount")
    if unreadable:
        return undecided("amount line without amount object")
    if items.unparsed or total.unparsed:
        return undecided("unparsed token in the block")
    if not item_amounts:
        return undecided("Summa without preceding item amounts")
    if len(item_amounts) < 2:
        return undecided("single item, arithmetic is trivial")
    item_named, total_named = named(items.values), named(total.values)
    if not item_named or not total_named:
        return undecided("no named denomination on one side")
    if set(item_named) != set(total_named):
        return undecided("denominations differ, an unknown conversion could explain it")
    if item_named == total_named:
        result["verdict"] = "exact-match"
        if "?" in items.values or "?" in total.values:
            result["residual_unassigned"] = True
        return result
    result["verdict"] = "mismatch"
    hit = subset_exact(item_amounts, total_named)
    if hit is not None:
        result["subset_exact"] = [block.items[i].index for i in hit]
    return result


# ---------- Report ----------


def check_run(path: Path) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    judged = []
    for page in record.get("parsed", {}).get("pages", []) or []:
        judged.extend(judge(block) for block in find_blocks(page))
    # A run of amount lines that no Summa closes is not a block; it is counted, not judged.
    blocks = [b for b in judged if b["head_line"] is not None]
    unclosed = len(judged) - len(blocks)
    unparsed = sorted({token for block in judged for token in block["unparsed"]})
    return {
        "run": path.name,
        "cohort": path.parent.parent.name,
        "page": record.get("page", ""),
        "repeat": record.get("repeat"),
        "iteration": record.get("iteration", ""),
        "blocks": blocks,
        "unclosed_amount_runs": unclosed,
        "unparsed_tokens": unparsed,
        "counts": counts_of(blocks),
    }


def counts_of(blocks: list[dict]) -> dict[str, int]:
    counts = {"exact-match": 0, "mismatch": 0, "unverifiable": 0}
    for block in blocks:
        counts[block["verdict"]] += 1
    counts["subset-only"] = sum(1 for b in blocks if b.get("subset_exact"))
    return counts


def build_report(run_dirs: Iterable[Path]) -> dict:
    paths = sorted(
        (p for d in run_dirs for p in Path(d).glob(RUN_GLOB)),
        key=lambda p: (p.parent.parent.name, p.name),
    )
    runs = [check_run(path) for path in paths]
    return {
        "tool": "check_amounts",
        "run_glob": RUN_GLOB,
        "runs": runs,
        "aggregate": aggregate(runs),
    }


def page_verdict(run: dict) -> str:
    """A run's page-level state.

    `clean` means at least one block adds up and none contradicts. A mismatch whose
    subset adds up does not count as a contradiction, because there the block carries
    an amount line that is not an addend rather than a wrong amount.
    """
    good = sum(
        1
        for b in run["blocks"]
        if b["verdict"] == "exact-match" or b.get("subset_exact")
    )
    bad = sum(
        1
        for b in run["blocks"]
        if b["verdict"] == "mismatch" and not b.get("subset_exact")
    )
    if bad:
        return "mismatch"
    return "clean" if good else "unverifiable"


def aggregate(runs: list[dict]) -> dict:
    cohorts: dict[str, dict[str, int]] = {}
    for run in runs:
        bucket = cohorts.setdefault(
            run["cohort"],
            {
                "runs": 0,
                "blocks": 0,
                "exact-match": 0,
                "mismatch": 0,
                "unverifiable": 0,
                "subset-only": 0,
                "unclosed_amount_runs": 0,
            },
        )
        bucket["runs"] += 1
        bucket["blocks"] += len(run["blocks"])
        bucket["unclosed_amount_runs"] += run["unclosed_amount_runs"]
        for key, value in run["counts"].items():
            bucket[key] += value
    pages: dict[str, dict[str, str]] = {}
    for run in runs:
        pages.setdefault(run["page"], {})[f"r{run['repeat']}"] = page_verdict(run)
    # Both selections need at least two repeats to say anything, and hold for any k.
    single = sorted(
        p
        for p, r in pages.items()
        if len(r) > 1 and sum(v == "clean" for v in r.values()) == 1
    )
    all_fail = sorted(
        p
        for p, r in pages.items()
        if len(r) > 1 and all(v == "mismatch" for v in r.values())
    )
    tokens: dict[str, int] = {}
    reasons: dict[str, int] = {}
    for run in runs:
        for token in run["unparsed_tokens"]:
            tokens[token] = tokens.get(token, 0) + 1
        for block in run["blocks"]:
            if block["verdict"] == "unverifiable":
                reasons[block["reason"]] = reasons.get(block["reason"], 0) + 1
    return {
        "cohorts": dict(sorted(cohorts.items())),
        "pages": dict(sorted(pages.items())),
        "sighting_candidates": single,
        "all_repeats_mismatch": all_fail,
        "unverifiable_reasons": dict(
            sorted(reasons.items(), key=lambda kv: (-kv[1], kv[0]))
        ),
        "unparsed_tokens": dict(sorted(tokens.items(), key=lambda kv: (-kv[1], kv[0]))),
    }


def format_amount(values: dict[str, int]) -> str:
    return " ".join(f"{v} {k}" for k, v in sorted(values.items())) or "-"


def render_markdown(report: dict) -> str:
    aggregate_data = report["aggregate"]
    out = [
        "# Arithmetische Probe der Raitbuch-Transkriptionen",
        "",
        "Posten eines Blocks gegen dessen Summenzeile, je Denomination und ohne "
        "angenommene Umrechnung. Erzeugt von `check_amounts.py`.",
        "",
        "## Kohorten",
        "",
        "| Kohorte | Läufe | Blöcke | exact-match | mismatch | unverifiable | davon Teilmengen-Treffer | "
        "Betragsläufe ohne Summenzeile |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for cohort, data in aggregate_data["cohorts"].items():
        out.append(
            f"| {cohort} | {data['runs']} | {data['blocks']} | {data['exact-match']} | "
            f"{data['mismatch']} | {data['unverifiable']} | {data['subset-only']} | "
            f"{data['unclosed_amount_runs']} |"
        )
    out += [
        "",
        "## Warum ein Block nicht entscheidet",
        "",
        "| Grund | Blöcke |",
        "|---|---|",
    ]
    out += [
        f"| {reason} | {count} |"
        for reason, count in aggregate_data["unverifiable_reasons"].items()
    ]
    out += [
        "",
        "## Seiten, auf denen genau eine Wiederholung aufgeht",
        "",
        "Kandidaten für eine gezielte Bildlektüre; die Probe weist dort einen Lauf aus.",
        "",
    ]
    if aggregate_data["sighting_candidates"]:
        columns = sorted(
            {
                key
                for page in aggregate_data["sighting_candidates"]
                for key in aggregate_data["pages"][page]
            },
            key=lambda key: int(key[1:]),
        )
        out += [
            "| Seite | " + " | ".join(columns) + " |",
            "|---|" + "---|" * len(columns),
        ]
        for page in aggregate_data["sighting_candidates"]:
            repeats = aggregate_data["pages"][page]
            cells = " | ".join(repeats.get(key, "-") for key in columns)
            out.append(f"| {page} | {cells} |")
    else:
        out.append("Keine.")
    out += ["", "## Seiten, auf denen alle Wiederholungen scheitern", ""]
    out.append(", ".join(aggregate_data["all_repeats_mismatch"]) or "Keine.")
    out += [
        "",
        "## Nicht geparste Tokens",
        "",
        "Tokens, die der Parser nicht liest und deshalb auch nicht rät.",
        "",
    ]
    if aggregate_data["unparsed_tokens"]:
        out += ["| Token | Läufe |", "|---|---|"]
        out += [
            f"| `{token}` | {count} |"
            for token, count in aggregate_data["unparsed_tokens"].items()
        ]
    else:
        out.append("Keine.")
    out += ["", "## Blöcke mit Befund", ""]
    for run in report["runs"]:
        decided = [
            b for b in run["blocks"] if b["verdict"] in {"exact-match", "mismatch"}
        ]
        if not decided:
            continue
        out.append(f"### {run['run']}")
        out.append("")
        for block in decided:
            note = ""
            if block.get("subset_exact"):
                note = f" (Teilmenge der Zeilen {block['subset_exact']} geht auf)"
            out.append(
                f"- {block['verdict']}{note}: Posten {format_amount(block['items_total'])} "
                f"gegen Summe {format_amount(block['sum_total'])} "
                f"[{block['page_label']}, „{block['head_text']}“]"
            )
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def write_reports(report: dict, out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "amounts_report.json"
    md_path = out_dir / "amounts_report.md"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=1, sort_keys=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    md_path.write_text(render_markdown(report), encoding="utf-8", newline="\n")
    return json_path, md_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--runs", action="append", type=Path, help="run directory (repeatable)"
    )
    parser.add_argument("--out", type=Path, default=ROOT, help="report directory")
    args = parser.parse_args()
    report = build_report(args.runs or DEFAULT_RUN_DIRS)
    json_path, md_path = write_reports(report, args.out)
    print(render_markdown(report))
    print(f"geschrieben: {json_path.name}, {md_path.name}")


if __name__ == "__main__":
    main()
