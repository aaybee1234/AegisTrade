param(
  [string]$ProjectDir = "C:\AegisTrade",
  [int]$PublicPort = 80
)

Write-Host "AegisTrade task status" -ForegroundColor Cyan
Get-ScheduledTask -TaskName "AegisTrade-*" -ErrorAction SilentlyContinue |
  Select-Object TaskName, State

Write-Host "`nHTTP checks" -ForegroundColor Cyan
try { "Public proxy HTTP " + (Invoke-WebRequest -UseBasicParsing "http://localhost:$PublicPort" -TimeoutSec 10).StatusCode } catch { "Proxy error: $($_.Exception.Message)" }
try { (Invoke-WebRequest -UseBasicParsing "http://localhost:$PublicPort/health" -TimeoutSec 10).Content } catch { "API error: $($_.Exception.Message)" }

Write-Host "`nMT5 bridge snapshot" -ForegroundColor Cyan
$snapshot = Join-Path $ProjectDir "runtime\accounts\primary\status.json"
if (Test-Path -LiteralPath $snapshot) {
  Get-Content -Raw -LiteralPath $snapshot
} else {
  "Snapshot missing: $snapshot"
}

Write-Host "`nRecent logs" -ForegroundColor Cyan
foreach ($name in "api", "web", "nginx", "worker") {
  $log = Join-Path $ProjectDir "logs\$name.log"
  if (Test-Path -LiteralPath $log) {
    "--- $name ---"
    Get-Content -LiteralPath $log -Tail 8
  }
}
