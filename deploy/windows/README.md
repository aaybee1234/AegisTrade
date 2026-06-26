# AegisTrade Windows Deployment

Use the maintained runbook:

- `docs/runbooks/WINDOWS_VPS_DEPLOYMENT.md`
- `docs/FUTURE_TERRAFORM.md`

Fresh VPS command:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
New-Item -ItemType Directory -Force C:\Installers | Out-Null
Set-Location C:\Installers
Invoke-WebRequest -UseBasicParsing `
  -Uri "https://raw.githubusercontent.com/aaybee1234/AegisTrade/main/deploy/windows/bootstrap.ps1" `
  -OutFile "bootstrap.ps1"
powershell.exe -ExecutionPolicy Bypass -File .\bootstrap.ps1 -StartApp
```

AegisTrade uses Nginx on port 80. Do not expose ports 3000 or 4000 publicly. MT5 runs in an interactive Windows session; the API reads account-scoped snapshots from the worker bridge.
