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
import re
import secrets
import sys
import tempfile
import tomllib
import traceback
import webbrowser
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
import local_registry as registry
import validate_tei as vt
from io_paths import DATA, PIPELINE_DIR, REPO_ROOT, load_json, write_json, write_text

DOCS = REPO_ROOT / "docs"
REGISTER = PIPELINE_DIR / "pages"
MAX_BODY = 256 * 1024


def allowed_host(host: str | None, port: int) -> bool:
    return host in (f"127.0.0.1:{port}", f"localhost:{port}")


def revision(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def document_payload(
    doc_id: int,
    register_dir: Path = REGISTER,
    review_dir: Path | None = None,
    locked: bool = False,
) -> dict:
    if not locked:
        with ar.review_lock(register_dir):
            return document_payload(doc_id, register_dir, review_dir, locked=True)
    path = register_dir / f"{doc_id}.json"
    if not path.is_file():
        raise FileNotFoundError(f"No register for document {doc_id}")
    register = load_json(path)
    transcription = br.transcription_of(doc_id, register_dir)
    if transcription is None:
        raise FileNotFoundError(f"No transcription for document {doc_id}")
    states = {
        str(page["pageNr"]): page.get("verification", {"status": "unbearbeitet"})
        for page in register["pages"]
    }
    transcription["revision"] = revision(path)
    transcription["reviewState"] = states
    registered_pages = {page["pageNr"]: page for page in register["pages"]}
    review_times = {}
    for review_path in (review_dir or register_dir.parent / "reviews").glob(
        f"review-{doc_id}-*.json"
    ):
        review = load_json(review_path)
        for page_nr, reviewed_page in ar.validate(review, str(review_path)).items():
            run_id = ar._review_id(
                review, doc_id, page_nr, reviewed_page["date"], review["reviewer"]
            )
            review_times[run_id] = review["exported"]
    for page in transcription["pages"]:
        runs = registered_pages[page["pageNr"]].get("runs", [])
        original_run = next(
            (run for run in runs if run.get("source") == "transkribus"), None
        )
        if original_run is None:
            original_run = br.newest_edition_run(registered_pages[page["pageNr"]])
        page["provenance"] = {
            "originalRunId": original_run["id"] if original_run else None,
            "originalRuns": [
                {
                    key: run.get(key)
                    for key in (
                        "id",
                        "source",
                        "model",
                        "date",
                        "prompt",
                        "prompt_hash",
                    )
                }
                for run in runs
                if not str(run.get("id", "")).startswith("review:")
            ],
            "humanCorrections": [
                {
                    "id": run["id"],
                    "reviewer": run.get("reviewer"),
                    "timestamp": review_times.get(run["id"], run.get("date")),
                }
                for run in br.review_runs(registered_pages[page["pageNr"]])
            ],
        }
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
        canonical = (review_dir or register_dir.parent / "reviews") / (
            f"review-{doc_id}-{review['reviewId']}.json"
        )
        write_json(canonical, review)
        try:
            write_json(path, register)
        except BaseException:
            # The register is the effective state and startup replays nothing,
            # so an event without its register write would be a phantom save.
            canonical.unlink(missing_ok=True)
            raise
        return document_payload(doc_id, register_dir, review_dir, locked=True)


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
            transcription = br.site_transcription(
                br.document_entry(doc_id, register_dir), register["pages"]
            )
            if transcription is not None:
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
    app_version = "development"

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, directory=str(self.docs_dir), **kwargs)

    def _json(self, status: HTTPStatus, payload: dict) -> None:
        try:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        except UnicodeEncodeError:
            # Echoed client text may hold a lone surrogate; escape it.
            body = json.dumps(payload).encode("utf-8")
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

    def _internal_error(self) -> None:
        """Answer an unexpected failure without leaking it; the log keeps it."""
        self.log_error("%s", traceback.format_exc())
        self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "internal error"})

    def do_GET(self) -> None:
        if not self._trusted_host():
            self._json(HTTPStatus.FORBIDDEN, {"error": "untrusted host"})
            return
        path = urlsplit(self.path).path
        if not path.startswith("/api/"):
            super().do_GET()
            return
        try:
            status, payload = self._get_api(path)
        except FileNotFoundError as exc:
            self._json(HTTPStatus.NOT_FOUND, {"error": str(exc)})
        except (ValueError, OSError, ar.ReviewError) as exc:
            # Stored state the server cannot read; the message names the file.
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
        except Exception:
            self._internal_error()
        else:
            self._json(status, payload)

    def _get_api(self, path: str) -> tuple[HTTPStatus, dict]:
        if path == "/api/session":
            return HTTPStatus.OK, {
                "write_enabled": True,
                "token": self.token,
                "version": self.app_version,
            }
        if path == "/api/registry":
            return HTTPStatus.OK, registry.read_registry(self.register_dir)
        readers = {
            "/api/documents/": lambda doc_id: document_payload(
                doc_id, self.register_dir, self.review_dir
            ),
            "/api/annotations/": lambda doc_id: annotations.read_decisions(
                doc_id, self.annotation_dir
            ),
        }
        for prefix, read in readers.items():
            if path.startswith(prefix):
                raw = unquote(path[len(prefix) :])
                if not re.fullmatch(r"[0-9]+", raw):
                    return HTTPStatus.BAD_REQUEST, {"error": "invalid document id"}
                return HTTPStatus.OK, read(int(raw))
        return HTTPStatus.NOT_FOUND, {"error": "not found"}

    def do_POST(self) -> None:
        if not self._trusted_host():
            self._json(HTTPStatus.FORBIDDEN, {"error": "untrusted host"})
            return
        endpoint = urlsplit(self.path).path
        if endpoint not in (
            "/api/review",
            "/api/annotations",
            "/api/registry",
            "/api/build",
        ):
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
                    payload,
                    self.register_dir,
                    self.annotation_dir,
                    self.data_dir / "entities",
                )
                result = {"saved": True, "annotations": decisions}
            elif endpoint == "/api/registry":
                result = {
                    "saved": True,
                    "registry": registry.save_registry(payload, self.register_dir),
                }
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
        except (ValueError, TypeError) as exc:
            # TypeError comes from payload values of the wrong JSON type, such
            # as a list where a validator tests membership in a set of names.
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except OSError as exc:
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
        except Exception:
            self._internal_error()
        else:
            self._json(HTTPStatus.OK, result)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8742)
    parser.add_argument("--open-browser", action="store_true")
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
    # One server uses one root. Set source readers before serving so a scratch
    # copy cannot silently read transcriptions or metadata from this checkout.
    br.DATA = EditorHandler.data_dir
    bt.DATA = EditorHandler.data_dir
    EditorHandler.token = secrets.token_urlsafe(32)
    manifest = root / "pyproject.toml"
    if manifest.exists():
        with manifest.open("rb") as source:
            EditorHandler.app_version = (
                tomllib.load(source).get("project", {}).get("version", "development")
            )
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), EditorHandler)
    except OSError as exc:
        print(
            f"ERROR DoCTA editor could not open port {args.port}. Another service may already be using it. {exc}",
            file=sys.stderr,
        )
        return 1
    print(f"OK DoCTA editor: http://127.0.0.1:{args.port}/viewer.html")
    if args.open_browser:
        webbrowser.open(f"http://127.0.0.1:{server.server_port}/viewer.html")
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
