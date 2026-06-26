param([string]$ProjectDir = "D:\AegisTrade")

$procs = Get-CimInstance Win32_Process -Filter "name = 'node.exe'" | Where-Object { $_.CommandLine -like "*$ProjectDir*" }
foreach ($p in $procs) {
  Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
  Write-Host "Stopped node process $($p.ProcessId)"
}
