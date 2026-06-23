# Foresight — one-time setup (Windows / PowerShell)
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$py = Join-Path $root "backend\.venv\Scripts\python.exe"

Write-Host "[1/3] Python venv..." -ForegroundColor Cyan
if (-not (Test-Path $py)) { python -m venv (Join-Path $root "backend\.venv") }

Write-Host "[2/3] Backend deps..." -ForegroundColor Cyan
& $py -m pip install --quiet --upgrade pip
& $py -m pip install --quiet -r (Join-Path $root "backend\requirements.txt")

Write-Host "[3/3] Frontend deps..." -ForegroundColor Cyan
Push-Location (Join-Path $root "frontend"); npm install; Pop-Location

Write-Host "`nDone. Run in two terminals:" -ForegroundColor Green
Write-Host "  .\run-backend.ps1   (http://127.0.0.1:8011)"
Write-Host "  .\run-frontend.ps1  (http://localhost:5173)"
