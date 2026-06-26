# AegisTrade Windows VPS Startup

This folder contains lightweight scripts for a low-cost Windows VPS deployment.

## Recommended Minimum VPS

For the first MVP/user account:

```text
2 vCPU
2 GB RAM
Windows Server
30 GB disk minimum
```

This is okay for:

- one MT5 terminal
- one API process
- one Next.js web process
- light demo trading/testing

For a smoother first VPS, 4 GB RAM and 2 vCPU is recommended. For multiple users/MT5 terminals, upgrade RAM first.

## Fast Fresh VPS Bootstrap

Use this when you are preparing a new Windows VPS from zero.

Open PowerShell as Administrator and run this on a completely fresh VPS:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

New-Item -ItemType Directory -Force C:\Installers | Out-Null
cd C:\Installers

Invoke-WebRequest `
  -UseBasicParsing `
  -Uri "https://raw.githubusercontent.com/aaybee1234/AegisTrade/main/deploy/windows/bootstrap.ps1" `
  -OutFile "bootstrap.ps1"

powershell.exe -ExecutionPolicy Bypass -File .\bootstrap.ps1 -StartApp
```

If `Invoke-WebRequest` fails, use the curl fallback:

```powershell
curl.exe -L "https://raw.githubusercontent.com/aaybee1234/AegisTrade/main/deploy/windows/bootstrap.ps1" -o bootstrap.ps1
powershell.exe -ExecutionPolicy Bypass -File .\bootstrap.ps1 -StartApp
```

The bootstrap script will:

- create `C:\Installers`
- download and install Git, Node.js, Python, and Exness MT5
- clone or update AegisTrade
- prompt for OpenAI and Exness credentials
- create `D:\AegisTrade\.env`
- install npm dependencies
- install Python worker dependencies
- optionally start the API and dashboard

MT5 may still require one manual GUI login/confirmation on the VPS. After that, keep MT5 open while AegisTrade is running.

By default, bootstrap skips `npm run build` to stay friendly to low-RAM Windows VPS machines. To force a build, add `-Build`:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\bootstrap.ps1 -StartApp -Build
```

## Bootstrap With S3 Artifacts

You do not need AWS CLI credentials just to run the VPS script if your installer files are available through public or pre-signed HTTPS URLs.

The script supports this optional artifact layout:

```text
https://YOUR_BUCKET_OR_CDN/aegistrade-installers/node-v20.18.1-x64.msi
https://YOUR_BUCKET_OR_CDN/aegistrade-installers/Git-2.51.0-64-bit.exe
https://YOUR_BUCKET_OR_CDN/aegistrade-installers/python-3.12.8-amd64.exe
https://YOUR_BUCKET_OR_CDN/aegistrade-installers/exness5setup.exe
```

Then run:

```powershell
.\deploy\windows\bootstrap.ps1 `
  -ArtifactBaseUrl "https://YOUR_BUCKET_OR_CDN/aegistrade-installers" `
  -StartApp
```

AWS CLI credentials are only needed if you want this repo to create the S3 bucket and upload installer artifacts for you. For the VPS itself, pre-signed/public artifact URLs are simpler.

## Manual Prerequisites

Windows Server 2016 usually does not include `winget`, so use direct installers.

Create an installer folder first:

```powershell
New-Item -ItemType Directory -Force C:\Installers
cd C:\Installers
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
```

### Node.js

```powershell
Invoke-WebRequest `
  -Uri "https://nodejs.org/dist/v20.18.1/node-v20.18.1-x64.msi" `
  -OutFile "node-v20.18.1-x64.msi"

msiexec /i .\node-v20.18.1-x64.msi /qn /norestart
```

If `Invoke-WebRequest` still fails, use:

```powershell
curl.exe -L "https://nodejs.org/dist/v20.18.1/node-v20.18.1-x64.msi" -o node-v20.18.1-x64.msi
msiexec /i .\node-v20.18.1-x64.msi /qn /norestart
```

### Git

```powershell
Invoke-WebRequest `
  -Uri "https://github.com/git-for-windows/git/releases/download/v2.51.0.windows.1/Git-2.51.0-64-bit.exe" `
  -OutFile "Git-2.51.0-64-bit.exe"

