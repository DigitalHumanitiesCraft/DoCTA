"""Integration checks for the loopback editor persistence boundary."""

import copy
import json
import shutil
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path

import build_register as br
import local_annotations as la
import local_editor as le
from io_paths import DATA, load_json, write_json

DOC = 11327963
PAGE = 2


def test_api_host_allowlist_rejects_dns_rebinding_names() -> None:
    assert le.allowed_host("127.0.0.1:8743", 8743)
    assert le.allowed_host("localhost:8743", 8743)
    assert not le.allowed_host("attacker.example:8743", 8743)
    assert not le.allowed_host("127.0.0.1:9999", 8743)


def test_tag_http_route_requires_same_origin_token() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        br.build(root / "pipeline")
        docs = root / "docs"
        docs.mkdir()
        handler = type("TestEditorHandler", (le.EditorHandler,), {})
        handler.token = "test-token"
        handler.docs_dir = docs
        handler.register_dir = root / "pipeline" / "pages"
        handler.tag_dir = root / "pipeline" / "tags"
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = server.server_port
            connection = HTTPConnection("127.0.0.1", port)
            connection.request("GET", f"/api/tags/{DOC}")
            current = json.loads(connection.getresponse().read())
            line = _request(handler.register_dir)["pages"][str(PAGE)]["lines"][0]
            body = json.dumps(
                {
                    "docId": DOC,
                    "baseRevision": current["revision"],
                    "sourceRevision": current["sourceRevision"],
                    "action": "add",
                    "tag": {
                        "pageNr": PAGE,
                        "lineId": line["id"],
                        "tag": "Test",
                        "note": "",
                        "reviewer": "XY",
                    },
                }
            )
            connection.request(
                "POST",
                "/api/tags",
                body,
                {
                    "Content-Type": "application/json",
                    "Origin": f"http://127.0.0.1:{port}",
                },
            )
            denied = connection.getresponse()
            assert denied.status == 403
            denied.read()
            connection.request(
                "POST",
                "/api/tags",
                body,
                {
                    "Content-Type": "application/json",
                    "Origin": f"http://127.0.0.1:{port}",
                    "X-DoCTA-Token": "test-token",
                },
            )
            response = connection.getresponse()
            assert response.status == 200
            assert json.loads(response.read())["saved"] is True
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


def _fixture(tmp: Path) -> tuple[Path, Path]:
    br.build(tmp)
    reviews = tmp / "reviews"
    reviews.mkdir()
    return tmp / "pages", reviews


def _request(pages: Path, corrected: str = "") -> dict:
    document = le.document_payload(DOC, pages)
    page = next(page for page in document["pages"] if page["pageNr"] == PAGE)
    line = page["regions"][0]["lines"][0]
    return {
        "docId": DOC,
        "baseRevision": document["revision"],
        "reviewer": "XY",
        "pages": {
            str(PAGE): {
                "status": "gesichtet",
                "date": "2026-09-21",
                "lines": [
                    {"id": line["id"], "original": line["text"], "corrected": corrected}
                ],
            }
        },
        "effort": {"activeSeconds": 12.5, "decisionCount": 1},
    }


def test_saved_empty_reading_survives_a_fresh_load() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        pages, reviews = _fixture(tmp)
        request = _request(pages)
        saved = le.save_review(request, pages, reviews)
        line = next(
            line
            for page in saved["pages"]
            if page["pageNr"] == PAGE
            for region in page["regions"]
            for line in region["lines"]
            if line["id"] == request["pages"][str(PAGE)]["lines"][0]["id"]
        )
        assert line["text"] == ""
        assert le.document_payload(DOC, pages)["revision"] == saved["revision"]
        canonical = list(reviews.glob("review-*.json"))
        assert len(canonical) == 1
        assert load_json(canonical[0])["effort"]["activeSeconds"] == 12.5


