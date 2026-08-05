# Create certificate and export for VSTO signing
$certDir = Join-Path $PSScriptRoot "certs"
New-Item -ItemType Directory -Force -Path $certDir | Out-Null

Write-Host "Creating self-signed certificate..." -ForegroundColor Green

$cert = New-SelfSignedCertificate `
    -Type Custom `
    -Subject "CN=EduPlay" `
    -KeyUsage DigitalSignature `
    -FriendlyName "EduPlay VSTO" `
    -CertStoreLocation "Cert:\CurrentUser\My" `
    -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3") `
    -NotAfter (Get-Date).AddYears(5)

$thumbprint = $cert.Thumbprint

Write-Host "Certificate created with thumbprint: $thumbprint" -ForegroundColor Cyan

# Export .cer file
$cerPath = Join-Path $certDir "EduPlayPowerPointAddinVsto.cer"
Export-Certificate -Cert $cert -FilePath $cerPath -Type CERT | Out-Null
Write-Host "Exported certificate to: $cerPath" -ForegroundColor Green

# Export .pfx file with password
$pfxPath = Join-Path $certDir "EduPlayPowerPointAddinVsto.pfx"
$pwd = ConvertTo-SecureString -String "test123" -Force -AsPlainText
Export-PfxCertificate -Cert $cert -FilePath $pfxPath -Password $pwd | Out-Null
Write-Host "Exported PFX to: $pfxPath" -ForegroundColor Green

# Set environment variable
Write-Host ""
Write-Host "Setting EDUPLAY_VSTO_CERT_THUMBPRINT environment variable..." -ForegroundColor Yellow
[System.Environment]::SetEnvironmentVariable("EDUPLAY_VSTO_CERT_THUMBPRINT", $thumbprint, "User")

Write-Host ""
Write-Host "Done! Certificate thumbprint: $thumbprint" -ForegroundColor Green
Write-Host ""
Write-Host "IMPORTANT: Close and reopen your terminal/PowerShell to load the new environment variable!" -ForegroundColor Red
Write-Host ""
