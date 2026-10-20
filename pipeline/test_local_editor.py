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
import pytest
from io_paths import DATA, load_json, write_json

DOC = 11327963
PAGE = 2


@pytest.mark.parametrize("with_export", [True, False])
def test_alternate_root_uses_its_own_sources_for_view_anchors_and_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, with_export: bool
) -> None:
    """Run startup over a real export copy with a deliberately different reading."""
    root = tmp_path
    pages, _ = _fixture(root / "pipeline")
    data = root / "docs" / "data"
    (data / "transcriptions").mkdir(parents=True)
    for name in (
        "source_mapping.json",
        "sources.json",
        "transkribus_status.json",
        "inventaria_mapping.json",
    ):
        shutil.copy2(DATA / name, data / name)
    mapping = load_json(data / "source_mapping.json")
    mapping["matched"] = [
        entry for entry in mapping["matched"] if entry["transkribus_id"] == DOC
    ]
    write_json(data / "source_mapping.json", mapping)
    export = load_json(DATA / "transcriptions" / f"{DOC}.json")
    source_page = next(page for page in export["pages"] if page["pageNr"] == PAGE)
    line = source_page["regions"][0]["lines"][0]
    isolated_reading = line["text"] + " [isolated source fixture]"
    line["text"] = isolated_reading
    if with_export:
        write_json(data / "transcriptions" / f"{DOC}.json", export)

    # Restore startup's process-wide configuration after this isolated server.
    monkeypatch.setattr(le.br, "DATA", le.br.DATA)
    monkeypatch.setattr(le.bt, "DATA", le.bt.DATA)
    for field in (
        "docs_dir",
        "register_dir",
        "review_dir",
        "annotation_dir",
        "tag_dir",
        "data_dir",
        "token",
        "app_version",
    ):
        monkeypatch.setattr(le.EditorHandler, field, getattr(le.EditorHandler, field))

    class IsolatedServer:
        server_port = 8742

        def serve_forever(self) -> None:
            if not with_export:
                with pytest.raises(FileNotFoundError, match="No transcription"):
                    le.document_payload(DOC, pages)
                with pytest.raises(FileNotFoundError, match="No TEI source"):
                    le.build_tei_documents(
                        {"date": "2026-10-17", "docIds": [DOC]}, pages, data
                    )
                return
            document = le.document_payload(DOC, pages)
            current = next(page for page in document["pages"] if page["pageNr"] == PAGE)
            assert current["regions"][0]["lines"][0]["text"] == isolated_reading
            assert la._lines(DOC, pages)[(PAGE, line["id"])] == isolated_reading
            result = le.build_tei_documents(
                {"date": "2026-10-17", "docIds": [DOC]}, pages, data
            )
            assert result["built"]
            assert isolated_reading in (data / "tei" / f"{DOC}.xml").read_text("utf-8")

        def server_close(self) -> None:
            pass

    monkeypatch.setattr(le, "ThreadingHTTPServer", lambda *_: IsolatedServer())
    monkeypatch.setattr(le.sys, "argv", ["local_editor.py", "--root", str(root)])
    assert le.main() == 0


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


VLM_DOC = 12647153


def _vlm_correction(pages: Path) -> dict:
    document = le.document_payload(VLM_DOC, pages)
    page = document["pages"][0]
    line = next(br.iter_lines(page))
    return {
        "docId": VLM_DOC,
        "baseRevision": document["revision"],
        "reviewer": "XY",
        "pages": {
            str(page["pageNr"]): {
                "status": None,
                "date": "2026-09-21",
                "lines": [
                    {"id": line["id"], "original": line["text"], "corrected": "x"}
                ],
            }
        },
    }


def test_document_payload_carries_the_title_of_a_vlm_document() -> None:
    with tempfile.TemporaryDirectory() as td:
        pages, _ = _fixture(Path(td))
        title = next(
            doc["title"]
            for doc in load_json(pages.parent / "documents.json")
            if doc["docId"] == VLM_DOC
        )
        assert title
        assert le.document_payload(VLM_DOC, pages)["title"] == title


def _project(register_root: Path, summary: Path) -> dict:
    docs = load_json(register_root / "documents.json")
    pages_by_doc = {
        doc["docId"]: load_json(register_root / "pages" / f"{doc['docId']}.json")[
            "pages"
        ]
        for doc in docs
    }
    return br.project(docs, pages_by_doc, summary)


