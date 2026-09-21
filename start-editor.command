#!/bin/bash
set -u
cd -- "$(dirname -- "$0")" || exit 1
export PATH="$HOME/.local/bin:$PATH"
if command -v uv >/dev/null 2>&1; then
    uv run --locked python pipeline/local_editor.py --open-browser "$@"
    editor_exit=$?
elif [ -x .venv/bin/python ]; then
    .venv/bin/python pipeline/local_editor.py --open-browser "$@"
    editor_exit=$?
else
    printf '%s\n' 'Bitte zuerst uv installieren. Anleitung: https://docs.astral.sh/uv/getting-started/installation/'
    editor_exit=1
fi
if [ "$editor_exit" -ne 0 ]; then
    read -r -p 'Enter zum Schliessen.' ignored
fi
exit "$editor_exit"
