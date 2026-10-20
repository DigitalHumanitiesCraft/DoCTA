#!/usr/bin/env sh
# Every gate of the repository in one run: lint, format, fast and slow pytest,
# the cross-artifact healthcheck and the six Playwright suites, in that order.
# Stops at the first failing gate and names it. Uses uv where it is on PATH,
# otherwise the project venv directly. Playwright must be installed once
# (tests/README.md). Same sequence as scripts/test-all.ps1.
set -u

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT" || exit 1

if command -v uv >/dev/null 2>&1; then
    PY="uv run --locked python"
elif [ -x .venv/bin/python ]; then
    PY=.venv/bin/python
elif [ -x .venv/Scripts/python.exe ]; then
    PY=.venv/Scripts/python.exe
else
    echo "test-all: neither uv nor a project venv found; run 'uv sync --locked'" >&2
    exit 1
fi

PASSED=""

run_gate() {
    name=$1
    shift
    echo "==> $name"
    if ! "$@"; then
        echo
        echo "test-all: FAILED at '$name'"
        [ -n "$PASSED" ] && echo "passed before it:$PASSED"
        exit 1
    fi
    PASSED="$PASSED
  $name"
}

# $PY is deliberately unquoted: with uv it is a command of several words.
run_gate "ruff check" $PY -m ruff check .
run_gate "ruff format --check" $PY -m ruff format --check .
run_gate "pytest (fast)" $PY -m pytest -q
run_gate "pytest -m slow" $PY -m pytest -q -m slow
run_gate "check_pipeline" $PY pipeline/check_pipeline.py
for suite in smoketest interaction-test sources-ui-test viewer-ui-test \
    registry-editor-test guide-walkthrough-test; do
    run_gate "node tests/$suite.mjs" node "tests/$suite.mjs"
done

echo
echo "test-all: all gates passed:$PASSED"
