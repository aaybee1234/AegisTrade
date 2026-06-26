param([string]$ProjectDir = "C:\AegisTrade")

$tasks = @("AegisTrade-MT5-Worker", "AegisTrade-Nginx", "AegisTrade-Web", "AegisTrade-API")
foreach ($task in $tasks) {
  if (Get-ScheduledTask -TaskName $task -ErrorAction SilentlyContinue) {
    Stop-ScheduledTask -TaskName $task -ErrorAction SilentlyContinue
    Write-Host "Stopped $task"
  }
}
