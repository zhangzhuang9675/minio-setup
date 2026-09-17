$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$env:TEMP = Join-Path $root 'tmp'
$env:TMP = $env:TEMP
$env:GOTMPDIR = $env:TEMP
$env:GOPATH = Join-Path $PSScriptRoot 'gopath'
$env:GOMODCACHE = Join-Path $PSScriptRoot 'modcache'
$env:GOCACHE = Join-Path $PSScriptRoot 'gocache'
$env:GOBIN = Join-Path $root 'bin'
$env:GOENV = 'off'
$env:GOTOOLCHAIN = 'go1.24.8'
$env:GOPROXY = 'https://goproxy.cn'
$env:CGO_ENABLED = '0'
$env:GOMAXPROCS = '4'
$flags = '-s -w -X github.com/minio/minio/cmd.Version=2025-10-15T17:29:55Z -X github.com/minio/minio/cmd.ReleaseTag=RELEASE.2025-10-15T17-29-55Z -X github.com/minio/minio/cmd.CommitID=9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a -X github.com/minio/minio/cmd.ShortCommitID=9e49d5e7a648 -X github.com/minio/minio/cmd.CopyrightYear=2025'
& (Join-Path $root 'tools\go\bin\go.exe') install -p 4 -trimpath -ldflags $flags 'github.com/minio/minio@v0.0.0-20251015172955-9e49d5e7a648'
if ($LASTEXITCODE -ne 0) { throw 'MinIO build failed.' }
& (Join-Path $root 'bin\minio.exe') --version
if ($LASTEXITCODE -ne 0) { throw 'MinIO executable validation failed.' }
