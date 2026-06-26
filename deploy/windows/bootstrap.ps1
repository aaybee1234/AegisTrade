param(
  [string]$ProjectDir = "C:\AegisTrade",
  [string]$RepoUrl = "https://github.com/aaybee1234/AegisTrade.git",
  [string]$InstallersDir = "C:\Installers",
  [string]$NodeUrl = "https://nodejs.org/dist/v20.18.1/node-v20.18.1-x64.msi",
  [string]$GitUrl = "https://github.com/git-for-windows/git/releases/download/v2.51.0.windows.1/Git-2.51.0-64-bit.exe",
  [string]$PythonUrl = "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe",
  [string]$Mt5Url = "https://download.terminal.free/cdn/web/exness.technologies.ltd/mt5/exness5setup.exe",
  [string]$ArtifactBaseUrl = "",
  [string]$OpenAiApiKey = "",
  [string]$ExnessLogin = "",
  [string]$ExnessPassword = "",
  [string]$ExnessServer = "",
  [switch]$SkipPrerequisites,
  [switch]$SkipMt5,
  [switch]$Build,
  [switch]$StartApp
)

$ErrorActionPreference = "Stop"

function Write-Step($Message) {
  Write-Host ""
  Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-Ok($Message) {
  Write-Host "[ok] $Message" -ForegroundColor Green
}

function Write-Warn($Message) {
  Write-Host "[warn] $Message" -ForegroundColor Yellow
}

function Refresh-Path {
  $machine = [Environment]::GetEnvironmentVariable("Path", "Machine")
  $user = [Environment]::GetEnvironmentVariable("Path", "User")
  $env:Path = "$machine;$user"
}

function ConvertTo-PlainText([securestring]$SecureValue) {
  if (-not $SecureValue) { return "" }
  $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureValue)
  try {
    return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
  } finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
  }
}

function Read-SecretIfMissing([string]$CurrentValue, [string]$Prompt) {
  if ($CurrentValue) { return $CurrentValue }
  $secure = Read-Host $Prompt -AsSecureString
  return ConvertTo-PlainText $secure
}

function Download-File([string]$Url, [string]$OutFile) {
  if (Test-Path -LiteralPath $OutFile) {
    Write-Ok "Using cached installer: $OutFile"
    return
  }

  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
  Write-Host "Downloading $Url"
  try {
    Invoke-WebRequest -UseBasicParsing -Uri $Url -OutFile $OutFile
  } catch {
    Write-Warn "Invoke-WebRequest failed, trying curl.exe fallback. $($_.Exception.Message)"
    & curl.exe -L $Url -o $OutFile
    if ($LASTEXITCODE -ne 0) {
      throw "curl.exe download failed for $Url"
    }
  }
}

function Resolve-ArtifactUrl([string]$DefaultUrl, [string]$FileName) {
  if (-not $ArtifactBaseUrl) { return $DefaultUrl }
  return ($ArtifactBaseUrl.TrimEnd("/") + "/" + $FileName)
}

function Test-CommandExists([string]$Command) {
  return [bool](Get-Command $Command -ErrorAction SilentlyContinue)
}

function Install-Node {
  if (Test-CommandExists "node") {
    Write-Ok "Node.js already installed: $(node --version)"
    return
  }
  $file = Join-Path $InstallersDir "node-v20.18.1-x64.msi"
  Download-File (Resolve-ArtifactUrl $NodeUrl "node-v20.18.1-x64.msi") $file
  Start-Process msiexec.exe -ArgumentList "/i", $file, "/qn", "/norestart" -Wait
  Refresh-Path
  if (-not (Test-CommandExists "node")) { throw "Node.js install finished but node is not on PATH. Reopen PowerShell and rerun." }
  Write-Ok "Node.js installed: $(node --version)"
}

function Install-Git {
  if (Test-CommandExists "git") {
    Write-Ok "Git already installed: $(git --version)"
    return
  }
  $file = Join-Path $InstallersDir "Git-2.51.0-64-bit.exe"
  Download-File (Resolve-ArtifactUrl $GitUrl "Git-2.51.0-64-bit.exe") $file
  Start-Process $file -ArgumentList "/VERYSILENT /NORESTART" -Wait
  Refresh-Path
  if (-not (Test-CommandExists "git")) { throw "Git install finished but git is not on PATH. Reopen PowerShell and rerun." }
  Write-Ok "Git installed: $(git --version)"
}

function Install-Python {
  if (Test-CommandExists "python") {
    Write-Ok "Python already installed: $(python --version)"
    return
  }
  $file = Join-Path $InstallersDir "python-3.12.8-amd64.exe"
  Download-File (Resolve-ArtifactUrl $PythonUrl "python-3.12.8-amd64.exe") $file
  Start-Process $file -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1 Include_pip=1" -Wait
  Refresh-Path
  if (-not (Test-CommandExists "python")) { throw "Python install finished but python is not on PATH. Reopen PowerShell and rerun." }
  Write-Ok "Python installed: $(python --version)"
}

