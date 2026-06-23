# Foresight frontend -> http://localhost:5173
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "frontend")
npm run dev
