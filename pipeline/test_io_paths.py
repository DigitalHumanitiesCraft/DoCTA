"""The shared file layer: prompt fences and the artifact serialisation.

Both are pinned here because a change to either is invisible at the call sites
and shows up as a different prompt hash or a rewritten artifact.
"""

import pytest
from io_paths import fenced_block, load_json, write_json

TAGGED = """Text before the payload.

```json
{"illustration": true}
```

More prose.

```
the frozen payload
```
"""


def test_a_language_tagged_fence_is_not_the_payload(tmp_path) -> None:
    """A tagged fence is prose illustration; the payload is the untagged block."""
    path = tmp_path / "prompt.md"
    path.write_text(TAGGED, encoding="utf-8")
    assert fenced_block(path) == "the frozen payload"


def test_a_document_without_an_untagged_fence_raises(tmp_path) -> None:
    """A caller reading a frozen prompt has nothing to fall back on."""
    path = tmp_path / "prompt.md"
    path.write_text("```json\n{}\n```\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"prompt\.md"):
        fenced_block(path)


def test_json_artifacts_carry_the_pinned_serialisation(tmp_path) -> None:
    """Indent 1, no ASCII escaping, LF and a final newline: the shape of every
    generated artifact in the repository, so a change here rewrites all of them."""
    path = tmp_path / "out.json"
    write_json(path, {"a": ["Kürass"]})
    assert path.read_bytes() == '{\n "a": [\n  "Kürass"\n ]\n}\n'.encode()
    assert load_json(path) == {"a": ["Kürass"]}
