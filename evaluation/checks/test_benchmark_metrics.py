# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Tests for the measuring instrument of the benchmark runner.

Three properties are under test: the agreement metric is symmetric and reports
nothing where a token class is absent, folio markers leave the text in every
spelling the corpus carries, and the committed summary states its own
normalisation profile and marks a degenerate reference as a data property.

The pure functions are tested on constructed token lists, the stripping and the
summary against the real corpus files, which is what the measure is applied to.
`evaluate()` itself is never called here: it writes summary.json beside the runs,
and a test must not rewrite a committed artifact.

Usage:
  pytest evaluation/checks/test_benchmark_metrics.py
"""

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parent
REPO = ROOT.parents[1]
BENCHMARK = REPO / "evaluation" / "benchmark"

_spec = importlib.util.spec_from_file_location(
    "run_benchmark", BENCHMARK / "run_benchmark.py"
)
bench = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bench)

SUMMARY = json.loads((BENCHMARK / "summary.json").read_text(encoding="utf-8"))


def agreement(a: list[str], b: list[str]) -> tuple[float | None, float | None]:
    """The metric on fair tokens that are their own raw form, which holds for
    every token in these cases: none carries a v or a j."""
    return bench.positionwise(a, b, a, b)


# ------------------------------- the metric ---------------------------------


def test_agreement_is_symmetric_on_constructed_tokens() -> None:
    """The old form took both denominators from the first repeat, so the longer
    repeat first and the shorter repeat first gave different numbers."""
    long, short = ["ain", "pett", "in", "der"], ["ain", "pett"]
    assert agreement(long, short) == agreement(short, long)
    # 2*2/(4+2), the Dice form; the recall against the first repeat was 0.5/1.0
    assert agreement(long, short)[0] == 0.667


def test_agreement_is_symmetric_on_every_benchmark_repeat_pair() -> None:
    """The property has to hold on the real material, not only on clean cases."""
    for page in ("rb2_p003", "inv_11330020_p1"):
        runs = sorted(BENCHMARK.glob(f"runs/{page}__it02__r*.json"))
        assert runs, page
        texts = [
            "\n".join(json.loads(f.read_text(encoding="utf-8"))["lines"]) for f in runs
        ]
        fair = [bench.normalize(t, "fair").split() for t in texts]
        raw = [bench.normalize(t, "fair-raw").split() for t in texts]
        for i in range(len(fair)):
            for j in range(i + 1, len(fair)):
                forward = bench.positionwise(fair[i], fair[j], raw[i], raw[j])
                backward = bench.positionwise(fair[j], fair[i], raw[j], raw[i])
                assert forward == backward, (page, i, j, forward, backward)


def test_agreement_never_exceeds_one() -> None:
    """A matched pair counts for a class only where both sides carry that class,
    which is what keeps a numerator inside its denominator."""
    # `vij` classifies as a numeral, its fair form `uii` does not; the pair is
    # therefore counted in neither class and still raises both denominators
    words, numbers = bench.positionwise(["uii"], ["uii"], ["vij"], ["uii"])
    assert words == 0.0
    assert numbers == 0.0


def test_absent_class_reports_nothing_and_two_empty_repeats_agree() -> None:
    """A page carrying no numeral is not a page whose numerals disagree."""
    assert agreement(["ain", "pett"], ["ain", "pett"]) == (1.0, None)
    assert agreement(["x", "iiij"], ["x", "iiij"]) == (None, 1.0)
    assert agreement([], []) == (1.0, None)
    # one side empty is a disagreement, not an absent class
    assert agreement(["ain"], []) == (0.0, None)


# ----------------------------- folio stripping ------------------------------


@pytest.mark.parametrize(
    "marker",
    ["[fol.1r]", "[fol. 7r]", "[fol.12v]", "[1r]", "[1v]", "[12v]", "2[r]"],
)
def test_every_folio_spelling_leaves_the_text(marker: str) -> None:
    for profile in ("fair", "strict"):
        assert (
            bench.normalize(f"{marker}\nItem ain pett", profile)
            .lower()
            .startswith("item")
        ), profile


@pytest.mark.parametrize(
    "line",
    [
        "Nota die dnico an pntibz sup[r]a hat",  # bracketed expansion inside a word
        "vor unnse[r] lieben frawen",
        "It[em] ain pett",
        "Item j alt kestl geht [...] cxx",  # content the run itself marked as lost",
        "Item [---] pett",
    ],
)
def test_a_bracket_that_is_no_folio_marker_survives(line: str) -> None:
    """Only page furniture is removed; a lost-content marker and an expansion
    bracket are statements about the text and stay in both profiles."""
    assert bench.normalize(line, "strict") == line


def test_the_named_reference_pages_carry_no_marker_after_normalisation() -> None:
    """The three pages of the review: two carried the short spelling, the third
    was already stripped and must stay that way."""
    heads = {
        page["id"]: bench.normalize("\n".join(page["gt_lines"]), "fair")
        for page in bench.resolve_pages()
        if page.get("gt_lines")
    }
    assert heads["inv_11328300_p1"].startswith("inuentori")
    assert heads["inv_11328300_p2"].startswith("item i gestreimbts")
    assert heads["inv_11330019_p1"].startswith("kronburg")
    for page_id, text in heads.items():
        assert not bench.FOLIO_MARKER_RE.search(text), page_id


# ------------------------------- the summary --------------------------------


def test_summary_states_the_instrument_it_was_measured_with() -> None:
    assert SUMMARY["temperature"] == bench.TEMPERATURE
    assert SUMMARY["normalisation_profile"] == bench.NORMALISATION_PROFILE


def test_every_page_names_what_it_is_measured_against() -> None:
    for page_id, page in SUMMARY["pages"].items():
        expected = "transkribus-done" if page.get("gt_lines") else "self-consistency"
        assert page["reference_class"] == expected, page_id


def test_a_degenerate_reference_is_a_flag_and_not_a_measured_value() -> None:
    """The flag must follow the stated criterion and must catch every page whose
    rate exceeds one, otherwise a consumer would have to exclude by the value."""
    flagged = set()
    for page_id, page in SUMMARY["pages"].items():
        if page["reference_class"] != "transkribus-done":
            assert "reference_degenerate" not in page, page_id
            continue
        assert page["reference_degenerate"] == (
            page["reference_chars"] < bench.DEGENERATE_REF_CHARS
        ), page_id
        if page["reference_degenerate"]:
            flagged.add(page_id)
        for entry in page["iterations"].values():
            if entry["cer_fair"]["mean"] > 1:
                assert page["reference_degenerate"], page_id
    assert flagged == {"inv_11328300_p4", "inv_11330019_p3"}


def test_a_rate_travels_with_its_distance_and_reference_length() -> None:
    for page_id, page in SUMMARY["pages"].items():
        for iteration, entry in page["iterations"].items():
            where = (page_id, iteration)
            assert ("cer_fair" in entry) == (
                page["reference_class"] == "transkribus-done"
            ), where
            if "cer_fair" not in entry:
                continue
            for field in ("cer_fair", "cer_strict"):
                rates = entry[field]
                assert len(rates["dist"]) == entry["k"], (where, field)
                assert rates["ref_len"] > 0, (where, field)
                recomputed = [round(d / rates["ref_len"], 4) for d in rates["dist"]]
                assert rates["min"] == min(recomputed), (where, field)
                assert rates["max"] == max(recomputed), (where, field)
            assert len(entry["empty"]) == entry["k"], where


# ------------------------------ few-shot pinning ----------------------------


def test_fewshot_hash_pins_the_block_that_goes_into_the_request() -> None:
    example = bench.fewshot_example()
    payload = json.dumps(example["answer"], ensure_ascii=False)
    assert (
        bench.fewshot_hash(example) == hashlib.sha256(payload.encode()).hexdigest()[:16]
    )
    # the block is assembled from the export at runtime and must not drift
    assert bench.fewshot_hash(bench.fewshot_example()) == bench.fewshot_hash(example)


def test_the_fewshot_document_is_in_no_measured_page_set() -> None:
    """An example the model has already been shown would make its own page easy."""
    measured = {page["docId"] for page in bench.resolve_pages() if page.get("docId")}
    assert bench.FEWSHOT_DOC not in {str(doc) for doc in measured}
    for runner in ("pilot/run_pilot.py", "pilot2/run_pilot2.py"):
        source = (REPO / "evaluation" / runner).read_text(encoding="utf-8")
        assert bench.FEWSHOT_DOC not in source, runner
