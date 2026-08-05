# Complete script to sign VSTO manifest files
$ErrorActionPreference = "Stop"

$binDir = Join-Path $PSScriptRoot "bin\Release"
$dllManifest = Join-Path $binDir "EduPlayPowerPointAddin.dll.manifest"
$vstoManifest = Join-Path $binDir "EduPlayPowerPointAddin.vsto"
$pfxFile = Join-Path $PSScriptRoot "certs\EduPlayPowerPointAddinVsto.pfx"
$pfxPassword = "test123"
$thumbprint = $env:EDUPLAY_VSTO_CERT_THUMBPRINT
$hashAlgorithm = "sha256RSA"

if (!(Test-Path $dllManifest)) {
    Write-Error "Manifest not found: $dllManifest. Run generate_manifests.ps1 first."
    exit 1
}

if (!(Test-Path $vstoManifest)) {
    Write-Error "Manifest not found: $vstoManifest. Run generate_manifests.ps1 first."
    exit 1
}

function Get-MageSignArgs {
    if (![string]::IsNullOrWhiteSpace($thumbprint)) {
        return @("-CertHash", $thumbprint, "-Algorithm", $hashAlgorithm)
    }

    if (Test-Path $pfxFile) {
        return @("-CertFile", $pfxFile, "-Password", $pfxPassword, "-Algorithm", $hashAlgorithm)
    }

    Write-Error "No signing certificate found. Set EDUPLAY_VSTO_CERT_THUMBPRINT or create certs\\EduPlayPowerPointAddinVsto.pfx by running create_cert_and_export.ps1."
    exit 1
}

# Find mage.exe
$magePath = "C:\Program Files (x86)\Microsoft SDKs\Windows\v10.0A\bin\NETFX 4.8 Tools\mage.exe"
if (!(Test-Path $magePath)) {
    $magePath = (Get-ChildItem -Path "C:\Program Files (x86)" -Recurse -Filter "mage.exe" -ErrorAction SilentlyContinue | Select-Object -First 1).FullName
    if (!$magePath) {
        Write-Error "mage.exe not found. Install Windows SDK or .NET Framework SDK."
        exit 1
    }
}

Write-Host "Found mage.exe: $magePath" -ForegroundColor Green
Write-Host ""

$signArgs = Get-MageSignArgs

# Sign .dll.manifest
Write-Host "Signing $dllManifest..." -ForegroundColor Yellow
& $magePath -Sign $dllManifest @signArgs
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to sign .dll.manifest"
    exit 1
}
Write-Host "OK Signed .dll.manifest successfully" -ForegroundColor Green

# Update .vsto manifest to reference signed .dll.manifest  
Write-Host ""
Write-Host "Updating $vstoManifest..." -ForegroundColor Yellow
& $magePath -Update $vstoManifest -AppManifest $dllManifest -Algorithm $hashAlgorithm
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to update .vsto manifest"
    exit 1
}
Write-Host "OK Updated .vsto manifest" -ForegroundColor Green

# Sign .vsto manifest
Write-Host ""
Write-Host "Signing $vstoManifest..." -ForegroundColor Yellow
& $magePath -Sign $vstoManifest @signArgs
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to sign .vsto manifest"
    exit 1
}
Write-Host "OK Signed .vsto manifest successfully" -ForegroundColor Green

Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "All manifests signed successfully!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next: Run build_ppt_vsto_addin_msi.cmd to create MSI" -ForegroundColor Yellow
Write-Host ""
