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
  be reconstructed without replaying a diff. Re-applying the same export replaces
  that run in place instead of appending a second one, which makes the ingest
  idempotent.
  A review is written against the base text it was made on. The base is the run
  the review builds upon, meaning the newest earlier review run of the page or,
  where none exists, the Transkribus run. Every corrected line must still carry
  its reported original in that base; where it does not, the export was taken
  before another change and the ingest refuses the whole file rather than
  silently overwriting work with a stale reading.
  Only the corrections travel into a run. A page marked reviewed without a single
  correction records the verification and no run, because there is no new
  transcription to record.

Usage:
  python apply_review.py                       # ingest pipeline/reviews/
  python apply_review.py review-11328300.json  # one or more files
  python apply_review.py DIR                   # every *.json below DIR
  python apply_review.py --register DIR --dry-run
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import build_register as br

ROOT = Path(__file__).parent
REVIEWS = ROOT / "reviews"
REGISTER = ROOT / "pages"

SOURCE = "docta-viewer"
# A review may only assert one of the two human states; the machine states of
# the register are not reachable from the viewer.
REVIEW_STATUS = ("gesichtet", "abgenommen")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ReviewError(Exception):
    """An export that violates the contract or no longer fits the register."""


def _run_id(doc_id: int, page_nr: int, date: str, reviewer: str) -> str:
    return f"review:{doc_id}-{page_nr}-{date}-{reviewer}"


def _str(value: Any, what: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReviewError(f"{what}: fehlt oder ist kein nichtleerer Text")
    return value


def validate(data: Any, origin: str) -> dict[int, dict]:
    """Check the export against the contract and return its pages by number.

    Validation is total: it reports the first violation with the place it sits
    in, because a half-applied review is worse than a refused one.
    """
    if not isinstance(data, dict):
        raise ReviewError(f"{origin}: kein JSON-Objekt")
    if data.get("source") != SOURCE:
        raise ReviewError(f"{origin}: source ist nicht {SOURCE!r}")
    doc_id = data.get("docId")
    if not isinstance(doc_id, int) or isinstance(doc_id, bool):
        raise ReviewError(f"{origin}: docId fehlt oder ist keine ganze Zahl")
    _str(data.get("reviewer"), f"{origin}: reviewer")
    _str(data.get("exported"), f"{origin}: exported")
    pages = data.get("pages")
    if not isinstance(pages, dict):
        raise ReviewError(f"{origin}: pages fehlt oder ist kein Objekt")

    out: dict[int, dict] = {}
    for key, page in pages.items():
        where = f"{origin}, Seite {key}"
        if not (isinstance(key, str) and key.isdigit()):
            raise ReviewError(f"{where}: Seitenschluessel ist keine Seitenzahl")
        if not isinstance(page, dict):
            raise ReviewError(f"{where}: kein Objekt")
        status = page.get("status")
        if status is not None and status not in REVIEW_STATUS:
            raise ReviewError(f"{where}: status {status!r} ist kein Reviewstatus")
        date = page.get("date")
        if not isinstance(date, str) or not DATE.match(date):
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
                    raise ReviewError(f"{where}, Zeile {line_id}:"
                                      f" {field} fehlt oder ist kein Text")
        out[int(key)] = page
    return out


def _review_runs(page: dict) -> list[dict]:
    return [r for r in page.get("runs") or []
            if str(r.get("id", "")).startswith("review:")]


def base_lines(page: dict, exclude_id: str) -> list[dict]:
    """The line list the review was made on, without the run it replaces.

    Newest earlier review run first, Transkribus run otherwise; a page with
    neither has no text to review against.
    """
    earlier = [r for r in _review_runs(page) if r["id"] != exclude_id]
    if earlier:
        return list(max(earlier, key=lambda r: (r.get("date") or "", r["id"]))["lines"])
    for run in page.get("runs") or []:
        if run.get("source") == "transkribus":
            return list(run["lines"])
    return []


def _corrected_lines(base: list[dict], corrections: list[dict],
                     where: str) -> list[dict]:
    """Full line list of the page with the reported corrections applied.

    Refuses a correction whose reported original no longer matches the base, so
    an export taken before another change cannot overwrite that change.
    """
    by_id = {line["id"]: line["text"] for line in base if line.get("id")}
    replacements: dict[str, str] = {}
    for correction in corrections:
        line_id = correction["id"]
        if line_id not in by_id:
            raise ReviewError(f"{where}: Zeile {line_id} steht nicht im Register")
        if by_id[line_id] != correction["original"]:
            raise ReviewError(
                f"{where}: Zeile {line_id} ist veraltet, das Register haelt"
                f" {by_id[line_id]!r}, der Export meldet"
                f" {correction['original']!r}")
        replacements[line_id] = correction["corrected"]
    return [{"id": line["id"],
             "text": replacements.get(line["id"], line["text"])}
            for line in base]


def apply_document(register: dict, review: dict, pages: dict[int, dict],
                   origin: str) -> list[str]:
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
        run_id = _run_id(doc_id, page_nr, date, reviewer)
        if entry["lines"]:
            base = base_lines(page, run_id)
            if not base:
                raise ReviewError(f"{where}: keine Basistranskription vorhanden")
            run = {
                "id": run_id,
                "source": "human",
                "reviewer": reviewer,
                "date": date,
                "lines": _corrected_lines(base, entry["lines"], where),
            }
            existing = next((i for i, r in enumerate(page["runs"])
                             if r.get("id") == run_id), None)
            if existing is None:
                page["runs"].append(run)
            else:
                page["runs"][existing] = run
            log.append(f"  Seite {page_nr}: {len(entry['lines'])} Zeilen"
                       f" korrigiert -> {run_id}")
        if status is not None:
            page["verification"] = {"status": status, "reviewer": reviewer,
                                    "date": date}
            log.append(f"  Seite {page_nr}: {status} ({reviewer}, {date})")
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


def ingest(targets: list[Path], register_dir: Path,
           dry_run: bool = False) -> list[str]:
    """Apply every review file below targets. Raises on the first violation."""
    files = _review_files(targets)
    if not files:
        return []
    log: list[str] = []
    for path in files:
        review = br._load(path)
        pages = validate(review, path.name)
        doc_id = review["docId"]
        register_path = register_dir / f"{doc_id}.json"
        if not register_path.exists():
            raise ReviewError(f"{path.name}: kein Register fuer Dokument {doc_id}")
        register = br._load(register_path)
        log.append(f"{path.name} -> {register_path.name}")
        log += apply_document(register, review, pages, path.name)
        if not dry_run:
            br._write(register_path, register)
    return log


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("targets", nargs="*", type=Path,
                    help=f"review files or directories (default: {REVIEWS})")
    ap.add_argument("--register", type=Path, default=REGISTER,
                    help="register page directory (default: pipeline/pages/)")
    ap.add_argument("--dry-run", action="store_true",
                    help="validate and report without writing")
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
    print(f"OK Reviews: {sum(1 for e in log if not e.startswith('  '))}"
          f" Datei(en) uebernommen{mode}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
