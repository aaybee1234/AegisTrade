param([string]$ProjectDir = "C:\AegisTrade")

$ErrorActionPreference = "Stop"
Push-Location (Join-Path $ProjectDir "services\worker")
Write-Host "Testing MT5 package and Exness connection..." -ForegroundColor Cyan
python -m aegis_worker.status_json
Write-Host "Testing advisory scan..." -ForegroundColor Cyan
python -m aegis_worker.advisory_json
Pop-Location
