param([string]$Root = 'E:\MinIO')
$ErrorActionPreference = 'Stop'
$directory = Join-Path $Root 'config'
New-Item -ItemType Directory -Path $directory -Force | Out-Null
$name = Read-Host 'MinIO username / AccessKeyId (at least 3 characters)'
if ($name.Length -lt 3) { throw 'Username must contain at least 3 characters.' }
$password = Read-Host 'MinIO password / SecretAccessKey (at least 8 characters)' -AsSecureString
$confirmation = Read-Host 'Confirm password' -AsSecureString
$credential = [PSCredential]::new($name, $password)
$confirmCredential = [PSCredential]::new($name, $confirmation)
if ($credential.GetNetworkCredential().Password.Length -lt 8) { throw 'Password must contain at least 8 characters.' }
if ($credential.GetNetworkCredential().Password -cne $confirmCredential.GetNetworkCredential().Password) { throw 'Passwords do not match.' }
$sid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
& icacls.exe $directory /inheritance:r /grant:r "${sid}:(OI)(CI)F" '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Failed to restrict config permissions.' }
$target = Join-Path $directory 'credentials.xml'
if (Test-Path -LiteralPath $target) {
    Copy-Item -LiteralPath $target -Destination ($target + '.' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '.bak')
}
$credential | Export-Clixml -LiteralPath $target
$credential = $null
$confirmCredential = $null
Write-Output 'Credentials saved with Windows DPAPI. Restart MinIO to apply. Use the same Windows user to start MinIO.'
