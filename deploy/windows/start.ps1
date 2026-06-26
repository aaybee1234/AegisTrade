param([string]$ProjectDir = "C:\AegisTrade")

$ErrorActionPreference = "Stop"
$tasks = @("AegisTrade-API", "AegisTrade-Web", "AegisTrade-Nginx", "AegisTrade-MT5-Worker")
foreach ($task in $tasks) {
  if (Get-ScheduledTask -TaskName $task -ErrorAction SilentlyContinue) {
    Start-ScheduledTask -TaskName $task
    Write-Host "Started $task" -ForegroundColor Green
  } else {
    Write-Host "Missing $task. Run deploy\windows\configure-services.ps1 first." -ForegroundColor Yellow
  }
}
Start-Sleep -Seconds 15
& (Join-Path $ProjectDir "deploy\windows\status.ps1") -ProjectDir $ProjectDir
