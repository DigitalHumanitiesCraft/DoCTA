# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Tests for the statistics of the benchmark secondary analysis.

The helpers under test decide what the report claims, so each one is checked
against a value computable by hand rather than against its own output: Spearman
on a perfectly ordered and a perfectly reversed pair, the exact permutation
p-value against the closed form 2/n! for a perfect correlation, and the sign
test against the binomial tail 1/2^n.

The analysis over the real summary is checked for the three properties that make
it citable: the degenerate references are excluded by the data flag, two builds
of one summary agree, and the committed analysis.json and analysis.md are what
the current script produces from the summary beside them.

Usage:
  pytest evaluation/checks/test_analyze_summary.py
"""

import importlib.util
import json
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).parent
REPO = ROOT.parents[1]
BENCHMARK = REPO / "evaluation" / "benchmark"

_spec = importlib.util.spec_from_file_location(
    "analyze_summary", BENCHMARK / "analyze_summary.py"
)
ana = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ana)

SUMMARY = json.loads((BENCHMARK / "summary.json").read_text(encoding="utf-8"))


# ------------------------------- ranks --------------------------------------


def test_ranks_are_one_based_and_share_the_mean_on_ties() -> None:
    assert ana.ranks([10.0, 20.0, 30.0]) == [1.0, 2.0, 3.0]
    # positions 2 and 3 tie, so both take (2 + 3) / 2
    assert ana.ranks([10.0, 20.0, 20.0, 40.0]) == [1.0, 2.5, 2.5, 4.0]


# ----------------------------- correlation ----------------------------------


def test_spearman_reaches_the_bounds_on_ordered_pairs() -> None:
    xs = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert ana.spearman(xs, xs) == pytest.approx(1.0)
    assert ana.spearman(xs, list(reversed(xs))) == pytest.approx(-1.0)


def test_spearman_matches_the_hand_computed_value() -> None:
    """One adjacent swap in five untied ranks: rho = 1 - 6*sum(d^2)/(n(n^2-1))
    with sum(d^2) = 2, so rho = 1 - 12/120 = 0.9."""
    assert ana.spearman(
        [1.0, 2.0, 3.0, 4.0, 5.0], [1.0, 2.0, 3.0, 5.0, 4.0]
    ) == pytest.approx(0.9)


def test_spearman_is_none_where_a_side_is_constant() -> None:
    assert ana.spearman([1.0, 2.0, 3.0], [7.0, 7.0, 7.0]) is None


def test_spearman_needs_three_points() -> None:
    assert ana.spearman([1.0, 2.0], [1.0, 2.0]) is None


# --------------------------- permutation p-value -----------------------------


@pytest.mark.parametrize("n", [4, 5, 6])
def test_permutation_p_of_a_perfect_correlation_is_two_over_n_factorial(n: int) -> None:
    """Only the identity labeling and its reversal reach |rho| = 1, and the test
    is two-sided, so the exact p is 2/n!."""
    xs = [float(i) for i in range(n)]
    assert ana.permutation_p(xs, xs) == pytest.approx(2 / math.factorial(n))


def test_permutation_p_is_orientation_free() -> None:
    """A sign flip of one side mirrors every permutation, so the two-sided tail
    is the same value."""
    xs = [1.0, 2.0, 3.0, 4.0, 5.0]
    ys = [2.0, 1.0, 4.0, 3.0, 5.0]
    assert ana.permutation_p(xs, ys) == ana.permutation_p(xs, [-y for y in ys])


def test_permutation_p_refuses_a_sample_it_cannot_enumerate() -> None:
    xs = [float(i) for i in range(ana.PERMUTATION_LIMIT + 1)]
    with pytest.raises(ValueError, match="exact permutation refused"):
        ana.permutation_p(xs, xs)


# ------------------------------- sign test -----------------------------------


def test_sign_test_of_a_clean_sweep_matches_the_binomial_tail() -> None:
    """Seven of seven in one direction: one-sided 1/2^7, two-sided twice that."""
    assert ana.sign_test_p(7, 0) == (pytest.approx(1 / 128), pytest.approx(2 / 128))


def test_sign_test_of_an_even_split_is_uninformative() -> None:
    one_sided, two_sided = ana.sign_test_p(3, 3)
    assert two_sided == pytest.approx(1.0)
    # tail over 0..3 successes of 6: (1+6+15+20)/2^6; doubling exceeds one and is clamped
    assert one_sided == pytest.approx(42 / 64)


def test_sign_test_is_symmetric_in_its_arguments() -> None:
    assert ana.sign_test_p(5, 2) == ana.sign_test_p(2, 5)


def test_sign_test_without_decided_pages_returns_one() -> None:
    assert ana.sign_test_p(0, 0) == (1.0, 1.0)


# ------------------------- the analysis on real data -------------------------


def test_reference_pages_exclude_the_degenerate_ones_by_the_data_flag() -> None:
    selected = {pid for pid, _ in ana.reference_pages(SUMMARY)}
    flagged = {
        pid
        for pid, page in SUMMARY["pages"].items()
        if page.get("reference_degenerate")
    }
    assert flagged, "the summary must still carry the degenerate flag"
    assert not (selected & flagged)
    assert all(
        SUMMARY["pages"][pid]["reference_class"] == "transkribus-done"
        for pid in selected
    )


def test_both_cer_aggregates_stay_rates_on_the_real_pages() -> None:
    """Length weighting and equal weighting are two aggregates of one set of
    rates, so each has to land inside the range the per-page means span."""
    pages = ana.reference_pages(SUMMARY)
    means = [page["iterations"]["it02"]["cer_fair"]["mean"] for _, page in pages]
    for value in (
        ana.micro_cer(pages, "it02", "cer_fair"),
        ana.page_mean_cer(pages, "it02", "cer_fair"),
    ):
        assert min(means) <= value <= max(means)


def test_analysis_is_deterministic_over_the_committed_summary() -> None:
    """No clock and no network, so two builds of the same summary agree."""
    assert ana.build(SUMMARY) == ana.build(SUMMARY)


def test_committed_analysis_matches_a_rebuild() -> None:
    """The checked-in artifacts are what the script produces from the summary
    beside them; a stale analysis.json would otherwise be cited as evidence."""
    result = ana.build(SUMMARY)
    on_disk = json.loads((BENCHMARK / "analysis.json").read_text(encoding="utf-8"))
    assert on_disk == result
    assert (BENCHMARK / "analysis.md").read_text(encoding="utf-8") == ana.report(result)
