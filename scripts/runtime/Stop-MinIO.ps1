$ErrorActionPreference = 'Stop'
$exe = Join-Path $PSScriptRoot 'bin\minio.exe'
$processes = @(Get-CimInstance Win32_Process -Filter "Name='minio.exe'" | Where-Object { $_.ExecutablePath -eq $exe })
foreach ($process in $processes) {
    Stop-Process -Id $process.ProcessId -ErrorAction Stop
    Wait-Process -Id $process.ProcessId -Timeout 15 -ErrorAction SilentlyContinue
}
Remove-Item -LiteralPath (Join-Path $PSScriptRoot 'minio.pid') -ErrorAction SilentlyContinue
Write-Output 'MinIO stopped.'
