$ErrorActionPreference = 'Stop'
$state = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'tunnel\current-tunnel.json') -Raw | ConvertFrom-Json
$process = Get-CimInstance Win32_Process -Filter "ProcessId=$($state.pid)" -ErrorAction SilentlyContinue
$exe = Join-Path $PSScriptRoot 'tunnel\cloudflared.exe'
if (-not $process -or $process.ExecutablePath -ne $exe) { throw 'The tunnel is not running. Start-Public-Tunnel.cmd creates a new URL.' }
if (-not $state.url) { throw 'The tunnel has not been assigned a public URL. Check its logs.' }
Write-Output "Endpoint: $($state.url)"
Write-Output 'Bucket: test'
Write-Output 'Region: us-east-1 ; Virtual Host: off'
Write-Output 'Use your configured MinIO username/access key and its corresponding password/secret.'
$status = & curl.exe --noproxy '*' --silent --show-error --output NUL --write-out '%{http_code}' --connect-timeout 8 --max-time 15 ($state.url + '/minio/health/ready')
if ($LASTEXITCODE -ne 0 -or $status -ne '200') { throw "Public endpoint health request failed (HTTP $status)." }
Write-Output "Public health HTTP status: $status"
