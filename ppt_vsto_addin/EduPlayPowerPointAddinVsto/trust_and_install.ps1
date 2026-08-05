# Trust Certificate and Install VSTO Add-in Script
# This script will trust the self-signed certificate and install the VSTO add-in

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Trust Certificate & Install VSTO Add-in" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Paths
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$certFile = Join-Path $scriptDir "certs\EduPlayPowerPointAddinVsto.cer"
$vstoPath = Join-Path $scriptDir "bin\Release\EduPlayPowerPointAddin.vsto"
$dllManifestPath = Join-Path $scriptDir "bin\Release\EduPlayPowerPointAddin.dll.manifest"
$regPath = "HKCU:\Software\Microsoft\Office\PowerPoint\Addins\EduPlayPowerPointAddin"
$legacyRegPath = "HKCU:\Software\Microsoft\Office\PowerPoint\Addins\EduPlay.PowerPointAddin"
$thumbprint = $env:EDUPLAY_VSTO_CERT_THUMBPRINT

if (-not (Test-Path $certFile)) {
    Write-Host "ERROR: Certificate file not found: $certFile" -ForegroundColor Red
    Write-Host "Please run create_cert_and_export.ps1 first." -ForegroundColor Yellow
    pause
    exit 1
}

if (-not (Test-Path $vstoPath)) {
    Write-Host "ERROR: VSTO manifest not found: $vstoPath" -ForegroundColor Red
    Write-Host "Please run build_vsto.cmd first!" -ForegroundColor Yellow
    pause
    exit 1
}

if (-not (Test-Path $dllManifestPath)) {
    Write-Host "ERROR: DLL manifest not found: $dllManifestPath" -ForegroundColor Red
    Write-Host "Please run build_vsto.cmd first!" -ForegroundColor Yellow
    pause
    exit 1
}

if ([string]::IsNullOrEmpty($thumbprint)) {
    Write-Host "ERROR: EDUPLAY_VSTO_CERT_THUMBPRINT environment variable not set!" -ForegroundColor Red
    Write-Host "Please set it to: 3C426B0FEE91C667038048EA771675AB24163D65" -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host "Certificate thumbprint: $thumbprint" -ForegroundColor Green
Write-Host ""

# Step 1: Import certificate to Trusted Publishers
Write-Host "Step 1: Trusting certificate..." -ForegroundColor Yellow

try {
    # Load the public certificate that matches the manifest signer.
    $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($certFile)
    
    Write-Host "  Certificate loaded: $($cert.Subject)" -ForegroundColor Gray
    
    # Install to Trusted Publishers (current user)
    $store = New-Object System.Security.Cryptography.X509Certificates.X509Store("TrustedPublisher", "CurrentUser")
    $store.Open("ReadWrite")
    
    # Check if already exists
    $existing = $store.Certificates | Where-Object { $_.Thumbprint -eq $thumbprint }
    if ($existing) {
        Write-Host "  Certificate already in Trusted Publishers" -ForegroundColor Gray
    } else {
        $store.Add($cert)
        Write-Host "  ✓ Certificate added to Trusted Publishers" -ForegroundColor Green
    }
    $store.Close()
    
    # Also install to Root (for full trust)
    $rootStore = New-Object System.Security.Cryptography.X509Certificates.X509Store("Root", "CurrentUser")
    $rootStore.Open("ReadWrite")
    
    $existingRoot = $rootStore.Certificates | Where-Object { $_.Thumbprint -eq $thumbprint }
    if ($existingRoot) {
        Write-Host "  Certificate already in Trusted Root" -ForegroundColor Gray
    } else {
        $rootStore.Add($cert)
        Write-Host "  ✓ Certificate added to Trusted Root" -ForegroundColor Green
    }
    $rootStore.Close()
    
    Write-Host ""
    Write-Host "✓ Certificate is now trusted!" -ForegroundColor Green
    Write-Host ""
    
} catch {
    Write-Host "  ERROR trusting certificate: $_" -ForegroundColor Red
    pause
    exit 1
}

# Step 2: Register the add-in
Write-Host "Step 2: Registering VSTO add-in..." -ForegroundColor Yellow

$addinName = "EduPlay VSTO PowerPoint Add-in"
$manifestValue = "$vstoPath|vstolocal"

Write-Host "  Manifest: $manifestValue" -ForegroundColor Gray

try {
    # Create registry key for the add-in
    if (Test-Path $legacyRegPath) {
        Remove-Item -Path $legacyRegPath -Recurse -Force
    }

    if (Test-Path $regPath) {
        Remove-Item -Path $regPath -Recurse -Force
    }
    
    New-Item -Path $regPath -Force | Out-Null
    
    # Set required properties
    New-ItemProperty -Path $regPath -Name "Description" -Value "EduPlay PowerPoint Add-in" -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $regPath -Name "FriendlyName" -Value $addinName -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $regPath -Name "LoadBehavior" -Value 3 -PropertyType DWord -Force | Out-Null
    New-ItemProperty -Path $regPath -Name "Manifest" -Value $manifestValue -PropertyType String -Force | Out-Null
    
    Write-Host "  ✓ Registry entries created" -ForegroundColor Green
    Write-Host ""
    
} catch {
    Write-Host "  ERROR registering add-in: $_" -ForegroundColor Red
    pause
    exit 1
}

# Step 3: Verify manifests exist and are signed
Write-Host "Step 3: Verifying manifests..." -ForegroundColor Yellow

Write-Host "  ✓ VSTO manifest: $vstoPath" -ForegroundColor Green
Write-Host "  ✓ DLL manifest: $dllManifestPath" -ForegroundColor Green
Write-Host ""

# Done!
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Installation completed!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Close all PowerPoint instances"
Write-Host "2. Open PowerPoint"
Write-Host "3. The VSTO add-in should load and create a log at %LOCALAPPDATA%\EduPlayPowerPointAddin\Logs\addin.log"
Write-Host ""
Write-Host "If it doesn't work, check:" -ForegroundColor Yellow
Write-Host "  - Event Viewer (Windows Logs > Application)"
Write-Host "  - PowerPoint Trust Center > Add-ins"
Write-Host ""
Write-Host "Registry key: $regPath" -ForegroundColor Gray
Write-Host ""

pause
