$ErrorActionPreference = 'Stop'
$exe = Join-Path $PSScriptRoot 'bin\minio.exe'
Get-CimInstance Win32_Process -Filter "Name='minio.exe'" | Where-Object { $_.ExecutablePath -eq $exe } | Select-Object ProcessId, ExecutablePath
$caFile = Join-Path $PSScriptRoot 'client-certs\minio-root-ca.crt'
$failed = $false
foreach ($endpoint in @('https://127.0.0.1:9000/minio/health/live', 'https://127.0.0.1:9000/minio/health/ready', 'https://127.0.0.1:9001')) {
    try {
        $status = & curl.exe --noproxy '*' --cacert $caFile --ssl-revoke-best-effort --silent --show-error --output NUL --write-out '%{http_code}' --connect-timeout 3 --max-time 5 $endpoint
        if ($LASTEXITCODE -ne 0 -or $status -ne '200') { throw "HTTPS check failed, HTTP status $status" }
        Write-Output "$endpoint : HTTP $status (certificate verified)"
    } catch { $failed = $true; Write-Output "$endpoint : unavailable ($($_.Exception.Message))" }
}
if ($failed) { throw 'One or more MinIO HTTPS checks failed.' }
