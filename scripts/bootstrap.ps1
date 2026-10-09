# Isla AI bootstrap - provisions a clean machine into a running local app.
#
# Windows PowerShell. Safe to re-run: every step is idempotent.
# Usage:  powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Py = Join-Path $Root ".venv\Scripts\python.exe"
$Step = 0

function Step-Start($msg) {
    $script:Step++
    Write-Host ""
    Write-Host "[$script:Step] $msg" -ForegroundColor Cyan
}

Write-Host "Isla AI bootstrap" -ForegroundColor White
Write-Host "  $Root"

# 1. Python 3.12 ------------------------------------------------------------
# 3.14 is installed by default on many machines but has NO wheels for
# transformers / gliner / presidio / llama-cpp-python / optimum.
Step-Start "Provisioning Python 3.12"
if (Test-Path $Py) {
    $ver = & $Py --version 2>&1
    Write-Host "  venv already present: $ver" -ForegroundColor DarkGray
} else {
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Write-Host "  'uv' not found. Install from https://docs.astral.sh/uv/ then re-run." -ForegroundColor Yellow
        exit 1
    }
    uv python install 3.12
    uv venv --python 3.12 .venv
    Write-Host "  created .venv on 3.12"
}

# 2. Dependencies ------------------------------------------------------------
Step-Start "Installing dependencies (CPU torch first)"
uv pip install --python $Py torch --index-url https://download.pytorch.org/whl/cpu --quiet
uv pip install --python $Py -r requirements.txt --quiet
Write-Host "  done"

# 3. Model weights -----------------------------------------------------------
Step-Start "Fetching model weights (this is the slow part on a cold network)"
$skipModels = $false
if ($args -contains "--skip-models") { $skipModels = $true }
if ($skipModels) {
    Write-Host "  --skip-models supplied; continuing without weights." -ForegroundColor Yellow
} else {
    & $Py models\download_models.py
}

# 4. Corpus ------------------------------------------------------------------
Step-Start "Fetching and indexing the Philippine privacy corpus"
& $Py corpus\fetch_corpus.py
& $Py corpus\chunk_corpus.py

# 5. UI ----------------------------------------------------------------------
Step-Start "Building the web UI"
Push-Location "$Root\apps\web"
if (-not (Test-Path "node_modules")) { npm install --no-audit --no-fund --silent }
npm run build --silent
Pop-Location
Write-Host "  built apps/web/dist"

# 6. Verify ------------------------------------------------------------------
Step-Start "Self-check"
& $Py -m pytest tests/ -q --tb=short
& $Py eval\run_eval.py --pii-only

Write-Host ""
Write-Host "Ready." -ForegroundColor Green
Write-Host "  Start Isla AI:" -ForegroundColor White
Write-Host "    .venv\Scripts\python.exe -m uvicorn services.core.app:app --host 127.0.0.1 --port 8765"
Write-Host "  Then open http://127.0.0.1:8765" -ForegroundColor White