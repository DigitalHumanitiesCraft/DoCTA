"""The corpus-wide entity index: slugs, merging, ordering."""

import entity_index as ei


def _extraction(doc_id, entities):
    return {"docId": doc_id, "provenance": {"source": "llm"}, "entities": entities}


def _entity(**kw):
    base = {
        "id": "e1",
        "text": "",
        "normalized": "",
        "type": "person",
        "pageNr": 1,
        "lineId": "r1l1",
        "role": "",
    }
    return base | kw


def test_slugify_german_convention():
    assert ei.slugify("Kürass") == "kuerass"
    assert ei.slugify("Groß & Klein") == "gross-klein"
    assert ei.slugify("Bär") == "baer"
    assert ei.slugify("---") == "x"


def test_merge_across_documents_collects_forms_roles_attestations():
    a = _extraction(
        1, [_entity(text="Hannsen Clamer", normalized="Hans Clamer", role="Pfleger")]
    )
    b = _extraction(
        2, [_entity(text="Hans Clamer", normalized="Hans Clamer", lineId="r2l4")]
    )
    entries = ei.build_index([a, b])
    assert len(entries) == 1
    entry = entries[0]
    assert entry["id"] == "per-hans-clamer"
    assert entry["forms"] == ["Hannsen Clamer", "Hans Clamer"]
    assert entry["roles"] == ["Pfleger"]
    assert [att["docId"] for att in entry["attestations"]] == [1, 2]


def test_same_normalized_form_different_type_stays_separate():
    ex = _extraction(
        1,
        [
            _entity(id="p1", normalized="Thaur", type="place"),
            _entity(id="o1", normalized="Thaur", type="object", lineId="r1l2"),
        ],
    )
    ids = {e["id"] for e in ei.build_index([ex])}
    assert ids == {"pl-thaur", "obj-thaur"}


def test_slug_collision_gets_deterministic_suffix():
    ex = _extraction(
        1,
        [
            _entity(id="o1", normalized="Bar", type="object"),
            _entity(id="o2", normalized="Bär", type="object", lineId="r1l2"),
        ],
    )
    ids = [e["id"] for e in ei.build_index([ex])]
    assert sorted(ids) == ["obj-baer", "obj-bar"]
    # No collision here; the suffix case needs two forms folding to one slug.
    ex2 = _extraction(
        1,
        [
            _entity(id="o1", normalized="Maß", type="object"),
            _entity(id="o2", normalized="Mass", type="object", lineId="r1l2"),
        ],
    )
    ids2 = [e["id"] for e in ei.build_index([ex2])]
    assert ids2 == ["obj-mass", "obj-mass-2"]


def test_time_entities_are_excluded():
    ex = _extraction(1, [_entity(normalized="1478", type="time")])
    assert ei.build_index([ex]) == []


def test_attestation_order_is_by_document_page_line():
    ex = _extraction(
        1,
        [
            _entity(
                id="a", normalized="Kronburg", type="place", pageNr=2, lineId="r1l1"
            ),
            _entity(
                id="b", normalized="Kronburg", type="place", pageNr=1, lineId="r10l2"
            ),
            _entity(
                id="c", normalized="Kronburg", type="place", pageNr=1, lineId="r2l11"
            ),
        ],
    )
    entry = ei.build_index([ex])[0]
    loci = [(att["page"], att["line"]) for att in entry["attestations"]]
    assert loci == [(1, "r2l11"), (1, "r10l2"), (2, "r1l1")]
