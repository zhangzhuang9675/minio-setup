$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$exe = Join-Path $root 'bin\minio.exe'
$caFile = Join-Path $root 'client-certs\minio-root-ca.crt'
foreach ($requiredFile in @('certs\public.crt', 'certs\private.key', 'client-certs\minio-root-ca.crt')) {
    if (-not (Test-Path -LiteralPath (Join-Path $root $requiredFile))) { throw "Missing HTTPS certificate: $requiredFile" }
}
$existing = @(Get-CimInstance Win32_Process -Filter "Name='minio.exe'" | Where-Object { $_.ExecutablePath -eq $exe })
if ($existing.Count -gt 0) {
    Write-Output "MinIO is already running (PID $($existing[0].ProcessId))."
    exit 0
}
foreach ($port in @(9000, 9001)) {
    if (Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue) {
        throw "Port $port is already in use."
    }
}
$credential = Import-Clixml -LiteralPath (Join-Path $root 'config\credentials.xml')
$env:MINIO_ROOT_USER = $credential.UserName
$env:MINIO_ROOT_PASSWORD = $credential.GetNetworkCredential().Password
$env:MINIO_BROWSER = 'on'
$env:MINIO_BROWSER_REDIRECT_URL = 'https://127.0.0.1:9001'
$env:MINIO_API_CORS_ALLOW_ORIGIN = '*'
$env:MINIO_UPDATE = 'off'
$env:TEMP = Join-Path $root 'tmp'
$env:TMP = $env:TEMP
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$stdout = Join-Path $root "logs\minio-$stamp.stdout.log"
$stderr = Join-Path $root "logs\minio-$stamp.stderr.log"
try {
    $process = Start-Process -FilePath $exe -ArgumentList @('server', ('"' + (Join-Path $root 'data') + '"'), '--address', '0.0.0.0:9000', '--console-address', '127.0.0.1:9001', '--certs-dir', ('"' + (Join-Path $root 'certs') + '"')) -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
} finally {
    Remove-Item Env:MINIO_ROOT_PASSWORD -ErrorAction SilentlyContinue
    Remove-Item Env:MINIO_ROOT_USER -ErrorAction SilentlyContinue
}
$process.Id | Set-Content -LiteralPath (Join-Path $root 'minio.pid')
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    Start-Sleep -Seconds 1
    $process.Refresh()
    if ($process.HasExited) { throw "MinIO exited. Check $stderr and $stdout" }
    try {
        # This private CA has no online CRL service; still verify its chain and hostname.
        & curl.exe --noproxy '*' --cacert $caFile --ssl-revoke-best-effort --fail --silent --connect-timeout 2 --max-time 3 'https://127.0.0.1:9000/minio/health/ready' > $null
        if ($LASTEXITCODE -eq 0) {
            Write-Output 'MinIO HTTPS is ready. Console: https://127.0.0.1:9001 ; S3 API: https://127.0.0.1:9000 (LAN uses your certificate LAN IP)'
            exit 0
        }
    } catch { }
}
throw "MinIO did not become ready within 30 seconds. Check $stderr and $stdout"
