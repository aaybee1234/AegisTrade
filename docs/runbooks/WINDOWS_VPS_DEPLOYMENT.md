# Windows VPS Deployment

This is the supported single-account deployment for AegisTrade. It is structured so a future multi-user orchestrator can create one isolated MT5 terminal/worker bridge per account.

## Architecture

```text
Browser -> Nginx :80 -> Next.js :3000
                    -> Express API :4000

Interactive Windows session:
Exness MT5 <-> Python worker
                  | snapshots and commands
                  v
runtime/accounts/<account_id>/
```

MT5 Python IPC is session-local. The web API must not call MetaTrader directly from a Windows service session. The interactive worker owns MT5 access and exchanges JSON snapshots/commands with the API.

## Fresh Server

Use Windows Server with at least 2 vCPU, 4 GB RAM, and 30 GB disk. Open inbound TCP 80 and RDP 3389. Restrict WinRM 5985 to an administrator IP or close it after setup.

Run PowerShell as Administrator:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
New-Item -ItemType Directory -Force C:\Installers | Out-Null
Set-Location C:\Installers

Invoke-WebRequest `
  -UseBasicParsing `
  -Uri "https://raw.githubusercontent.com/aaybee1234/AegisTrade/main/deploy/windows/bootstrap.ps1" `
  -OutFile "bootstrap.ps1"

powershell.exe -ExecutionPolicy Bypass -File .\bootstrap.ps1 -StartApp
```

The bootstrap installs Git, Node.js, Python, Exness MT5, Nginx, dependencies, production builds, firewall rules, and persistent scheduled tasks.

## Required Interactive Step

1. Sign in to the Windows desktop as the deployment user.
2. Open Exness MT5.
3. Log into the exact account/server.
4. Enable Algo Trading.
5. Keep that Windows user session signed in. RDP may be disconnected, but do not sign out.

The `AegisTrade-MT5-Worker` task starts at that user's logon. API, web, and Nginx start with Windows.

## Environment

Secrets stay in `C:\AegisTrade\.env` and are ignored by Git.

Important settings:

```env
MT5_TERMINAL_PATH=C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe
MT5_ACCOUNT_ID=primary
SINGLE_USER_ACCOUNT_ID=primary
SINGLE_USER_CONTROL_TOKEN=<random-secret>
AUTO_TRADE_ENABLED=false
WORKER_POLL_SECONDS=5
MAX_OPEN_TRADES=2
MAX_DAILY_TRADES=100
MAX_RISK_PER_TRADE_USD=10
TARGET_PROFIT_PER_TRADE_USD=0.50
```

Keep `AUTO_TRADE_ENABLED=false` until status/advisory data has been observed and validated. Automatic execution remains demo-only in code.

## Existing Server Update

```powershell
Set-Location C:\AegisTrade
git pull
npm install
python -m pip install -r .\services\worker\requirements.txt
.\deploy\windows\configure-services.ps1 -ProjectDir C:\AegisTrade
```

Then log into MT5 and run:

```powershell
Start-ScheduledTask -TaskName AegisTrade-MT5-Worker
.\deploy\windows\status.ps1
```

## Operations

```powershell
.\deploy\windows\start.ps1
.\deploy\windows\stop.ps1
.\deploy\windows\status.ps1
.\deploy\windows\test-mt5.ps1
```

Public checks:

```powershell
Invoke-WebRequest http://SERVER_IP/
Invoke-WebRequest http://SERVER_IP/health
Invoke-WebRequest http://SERVER_IP/mt5/status
```

## Trading Semantics

- `$10` means maximum estimated loss at the broker-side stop, not `$10` notional exposure.
- `$0.50` is the desired profit target; broker minimum stop distance can make the actual TP larger.
- `100` is a daily ceiling, never a required trade quota.
- Win rate is measured from closed bot deals. It is not fixed or guaranteed.
- AI can explain, rank, reduce confidence, or veto. It cannot change deterministic trade parameters or bypass risk.