def test_same_day_later_reviewer_wins_after_reload_and_rebuild() -> None:
    """Restore a real source reading after an empty-reading boundary correction."""
    with tempfile.TemporaryDirectory() as td:
        pages, reviews = _fixture(Path(td))
        first = _request(pages)
        original = first["pages"][str(PAGE)]["lines"][0]["original"]
        first["reviewer"] = "ZZ"
        le.save_review(first, pages, reviews)
        second = _request(pages, original)
        second["reviewer"] = "AA"
        saved = le.save_review(second, pages, reviews)
        line_id = second["pages"][str(PAGE)]["lines"][0]["id"]
        for document in (saved, le.document_payload(DOC, pages)):
            page = next(item for item in document["pages"] if item["pageNr"] == PAGE)
            line = next(item for item in br.iter_lines(page) if item["id"] == line_id)
            assert line["text"] == original
        br.build(pages.parent)
        rebuilt = le.document_payload(DOC, pages)
        page = next(item for item in rebuilt["pages"] if item["pageNr"] == PAGE)
        assert (
            next(item for item in br.iter_lines(page) if item["id"] == line_id)["text"]
            == original
        )
        stored = load_json(pages / f"{DOC}.json")
        page = next(item for item in stored["pages"] if item["pageNr"] == PAGE)
        assert br.newest_review_run(page)["reviewer"] == "AA"
        assert br.newest_review_run(page)["timestamp"].endswith("Z")


def test_stale_revision_writes_neither_register_nor_review() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        pages, reviews = _fixture(tmp)
        request = _request(pages, "corrected")
        request["baseRevision"] = "0" * 64
        before = (pages / f"{DOC}.json").read_bytes()
        try:
            le.save_review(request, pages, reviews)
        except RuntimeError as exc:
            assert str(exc) == "stale revision"
        else:
            raise AssertionError("stale request was accepted")
        assert (pages / f"{DOC}.json").read_bytes() == before
        assert not list(reviews.iterdir())


def test_concurrent_saves_with_one_revision_accept_exactly_one() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        pages, reviews = _fixture(tmp)
        request = _request(pages, "corrected")

        def attempt() -> str:
            try:
                le.save_review(copy.deepcopy(request), pages, reviews)
            except RuntimeError as exc:
                return str(exc)
            return "saved"

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: attempt(), range(2)))
        assert sorted(results) == ["saved", "stale revision"]
        assert len(list(reviews.glob("review-*.json"))) == 1
        assert not list(tmp.rglob("*.tmp"))


def test_invalid_line_writes_neither_register_nor_review() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        pages, reviews = _fixture(tmp)
        request = _request(pages, "corrected")
        broken = copy.deepcopy(request)
        broken["pages"][str(PAGE)]["lines"][0]["id"] = "unknown"
        before = (pages / f"{DOC}.json").read_bytes()
        try:
            le.save_review(broken, pages, reviews)
        except Exception as exc:
            assert "steht nicht im Register" in str(exc)
        else:
            raise AssertionError("unknown line was accepted")
        assert (pages / f"{DOC}.json").read_bytes() == before
        assert not list(reviews.iterdir())


def test_concurrent_annotation_saves_accept_exactly_one() -> None:
    entity_doc = 11328300
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        br.build(tmp)
        sidecars = tmp / "annotations"
        current = la.read_decisions(entity_doc, sidecars)
        entity = load_json(DATA / "entities" / f"{entity_doc}.json")["entities"][0]
        transcription = br.transcription_of(entity_doc, tmp / "pages")
        line = next(
            line
            for page in transcription["pages"]
            if page["pageNr"] == entity["pageNr"]
            for region in page["regions"]
            for line in region["lines"]
            if line["id"] == entity["lineId"]
        )
        payload = {
            "docId": entity_doc,
            "reviewer": "XY",
            "baseRevision": current["revision"],
            "decisions": [
                {
                    "id": entity["id"],
                    "kind": entity["type"],
                    "normalized": entity["normalized"],
                    "authority": None,
                    "status": "accepted",
                    "reason": None,
                    "textDigest": la.line_digest(line["text"]),
                }
            ],
        }

        def attempt() -> str:
            try:
                la.save_decisions(copy.deepcopy(payload), tmp / "pages", sidecars)
            except RuntimeError as exc:
                return str(exc)
            return "saved"

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: attempt(), range(2)))
        assert sorted(results) == ["saved", "stale revision"]