def test_api_build_projection_equals_the_register_projection_for_a_vlm_document() -> (
    None
):
    """The /api/build projection and build_register.project agree field by field."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        pages, reviews = _fixture(tmp)
        data = tmp / "data"
        (data / "entities").mkdir(parents=True)
        # The site projection as published before the correction.
        _project(tmp, data / "pipeline" / "register_summary.json")
        le.save_review(_vlm_correction(pages), pages, reviews)
        le.build_tei_documents({"date": "2026-09-21", "docIds": [VLM_DOC]}, pages, data)

        expected = tmp / "projection" / "register_summary.json"
        projected = _project(tmp, expected)
        assert load_json(data / "pipeline" / "register_summary.json") == projected
        entry = next(d for d in projected["documents"] if d["docId"] == VLM_DOC)
        assert entry["transcription_source"] == "vlm"
        assert entry["effective_transcription"] is True
        built = load_json(data / "pipeline" / "transcriptions" / f"{VLM_DOC}.json")
        assert built["title"] == entry["title"]
        assert built == load_json(
            expected.parent / "transcriptions" / f"{VLM_DOC}.json"
        )


def test_local_payload_and_projection_count_the_same_changed_lines() -> None:
    """Both routes count lines against the machine run, not the previous save."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        pages, reviews = _fixture(tmp)
        request = _vlm_correction(pages)
        page_nr = next(iter(request["pages"]))
        first, second = list(
            br.iter_lines(le.document_payload(VLM_DOC, pages)["pages"][0])
        )[:2]
        request["pages"][page_nr]["lines"].append(
            {"id": second["id"], "original": second["text"], "corrected": "y"}
        )
        le.save_review(request, pages, reviews)
        # Restoring one line to its machine reading leaves one changed line.
        restore = _vlm_correction(pages)
        restore["pages"][page_nr]["lines"] = [
            {"id": first["id"], "original": "x", "corrected": first["text"]}
        ]
        le.save_review(restore, pages, reviews)

        local = le.document_payload(VLM_DOC, pages)
        _project(tmp, tmp / "projection" / "register_summary.json")
        static = load_json(tmp / "projection" / "transcriptions" / f"{VLM_DOC}.json")
        for document in (local, static):
            counts = {
                page["pageNr"]: page["changedLines"]
                for page in document["pages"]
                if "changedLines" in page
            }
            assert counts == {int(page_nr): 1}


def test_failed_register_write_leaves_no_orphan_review_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as td:
        pages, reviews = _fixture(Path(td))
        request = _request(pages, "corrected")
        register = pages / f"{DOC}.json"
        before = register.read_bytes()
        write = le.write_json

        def failing(path: Path, payload: object) -> None:
            if path == register:
                raise OSError("disk full")
            write(path, payload)

        monkeypatch.setattr(le, "write_json", failing)
        with pytest.raises(OSError):
            le.save_review(request, pages, reviews)
        assert register.read_bytes() == before
        assert not list(reviews.iterdir())


