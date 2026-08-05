# Bypass VSTO security for development/testing
# WARNING: This reduces security - only use for development/testing!

Write-Host "Configuring VSTO security bypass for development..." -ForegroundColor Yellow
Write-Host "WARNING: This reduces security. Only use for development/testing!" -ForegroundColor Red
Write-Host ""

# Add Inclusion List entry (trust specific manifest path)
$manifestPath = "$env:LOCALAPPDATA\EduPlayPowerPointAddin\EduPlayPowerPointAddin.vsto"

# Trust the location
$regPath = "HKCU:\Software\Microsoft\VSTO\Security\Inclusion\{$(New-Guid)}"
New-Item -Path $regPath -Force | Out-Null
Set-ItemProperty -Path $regPath -Name "Url" -Value $manifestPath -Type String
Set-ItemProperty -Path $regPath -Name "PublicKey" -Value "" -Type String  
Set-ItemProperty -Path $regPath -Name "AllowCache" -Value 1 -Type DWord

Write-Host "Added trust entry for: $manifestPath" -ForegroundColor Green

# Also lower security settings (development only!)
$settingsPath = "HKCU:\Software\Microsoft\VSTO\Security"
if (!(Test-Path $settingsPath)) {
    New-Item -Path $settingsPath -Force | Out-Null
}
#Set-ItemProperty -Path $settingsPath -Name "LoadFromMyComputerZone" -Value 1 -Type DWord

Write-Host ""
Write-Host "Done! VSTO security configured for development." -ForegroundColor Green
Write-Host "Now uninstall the current MSI (if installed) and reinstall." -ForegroundColor Cyan
