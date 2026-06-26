param(
  [string]$ProjectDir = "D:\AegisTrade",
  [int]$ApiPort = 4000,
  [int]$WebPort = 3000
)

Write-Host "AegisTrade process status" -ForegroundColor Cyan
Get-CimInstance Win32_Process -Filter "name = 'node.exe'" | Where-Object { $_.CommandLine -like "*$ProjectDir*" } | Select-Object ProcessId,CommandLine

Write-Host "\nHTTP checks" -ForegroundColor Cyan
try { (Invoke-WebRequest -UseBasicParsing "http://localhost:$ApiPort/health" -TimeoutSec 10).Content } catch { "API error: $($_.Exception.Message)" }
try { "Web HTTP " + (Invoke-WebRequest -UseBasicParsing "http://localhost:$WebPort" -TimeoutSec 10).StatusCode } catch { "Web error: $($_.Exception.Message)" }

Write-Host "\nMT5 status" -ForegroundColor Cyan
Push-Location (Join-Path $ProjectDir "services\worker")
python -m aegis_worker.status_json
Pop-Location
