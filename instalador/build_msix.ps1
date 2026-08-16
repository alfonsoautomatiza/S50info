<#
Compatibility wrapper. The MSIX builder now lives in Python at msix/build_msix.py.

Example:
  powershell -ExecutionPolicy Bypass -File instalador/build_msix.ps1 --certificate-path .\cert.pfx --certificate-password "secret"
#>

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..")
$Builder = Join-Path $RepoRoot "msix\build_msix.py"

if (-not (Test-Path -LiteralPath $Builder -PathType Leaf)) {
    throw "Python MSIX builder not found: $Builder"
}

$Python = Get-Command py -ErrorAction SilentlyContinue
if ($Python) {
    & py -3 $Builder @args
}
else {
    & python $Builder @args
}

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
