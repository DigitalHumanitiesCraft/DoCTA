"""Serve the DoCTA site and persist local scholarly review decisions.

The stdlib server binds to loopback, serves only ``docs/``, and exposes a small
same-origin API over the page register. Writes use the existing review ingest
contract, optimistic revision checks and atomic replacement. Source exports are
never changed. Run with ``uv run python pipeline/local_editor.py``.

The local editing architecture is specified in ``docs/knowledge/specification.md``.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import secrets
import sys
import tempfile
from collections import Counter
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

import apply_review as ar
import build_graph as bg
import build_register as br
import build_tei as bt
import local_annotations as annotations
import validate_tei as vt
from io_paths import DATA, PIPELINE_DIR, REPO_ROOT, load_json, write_json, write_text

DOCS = REPO_ROOT / "docs"
REGISTER = PIPELINE_DIR / "pages"
MAX_BODY = 256 * 1024


def allowed_host(host: str | None, port: int) -> bool:
    return host in (f"127.0.0.1:{port}", f"localhost:{port}")


def revision(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def document_payload(doc_id: int, register_dir: Path = REGISTER) -> dict:
    path = register_dir / f"{doc_id}.json"
    if not path.is_file():
        raise FileNotFoundError(f"No register for document {doc_id}")
    register = load_json(path)
    transcription = br.transcription_of(doc_id, register_dir, register.get("title"))
    if transcription is None:
        raise FileNotFoundError(f"No transcription for document {doc_id}")
    states = {
        str(page["pageNr"]): page.get("verification", {"status": "unbearbeitet"})
        for page in register["pages"]
    }
    transcription["revision"] = revision(path)
    transcription["reviewState"] = states
    return transcription


def save_review(
    payload: dict, register_dir: Path = REGISTER, review_dir: Path | None = None
) -> dict:
    with ar.review_lock(register_dir):
        if not isinstance(payload, dict):
            raise ar.ReviewError("request: kein JSON-Objekt")
        doc_id = payload.get("docId")
        if not isinstance(doc_id, int) or isinstance(doc_id, bool):
            raise ar.ReviewError("request: docId fehlt oder ist keine ganze Zahl")
        path = register_dir / f"{doc_id}.json"
        if not path.is_file():
            raise FileNotFoundError(f"No register for document {doc_id}")
        base_revision = payload.get("baseRevision")
        if not isinstance(base_revision, str) or base_revision != revision(path):
            raise RuntimeError("stale revision")

        now = datetime.now(UTC)
        review = {
            "schemaVersion": 2,
            "source": ar.SOURCE,
            "exported": now.isoformat().replace("+00:00", "Z"),
            "reviewId": now.strftime("%H%M%S%f"),
            "docId": doc_id,
            "reviewer": payload.get("reviewer"),
            "pages": payload.get("pages"),
            "effort": payload.get("effort"),
        }
        pages = ar.validate(review, "request")
        register = copy.deepcopy(load_json(path))
        ar.apply_document(register, review, pages, "request")
        canonical = (review_dir or PIPELINE_DIR / "reviews") / (
            f"review-{doc_id}-{review['reviewId']}.json"
        )
        write_json(canonical, review)
        try:
            write_json(path, register)
        except OSError as exc:
            raise RuntimeError(
                f"register write failed; recover by replaying {canonical.name}"
            ) from exc
        return document_payload(doc_id, register_dir)


def build_tei_documents(
    payload: dict,
    register_dir: Path = REGISTER,
    data_dir: Path = DATA,
    annotation_dir: Path | None = None,
) -> dict:
    with ar.review_lock(register_dir):
        return _build_tei_documents(
            payload,
            register_dir,
            data_dir,
            annotation_dir or register_dir.parent / "annotations",
        )


def _publish_artifacts(artifacts: dict[Path, str]) -> None:
    """Replace a coherent build set, restoring every prior file on failure."""
    prior = {path: path.read_bytes() if path.exists() else None for path in artifacts}
    written: list[Path] = []
    try:
        for path, content in artifacts.items():
            write_text(path, content)
            written.append(path)
    except OSError:
        for path in reversed(written):
            old = prior[path]
            if old is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(old)
        raise


def _build_tei_documents(
    payload: dict, register_dir: Path, data_dir: Path, annotation_dir: Path
) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("build payload must be an object")
    date = payload.get("date")
    doc_ids = payload.get("docIds")
    if not isinstance(date, str):
        raise ValueError("date must be YYYY-MM-DD")
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("date must be YYYY-MM-DD") from exc
    if (
        not isinstance(doc_ids, list)
        or not doc_ids
        or any(not isinstance(item, int) or isinstance(item, bool) for item in doc_ids)
    ):
        raise ValueError("docIds must be a non-empty integer list")
    selected = sorted(set(doc_ids))
    with tempfile.TemporaryDirectory() as td:
        temp = Path(td)
        entity_dir = data_dir / "entities"
        built = bt.build(
            temp,
            date,
            register_dir,
            entity_dir=entity_dir,
            annotation_dir=annotation_dir,
        )
        missing = [doc_id for doc_id in selected if doc_id not in built]
        if missing:
            raise FileNotFoundError(f"No TEI source for documents: {missing}")
        files = [temp / f"{doc_id}.xml" for doc_id in built]
        register_xml = temp / bt.REGISTER_FILE
        if register_xml.exists():
            files.append(register_xml)
        for label, schema in vt.STAGES:
            if invalid := vt.run_stage(label, files, schema, vt.DEFAULT_MAX_ERRORS):
                raise RuntimeError(
                    "TEI validation failed for "
                    + ", ".join(path.name for path in invalid)
                )
        artifacts: dict[Path, str] = {}
        for doc_id, xml in built.items():
            target = data_dir / "tei" / f"{doc_id}.xml"
            artifacts[target] = xml
            register = load_json(register_dir / f"{doc_id}.json")
            has_review = any(br.review_runs(page) for page in register["pages"])
            transcription = br.transcription_of(doc_id, register_dir)
            if has_review and transcription is not None:
                projection = data_dir / "pipeline" / "transcriptions" / f"{doc_id}.json"
                artifacts[projection] = (
                    json.dumps(transcription, ensure_ascii=False, indent=1) + "\n"
                )
        if register_xml.exists():
            artifacts[data_dir / "tei" / bt.REGISTER_FILE] = register_xml.read_text(
                encoding="utf-8"
            )
        graph = bg.build(entity_dir, annotation_dir, register_dir)
        artifacts[data_dir / "graph.jsonld"] = (
            json.dumps(graph, ensure_ascii=False, indent=1) + "\n"
        )
        summary_path = data_dir / "pipeline" / "register_summary.json"
        if summary_path.exists():
            summary = load_json(summary_path)
            by_id = {doc["docId"]: doc for doc in summary["documents"]}
            for doc_id, document in by_id.items():
                register_path = register_dir / f"{doc_id}.json"
                if not register_path.exists():
                    continue
                register = load_json(register_path)
                counts = Counter(
                    page["verification"]["status"] for page in register["pages"]
                )
                document["verification"] = {
                    state: counts.get(state, 0) for state in br.VERIFICATION_STATUS
                }
                document["effective_transcription"] = any(
                    br.review_runs(page) for page in register["pages"]
                )
            artifacts[summary_path] = (
                json.dumps(summary, ensure_ascii=False, indent=1) + "\n"
            )
        try:
            _publish_artifacts(artifacts)
        except OSError as exc:
            raise RuntimeError(
                "edition build could not be published; prior files restored"
            ) from exc
    return {"built": True, "date": date, "paths": [str(path) for path in artifacts]}


class EditorHandler(SimpleHTTPRequestHandler):
    """Loopback-only static and API handler holding one unguessable write token."""

    server_version = "DoCTALocalEditor/1"
    token = ""
    register_dir = REGISTER
    review_dir = PIPELINE_DIR / "reviews"
    annotation_dir = PIPELINE_DIR / "annotations"
    data_dir = DATA
    docs_dir = DOCS

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, directory=str(self.docs_dir), **kwargs)

    def _json(self, status: HTTPStatus, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _same_origin(self) -> bool:
        origin = self.headers.get("Origin")
        expected = f"http://{self.headers.get('Host', '')}"
        return origin == expected

    def _trusted_host(self) -> bool:
        return allowed_host(self.headers.get("Host"), self.server.server_port)

    def do_GET(self) -> None:
        if not self._trusted_host():
            self._json(HTTPStatus.FORBIDDEN, {"error": "untrusted host"})
            return
        path = urlsplit(self.path).path
        if path == "/api/session":
            self._json(HTTPStatus.OK, {"write_enabled": True, "token": self.token})
            return
        prefix = "/api/documents/"
        if path.startswith(prefix):
            raw = unquote(path[len(prefix) :])
            if not raw.isdigit():
                self._json(HTTPStatus.BAD_REQUEST, {"error": "invalid document id"})
                return
            try:
                payload = document_payload(int(raw), self.register_dir)
            except FileNotFoundError as exc:
                self._json(HTTPStatus.NOT_FOUND, {"error": str(exc)})
            else:
                self._json(HTTPStatus.OK, payload)
            return
        annotation_prefix = "/api/annotations/"
        if path.startswith(annotation_prefix):
            raw = unquote(path[len(annotation_prefix) :])
            if not raw.isdigit():
                self._json(HTTPStatus.BAD_REQUEST, {"error": "invalid document id"})
                return
            self._json(
                HTTPStatus.OK,
                annotations.read_decisions(int(raw), self.annotation_dir),
            )
            return
        super().do_GET()

    def do_POST(self) -> None:
        if not self._trusted_host():
            self._json(HTTPStatus.FORBIDDEN, {"error": "untrusted host"})
            return
        endpoint = urlsplit(self.path).path
        if endpoint not in ("/api/review", "/api/annotations", "/api/build"):
            self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        if not self._same_origin() or not secrets.compare_digest(
            self.headers.get("X-DoCTA-Token", ""), self.token
        ):
            self._json(HTTPStatus.FORBIDDEN, {"error": "write authorization failed"})
            return
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            length = -1
        if length < 0 or length > MAX_BODY:
            self._json(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "invalid body size"}
            )
            return
        try:
            payload = json.loads(self.rfile.read(length))
            if endpoint == "/api/review":
                document = save_review(payload, self.register_dir, self.review_dir)
                result = {
                    "saved": True,
                    "revision": document["revision"],
                    "document": document,
                }
            elif endpoint == "/api/annotations":
                decisions = annotations.save_decisions(
                    payload, self.register_dir, self.annotation_dir
                )
                result = {"saved": True, "annotations": decisions}
            else:
                result = build_tei_documents(
                    payload,
                    self.register_dir,
                    self.data_dir,
                    self.annotation_dir,
                )
        except json.JSONDecodeError:
            self._json(HTTPStatus.BAD_REQUEST, {"error": "invalid JSON"})
        except ar.ReviewError as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except FileNotFoundError as exc:
            self._json(HTTPStatus.NOT_FOUND, {"error": str(exc)})
        except RuntimeError as exc:
            self._json(HTTPStatus.CONFLICT, {"error": str(exc)})
        except ValueError as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except OSError as exc:
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
        else:
            self._json(HTTPStatus.OK, result)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8742)
    parser.add_argument(
        "--root",
        type=Path,
        default=REPO_ROOT,
        help="repository root, for an isolated scratch copy",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    docs = root / "docs"
    register = root / "pipeline" / "pages"
    if not docs.is_dir() or not register.is_dir():
        parser.error("--root must contain docs/ and pipeline/pages/")
    EditorHandler.docs_dir = docs
    EditorHandler.register_dir = register
    EditorHandler.review_dir = root / "pipeline" / "reviews"
    EditorHandler.annotation_dir = root / "pipeline" / "annotations"
    EditorHandler.data_dir = docs / "data"
    EditorHandler.token = secrets.token_urlsafe(32)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), EditorHandler)
    print(f"OK DoCTA editor: http://127.0.0.1:{args.port}/viewer.html")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nOK DoCTA editor stopped")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
