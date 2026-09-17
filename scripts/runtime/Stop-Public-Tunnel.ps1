$ErrorActionPreference = 'Stop'
$exe = Join-Path $PSScriptRoot 'tunnel\cloudflared.exe'
$processes = @(Get-CimInstance Win32_Process -Filter "Name='cloudflared.exe'" | Where-Object { $_.ExecutablePath -eq $exe })
foreach ($process in $processes) { Stop-Process -Id $process.ProcessId -ErrorAction Stop }
Write-Output 'This deployment public tunnel has been stopped. MinIO itself remains running.'
