# PowerPoint VSTO Add-in - Deployment Guide

## ✅ BUILD COMPLETED SUCCESSFULLY

File MSI đã được tạo thành công với manifest đã ký đúng cách!

**MSI Location:**
```
C:\Users\pc\Desktop\laptrinh\eduplay\v1.0.0-real\eduplay_studio\eduplay\resources\vsto_addin\EduPlayPowerPointAddin.msi
```

## 📋 NEXT STEPS: Testing on Local Machine

### Step 1: Uninstall Old Version (if installed)

1. Mở **Control Panel** → **Programs and Features**
2. Tìm "EduPlay PowerPoint Add-in" 
3. Click **Uninstall**
4. Hoặc chạy lệnh:
```powershell
wmic product where "name like '%EduPlay%'" call uninstall
```

### Step 2: Clear VSTO Cache

```cmd
rmdir /s /q "%LOCALAPPDATA%\EduPlayPowerPointAddin"
taskkill /F /IM POWERPNT.EXE 2>nul
```

### Step 3: Install New MSI

Double-click file MSI hoặc chạy:
```cmd
msiexec /i "C:\Users\pc\Desktop\laptrinh\eduplay\v1.0.0-real\eduplay_studio\eduplay\resources\vsto_addin\EduPlayPowerPointAddin.msi" /qb
```

### Step 4: Test in PowerPoint

1. Mở PowerPoint
2. Kiểm tra tab "EduPlay" xuất hiện trong ribbon
3. Test các chức năng của add-in

## 🔒 Certificate Information

- **Self-signed Certificate**: `EduPlayPowerPointAddinVsto`
- **Thumbprint**: `3C426B0FEE91C667048EA771675AB24163D65`
- **Location**: `CurrentUser\My` certificate store
- **Files**:
  - Public cert: `ppt_vsto_addin\EduPlayPowerPointAddinVsto\certs\EduPlayPowerPointAddinVsto.cer`
  - Private key: `ppt_vsto_addin\EduPlayPowerPointAddinVsto\certs\EduPlayPowerPointAddinVsto.pfx` (password: test123)

## 📦 Deployment to Other Machines

### Option 1: MSI Only (Recommended for end users)

1. Copy MSI file sang máy khác
2. Install MSI bằng cách double-click
3. Nếu gặp security warning, user cần:
   - Click "Install" để tiếp tục
   - Hoặc import certificate vào Trusted Publishers (xem Option 2)

### Option 2: MSI + Certificate (Recommended for enterprise)

1. Copy 2 files:
   - `EduPlayPowerPointAddin.msi`
   - `EduPlayPowerPointAddinVsto.cer`

2. Trên máy đích, import certificate vào Trusted Publishers:
```powershell
Import-Certificate -FilePath "EduPlayPowerPointAddinVsto.cer" -CertStoreLocation Cert:\LocalMachine\TrustedPublisher
Import-Certificate -FilePath "EduPlayPowerPointAddinVsto.cer" -CertStoreLocation Cert:\LocalMachine\Root
```

3. Install MSI:
```cmd
msiexec /i EduPlayPowerPointAddin.msi /qb
```

### Option 3: Group Policy Deployment (Enterprise only)

Sử dụng Group Policy để deploy MSI và certificate tự động cho nhiều máy trong domain.

## 🔧 Troubleshooting

### Error: "The manifest is missing required hashes"

✅ **FIXED** - Manifests đã được generate với SHA256 hashes và ký đúng cách

### Error: "Customized functionality will not work because the deployment manifest does not have a strong name"

✅ **FIXED** - Manifests đã được ký với mage.exe using certificate

### Add-in không xuất hiện trong PowerPoint

1. Kiểm tra registry:
```powershell
Get-ItemProperty "HKCU:\Software\Microsoft\Office\PowerPoint\Addins\EduPlay.PowerPointAddin"
```

2. Kiểm tra VSTO logs:
```powershell
Get-Content "$env:TEMP\VSTOInstallLog*.txt" | Select-Object -Last 50
```

