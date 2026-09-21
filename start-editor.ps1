$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $repo
if (Get-Command uv -ErrorAction SilentlyContinue) {
    uv run python pipeline/local_editor.py @args
} elseif (Test-Path -LiteralPath '.venv/Scripts/python.exe') {
    & '.venv/Scripts/python.exe' pipeline/local_editor.py @args
} else {
    throw 'Install uv and run uv sync --locked in this repository before starting the editor.'
}
