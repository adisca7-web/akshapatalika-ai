# Set up the development environment on Windows.
#
#   powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
#
# Creates .venv from uv.lock, so every machine gets byte-identical dependency
# versions, then runs the test suite to prove the environment works before you
# start changing things.

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

Write-Host ''
Write-Host 'Akshapatalika AI - development setup' -ForegroundColor Cyan
Write-Host ''

# -- uv ---------------------------------------------------------------------
# uv manages both the interpreter and the packages, so a contributor does not
# need a matching Python already installed.
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host 'uv is not installed. Install it with:' -ForegroundColor Yellow
    Write-Host ''
    Write-Host '    powershell -c "irm https://astral.sh/uv/install.ps1 | iex"'
    Write-Host ''
    Write-Host 'then run this script again.'
    exit 1
}
Write-Host ("  uv          {0}" -f (uv --version))

# -- interpreter + packages -------------------------------------------------
# .python-version pins 3.11; uv downloads it if this machine lacks it.
Write-Host '  syncing     .venv from uv.lock ...'
uv sync --extra app --extra dev --quiet
if ($LASTEXITCODE -ne 0) { throw 'uv sync failed' }

$python = Join-Path $repo '.venv\Scripts\python.exe'
Write-Host ("  python      {0}" -f (& $python -c 'import sys; print(sys.version.split()[0])'))

# -- prove it works ---------------------------------------------------------
Write-Host '  tests       running ...'
& $python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'test suite failed - the environment is not ready' }

Write-Host ''
Write-Host 'Ready.' -ForegroundColor Green
Write-Host ''
Write-Host '  Start the app     .\.venv\Scripts\python.exe -m streamlit run devapp\app.py --server.address localhost'
Write-Host '  Run the tests     .\.venv\Scripts\python.exe -m pytest'
Write-Host '  Try the kernel    .\.venv\Scripts\python.exe examples\demo.py'
Write-Host ''
Write-Host 'PowerShell chains commands with ";" - "&&" is a parser error there.' -ForegroundColor DarkGray
Write-Host ''
