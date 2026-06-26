param(
  [string]$ProjectDir = "D:\AegisTrade",
  [int]$ApiPort = 4000,
  [int]$WebPort = 3000
)

$ErrorActionPreference = "Stop"
$logDir = Join-Path $ProjectDir "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Start-AegisProcess($Name, $Command, $WorkingDirectory, $LogFile) {
  $existing = Get-CimInstance Win32_Process -Filter "name = 'node.exe'" | Where-Object { $_.CommandLine -like "*$ProjectDir*" -and $_.CommandLine -like "*$Name*" }
  if ($existing) {
    Write-Host "$Name appears to already be running." -ForegroundColor Yellow
    return
  }

  $ps = "Set-Location '$WorkingDirectory'; $Command *> '$LogFile'"
  Start-Process powershell.exe -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $ps -WindowStyle Hidden
  Write-Host "Started $Name. Log: $LogFile" -ForegroundColor Green
}

Push-Location $ProjectDir

Start-AegisProcess "tsx" "npm run dev:api" $ProjectDir (Join-Path $logDir "api.log")
Start-Sleep -Seconds 3
Start-AegisProcess "next" "npm run dev:web" $ProjectDir (Join-Path $logDir "web.log")

Start-Sleep -Seconds 8
try {
  $api = Invoke-WebRequest -UseBasicParsing "http://localhost:$ApiPort/health" -TimeoutSec 10
  Write-Host "API: $($api.Content)" -ForegroundColor Green
} catch {
  Write-Host "API did not respond yet. Check logs\api.log" -ForegroundColor Yellow
}

try {
  $web = Invoke-WebRequest -UseBasicParsing "http://localhost:$WebPort" -TimeoutSec 20
  Write-Host "Web: HTTP $($web.StatusCode)" -ForegroundColor Green
} catch {
  Write-Host "Web did not respond yet. Check logs\web.log" -ForegroundColor Yellow
}

Write-Host "Dashboard: http://localhost:$WebPort"
Pop-Location
