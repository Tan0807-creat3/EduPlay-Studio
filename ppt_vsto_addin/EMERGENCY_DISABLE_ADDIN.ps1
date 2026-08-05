# Emergency: Disable EduPlay PowerPoint Add-in
# Run this if PowerPoint won't open after installing the add-in

Write-Host "Disabling EduPlay PowerPoint Add-in..." -ForegroundColor Yellow

$regPath = "HKCU:\Software\Microsoft\Office\PowerPoint\Addins\EduPlayPowerPointAddin"

if (Test-Path $regPath) {
    Set-ItemProperty -Path $regPath -Name "LoadBehavior" -Value 2 -Type DWord
    Write-Host "✓ Add-in disabled (LoadBehavior = 2)" -ForegroundColor Green
    Write-Host ""
    Write-Host "You can now open PowerPoint." -ForegroundColor Cyan
    Write-Host "To re-enable: File → Options → Add-ins → Manage COM Add-ins → Check 'EduPlay'" -ForegroundColor Gray
} else {
    Write-Host "Add-in registry key not found." -ForegroundColor Red
}

Write-Host ""
Write-Host "Press any key to continue..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
