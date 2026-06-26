param(
  [string]$ProjectDir = "C:\AegisTrade",
  [string]$RepoUrl = "https://github.com/aaybee1234/AegisTrade.git",
  [switch]$SkipClone
)

$ErrorActionPreference = "Stop"

function Require-Command($Name, $InstallHint) {
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    Write-Host "Missing $Name. $InstallHint" -ForegroundColor Yellow
    return $false
  }
  return $true
}

Write-Host "AegisTrade Windows VPS installer" -ForegroundColor Cyan
Write-Host "Target: $ProjectDir"

if (-not (Test-Path $ProjectDir)) {
  New-Item -ItemType Directory -Force -Path $ProjectDir | Out-Null
}

$hasGit = Require-Command git "Install Git using deploy\windows\README.md or run bootstrap.ps1"
$hasNode = Require-Command node "Install Node.js using deploy\windows\README.md or run bootstrap.ps1"
$hasNpm = Require-Command npm "Node.js should include npm."
$hasPython = Require-Command python "Install Python using deploy\windows\README.md or run bootstrap.ps1"

if (-not ($hasGit -and $hasNode -and $hasNpm -and $hasPython)) {
  Write-Host "Install missing prerequisites with deploy\windows\bootstrap.ps1 or the manual README steps, then rerun this script." -ForegroundColor Red
  exit 1
}

if (-not $SkipClone) {
  if (-not (Test-Path (Join-Path $ProjectDir ".git"))) {
    $parent = Split-Path $ProjectDir -Parent
    if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    git clone $RepoUrl $ProjectDir
  } else {
    Push-Location $ProjectDir
    git pull
    Pop-Location
  }
}

Push-Location $ProjectDir

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
  Write-Host "Created .env from .env.example. Fill OpenAI and Exness credentials before running live." -ForegroundColor Yellow
}

npm install
npm run build

Push-Location "services\worker"
python -m pip install -r requirements.txt
Pop-Location

Write-Host "Install complete." -ForegroundColor Green
Write-Host "Next: edit $ProjectDir\.env, open/login MT5, then run deploy\windows\start.ps1"
Pop-Location
