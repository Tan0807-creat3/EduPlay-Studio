# Sign VSTO manifest files using signtool
$ErrorActionPreference = "Stop"

$binDir = Join-Path $PSScriptRoot "bin\Release"
$dllManifest = Join-Path $binDir "EduPlayPowerPointAddin.dll.manifest"
$vstoManifest = Join-Path $binDir "EduPlayPowerPointAddin.vsto"

if (!(Test-Path $dllManifest)) {
    Write-Error "Manifest not found: $dllManifest"
    exit 1
}

if (!(Test-Path $vstoManifest)) {
    Write-Error "Manifest not found: $vstoManifest"
    exit 1
}

# Find signtool.exe
$signtoolPaths = @(
    "C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64\signtool.exe",
    "C:\Program Files (x86)\Windows Kits\10\bin\10.0.22000.0\x64\signtool.exe",
    "C:\Program Files (x86)\Windows Kits\10\bin\10.0.19041.0\x64\signtool.exe",
    "C:\Program Files (x86)\Windows Kits\10\bin\x64\signtool.exe"
)

$signtool = $null
foreach ($path in $signtoolPaths) {
    if (Test-Path $path) {
        $signtool = $path
        break
    }
}

if (!$signtool) {
    # Try to find any version
    $kitRoot = "C:\Program Files (x86)\Windows Kits\10\bin"
    if (Test-Path $kitRoot) {
        $signtool = Get-ChildItem -Path $kitRoot -Recurse -Filter "signtool.exe" -ErrorAction SilentlyContinue | 
                    Where-Object { $_.FullName -like "*\x64\*" } | 
                    Select-Object -First 1 -ExpandProperty FullName
    }
}

if (!$signtool) {
    Write-Error "signtool.exe not found. Install Windows SDK."
    exit 1
}

Write-Host "Found signtool: $signtool" -ForegroundColor Green

# Get thumbprint
$thumbprint = $env:EDUPLAY_VSTO_CERT_THUMBPRINT
if (!$thumbprint) {
    $thumbprint = "3C426B0FEE91C667038048EA771675AB24163D65"
}

Write-Host "Signing manifests with certificate: $thumbprint" -ForegroundColor Cyan

# Sign .dll.manifest
Write-Host "Signing $dllManifest..." -ForegroundColor Yellow
& $signtool sign /sha1 $thumbprint /fd SHA256 /v $dllManifest
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to sign .dll.manifest"
    exit 1
}

# Sign .vsto
Write-Host "Signing $vstoManifest..." -ForegroundColor Yellow
& $signtool sign /sha1 $thumbprint /fd SHA256 /v $vstoManifest
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to sign .vsto"
    exit 1
}

Write-Host ""
Write-Host "Successfully signed both manifests!" -ForegroundColor Green
Write-Host ""
Write-Host "You can now run build_ppt_vsto_addin_msi.cmd to create the MSI installer." -ForegroundColor Cyan
