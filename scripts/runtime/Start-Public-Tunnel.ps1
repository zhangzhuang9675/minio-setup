$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$tunnelRoot = Join-Path $root 'tunnel'
$exe = Join-Path $tunnelRoot 'cloudflared.exe'
$stateFile = Join-Path $tunnelRoot 'current-tunnel.json'
if (Test-Path -LiteralPath $stateFile) {
    $state = Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json
    $existing = Get-CimInstance Win32_Process -Filter "ProcessId=$($state.pid)" -ErrorAction SilentlyContinue
    if ($existing -and $existing.ExecutablePath -eq $exe) {
        Write-Output "Tunnel process is already running (PID $($state.pid)). Last assigned URL: $($state.url)"
        exit 0
    }
}
$caFile = Join-Path $root 'client-certs\minio-root-ca.crt'
& curl.exe --noproxy '*' --cacert $caFile --ssl-revoke-best-effort --fail --silent --show-error --max-time 5 'https://127.0.0.1:9000/minio/health/ready'
if ($LASTEXITCODE -ne 0) { throw 'Start MinIO successfully before starting the tunnel.' }
$env:TEMP = Join-Path $root 'tmp'
$env:TMP = $env:TEMP
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$stdout = Join-Path $root "logs\tunnel-$stamp.stdout.log"
$stderr = Join-Path $root "logs\tunnel-$stamp.stderr.log"
$arguments = @('tunnel', '--no-autoupdate', '--protocol', 'http2', '--edge-ip-version', '4', '--url', 'https://127.0.0.1:9000', '--origin-server-name', 'localhost', '--origin-ca-pool', ('"' + $caFile + '"'))
$process = Start-Process -FilePath $exe -ArgumentList $arguments -WorkingDirectory $tunnelRoot -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
$state = [ordered]@{pid=$process.Id;url=$null;startedAt=(Get-Date -Format o);stdout=$stdout;stderr=$stderr;kind='temporary Cloudflare Quick Tunnel';origin='https://127.0.0.1:9000'}
$state | ConvertTo-Json | Set-Content -LiteralPath $stateFile
for ($attempt=0; $attempt -lt 45; $attempt++) {
    Start-Sleep -Seconds 1
    $process.Refresh()
    if ($process.HasExited) { throw "Tunnel process exited. Check $stderr" }
    $log = Get-Content -LiteralPath $stderr -Raw -ErrorAction SilentlyContinue
    if ($log -match 'https://[a-z0-9-]+\.trycloudflare\.com') {
        $state.url = $Matches[0]
        $state | ConvertTo-Json | Set-Content -LiteralPath $stateFile
        Write-Output "Assigned temporary public HTTPS endpoint: $($state.url)"
        Write-Output 'Check public connectivity before using it. Restarting this tunnel changes the endpoint.'
        exit 0
    }
}
throw "No public URL assigned within 45 seconds. Check $stderr"
