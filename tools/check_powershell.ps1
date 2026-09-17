$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$count = 0
$problems = @()
Get-ChildItem -LiteralPath (Join-Path $root 'scripts') -Filter '*.ps1' -Recurse | ForEach-Object {
    $tokens = $null
    $parseErrors = $null
    [System.Management.Automation.Language.Parser]::ParseFile($_.FullName, [ref]$tokens, [ref]$parseErrors) | Out-Null
    $count++
    foreach ($problem in $parseErrors) { $problems += ($_.Name + ': ' + $problem.Message) }
}
# Parse every PowerShell snippet in the manual without executing it.
$guide = Get-Content -LiteralPath (Join-Path $root 'docs\manual-guide.md') -Raw -Encoding UTF8
$blocks = [regex]::Matches($guide, '(?s)```powershell\r?\n(.*?)```')
foreach ($block in $blocks) {
    $tokens = $null
    $parseErrors = $null
    [System.Management.Automation.Language.Parser]::ParseInput($block.Groups[1].Value, [ref]$tokens, [ref]$parseErrors) | Out-Null
    foreach ($problem in $parseErrors) { $problems += ('Manual: ' + $problem.Message) }
}
if ($problems.Count -gt 0) { throw ($problems -join "`n") }
Write-Output "PASS: $count PowerShell scripts and $($blocks.Count) manual command blocks parsed."
