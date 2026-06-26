param(
  [string]$ProjectDir = "C:\AegisTrade",
  [string]$NginxDir = "C:\nginx",
  [string]$NginxUrl = "https://nginx.org/download/nginx-1.26.3.zip",
  [string]$Mt5Path = "C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe",
  [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
$logs = Join-Path $ProjectDir "logs"
New-Item -ItemType Directory -Force -Path $logs | Out-Null

function Write-Runner([string]$Name, [string]$Body) {
  Set-Content -LiteralPath (Join-Path $ProjectDir $Name) -Value $Body -Encoding ASCII
}

function Register-SystemTask([string]$Name, [string]$Runner, [int]$DelaySeconds = 0) {
  $action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$Runner`""
  $trigger = New-ScheduledTaskTrigger -AtStartup
  if ($DelaySeconds -gt 0) {
    $trigger.Delay = "PT${DelaySeconds}S"
  }
  $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
  $settings = New-ScheduledTaskSettingsSet -RestartCount 5 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero)
  Register-ScheduledTask -TaskName $Name -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
}

if (-not (Test-Path -LiteralPath (Join-Path $NginxDir "nginx.exe"))) {
  $zip = Join-Path $env:TEMP "aegistrade-nginx.zip"
  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
  Invoke-WebRequest -UseBasicParsing -Uri $NginxUrl -OutFile $zip
  $extract = Join-Path $env:TEMP "aegistrade-nginx"
  if (Test-Path -LiteralPath $extract) { Remove-Item -LiteralPath $extract -Recurse -Force }
  Expand-Archive -LiteralPath $zip -DestinationPath $extract -Force
  $source = Get-ChildItem -LiteralPath $extract -Directory | Select-Object -First 1
  Move-Item -LiteralPath $source.FullName -Destination $NginxDir
}

Copy-Item `
  -LiteralPath (Join-Path $ProjectDir "deploy\windows\nginx\nginx.conf") `
  -Destination (Join-Path $NginxDir "conf\nginx.conf") `
  -Force

if (-not $SkipBuild) {
  Push-Location $ProjectDir
  npm run build
  Pop-Location
}

$apiRunner = @"
Set-Location '$ProjectDir'
npm run start:api *>> '$logs\api.log'
"@
$webRunner = @"
Set-Location '$ProjectDir'
npm run start:web *>> '$logs\web.log'
"@
$nginxRunner = @"
Set-Location '$NginxDir'
& '$NginxDir\nginx.exe' -p '$NginxDir' *>> '$logs\nginx.log'
"@
$workerRunner = @"
Set-Location '$ProjectDir\services\worker'
python -m aegis_worker.daemon *>> '$logs\worker.log'
"@
$mt5Runner = @"
if (Test-Path -LiteralPath '$Mt5Path') {
  if (-not (Get-Process terminal64 -ErrorAction SilentlyContinue)) {
    Start-Process -FilePath '$Mt5Path'
    Start-Sleep -Seconds 20
  }
}
Set-Location '$ProjectDir\services\worker'
python -m aegis_worker.daemon *>> '$logs\worker.log'
"@

Write-Runner "run-api.ps1" $apiRunner
Write-Runner "run-web.ps1" $webRunner
Write-Runner "run-nginx.ps1" $nginxRunner
Write-Runner "run-worker.ps1" $workerRunner
Write-Runner "run-mt5-worker.ps1" $mt5Runner

Register-SystemTask "AegisTrade-API" (Join-Path $ProjectDir "run-api.ps1") 10
Register-SystemTask "AegisTrade-Web" (Join-Path $ProjectDir "run-web.ps1") 15
Register-SystemTask "AegisTrade-Nginx" (Join-Path $ProjectDir "run-nginx.ps1") 25

$interactiveAction = New-ScheduledTaskAction `
  -Execute "powershell.exe" `
  -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$(Join-Path $ProjectDir 'run-mt5-worker.ps1')`""
$interactiveTrigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$interactivePrincipal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest
$interactiveSettings = New-ScheduledTaskSettingsSet -RestartCount 5 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero)
Register-ScheduledTask `
  -TaskName "AegisTrade-MT5-Worker" `
  -Action $interactiveAction `
  -Trigger $interactiveTrigger `
  -Principal $interactivePrincipal `
  -Settings $interactiveSettings `
  -Force | Out-Null

if (-not (Get-NetFirewallRule -DisplayName "AegisTrade HTTP" -ErrorAction SilentlyContinue)) {
  New-NetFirewallRule -DisplayName "AegisTrade HTTP" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 80 | Out-Null
}

foreach ($task in "AegisTrade-API", "AegisTrade-Web", "AegisTrade-Nginx", "AegisTrade-MT5-Worker") {
  Start-ScheduledTask -TaskName $task
}

Start-Sleep -Seconds 20
Write-Host "AegisTrade persistent tasks configured." -ForegroundColor Green
& (Join-Path $ProjectDir "deploy\windows\status.ps1") -ProjectDir $ProjectDir
