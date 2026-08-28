"""Tests for the date normalisation of scripts/transform_sources.py.

The file lives here because pytest collects `pipeline` and `evaluation/checks`
only (see `[tool.pytest.ini_options]` in pyproject.toml); `scripts/` is not a
test path, so a test module beside the script would never run.

The table covers the raw shapes the finding aid uses in docs/data/sources.json,
written with the hyphen the script folds every dash to; EN_DASH covers the fold
itself. The two corpus tests bind the published file to the function that
produced it.
"""

import json
from pathlib import Path

import pytest

from scripts.transform_sources import normalize_date

SOURCES = Path(__file__).resolve().parents[1] / "docs" / "data" / "sources.json"

# Built from the code point, so the file stays free of ambiguous characters.
EN_DASH = chr(0x2013)

# raw, start, end, circa
CASES = [
    ("", None, None, False),
    ("   ", None, None, False),
    ("1479", 1479, 1479, False),
    ("1462.07.15", 1462, 1462, False),
    ("1425.08.16", 1425, 1425, False),
    ("1487-1594", 1487, 1594, False),
    ("1004-1780", 1004, 1780, False),
    ("1323-1560 (ca.)", 1323, 1560, True),
    ("1495 (ca.)", 1495, 1495, True),
    ("1450 ca", 1450, 1450, True),
    # Unchanged behaviour, recorded rather than endorsed: a range whose first
    # year is followed by anything other than the dash (a month, a "(ca.)"
    # suffix) or preceded by a "ca." prefix collapses to its first year.
    ("1477.04-1478.04", 1477, 1477, False),
    ("1280 (ca.)-1480 (ca.)", 1280, 1280, True),
    ("ca. 1300-1900", 1300, 1300, True),
    ("ca. (1450) 1600-1850", 1450, 1450, True),
    # An open end keeps the named year on both sides, unchanged behaviour.
    ("1229-", 1229, 1229, False),
    ("1450 (ca.)-", 1450, 1450, True),
    ("ca. 1280-laufend", 1280, 1280, True),
    # Centuries: the span runs from the first year of the first century to the
    # last year of the last.
    ("15. Jh.", 1401, 1500, True),
    ("13. Jh.-17. Jh.", 1201, 1700, True),
    ("13. Jh.-14. Jh.", 1201, 1400, True),
    ("15. Jh.-17. Jh.", 1401, 1700, True),
    # The split form, where only the second century carries the unit.
    ("15.-18. Jh.", 1401, 1800, True),
    # A leading dash is "bis": an open start, never a negative year.
    ("-1564", None, 1564, False),
    ("-1765", None, 1765, False),
    ("-17. Jh.", None, 1700, True),
]


@pytest.mark.parametrize(("raw", "start", "end", "circa"), CASES)
def test_normalize_date(raw, start, end, circa):
    got = normalize_date(raw)
    assert got["start"] == start
    assert got["end"] == end
    assert got["circa"] is circa


def test_en_dash_reads_like_a_hyphen():
    assert normalize_date(f"1004{EN_DASH}1780")["start"] == 1004
    assert normalize_date(f"15.{EN_DASH}18. Jh.")["end"] == 1800


def test_raw_is_kept_verbatim():
    assert normalize_date(f"  1004{EN_DASH}1780 ")["raw"] == f"1004{EN_DASH}1780"


def test_no_negative_or_inverted_years_in_sources():
    for entry in json.loads(SOURCES.read_text(encoding="utf-8")):
        dating = entry["datierung"]
        start, end = dating["start"], dating["end"]
        assert start is None or start >= 1000, entry["signatur"]
        assert end is None or end >= 1000, entry["signatur"]
        if start is not None and end is not None:
            assert start <= end, entry["signatur"]


def test_published_datings_match_the_normaliser():
    """The migrate path recomputes datierung from raw, so the file must agree."""
    for entry in json.loads(SOURCES.read_text(encoding="utf-8")):
        assert normalize_date(entry["datierung"]["raw"]) == entry["datierung"], entry[
            "signatur"
        ]