Start-Process .\Git-2.51.0-64-bit.exe -ArgumentList "/VERYSILENT /NORESTART" -Wait
```

If `Invoke-WebRequest` still fails, use:

```powershell
curl.exe -L "https://github.com/git-for-windows/git/releases/download/v2.51.0.windows.1/Git-2.51.0-64-bit.exe" -o Git-2.51.0-64-bit.exe
Start-Process .\Git-2.51.0-64-bit.exe -ArgumentList "/VERYSILENT /NORESTART" -Wait
```

### Python

```powershell
Invoke-WebRequest `
  -Uri "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe" `
  -OutFile "python-3.12.8-amd64.exe"

Start-Process .\python-3.12.8-amd64.exe -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1 Include_pip=1" -Wait
```

If `Invoke-WebRequest` still fails, use:

```powershell
curl.exe -L "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe" -o python-3.12.8-amd64.exe
Start-Process .\python-3.12.8-amd64.exe -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1 Include_pip=1" -Wait
```

Close and reopen PowerShell, then confirm:

```powershell
git --version
node --version
npm --version
python --version
pip --version
```

If you are on a newer Windows machine with `winget`, this shortcut is also okay:

```powershell
winget install --id Git.Git -e
winget install --id OpenJS.NodeJS.LTS -e
winget install --id Python.Python.3.12 -e
```

## MetaTrader 5

Install MetaTrader 5 x64 and log into the Exness MT5 account on the VPS.

Official Exness MT5 page:

```text
https://www.exness.com/metatrader-5/
```

Direct Exness MT5 Windows installer:

```powershell
cd C:\Installers
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

Invoke-WebRequest `
  -Uri "https://download.terminal.free/cdn/web/exness.technologies.ltd/mt5/exness5setup.exe" `
  -OutFile "exness5setup.exe"

Start-Process .\exness5setup.exe -Wait
```

If `Invoke-WebRequest` fails, use:

```powershell
curl.exe -L "https://download.terminal.free/cdn/web/exness.technologies.ltd/mt5/exness5setup.exe" -o exness5setup.exe
Start-Process .\exness5setup.exe -Wait
```

After installing MT5:

- open MetaTrader 5 on the VPS
- log in to the correct Exness demo/live account
- select the exact server shown in Exness, for example `Exness-MT5Trial16`
- keep MT5 running while AegisTrade is running
- enable Algo Trading in MT5 if the terminal asks for it

## First Setup Without Bootstrap

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
cd D:\
git clone https://github.com/aaybee1234/AegisTrade.git
cd D:\AegisTrade
.\deploy\windows\install.ps1 -SkipClone
```

Edit:

```text
D:\AegisTrade\.env
```

Set:

```env
OPENAI_API_KEY=
EXNESS_DEMO_LOGIN=
EXNESS_DEMO_PASSWORD=
EXNESS_DEMO_SERVER=
```

## Start

```powershell
cd D:\AegisTrade
.\deploy\windows\start.ps1
```

Open:

```text
http://SERVER_PUBLIC_IP:3000
```

For production, put Caddy/Nginx/IIS reverse proxy in front later.

## Stop

```powershell
.\deploy\windows\stop.ps1
```

## Status

```powershell
.\deploy\windows\status.ps1
```

## MT5 Test

```powershell
.\deploy\windows\test-mt5.ps1
```

## Logs

```text
D:\AegisTrade\logs\api.log
D:\AegisTrade\logs\web.log
```

## Cost-Saving Notes

For startup MVP, keep everything on one Windows VPS:

- no Docker unless needed
- no managed Postgres yet
- no Redis until queues are added
- one MT5 terminal/account first

Move database/dashboard to Linux only after user load justifies a second server.
