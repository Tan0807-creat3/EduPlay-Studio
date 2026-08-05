# Uninstall VSTO Add-in Script

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Uninstalling VSTO Add-in" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Remove registry entries
$regPath = "HKCU:\Software\Microsoft\Office\PowerPoint\Addins\EduPlayPowerPointAddin"

if (Test-Path $regPath) {
    Remove-Item -Path $regPath -Recurse -Force
    Write-Host "✓ Registry entries removed" -ForegroundColor Green
} else {
    Write-Host "  (Registry entries not found)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Uninstallation completed!" -ForegroundColor Green
Write-Host "Please close all PowerPoint instances." -ForegroundColor Yellow
Write-Host ""

pause