def test_publish_rollback_restores_earlier_targets_and_removes_new_ones(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    existing, created, third = (tmp_path / n for n in ("a.xml", "b.json", "c.json"))
    existing.write_bytes(b"prior\n")
    write = le.write_text

    def failing(path: Path, text: str) -> None:
        if path == third:
            raise OSError("disk full")
        write(path, text)

    monkeypatch.setattr(le, "write_text", failing)
    with pytest.raises(OSError):
        le._publish_artifacts({existing: "new", created: "new", third: "new"})
    assert existing.read_bytes() == b"prior\n"
    assert not created.exists() and not third.exists()


ENTITY_DOC = 11328300
TOKEN = "contract-token"


@pytest.fixture(scope="module")
def editor(tmp_path_factory: pytest.TempPathFactory):
    """One loopback server over a scratch register, shared by the contract cases."""
    root = tmp_path_factory.mktemp("editor")
    br.build(root / "pipeline")
    (root / "docs").mkdir()
    (root / "pipeline" / "reviews").mkdir()
    handler = type("ContractHandler", (le.EditorHandler,), {})
    handler.token = TOKEN
    handler.docs_dir = root / "docs"
    handler.register_dir = root / "pipeline" / "pages"
    handler.review_dir = root / "pipeline" / "reviews"
    handler.annotation_dir = root / "pipeline" / "annotations"
    handler.tag_dir = root / "pipeline" / "tags"
    handler.data_dir = root / "docs" / "data"
    shutil.copytree(DATA / "entities", handler.data_dir / "entities")
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield handler, server.server_port
    server.shutdown()
    server.server_close()
    thread.join()


def _call(
    port: int,
    method: str,
    path: str,
    body: object = None,
    headers: dict | None = None,
    raw: bytes | None = None,
) -> tuple[int, str, dict]:
    connection = HTTPConnection("127.0.0.1", port, timeout=60)
    sent = {}
    if method == "POST":
        sent = {"Origin": f"http://127.0.0.1:{port}", "X-DoCTA-Token": TOKEN}
    sent.update(headers or {})
    data = raw if raw is not None else None if body is None else json.dumps(body)
    try:
        connection.request(method, path, data, sent)
        response = connection.getresponse()
        return (
            response.status,
            response.getheader("Content-Type", ""),
            json.loads(response.read()),
        )
    finally:
        connection.close()


def _annotation_payload(port: int) -> dict:
    current = _call(port, "GET", f"/api/annotations/{ENTITY_DOC}")[2]
    entity = load_json(DATA / "entities" / f"{ENTITY_DOC}.json")["entities"][0]
    return {
        "docId": ENTITY_DOC,
        "reviewer": "XY",
        "baseRevision": current["revision"],
        "decisions": [
            {
                "id": entity["id"],
                "kind": [entity["type"]],
                "normalized": entity["normalized"],
                "authority": None,
                "status": ["accepted"],
                "reason": None,
                "textDigest": "0" * 64,
            }
        ],
    }


def _bad_review_dir(handler: type, monkeypatch: pytest.MonkeyPatch) -> None:
    bad = handler.review_dir.parent / "bad-reviews"
    bad.mkdir(exist_ok=True)
    write_json(bad / f"review-{DOC}-broken.json", {"docId": DOC})
    monkeypatch.setattr(handler, "review_dir", bad)


def _bad_tag_sidecar(handler: type, monkeypatch: pytest.MonkeyPatch) -> None:
    bad = handler.tag_dir.parent / "bad-tags"
    bad.mkdir(exist_ok=True)
    write_json(bad / f"{DOC}.json", [])
    monkeypatch.setattr(handler, "tag_dir", bad)


def _patch(target: object, name: str, exc: BaseException):
    def fail(*_: object, **__: object) -> None:
        raise exc

    return lambda handler, monkeypatch: monkeypatch.setattr(target, name, fail)


def _body(body: object = None, headers: dict | None = None, raw: bytes | None = None):
    return lambda port: (body, headers, raw)


ANY = "<any message>"

# name: (method, path, request, setup, status, error). The request returns
# (body, headers, raw bytes); an error of None expects a success payload.
CONTRACT = {
    "untrusted host": (
        "GET",
        f"/api/documents/{DOC}",
        _body(headers={"Host": "attacker.example"}),
        None,
        403,
        "untrusted host",
    ),
    "missing token": (
        "POST",
        "/api/review",
        _body({}, {"X-DoCTA-Token": ""}),
        None,
        403,
        "write authorization failed",
    ),
    "unknown get path": ("GET", "/api/nothing", None, None, 404, "not found"),
    "unknown post path": ("POST", "/api/nothing", None, None, 404, "not found"),
    "unknown document": ("GET", "/api/documents/999", None, None, 404, ANY),
    "non-digit document id": (
        "GET",
        "/api/documents/12a",
        None,
        None,
        400,
        "invalid document id",
    ),
    "non-ascii digit tag id": (
        "GET",
        "/api/tags/%C2%B2",
        None,
        None,
        400,
        "invalid document id",
    ),
    "non-digit annotation id": (
        "GET",
        "/api/annotations/x",
        None,
        None,
        400,
        "invalid document id",
    ),
    "invalid content length": (
        "POST",
        "/api/review",
        _body(headers={"Content-Length": "abc"}, raw=b"{}"),
        None,
        413,
        "invalid body size",
    ),
    "oversize body": (
        "POST",
        "/api/review",
        _body(headers={"Content-Length": str(le.MAX_BODY + 1)}, raw=b"{}"),
        None,
        413,
        "invalid body size",
    ),
    "malformed json": (
        "POST",
        "/api/review",
        _body(raw=b"{"),
        None,
        400,
        "invalid JSON",
    ),
    "review contract": ("POST", "/api/review", _body({"docId": "1"}), None, 400, ANY),
    "stale review": (
        "POST",
        "/api/review",
        _body({"docId": DOC, "baseRevision": "0" * 64}),
        None,
        409,
        "stale revision",
    ),
    "review for unknown document": (
        "POST",
        "/api/review",
        _body({"docId": 999, "baseRevision": "0" * 64}),
        None,
        404,
        ANY,
    ),
    "malformed stored review": (
        "GET",
        f"/api/documents/{DOC}",
        None,
        _bad_review_dir,
        500,
        ANY,
    ),
    "forced document read OSError": (
        "GET",
        f"/api/documents/{DOC}",
        None,
        _patch(le, "document_payload", OSError("disk")),
        500,
        "disk",
    ),
    "unexpected document failure": (
        "GET",
        f"/api/documents/{DOC}",
        None,
        _patch(le, "document_payload", KeyError("x")),
        500,
        "internal error",
    ),
    "forced review write OSError": (
        "POST",
        "/api/review",
        _body({"docId": DOC}),
        _patch(le, "save_review", OSError("disk")),
        500,
        "disk",
    ),
    "unexpected review failure": (
        "POST",
        "/api/review",
        _body({"docId": DOC}),
        _patch(le, "save_review", KeyError("x")),
        500,
        "internal error",
    ),
    "annotation kind of the wrong type": (
        "POST",
        "/api/annotations",
        lambda port: (_annotation_payload(port), None, None),
        None,
        400,
        ANY,
    ),
    "stale annotation": (
        "POST",
        "/api/annotations",
        _body({"docId": ENTITY_DOC, "baseRevision": "x"}),
        None,
        409,
        ANY,
    ),
    "registry read": ("GET", "/api/registry", None, None, 200, None),
    "registry not an object": (
        "POST",
        "/api/registry",
        _body([]),
        None,
        400,
        ANY,
    ),
    "stale registry": (
        "POST",
        "/api/registry",
        _body({"baseRevision": "x"}),
        None,
        409,
        ANY,
    ),
    "forced registry read OSError": (
        "GET",
        "/api/registry",
        None,
        _patch(le.registry, "read_registry", OSError("disk")),
        500,
        "disk",
    ),
    "build with an impossible date": (
        "POST",
        "/api/build",
        _body({"date": "2026-02-30", "docIds": [DOC]}),
        None,
        400,
        ANY,
    ),
    "build without documents": (
        "POST",
        "/api/build",
        _body({"date": "2026-02-03", "docIds": []}),
        None,
        400,
        ANY,
    ),
    "tags read": ("GET", f"/api/tags/{DOC}", None, None, 200, None),
    "malformed tag sidecar": (
        "GET",
        f"/api/tags/{DOC}",
        None,
        _bad_tag_sidecar,
        500,
        ANY,
    ),
    "tags for unknown document": ("GET", "/api/tags/999", None, None, 404, ANY),
    "tag payload not an object": ("POST", "/api/tags", _body([]), None, 400, ANY),
    "stale tags": (
        "POST",
        "/api/tags",
        _body({"docId": DOC, "baseRevision": "x"}),
        None,
        409,
        ANY,
    ),
}


@pytest.mark.parametrize("case", CONTRACT)
def test_every_api_failure_is_a_json_answer_with_its_status(
    editor: tuple[type, int], monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    handler, port = editor
    method, path, request, setup, status, error = CONTRACT[case]
    if setup is not None:
        setup(handler, monkeypatch)
    body, headers, raw = request(port) if request else (None, None, None)
    if method == "POST" and body is None and raw is None:
        raw = b"{}"
    got, content_type, payload = _call(port, method, path, body, headers, raw)
    assert got == status, payload
    assert content_type.startswith("application/json")
    if error is None:
        assert "error" not in payload
    else:
        assert isinstance(payload["error"], str) and payload["error"]
        if error is not ANY:
            assert payload["error"] == error
