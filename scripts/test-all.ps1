# Every gate of the repository in one run: lint, format, fast and slow pytest,
# the cross-artifact healthcheck and the six Playwright suites, in that order.
# Stops at the first failing gate and names it. Uses uv where it is on PATH,
# otherwise the project venv directly. Playwright must be installed once
# (tests/README.md). Same sequence as scripts/test-all.sh.
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)

if (Get-Command uv -ErrorAction SilentlyContinue) {
    $Py = @('uv', 'run', '--locked', 'python')
} elseif (Test-Path '.venv\Scripts\python.exe') {
    $Py = @('.venv\Scripts\python.exe')
} else {
    Write-Error "test-all: neither uv nor a project venv found; run 'uv sync --locked'"
}

$Passed = [System.Collections.Generic.List[string]]::new()

function Invoke-Gate([string]$Name, [string[]]$Command) {
    Write-Host "==> $Name"
    $exe = $Command[0]
    $rest = @($Command | Select-Object -Skip 1)
    & $exe @rest
    if ($LASTEXITCODE -ne 0) {
        Write-Host ''
        Write-Host "test-all: FAILED at '$Name' (exit $LASTEXITCODE)"
        if ($Passed.Count) { Write-Host "passed before it: $($Passed -join ', ')" }
        exit 1
    }
    $Passed.Add($Name)
}

Invoke-Gate 'ruff check' ($Py + @('-m', 'ruff', 'check', '.'))
Invoke-Gate 'ruff format --check' ($Py + @('-m', 'ruff', 'format', '--check', '.'))
Invoke-Gate 'pytest (fast)' ($Py + @('-m', 'pytest', '-q'))
Invoke-Gate 'pytest -m slow' ($Py + @('-m', 'pytest', '-q', '-m', 'slow'))
Invoke-Gate 'check_pipeline' ($Py + @('pipeline/check_pipeline.py'))
foreach ($suite in 'smoketest', 'interaction-test', 'sources-ui-test', 'viewer-ui-test',
    'registry-editor-test', 'guide-walkthrough-test') {
    Invoke-Gate "node tests/$suite.mjs" @('node', "tests/$suite.mjs")
}

Write-Host ''
Write-Host "test-all: all gates passed: $($Passed -join ', ')"
