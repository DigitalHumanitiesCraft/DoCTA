"""Ingest review exports of the DoCTA viewer into the page register.

A reviewer reads a page against its scan in the browser viewer, marks the page
gesichtet or abgenommen and corrects single lines. The viewer exports that
decision as one JSON file per document; this script writes it into the register,
which is the only place where the state of a page is held.

Export contract (produced by the viewer, validated here):
  {"docId": N, "reviewer": "XY",
   "pages": {"<pageNr>": {"status": "gesichtet"|"abgenommen"|null,
                          "date": "YYYY-MM-DD",
                          "lines": [{"id": lineId,
                                     "original": "...", "corrected": "..."}]}},
   "exported": "<ISO datetime>", "source": "docta-viewer"}

Writes:
  pipeline/pages/<docId>.json        verification and one review run per page

Design decisions:
  A correction never edits an existing run, because runs are immutable. The
  corrections of one page review become a new run "review:<docId>-<pageNr>-<date>
  -<reviewer>" that carries the full line list of the page with the corrections
  applied, so the run is readable on its own and the transcription it produced can
  be reconstructed without replaying a diff. Re-applying an identical export
  skips its existing run without changing later verification. Changed content
  under an existing run identity is refused.
  A review is written against the base text it was made on. The base is the run
  the review builds upon, meaning the newest earlier review run of the page,
  where none exists the Transkribus run, and for a document DoCTA transcribed
  itself the newest edition run. Every corrected line must still carry
  its reported original in that base; where it does not, the export was taken
  before another change and the ingest refuses the whole file rather than
  silently overwriting work with a stale reading.
  Only the corrections travel into a run. A page marked reviewed without a single
  correction records the verification and no run, because there is no new
  transcription to record.

Usage:
  python apply_review.py                       # ingest pipeline/reviews/
  python apply_review.py review-11328300.json  # one or more files
  python apply_review.py DIR                   # every *.json directly in DIR
  python apply_review.py --register DIR --dry-run
"""

import argparse
import hashlib
import json
import math
import re
import sys
from datetime import date as calendar_date
from datetime import datetime
from pathlib import Path
from typing import Any

import build_register as br
from io_paths import PIPELINE_DIR, load_json, review_lock, write_json

REVIEWS = PIPELINE_DIR / "reviews"
REGISTER = PIPELINE_DIR / "pages"

SOURCE = "docta-viewer"
# A review may only assert one of the two human states; the machine states of
# the register are not reachable from the viewer.
REVIEW_STATUS = ("gesichtet", "abgenommen")
DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
REVIEW_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class ReviewError(Exception):
    """An export that violates the contract or no longer fits the register."""


def _run_id(doc_id: int, page_nr: int, date: str, reviewer: str) -> str:
    return f"review:{doc_id}-{page_nr}-{date}-{reviewer}"


def _review_id(
    review: dict, doc_id: int, page_nr: int, date: str, reviewer: str
) -> str:
    run_id = _run_id(doc_id, page_nr, date, reviewer)
    if suffix := review.get("reviewId"):
        run_id += f"-{suffix}"
    return run_id


