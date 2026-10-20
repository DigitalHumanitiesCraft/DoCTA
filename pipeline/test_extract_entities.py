"""The deterministic half of the entity extraction: line index, prompt text,
verbatim location and post-validation.

None of these functions touches the network or the API key, so the tests run
offline. The model's answer is the untrusted input here; what these tests pin is
that only an entity proven by its named line survives, and that its stored
surface form is the raw substring of the transcription, byte for byte.
"""

import pytest
from extract_entities import assert_verbatim, load_lines, locate, serialize, validate

# "Mu" plus a combining diaeresis: the decomposed spelling a minority of
# Transkribus lines carry, which a model tends to return precomposed.
DECOMPOSED = "München"

DOC = {
    "docId": 1,
    "title": "Raitbuch",
    "pages": [
        {
            "pageNr": 1,
            "regions": [
                {
                    "id": "r1",
                    "lines": [
                        {"id": "r1l1", "text": "Item Hanns Keller zu Hall"},
                        {"id": "r1l2", "text": f"ain harnasch von {DECOMPOSED}"},
                    ],
                },
            ],
        },
        {
            "pageNr": 2,
            "regions": [
                # Region ids restart per page: r1l1 again, on another page.
                {"id": "r1", "lines": [{"id": "r1l1", "text": "Hall und Hanns"}]},
                {"id": "r2", "lines": [{"id": "r2l1", "text": "Summa"}]},
            ],
        },
    ],
}


def test_the_line_index_is_page_qualified_and_in_document_order() -> None:
    index = load_lines(DOC)
    assert list(index) == ["p1_r1l1", "p1_r1l2", "p2_r1l1", "p2_r2l1"]
    assert index["p2_r1l1"] == {
        "pageNr": 2,
        "lineId": "r1l1",
        "text": "Hall und Hanns",
        "order": 2,
    }


def test_a_duplicate_line_id_on_one_page_aborts() -> None:
    page = {"pageNr": 1, "regions": [{"lines": [{"id": "l1", "text": "a"}] * 2}]}
    with pytest.raises(SystemExit):
        load_lines({"docId": 9, "pages": [page]})


def test_the_prompt_text_tags_every_line_with_its_qualified_id() -> None:
    assert serialize(DOC) == (
        "DOKUMENT: Raitbuch\n"
        "\n== Seite 1 ==\n"
        "p1_r1l1\tItem Hanns Keller zu Hall\n"
        f"p1_r1l2\tain harnasch von {DECOMPOSED}\n"
        "\n== Seite 2 ==\n"
        "p2_r1l1\tHall und Hanns\n"
        "p2_r2l1\tSumma"
    )


@pytest.mark.parametrize(
    ("line", "surface", "expected"),
    [
        ("Item Hanns Keller", "Hanns", "Hanns"),
        ("Item Hanns Keller", "Hans", None),
        ("Item Hanns Keller", "", None),
        # Precomposed surface against a decomposed line: the raw substring comes
        # back, not the model's spelling.
        (f"von {DECOMPOSED}", "München", DECOMPOSED),
        (f"von {DECOMPOSED}", DECOMPOSED, DECOMPOSED),
        ("von München", "Munchen", None),
    ],
)
def test_locate_returns_the_raw_substring_or_none(line, surface, expected) -> None:
    assert locate(line, surface) == expected


def _entity(line_id: str, text: str, etype: str = "person", **extra) -> dict:
    return {"lineId": line_id, "text": text, "normalized": "", "type": etype, **extra}


@pytest.mark.parametrize(
    ("item", "reason"),
    [
        (_entity("p1_r1l1", "Hanns", "ship"), "type_invalid"),
        (_entity("r1l1", "Hanns"), "line_unknown"),
        (_entity("p9_r1l1", "Hanns"), "line_unknown"),
        (_entity("p1_r1l1", "Hans"), "not_verbatim"),
        (_entity("p2_r1l1", "Keller"), "not_verbatim"),
    ],
)
def test_validate_rejects_an_entity_its_line_does_not_prove(item, reason) -> None:
    kept, rejected = validate([item], load_lines(DOC))
    assert kept == []
    assert [r["reason"] for r in rejected] == [reason]


def test_a_not_verbatim_rejection_keeps_the_line_for_inspection() -> None:
    _, rejected = validate([_entity("p1_r1l1", "Hans")], load_lines(DOC))
    assert rejected[0]["lineText"] == "Item Hanns Keller zu Hall"


def test_the_second_identical_claim_on_a_line_is_a_duplicate() -> None:
    raw = [_entity("p1_r1l1", "Hanns"), _entity("p1_r1l1", " Hanns ")]
    kept, rejected = validate(raw, load_lines(DOC))
    assert [e["text"] for e in kept] == ["Hanns"]
    assert [r["reason"] for r in rejected] == ["duplicate"]


def test_kept_entities_are_ordered_by_line_and_offset_and_numbered_per_type() -> None:
    """The model's order is arbitrary; ids follow the reading order of the source."""
    raw = [
        _entity("p2_r1l1", "Hall", "place"),
        _entity("p1_r1l1", "Hall", "place"),
        _entity("p1_r1l2", "München", "place", normalized="München"),
        _entity("p1_r1l1", "Hanns Keller", "person", role=" Schuldner "),
        _entity("p1_r1l2", "harnasch", "object"),
    ]
    kept, rejected = validate(raw, load_lines(DOC))
    assert rejected == []
    assert [(e["id"], e["pageNr"], e["lineId"], e["text"]) for e in kept] == [
        ("p1", 1, "r1l1", "Hanns Keller"),
        ("pl1", 1, "r1l1", "Hall"),
        ("o1", 1, "r1l2", "harnasch"),
        ("pl2", 1, "r1l2", DECOMPOSED),
        ("pl3", 2, "r1l1", "Hall"),
    ]
    # An empty normalized form falls back to the stored surface; role is trimmed.
    assert kept[0]["normalized"] == "Hanns Keller"
    assert kept[0]["role"] == "Schuldner"
    assert kept[3]["normalized"] == "München"
    assert all("_order" not in e for e in kept)


def test_assert_verbatim_accepts_what_validate_kept() -> None:
    index = load_lines(DOC)
    kept, _ = validate([_entity("p1_r1l2", "München", "place")], index)
    assert_verbatim(kept, index)


@pytest.mark.parametrize(
    "entity",
    [
        {"id": "p1", "text": "Hans", "pageNr": 1, "lineId": "r1l1"},
        # Right text, wrong page: r1l1 on page 2 does not hold "Keller".
        {"id": "p1", "text": "Keller", "pageNr": 2, "lineId": "r1l1"},
        {"id": "p1", "text": "Hanns", "pageNr": 1, "lineId": "r1l1", "confidence": 1},
    ],
)
def test_assert_verbatim_raises_on_an_unproven_or_scored_entity(entity) -> None:
    with pytest.raises(ValueError, match="p1"):
        assert_verbatim([entity], load_lines(DOC))