3. Enable VSTO logging:
```powershell
New-Item -Path "HKCU:\Software\Microsoft\VSTO\LogLevel" -Force
Set-ItemProperty -Path "HKCU:\Software\Microsoft\VSTO" -Name "LogLevel" -Value 0
```

### Reset Toàn Bộ và Cài Lại

```cmd
# Uninstall MSI
wmic product where "name like '%EduPlay%'" call uninstall

# Clear all data
rmdir /s /q "%LOCALAPPDATA%\EduPlayPowerPointAddin"
rmdir /s /q "%APPDATA%\Microsoft\PowerPoint"
reg delete "HKCU\Software\Microsoft\Office\PowerPoint\Addins\EduPlay.PowerPointAddin" /f

# Kill PowerPoint
taskkill /F /IM POWERPNT.EXE

# Install lại
msiexec /i EduPlayPowerPointAddin.msi /qb
```

## 🔄 Rebuilding MSI (For Developers)

Để rebuild MSI sau khi thay đổi code:

```cmd
cd "C:\Users\pc\Desktop\laptrinh\eduplay\v1.0.0-real\ppt_vsto_addin"
build_and_sign.cmd
cd ..
build_ppt_vsto_addin_msi.cmd
```

Script `build_and_sign.cmd` sẽ:
1. Build DLL với MSBuild
2. Generate manifest files với proper SHA256 hashes
3. Sign manifest files bằng mage.exe

Script `build_ppt_vsto_addin_msi.cmd` sẽ:
1. Publish VSTO add-in
2. Stage files vào WiX staging directory
3. Build MSI bằng WiX toolset

## 📝 Files Summary

### Build Artifacts
- `bin\Release\EduPlayPowerPointAddin.dll` - Main add-in assembly
- `bin\Release\EduPlayPowerPointAddin.dll.manifest` - Application manifest (signed ✓)
- `bin\Release\EduPlayPowerPointAddin.vsto` - Deployment manifest (signed ✓)
- `bin\Release\Microsoft.Office.Tools.Common.v4.0.Utilities.dll` - VSTO utilities

### Installer
- `eduplay_studio\eduplay\resources\vsto_addin\EduPlayPowerPointAddin.msi` - Final installer

### Certificates
- `certs\EduPlayPowerPointAddinVsto.cer` - Public certificate
- `certs\EduPlayPowerPointAddinVsto.pfx` - Private key (password: test123)

### Scripts
- `build_and_sign.cmd` - Build DLL, generate manifests, sign manifests
- `generate_manifests.ps1` - Generate manifest files with SHA256 hashes
- `sign_manifests_complete.ps1` - Sign manifests using mage.exe
- `create_cert_and_export.ps1` - Create self-signed certificate
- `register_addin.ps1` - Register add-in directly (dev testing)
- `unregister_addin.ps1` - Unregister add-in

## ⚠️ Production Deployment

Để deploy lên production, nên:

1. **Replace self-signed certificate** với code signing certificate từ trusted CA (e.g., DigiCert, Sectigo)
2. **Update certificate** trong build scripts
3. **Re-sign manifests** với production certificate
4. **Rebuild MSI**

Self-signed certificate chỉ nên dùng cho development/testing!

## 🎯 What Was Fixed

1. ✅ Added Office PIA references (Office.Core, PowerPoint Interop)
2. ✅ Fixed ThisAddIn.Designer.cs constructor
3. ✅ Created self-signed certificate with export scripts
4. ✅ Generated manifest files with proper SHA256 hashes
5. ✅ Signed manifests using mage.exe with certificate
6. ✅ Built MSI installer with WiX toolset
7. ✅ All manifests properly signed and verified

## 📞 Support

Nếu gặp vấn đề, kiểm tra:
- VSTO logs: `%TEMP%\VSTOInstallLog*.txt`
- Windows Event Viewer: Application logs
- PowerPoint Trust Center settings
- Antivirus/firewall không block add-in

---

**Build Date**: June 8, 2026, 9:44 PM
**Version**: 1.0.0.0
**Certificate**: EduPlayPowerPointAddinVsto (Self-signed)