function Install-Mt5 {
  if ($SkipMt5) {
    Write-Warn "Skipping MT5 installer."
    return
  }
  $terminalPaths = @(
    "C:\Program Files\MetaTrader 5\terminal64.exe",
    "C:\Program Files\Exness MetaTrader 5\terminal64.exe",
    "C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
  )
  foreach ($path in $terminalPaths) {
    if (Test-Path -LiteralPath $path) {
      Write-Ok "MT5 appears installed: $path"
      return
    }
  }

  $file = Join-Path $InstallersDir "exness5setup.exe"
  Download-File (Resolve-ArtifactUrl $Mt5Url "exness5setup.exe") $file
  Write-Warn "The MT5 installer may show a GUI. Complete it if prompted."
  Start-Process $file -Wait
}

function Sync-Repository {
  if (-not (Test-Path -LiteralPath $ProjectDir)) {
    $parent = Split-Path $ProjectDir -Parent
    if (-not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
  }

  if (Test-Path -LiteralPath (Join-Path $ProjectDir ".git")) {
    Write-Step "Updating repository"
    Push-Location $ProjectDir
    git pull
    Pop-Location
  } else {
    Write-Step "Cloning repository"
    if (Test-Path -LiteralPath $ProjectDir) {
      $items = Get-ChildItem -LiteralPath $ProjectDir -Force -ErrorAction SilentlyContinue
      if ($items) { throw "$ProjectDir exists but is not empty and is not a git repo." }
    }
    git clone $RepoUrl $ProjectDir
  }
}

function Write-EnvFile {
  Write-Step "Preparing .env"
  Push-Location $ProjectDir
  if (-not (Test-Path -LiteralPath ".env.example")) { throw ".env.example not found in $ProjectDir" }

  if (-not (Test-Path -LiteralPath ".env")) {
    Copy-Item ".env.example" ".env"
  }

  $script:OpenAiApiKey = Read-SecretIfMissing $script:OpenAiApiKey "OpenAI API key"
  if (-not $script:ExnessLogin) { $script:ExnessLogin = Read-Host "Exness MT5 login" }
  $script:ExnessPassword = Read-SecretIfMissing $script:ExnessPassword "Exness MT5 password"
  if (-not $script:ExnessServer) { $script:ExnessServer = Read-Host "Exness MT5 server, for example Exness-MT5Trial16" }

  $lines = @(
    "NODE_ENV=production",
    "DATABASE_URL=postgresql://aegis:aegis@localhost:5432/aegistrade",
    "REDIS_URL=redis://localhost:6379",
    "API_PORT=4000",
    "WEB_PORT=3000",
    "OPENAI_API_KEY=$script:OpenAiApiKey",
    "OPENAI_MODEL=gpt-4.1-mini",
    "OPENAI_REASONING_MODEL=gpt-4.1",
    "EXNESS_DEMO_LOGIN=$script:ExnessLogin",
    "EXNESS_DEMO_PASSWORD=$script:ExnessPassword",
    "EXNESS_DEMO_SERVER=$script:ExnessServer",
    "MT5_TERMINAL_PATH=C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe",
    "MT5_ACCOUNT_ID=primary",
    "SINGLE_USER_ACCOUNT_ID=primary",
    "SINGLE_USER_CONTROL_TOKEN=$([guid]::NewGuid().ToString('N'))",
    "AUTO_TRADE_ENABLED=false",
    "WORKER_POLL_SECONDS=5",
    "MAX_OPEN_TRADES=2",
    "MAX_DAILY_TRADES=100",
    "MAX_RISK_PER_TRADE_USD=10",
    "TARGET_PROFIT_PER_TRADE_USD=0.50"
  )
  Set-Content -LiteralPath ".env" -Value $lines -Encoding UTF8
  Write-Ok ".env written at $ProjectDir\.env"
  Pop-Location
}

function Install-AppDependencies {
  Write-Step "Installing AegisTrade dependencies"
  Push-Location $ProjectDir
  npm install

  Push-Location "services\worker"
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
  Pop-Location

  if ($Build) {
    npm run build
  } else {
    Write-Warn "Skipping npm run build for low-RAM VPS startup. Run npm run build later for production validation."
  }
  Pop-Location
}

function Start-AegisTrade {
  if (-not $StartApp) { return }
  Write-Step "Starting AegisTrade"
  & (Join-Path $ProjectDir "deploy\windows\configure-services.ps1") -ProjectDir $ProjectDir
}

Write-Step "AegisTrade fresh Windows VPS bootstrap"
Write-Host "ProjectDir: $ProjectDir"
Write-Host "InstallersDir: $InstallersDir"
if ($ArtifactBaseUrl) { Write-Host "ArtifactBaseUrl: $ArtifactBaseUrl" }

New-Item -ItemType Directory -Force -Path $InstallersDir | Out-Null
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

if (-not $SkipPrerequisites) {
  Write-Step "Installing prerequisites"
  Install-Git
  Install-Node
  Install-Python
  Install-Mt5
} else {
  Write-Warn "Skipping prerequisite installation."
}

Sync-Repository
Write-EnvFile
Install-AppDependencies
Start-AegisTrade

Write-Host ""
Write-Ok "VPS bootstrap complete."
Write-Host "Next checks:"
Write-Host "  cd $ProjectDir"
Write-Host "  .\deploy\windows\status.ps1"
Write-Host "  .\deploy\windows\test-mt5.ps1"
Write-Host ""
Write-Warn "MT5 may still require one manual GUI login/confirmation on the VPS. Keep MT5 open while AegisTrade is running."
