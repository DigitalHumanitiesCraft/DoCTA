"""The JSON-LD graph builder: shape, links, determinism."""

import json

import build_graph as bg


def _write_extraction(tmp_path, doc_id, title, entities):
    payload = {
        "docId": doc_id,
        "title": title,
        "provenance": {"source": "llm", "model": "m", "date": "2026-08-27"},
        "entities": entities,
    }
    (tmp_path / f"{doc_id}.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )


def _fixture_dir(tmp_path):
    _write_extraction(
        tmp_path,
        11,
        "Kronburg_TLA Inventare A 144.1_1478",
        [
            {
                "id": "p1",
                "text": "Hannsen Clamer",
                "normalized": "Hans Clamer",
                "type": "person",
                "pageNr": 1,
                "lineId": "r3l3",
                "role": "Pfleger",
            },
            {
                "id": "pl1",
                "text": "Kronburg",
                "normalized": "Kronburg",
                "type": "place",
                "pageNr": 1,
                "lineId": "r3l3",
                "role": "",
            },
            {
                "id": "t1",
                "text": "anno LXXVIII",
                "normalized": "1478",
                "type": "time",
                "pageNr": 1,
                "lineId": "r3l9",
                "role": "",
            },
        ],
    )
    _write_extraction(
        tmp_path,
        12,
        "Thaur_TLA Inventare A 49.1_1471",
        [
            {
                "id": "pl1",
                "text": "Kronburg",
                "normalized": "Kronburg",
                "type": "place",
                "pageNr": 2,
                "lineId": "r1l1",
                "role": "",
            },
        ],
    )
    return tmp_path


def _by_id(payload):
    return {node["@id"]: node for node in payload["@graph"]}


def test_graph_holds_documents_entities_and_cooccurrence(tmp_path):
    payload = bg.build(_fixture_dir(tmp_path))
    nodes = _by_id(payload)
    assert nodes["docta:doc-11"]["label"] == "Kronburg, TLA Inventare A 144.1 (1478)"
    person = nodes["docta:per-hans-clamer"]
    assert person["@type"] == "docta:Person"
    assert person["role"] == ["Pfleger"]
    assert person["attestedIn"] == ["docta:doc-11"]
    place = nodes["docta:pl-kronburg"]
    assert place["attestedIn"] == ["docta:doc-11", "docta:doc-12"]
    cooc = nodes["docta:cooc-per-hans-clamer--pl-kronburg"]
    assert cooc["count"] == 1
    assert cooc["attestation"] == [{"docId": 11, "page": 1, "line": "r3l3"}]


def test_time_entities_enter_no_node(tmp_path):
    nodes = _by_id(bg.build(_fixture_dir(tmp_path)))
    assert not any("1478" in i for i in nodes)


def test_ids_are_unique_and_context_present(tmp_path):
    payload = bg.build(_fixture_dir(tmp_path))
    ids = [node["@id"] for node in payload["@graph"]]
    assert len(ids) == len(set(ids))
    assert payload["@context"]["docta"] == "https://dhcraft.org/DoCTA/ns#"
    assert payload["provenance"]["aggregation"]["source"] == "workflow"
    assert [p["docId"] for p in payload["provenance"]["identification"]] == [11, 12]


def test_build_is_deterministic(tmp_path):
    fixture = _fixture_dir(tmp_path)
    first = json.dumps(bg.build(fixture), ensure_ascii=False, sort_keys=True)
    second = json.dumps(bg.build(fixture), ensure_ascii=False, sort_keys=True)
    assert first == second


def test_real_corpus_builds_and_every_member_resolves():
    payload = bg.build()
    nodes = _by_id(payload)
    for node in payload["@graph"]:
        for ref in node.get("member", []) + node.get("attestedIn", []):
            assert ref in nodes, f"dangling reference {ref}"
    # The extracted documents carry Inventaria transcriptions; the attribution
    # must travel on their nodes.
    docs = [n for n in payload["@graph"] if n["@type"] == "docta:Document"]
    assert docs and all(d.get("transcriptionBy") == "Inventaria" for d in docs)
