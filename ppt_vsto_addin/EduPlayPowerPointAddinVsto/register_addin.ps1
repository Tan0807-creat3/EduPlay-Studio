# PowerShell script to register the VSTO add-in for PowerPoint
# Run as Administrator

$ErrorActionPreference = "Stop"

# Paths
$vstoPath = Join-Path $PSScriptRoot "bin\Release\EduPlayPowerPointAddin.vsto"
$dllManifestPath = Join-Path $PSScriptRoot "bin\Release\EduPlayPowerPointAddin.dll.manifest"
$currentRegPath = "HKCU:\Software\Microsoft\Office\PowerPoint\Addins\EduPlayPowerPointAddin"
$legacyRegPath = "HKCU:\Software\Microsoft\Office\PowerPoint\Addins\EduPlay.PowerPointAddin"

if (!(Test-Path $vstoPath)) {
    Write-Error "VSTO manifest not found: $vstoPath"
    exit 1
}

if (!(Test-Path $dllManifestPath)) {
    Write-Error "Application manifest not found: $dllManifestPath"
    exit 1
}

$manifestValue = "$vstoPath|vstolocal"

Write-Host "Registering add-in..." -ForegroundColor Green

# Remove the legacy key so PowerPoint does not keep a stale registration.
if (Test-Path $legacyRegPath) {
    Remove-Item -Path $legacyRegPath -Recurse -Force
}

# Create registry key
if (!(Test-Path $currentRegPath)) {
    New-Item -Path $currentRegPath -Force | Out-Null
}

# Set registry values
Set-ItemProperty -Path $currentRegPath -Name "Description" -Value "EduPlay PowerPoint Add-in" -Type String
Set-ItemProperty -Path $currentRegPath -Name "FriendlyName" -Value "EduPlay PowerPoint Add-in" -Type String
Set-ItemProperty -Path $currentRegPath -Name "LoadBehavior" -Value 3 -Type DWord
Set-ItemProperty -Path $currentRegPath -Name "Manifest" -Value $manifestValue -Type String

Write-Host "Add-in registered successfully!" -ForegroundColor Green
Write-Host "Registry path: $currentRegPath" -ForegroundColor Yellow
Write-Host "Manifest: $manifestValue" -ForegroundColor Yellow
Write-Host ""
Write-Host "Please restart PowerPoint for changes to take effect." -ForegroundColor Cyan
