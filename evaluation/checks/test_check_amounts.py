# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Tests for check_amounts. Plain asserts, run with: python test_check_amounts.py

Every parser case is a real amount object taken from a run file; the source file is
named in the comment above it. The two block cases are the arithmetic the visual
referee review verified against the image
(evaluation/pilot2/review/raitbuch.md, section "Beträge").
"""

import json
import sys
import tempfile
from pathlib import Path

import check_amounts as ca

ROOT = Path(__file__).parent
REPO = ROOT.parent.parent
PILOT2 = REPO / "evaluation" / "pilot2" / "runs"
PILOT = REPO / "evaluation" / "pilot" / "runs"


def amount(numeral: str, multiplier: str = "", unit: str = "") -> dict[str, int]:
    return ca.parse_amount(numeral, multiplier, unit).values


def test_roman_forms() -> None:
    assert ca.roman_value("iiij") == 4
    assert ca.roman_value("xl") == 40
    assert ca.roman_value("lxxxxiiij") == 94
    assert ca.roman_value("cccc") == 400
    assert ca.roman_value("dreizehn") is None


def test_parse_real_amounts() -> None:
    # pilot2_rb2_p025__it02__r2.json, verso: the three items of the Innemen block
    assert amount("iij", "C", "Rhgld") == {"gld": 300}
    assert amount("vij", "C", "Rhgld") == {"gld": 700}
    assert amount("vj C lxxxxiiij", "C", "Rhgld") == {"gld": 694}
    # same file, the Summa: `m` is the thousand multiplier because a `C` follows
    assert amount("m vj C lxxxxiiij", "m", "Rhgld") == {"gld": 1694}
    # pilot2_rb2_p030__it02__r1.json, 30r: hundred mark and a bare group
    assert amount("xij C xx", "C", "duc") == {"duc": 1220}
    assert amount("lxvij", "", "duc") == {"duc": 67}
    assert amount("c l iiij", "", "duc") == {"duc": 154}  # leading c is the Roman 100
    assert amount("xij C lxxxvij", "C", "duc") == {"duc": 1287}
    # evaluation/pilot2/review/raitbuch.md: the head sum of p038 recto read from the
    # image; here `m` is the mark denomination, because no hundred mark follows
    assert amount("xxxviij m viij lb ij d") == {"m": 38, "lb": 8, "d": 2}
    # pilot2_rb2_p026__it02__r1.json, 26r: thousand and hundred in one amount
    assert amount("vij m ij c xv", "m", "lb") == {"lb": 7215}
    # pilot2_rb2_p027__it02__r1.json, verso: the trailing viij carries no denomination
    assert amount("ij m iiij c xlvij lb iiij ß j d viij", "m / c", "lb, ß, d") == {
        "lb": 2447,
        "ß": 4,
        "d": 1,
        "?": 8,
    }
    # pilot2_rb2_p031__it02__r2.json: multiplier carried only by the multiplier field
    assert amount("lxxj", "ijC", "duc") == {"duc": 271}
    # pilot2_rb2_p039__it02__r1.json, 39r: the same field, but the text shows the mark
    # standing before the group, so it is the Roman 100 and not a hundredfold
    assert ca.parse_amount(
        "lxxij", "C", "lb", "bleibt hat C lxxij lb xiij ß ix d"
    ).values == {"lb": 172}
    # pilot2_rb2_p024__it02__r1.json, verso: the same field with the mark behind the group
    assert ca.parse_amount(
        "viij liij", "C", "guld", "benant Soldner —— viijC liij guld ij ß v d"
    ).values == {"gld": 853}
    # pilot2_rb2_p040__it02__r1.json, 40r: mark with abbreviation stroke is the
    # denomination; the declared unit `hl` does not claim the trailing viij
    assert amount("lxxxv m̄ ix ß viij", "", "hl") == {"m": 85, "ß": 9, "?": 8}


def test_unparsed_is_never_guessed() -> None:
    # pilot2_rb2_p025__it02__r2.json, 25r: `tt` is the model's misread of `lb`
    parsed = ca.parse_amount("viij tt", "", "Rhgld")
    assert parsed.unparsed == ["tt"]
    assert parsed.values == {"gld": 8}
    # pilot_rb2_p006__it02__r1.json, 6r: a German number word stays unread
    assert ca.parse_amount("dreizehn", "", "gld") == ca.Amount(
        values={}, unparsed=["dreizehn"]
    )
    # pilot2_rb2_p040__it02__r1.json, verso: lost content marked by the run itself
    assert (
        "..." in ca.parse_amount("viij ... vij ... iiij ... xxvij", "", "mr").unparsed
    )


def page_of(run: str, index: int) -> dict:
    directory = PILOT2 if run.startswith("pilot2") else PILOT
    return json.loads((directory / run).read_text(encoding="utf-8"))["parsed"]["pages"][
        index
    ]


def verdicts(page: dict) -> list[dict]:
    return [ca.judge(block) for block in ca.find_blocks(page)]


def test_review_case_p025_verso_exact_match() -> None:
    """300 + 700 + 694 = 1694, verified against the image for r2."""
    block = next(
        v
        for v in verdicts(page_of("pilot2_rb2_p025__it02__r2.json", 0))
        if v["head_text"].startswith("Summa")
    )
    assert block["verdict"] == "exact-match", block
    assert block["items_total"] == {"gld": 1694}
    assert block["sum_total"] == {"gld": 1694}


def test_review_case_p030_recto_exact_match() -> None:
    """1220 + 67 = 1287, verified against the image for r1.

    The block carries a third amount line, `vnd munz c l iiij duc ...`, which is not
    an addend. The full set therefore mismatches and the checker reports the one
    subset that adds up, instead of silently accepting the block.
    """
    block = next(
        v
        for v in verdicts(page_of("pilot2_rb2_p030__it02__r1.json", 1))
        if v["sum_total"] == {"duc": 1287}
    )
    assert block["verdict"] == "mismatch", block
    assert block["items_total"] == {"duc": 1441}
    assert block["subset_exact"] is not None
    items = [
        ca.parse_amount("xij C xx", "C", "duc"),
        ca.parse_amount("lxvij", "", "duc"),
    ]
    assert ca.merge(items).values == {"duc": 1287}


def test_constructed_mismatch() -> None:
    page = {
        "label": "test",
        "lines": [
            {"text": "Item", "kind": "marginal"},
            {
                "text": "iij C Rhgld",
                "kind": "amount",
                "amount": {"multiplier": "C", "numeral": "iij", "unit": "Rhgld"},
            },
            {
                "text": "vij C Rhgld",
                "kind": "amount",
                "amount": {"multiplier": "C", "numeral": "vij", "unit": "Rhgld"},
            },
            {"text": "Summa", "kind": "sum"},
            {
                "text": "m Rhgld",
                "kind": "amount",
                "amount": {"multiplier": "", "numeral": "m j", "unit": "Rhgld"},
            },
        ],
    }
    block = verdicts(page)[0]
    assert block["verdict"] == "mismatch"
    assert block["items_total"] == {"gld": 1000}
    assert block["sum_total"] == {"gld": 1001}
    assert "subset_exact" not in block


def test_unverifiable_on_differing_denominations() -> None:
    page = {
        "label": "test",
        "lines": [
            {
                "text": "x lb",
                "kind": "amount",
                "amount": {"numeral": "x", "unit": "lb"},
            },
            {
                "text": "v lb",
                "kind": "amount",
                "amount": {"numeral": "v", "unit": "lb"},
            },
            {
                "text": "Summa xv ß",
                "kind": "sum",
                "amount": {"numeral": "xv", "unit": "ß"},
            },
        ],
    }
    block = verdicts(page)[0]
    assert block["verdict"] == "unverifiable"
    assert "conversion" in block["reason"]


def test_single_item_block_is_not_a_check() -> None:
    page = {
        "label": "test",
        "lines": [
            {
                "text": "x lb",
                "kind": "amount",
                "amount": {"numeral": "x", "unit": "lb"},
            },
            {
                "text": "Summa x lb",
                "kind": "sum",
                "amount": {"numeral": "x", "unit": "lb"},
            },
        ],
    }
    assert verdicts(page)[0]["reason"] == "single item, arithmetic is trivial"


def test_report_is_idempotent() -> None:
    report = ca.build_report(DEFAULT_DIRS)
    with tempfile.TemporaryDirectory() as tmp:
        first = Path(tmp) / "a"
        second = Path(tmp) / "b"
        ca.write_reports(report, first)
        ca.write_reports(ca.build_report(DEFAULT_DIRS), second)
        for name in ("amounts_report.json", "amounts_report.md"):
            assert (first / name).read_bytes() == (second / name).read_bytes(), name


DEFAULT_DIRS = (PILOT, PILOT2)


def main() -> int:
    tests = [
        value for name, value in sorted(globals().items()) if name.startswith("test_")
    ]
    failed = 0
    for test in tests:
        try:
            test()
            print(f"ok   {test.__name__}")
        except AssertionError as error:
            failed += 1
            print(f"FAIL {test.__name__}: {error}")
    print(f"\n{len(tests) - failed}/{len(tests)} bestanden")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
