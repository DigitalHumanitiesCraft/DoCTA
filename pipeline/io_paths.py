"""Where the pipeline's files live and how they are read and written.

Every pipeline script anchors its paths here rather than at its own file
location, so the three names are unambiguous across the modules that import each
other: PIPELINE_DIR is pipeline/, REPO_ROOT the repository, DATA the site data
directory. Anchoring stays at file location, so a script runs from anywhere.

Writing goes through a sibling temp file and a replace, so an interrupted run
cannot leave a truncated artifact behind. The JSON serialisation parameters are
part of the generated data: indent 1, no ASCII escaping, LF line ends and a
final newline. A change to them rewrites every artifact of the repository, which
is why they stand in one place instead of at each call site.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PIPELINE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PIPELINE_DIR.parent
DATA = REPO_ROOT / "docs" / "data"

# Fence line of a Markdown code block, tagged or not.
FENCE = "```"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, text: str) -> None:
    """Write text atomically, creating the parent directory where needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    tmp.replace(path)


def write_json(path: Path, payload: Any) -> None:
    """Write a generated JSON artifact in the serialisation the repository holds."""
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=1) + "\n")


def fenced_block(path: Path) -> str:
    """Payload of the first untagged fenced block of a Markdown document.

    This is the convention a frozen prompt is stored under, and its hash is
    provenance in every file the prompt produced. Blocks are therefore paired
    off in document order and a block whose opening fence carries a language tag
    is passed over as prose illustration, rather than being read across by a
    pattern that would silently return the text after it. A document without an
    untagged block raises, because a caller reading a frozen prompt has nothing
    to fall back on.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    fences = [n for n, line in enumerate(lines) if line.startswith(FENCE)]
    for start, end in zip(fences[::2], fences[1::2], strict=False):
        if lines[start].strip() == FENCE:
            return "\n".join(lines[start + 1 : end])
    raise ValueError(f"{path.name}: no untagged fenced code block")
