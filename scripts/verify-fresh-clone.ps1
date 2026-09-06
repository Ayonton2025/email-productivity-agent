[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$runner = Join-Path $PSScriptRoot 'verify.py'
if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3.11 $runner
} else {
    & python3.11 $runner
}
exit $LASTEXITCODE
