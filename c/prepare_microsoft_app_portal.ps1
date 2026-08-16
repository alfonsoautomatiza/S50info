# Prepares the built s50info distribution for manual upload to Microsoft Partner Center.
# Run from Windows PowerShell, not from WSL.

[CmdletBinding()]
param(
    [string]$DistPath = "D:\c\s50info\dist\s50info",
    [string]$ProductJsonPath = "D:\c\s50info\c\product.json",
    [string]$OutputDir = "D:\c\s50info\c\RELEASE\microsoft-portal",
    [string]$PortalUrl = "https://partner.microsoft.com/dashboard/apps-and-games/overview",
    [switch]$NoOpenPortal
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Fail-WithReason {
    param([string]$Message)
    Write-Host "ERROR: $Message" -ForegroundColor Red
    exit 1
}

Write-Step "Checking distribution folder"
if (-not (Test-Path -LiteralPath $DistPath -PathType Container)) {
    Fail-WithReason "Distribution folder not found: $DistPath. Run the build first and verify the path."
}

$exePath = Join-Path $DistPath "s50info.exe"
if (-not (Test-Path -LiteralPath $exePath -PathType Leaf)) {
    Fail-WithReason "s50info.exe not found inside $DistPath. The portal package would be incomplete."
}

Write-Step "Reading product metadata"
if (-not (Test-Path -LiteralPath $ProductJsonPath -PathType Leaf)) {
    Fail-WithReason "Product metadata not found: $ProductJsonPath"
}

$product = Get-Content -LiteralPath $ProductJsonPath -Raw | ConvertFrom-Json
$projectId = if ($product.project_id) { [string]$product.project_id } else { "s50info" }
$version = if ($product.version) { [string]$product.version } else { "0.0.0" }

if ($version -notmatch '^\d+\.\d+\.\d+$') {
    Fail-WithReason "Invalid version '$version'. Microsoft/release packaging expects strict X.Y.Z."
}

Write-Step "Creating portal package folder"
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$packageName = "$projectId-$version-microsoft-portal.zip"
$packagePath = Join-Path $OutputDir $packageName

if (Test-Path -LiteralPath $packagePath -PathType Leaf) {
    Remove-Item -LiteralPath $packagePath -Force
}

Write-Step "Compressing $DistPath"
Compress-Archive -Path (Join-Path $DistPath "*") -DestinationPath $packagePath -CompressionLevel Optimal

if (-not (Test-Path -LiteralPath $packagePath -PathType Leaf)) {
    Fail-WithReason "Package was not created: $packagePath"
}

$packageInfo = Get-Item -LiteralPath $packagePath
Write-Host "Package ready: $packagePath" -ForegroundColor Green
Write-Host ("Size: {0:N2} MB" -f ($packageInfo.Length / 1MB))

Write-Step "Opening output folder"
Invoke-Item -LiteralPath $OutputDir

if (-not $NoOpenPortal) {
    Write-Step "Opening Microsoft Partner Center"
    Start-Process $PortalUrl
}

Write-Host "Done. Upload the ZIP package in Partner Center using your Microsoft account." -ForegroundColor Green
