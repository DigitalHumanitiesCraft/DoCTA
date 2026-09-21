$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $repo
if (Get-Command uv -ErrorAction SilentlyContinue) {
    uv run --locked python pipeline/local_editor.py --open-browser @args
} elseif (Test-Path -LiteralPath '.venv/Scripts/python.exe') {
    & '.venv/Scripts/python.exe' pipeline/local_editor.py --open-browser @args
} else {
    throw 'Install uv and run uv sync --locked in this repository before starting the editor.'
}
exit $LASTEXITCODE
