# Foresight backend -> http://127.0.0.1:8011
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$py = Join-Path $root "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { Write-Host "Run .\setup.ps1 first." -ForegroundColor Yellow; exit 1 }
Set-Location (Join-Path $root "backend")
& $py -m uvicorn main:app --host 127.0.0.1 --port 8011
