# PowerShell script to unregister the VSTO add-in from PowerPoint

$regPaths = @(
    "HKCU:\Software\Microsoft\Office\PowerPoint\Addins\EduPlayPowerPointAddin",
    "HKCU:\Software\Microsoft\Office\PowerPoint\Addins\EduPlay.PowerPointAddin"
)

Write-Host "Unregistering add-in..." -ForegroundColor Yellow

if (($regPaths | Where-Object { Test-Path $_ }).Count -gt 0) {
    foreach ($regPath in $regPaths) {
        if (Test-Path $regPath) {
            Remove-Item -Path $regPath -Recurse -Force
            Write-Host "Removed: $regPath" -ForegroundColor Green
        }
    }
    Write-Host "Add-in unregistered successfully!" -ForegroundColor Green
}
else {
    Write-Host "Add-in was not registered." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Please restart PowerPoint for changes to take effect." -ForegroundColor Cyan
