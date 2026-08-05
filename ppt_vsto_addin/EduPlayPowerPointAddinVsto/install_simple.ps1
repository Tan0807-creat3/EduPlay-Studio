# Simple VSTO Installation Script

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Installing VSTO Add-in" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$manifestPath = Join-Path $scriptDir "bin\Release\EduPlayPowerPointAddin.vsto"
$dllManifestPath = Join-Path $scriptDir "bin\Release\EduPlayPowerPointAddin.dll.manifest"
$regPath = "HKCU:\Software\Microsoft\Office\PowerPoint\Addins\EduPlayPowerPointAddin"
$legacyRegPath = "HKCU:\Software\Microsoft\Office\PowerPoint\Addins\EduPlay.PowerPointAddin"

if (-not (Test-Path $manifestPath)) {
    Write-Host "ERROR: Manifest not found: $manifestPath" -ForegroundColor Red
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

$manifestValue = "$manifestPath|vstolocal"

Write-Host "Manifest: $manifestValue" -ForegroundColor Gray
Write-Host ""

if (Test-Path $legacyRegPath) {
    Remove-Item -Path $legacyRegPath -Recurse -Force
}

if (Test-Path $regPath) {
    Remove-Item -Path $regPath -Recurse -Force
}

New-Item -Path $regPath -Force | Out-Null

Set-ItemProperty -Path $regPath -Name "Description" -Value "EduPlay PowerPoint Add-in"
Set-ItemProperty -Path $regPath -Name "FriendlyName" -Value "EduPlay PowerPoint Add-in"
Set-ItemProperty -Path $regPath -Name "LoadBehavior" -Value 3 -Type DWord
Set-ItemProperty -Path $regPath -Name "Manifest" -Value $manifestValue

Write-Host "Registry entries created" -ForegroundColor Green
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Installation completed!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Close all PowerPoint instances"
Write-Host "2. Open PowerPoint"
Write-Host "3. The VSTO add-in should load"
Write-Host ""
Write-Host "If error occurs, check Event Viewer:" -ForegroundColor Yellow
Write-Host "  Windows Logs > Application > Filter by VSTO" -ForegroundColor Gray
Write-Host ""

pause
