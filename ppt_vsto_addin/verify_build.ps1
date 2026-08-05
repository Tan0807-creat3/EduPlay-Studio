# Verify VSTO Build
Write-Host "========================================"
Write-Host "  VSTO Build Verification"
Write-Host "========================================`n"

$binDir = "C:\Users\pc\Desktop\laptrinh\eduplay\v1.0.0-real\ppt_vsto_addin\EduPlayPowerPointAddinVsto\bin\Release"
$msi = "C:\Users\pc\Desktop\laptrinh\eduplay\v1.0.0-real\eduplay_studio\eduplay\resources\vsto_addin\EduPlayPowerPointAddin.msi"
$allGood = $true

Write-Host "[1] Checking DLL..."
if (Test-Path "$binDir\EduPlayPowerPointAddin.dll") {
    Write-Host "  OK DLL exists" -Fore Green
} else {
    Write-Host "  ERROR DLL not found" -Fore Red
    $allGood = $false
}

Write-Host "[2] Checking Application Manifest..."
if (Test-Path "$binDir\EduPlayPowerPointAddin.dll.manifest") {
    Write-Host "  OK manifest exists" -Fore Green
} else {
    Write-Host "  ERROR manifest not found" -Fore Red
    $allGood = $false
}

Write-Host "[3] Checking Deployment Manifest..."
if (Test-Path "$binDir\EduPlayPowerPointAddin.vsto") {
    Write-Host "  OK vsto exists" -Fore Green
} else {
    Write-Host "  ERROR vsto not found" -Fore Red
    $allGood = $false
}

Write-Host "[4] Checking MSI..."
if (Test-Path $msi) {
    $msiInfo = Get-Item $msi
    Write-Host "  OK MSI exists: $([math]::Round($msiInfo.Length/1MB, 2)) MB" -Fore Green
} else {
    Write-Host "  ERROR MSI not found" -Fore Red
    $allGood = $false
}

Write-Host "`n========================================"
if ($allGood) {
    Write-Host "  ALL CHECKS PASSED" -Fore Green
    Write-Host "========================================`n"
    Write-Host "MSI ready for deployment!" -Fore Cyan
    Write-Host "Location: $msi`n"
} else {
    Write-Host "  SOME CHECKS FAILED" -Fore Red
    Write-Host "========================================`n"
}