def test_annotation_boundary_rejects_invalid_curated_values() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        br.build(tmp)
        for payload in ([], "not an object"):
            try:
                la.save_decisions(payload, tmp / "pages", tmp / "annotations")
            except ValueError:
                pass
            else:
                raise AssertionError("non-object annotation payload accepted")


def test_one_stale_annotation_can_be_rechecked_while_another_is_unchanged() -> None:
    entity_doc = 11328300
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        br.build(tmp)
        sidecars = tmp / "annotations"
        extraction = load_json(DATA / "entities" / f"{entity_doc}.json")["entities"]
        transcription = br.transcription_of(entity_doc, tmp / "pages")
        lines = {
            (page["pageNr"], line["id"]): line["text"]
            for page in transcription["pages"]
            for region in page["regions"]
            for line in region["lines"]
        }

        def decision(entity: dict, digest: str) -> dict:
            return {
                "id": entity["id"],
                "kind": entity["type"],
                "normalized": entity["normalized"],
                "authority": None,
                "status": "accepted",
                "reason": None,
                "textDigest": digest,
            }

        first, second = extraction[:2]
        stale = [decision(first, "0" * 64), decision(second, "0" * 64)]
        write_json(
            sidecars / f"{entity_doc}.json", {"docId": entity_doc, "decisions": stale}
        )
        current = la.read_decisions(entity_doc, sidecars)
        first_checked = copy.deepcopy(stale)
        first_checked[0]["textDigest"] = la.line_digest(
            lines[(first["pageNr"], first["lineId"])]
        )
        saved = la.save_decisions(
            {
                "reviewer": "XY",
                "docId": entity_doc,
                "baseRevision": current["revision"],
                "decisions": first_checked,
            },
            tmp / "pages",
            sidecars,
        )
        second_checked = copy.deepcopy(saved["decisions"])
        second_checked[1]["textDigest"] = la.line_digest(
            lines[(second["pageNr"], second["lineId"])]
        )
        final = la.save_decisions(
            {
                "reviewer": "XY",
                "docId": entity_doc,
                "baseRevision": saved["revision"],
                "decisions": second_checked,
            },
            tmp / "pages",
            sidecars,
        )
        assert all(item["textDigest"] != "0" * 64 for item in final["decisions"])


def test_selected_tei_build_writes_valid_document_and_static_projection() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        pages, reviews = _fixture(tmp)
        le.save_review(_request(pages, "corrected"), pages, reviews)
        data = tmp / "data"
        (data / "entities").mkdir(parents=True)
        entity = next((DATA / "entities").glob("*.json"))
        shutil.copy2(entity, data / "entities" / entity.name)
        summary = data / "pipeline" / "register_summary.json"
        summary.parent.mkdir(parents=True)
        summary.write_text(
            '{"documents":[{"docId":11327963,"verification":{}}]}',
            encoding="utf-8",
        )
        result = le.build_tei_documents(
            {"date": "2026-09-21", "docIds": [DOC]}, pages, data
        )
        assert result["built"] is True
        assert (data / "tei" / f"{DOC}.xml").is_file()
        assert (data / "tei" / "register.xml").is_file()
        projection = data / "pipeline" / "transcriptions" / f"{DOC}.json"
        assert projection.is_file()
        assert load_json(projection)["docId"] == DOC
        projected = load_json(summary)["documents"][0]
        assert projected["effective_transcription"] is True