def _str(value: Any, what: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReviewError(f"{what}: fehlt oder ist kein nichtleerer Text")
    return value


def _encodable(data: Any, what: str) -> None:
    """Refuse text UTF-8 cannot store, such as a lone surrogate from a JSON escape."""
    try:
        json.dumps(data, ensure_ascii=False).encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ReviewError(f"{what}: enthaelt nicht speicherbaren Text") from exc


def _valid_date(value: Any) -> bool:
    if not isinstance(value, str) or not DATE.fullmatch(value):
        return False
    try:
        calendar_date.fromisoformat(value)
    except ValueError:
        return False
    return True


def validate(data: Any, origin: str) -> dict[int, dict]:
    """Check the export against the contract and return its pages by number.

    Reports the first violation with the place it sits in; a half-applied
    review is worse than a refused one.
    """
    if not isinstance(data, dict):
        raise ReviewError(f"{origin}: kein JSON-Objekt")
    _encodable(data, origin)
    if data.get("source") != SOURCE:
        raise ReviewError(f"{origin}: source ist nicht {SOURCE!r}")
    doc_id = data.get("docId")
    if not isinstance(doc_id, int) or isinstance(doc_id, bool):
        raise ReviewError(f"{origin}: docId fehlt oder ist keine ganze Zahl")
    _str(data.get("reviewer"), f"{origin}: reviewer")
    _str(data.get("exported"), f"{origin}: exported")
    if data.get("schemaVersion") == 2:
        try:
            exported = datetime.fromisoformat(data["exported"])
        except ValueError as exc:
            raise ReviewError(f"{origin}: exported ist kein ISO-Zeitstempel") from exc
        if exported.tzinfo is None:
            raise ReviewError(f"{origin}: exported braucht eine Zeitzone")
    if "reviewId" in data and (
        not isinstance(data["reviewId"], str)
        or not REVIEW_ID.fullmatch(data["reviewId"])
    ):
        raise ReviewError(f"{origin}: reviewId ist ungueltig")
    effort = data.get("effort")
    if effort is not None:
        if not isinstance(effort, dict):
            raise ReviewError(f"{origin}: effort ist kein Objekt")
        active = effort.get("activeSeconds")
        decisions = effort.get("decisionCount")
        notes = effort.get("notes")
        if (
            not isinstance(active, (int, float))
            or isinstance(active, bool)
            or not math.isfinite(active)
            or active < 0
        ):
            raise ReviewError(f"{origin}: effort.activeSeconds ist ungueltig")
        if (
            not isinstance(decisions, int)
            or isinstance(decisions, bool)
            or decisions < 0
        ):
            raise ReviewError(f"{origin}: effort.decisionCount ist ungueltig")
        if notes is not None and (not isinstance(notes, str) or len(notes) > 2000):
            raise ReviewError(f"{origin}: effort.notes ist ungueltig")
    pages = data.get("pages")
    if not isinstance(pages, dict):
        raise ReviewError(f"{origin}: pages fehlt oder ist kein Objekt")

    out: dict[int, dict] = {}
    for key, page in pages.items():
        where = f"{origin}, Seite {key}"
        if not (isinstance(key, str) and re.fullmatch(r"[0-9]+", key)):
            raise ReviewError(f"{where}: Seitenschluessel ist keine Seitenzahl")
        if int(key) in out:
            raise ReviewError(f"{where}: Seite {int(key)} mehrfach angegeben")
        if not isinstance(page, dict):
            raise ReviewError(f"{where}: kein Objekt")
        if "status" not in page:
            raise ReviewError(f"{where}: status fehlt")
        status = page["status"]
        if status is not None and status not in REVIEW_STATUS:
            raise ReviewError(f"{where}: status {status!r} ist kein Reviewstatus")
        if not _valid_date(page.get("date")):
            raise ReviewError(f"{where}: date fehlt oder ist nicht YYYY-MM-DD")
        lines = page.get("lines")
        if not isinstance(lines, list):
            raise ReviewError(f"{where}: lines fehlt oder ist keine Liste")
        seen: set[str] = set()
        for line in lines:
            if not isinstance(line, dict):
                raise ReviewError(f"{where}: Zeileneintrag ist kein Objekt")
            line_id = _str(line.get("id"), f"{where}: Zeilen-id")
            if line_id in seen:
                raise ReviewError(f"{where}: Zeile {line_id} doppelt korrigiert")
            seen.add(line_id)
            for field in ("original", "corrected"):
                if not isinstance(line.get(field), str):
                    raise ReviewError(
                        f"{where}, Zeile {line_id}: {field} fehlt oder ist kein Text"
                    )
            if "excluded" in line and not isinstance(line["excluded"], bool):
                raise ReviewError(
                    f"{where}, Zeile {line_id}: excluded ist kein Wahrheitswert"
                )
        out[int(key)] = page
    return out


def base_lines(page: dict, exclude_id: str) -> list[dict]:
    """The line list the review was made on, without the run it replaces.

    Newest earlier review run first, then the Transkribus run, then the newest
    edition run, which is the base of a document DoCTA transcribed itself; a
    page with none of the three has no text to review against.
    """
    earlier = br.newest_review_run(page, exclude_id)
    if earlier:
        return list(earlier["lines"])
    for run in page.get("runs") or []:
        if run.get("source") == "transkribus":
            return list(run["lines"])
    edition = br.newest_edition_run(page)
    if edition:
        return list(edition["lines"])
    return []


def _corrected_lines(
    base: list[dict], corrections: list[dict], where: str
) -> list[dict]:
    """Full line list of the page with the reported corrections applied.

    Refuses a correction whose reported original no longer matches the base, so
    an export taken before another change cannot overwrite that change. An
    excluded line keeps its text and leaves the edition text; the flag carries
    over from the base until a correction sets it, so restoring is a correction
    with ``excluded: false``. Only a set flag is written, which leaves the
    lines never excluded in the shape they always had.
    """
    by_id = {line["id"]: line["text"] for line in base if line.get("id")}
    excluded = {line["id"] for line in base if line.get("excluded")}
    replacements: dict[str, str] = {}
    for correction in corrections:
        line_id = correction["id"]
        if line_id not in by_id:
            raise ReviewError(f"{where}: Zeile {line_id} steht nicht im Register")
        if by_id[line_id] != correction["original"]:
            raise ReviewError(
                f"{where}: Zeile {line_id} ist veraltet, das Register haelt"
                f" {by_id[line_id]!r}, der Export meldet"
                f" {correction['original']!r}"
            )
        replacements[line_id] = correction["corrected"]
        if "excluded" in correction:
            excluded.discard(line_id)
            if correction["excluded"]:
                excluded.add(line_id)
    return [
        {
            "id": line["id"],
            "text": replacements.get(line["id"], line["text"]),
            **({"excluded": True} if line["id"] in excluded else {}),
        }
        for line in base
    ]


def _recorded_time(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        instant = datetime.fromisoformat(value)
    except ValueError:
        return None
    return instant if instant.tzinfo is not None else None


def _obsolete_status(page: dict, review: dict, entry: dict, where: str) -> bool:
    """Keep old decisions from approving a subsequent, changed reading."""
    instant = _recorded_time(review["exported"])
    current = page.get("verification") or {}
    expected = {
        "status": entry["status"],
        "reviewer": review["reviewer"],
        "date": entry["date"],
    }
    if review.get("schemaVersion") == 2:
        expected["timestamp"] = review["exported"]
    if review.get("effort") is not None:
        expected["effort"] = review["effort"]
    ambiguous = False
    latest = br.newest_review_run(page)
    for record in [latest, current]:
        if record is None:
            continue
        if record is current and record == expected:
            continue
        recorded = _recorded_time(record.get("timestamp"))
        if recorded is None and re.fullmatch(
            r"[0-9]{12}", record.get("id", "").rsplit("-", 1)[-1]
        ):
            recorded = _recorded_time(br._review_order(record)[0])
        if instant is not None and recorded is not None:
            if instant < recorded:
                return True
            ambiguous |= instant == recorded
        elif record.get("date"):
            if entry["date"] < record["date"]:
                return True
            ambiguous |= entry["date"] == record["date"]
    if ambiguous:
        raise ReviewError(
            f"{where}: ambiguous same-day page decision; review the changed text again"
        )
    return False


def apply_document(
    register: dict, review: dict, pages: dict[int, dict], origin: str
) -> list[str]:
    """Write one validated review into the register payload. Returns a log."""
    doc_id = review["docId"]
    reviewer = review["reviewer"]
    by_nr = {p["pageNr"]: p for p in register["pages"]}
    log: list[str] = []
    for page_nr in sorted(pages):
        where = f"{origin}, Seite {page_nr}"
        page = by_nr.get(page_nr)
        if page is None:
            raise ReviewError(f"{where}: Seite fehlt im Register von {doc_id}")
        entry = pages[page_nr]
        status, date = entry["status"], entry["date"]
        run_id = _review_id(review, doc_id, page_nr, date, reviewer)
        existing_run = (
            next((run for run in br.review_runs(page) if run["id"] == run_id), None)
            if entry["lines"]
            else None
        )
        digest = hashlib.sha256(
            json.dumps(review, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        if existing_run is not None and existing_run.get("reviewDigest") is not None:
            if existing_run["reviewDigest"] != digest:
                raise ReviewError(
                    f"{where}: changed content for existing review {run_id}"
                )
            continue
        if (
            not entry["lines"]
            and status is not None
            and _obsolete_status(page, review, entry, where)
        ):
            log.append(f"  Seite {page_nr}: older page decision skipped")
            continue
        if entry["lines"]:
            base_page = page
            if existing_run is not None:
                # Historical runs have no event digest. Reconstruct their saved
                # reading from predecessors, never from subsequent corrections.
                base_page = {
                    **page,
                    "runs": [
                        run
                        for run in page["runs"]
                        if not str(run.get("id", "")).startswith("review:")
                        or br._review_order(run) < br._review_order(existing_run)
                    ],
                }
            base = base_lines(base_page, run_id)
            if not base:
                raise ReviewError(f"{where}: keine Basistranskription vorhanden")
            run = {
                "id": run_id,
                "source": "human",
                "reviewer": reviewer,
                "date": date,
                "lines": _corrected_lines(base, entry["lines"], where),
            }
            if review.get("schemaVersion") == 2:
                run["timestamp"] = review["exported"]
            if review.get("effort") is not None:
                run["effort"] = review["effort"]
            if existing_run is not None:
                # Earlier local saves predate persisted timestamps; replay
                # must not rewrite those immutable historical runs.
                if "timestamp" not in existing_run:
                    run.pop("timestamp", None)
                if existing_run != run:
                    raise ReviewError(
                        f"{where}: changed content for existing review {run_id}"
                    )
                continue
            run["reviewDigest"] = digest
            page["runs"].append(run)
            log.append(
                f"  Seite {page_nr}: {len(entry['lines'])} Zeilen"
                f" korrigiert -> {run_id}"
            )
        effective_status = status
        reason = None
        if entry["lines"] and status is None:
            effective_status = "gesichtet"
            reason = (
                "review-reopened-after-text-change"
                if (page.get("verification") or {}).get("status") == "abgenommen"
                else "text-corrected"
            )
        if effective_status is not None:
            page["verification"] = {
                "status": effective_status,
                "reviewer": reviewer,
                "date": date,
            }
            if review.get("schemaVersion") == 2:
                page["verification"]["timestamp"] = review["exported"]
            if reason:
                page["verification"]["reason"] = reason
            if review.get("effort") is not None:
                page["verification"]["effort"] = review["effort"]
            log.append(f"  Seite {page_nr}: {effective_status} ({reviewer}, {date})")
    return log


def _review_files(targets: list[Path]) -> list[Path]:
    files: list[Path] = []
    for target in targets:
        if target.is_dir():
            files += sorted(target.glob("*.json"))
        elif target.exists():
            files.append(target)
        else:
            raise ReviewError(f"{target}: nicht gefunden")
    return files


def _read(path: Path) -> Any:
    """Parse a review export, reporting a broken file as a refusal."""
    try:
        return load_json(path)
    except json.JSONDecodeError as exc:
        raise ReviewError(f"{path.name}: kein lesbares JSON ({exc})") from exc


def _ingest_unlocked(
    targets: list[Path], register_dir: Path, dry_run: bool = False
) -> list[str]:
    """Apply every review file below targets, all or nothing.

    Every file of the batch is validated and applied in memory before any
    register file is written, so a refused file leaves the register untouched
    even when earlier files of the same batch were fine. Later files of a
    batch see the changes of earlier ones, because documents are shared in
    memory. The writing phase itself runs file by file, each one atomic, so no
    register file is ever half written.
    """
    files = _review_files(targets)
    if not files:
        return []
    log: list[str] = []
    registers: dict[Path, dict] = {}
    for path in files:
        review = _read(path)
        pages = validate(review, path.name)
        doc_id = review["docId"]
        register_path = register_dir / f"{doc_id}.json"
        if register_path not in registers:
            if not register_path.exists():
                raise ReviewError(f"{path.name}: kein Register fuer Dokument {doc_id}")
            registers[register_path] = _read(register_path)
        log.append(f"{path.name} -> {register_path.name}")
        log += apply_document(registers[register_path], review, pages, path.name)
    # Refuse before the first write, so a batch is never half written for it.
    for register_path, register in registers.items():
        _encodable(register, register_path.name)
    if not dry_run:
        for register_path, register in registers.items():
            write_json(register_path, register)
    return log


def ingest(targets: list[Path], register_dir: Path, dry_run: bool = False) -> list[str]:
    """Apply a batch while excluding concurrent API or CLI review writes."""
    with review_lock(register_dir):
        return _ingest_unlocked(targets, register_dir, dry_run)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "targets",
        nargs="*",
        type=Path,
        help=f"review files or directories (default: {REVIEWS})",
    )
    ap.add_argument(
        "--register",
        type=Path,
        default=REGISTER,
        help="register page directory (default: pipeline/pages/)",
    )
    ap.add_argument(
        "--dry-run", action="store_true", help="validate and report without writing"
    )
    args = ap.parse_args()

    targets = args.targets or [REVIEWS]
    if not args.targets and not REVIEWS.exists():
        print(f"OK Reviews: nichts zu tun, {REVIEWS} existiert nicht")
        return 0
    try:
        log = ingest(targets, args.register, args.dry_run)
    except ReviewError as exc:
        print(f"FEHLER {exc}", file=sys.stderr)
        return 1
    for entry in log:
        print(entry)
    mode = " (dry run)" if args.dry_run else ""
    print(
        f"OK Reviews: {sum(1 for e in log if not e.startswith('  '))}"
        f" Datei(en) uebernommen{mode}"
    )
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
