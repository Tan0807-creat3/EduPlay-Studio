# Hướng dẫn Sửa lỗi và Cài đặt lại

## ⚠️ Vấn đề hiện tại

MSI Installer có vấn đề **ClickOnce deployment lock**, khiến PowerPoint không mở được.

Các lỗi trong Event Viewer:
1. ❌ **Lock timeout exception** - ClickOnce cache bị lock
2. ❌ **Manifest signature invalid** - Hash không khớp
3. ❌ **Missing strong name** - Manifest không có chữ ký

## ✅ Giải pháp: Không dùng MSI, cài thủ công

MSI installer có vấn đề với ClickOnce deployment. Thay vào đó, cài trực tiếp từ build output.

---

## 📋 Các bước cài đặt (Thủ công - Không MSI)

### Bước 1: Cleanup hoàn toàn

Chạy file:
```
ppt_vsto_addin\COMPLETE_CLEANUP.cmd
```

Hoặc chạy từng lệnh:
```cmd
taskkill /F /IM POWERPNT.EXE
rmdir /s /q "%LocalAppData%\EduPlayPowerPointAddin"
rmdir /s /q "%LocalAppData%\Apps\2.0"
reg delete "HKCU\Software\Microsoft\Office\PowerPoint\Addins\EduPlayPowerPointAddin" /f
```

### Bước 2: Cài đặt thủ công bằng PowerShell

Mở PowerShell **as Administrator** và chạy:

```powershell
cd ppt_vsto_addin\EduPlayPowerPointAddinVsto
.\trust_and_install.ps1
```

Script này sẽ:
1. ✅ Trust certificate
2. ✅ Copy files vào `%LocalAppData%\EduPlayPowerPointAddin\`
3. ✅ Đăng ký add-in với PowerPoint
4. ✅ Set LoadBehavior = 3 (auto-load)

### Bước 3: Kiểm tra files đã copy

```
%LocalAppData%\EduPlayPowerPointAddin\
```

Phải có **đầy đủ** các files:
- ✅ EduPlayPowerPointAddin.dll
- ✅ EduPlayPowerPointAddin.dll.manifest
- ✅ EduPlayPowerPointAddin.vsto
- ✅ Microsoft.Office.Tools.Common.v4.0.Utilities.dll
- ✅ Microsoft.Web.WebView2.Core.dll
- ✅ Microsoft.Web.WebView2.WinForms.dll
- ✅ Microsoft.Web.WebView2.Wpf.dll
- ✅ runtimes\win-x64\native\WebView2Loader.dll
- ✅ runtimes\win-x86\native\WebView2Loader.dll
- ✅ runtimes\win-arm64\native\WebView2Loader.dll

### Bước 4: Khởi động PowerPoint

- Mở PowerPoint
- Tab **EduPlay** sẽ xuất hiện
- Nếu không xuất hiện: File → Options → Add-ins → Manage COM Add-ins → Tích ✅ EduPlay

---

## 🔧 Nếu vẫn gặp lỗi

### Lỗi: PowerPoint không mở được

**Giải pháp:**
```powershell
Set-ItemProperty -Path "HKCU:\Software\Microsoft\Office\PowerPoint\Addins\EduPlayPowerPointAddin" -Name "LoadBehavior" -Value 2
```

Sau đó mở PowerPoint, rồi enable lại add-in từ Options.

### Lỗi: "Could not load Microsoft.Web.WebView2.WinForms"

**Nguyên nhân:** Files không được copy đầy đủ

**Giải pháp:**
```powershell
# Copy lại toàn bộ
$source = "ppt_vsto_addin\EduPlayPowerPointAddinVsto\bin\Release"
$dest = "$env:LOCALAPPDATA\EduPlayPowerPointAddin"
Remove-Item $dest -Recurse -Force -ErrorAction SilentlyContinue
Copy-Item $source -Destination $dest -Recurse -Force
```

### Lỗi: "Lock timeout exception"

**Nguyên nhân:** ClickOnce cache bị stuck

**Giải pháp:**
```cmd
rmdir /s /q "%LocalAppData%\Apps\2.0"
```

Sau đó chạy lại `trust_and_install.ps1`

---

## 📝 Script trust_and_install.ps1 làm gì?

```powershell
# 1. Install certificate vào Trusted Root
$cert = Get-PfxCertificate -FilePath "path\to\cert.pfx"
Import-Certificate -FilePath "cert.cer" -CertStoreLocation Cert:\CurrentUser\Root

# 2. Install certificate vào Trusted Publishers
Import-Certificate -FilePath "cert.cer" -CertStoreLocation Cert:\CurrentUser\TrustedPublisher

# 3. Copy files
Copy-Item "bin\Release\*" -Destination "$env:LOCALAPPDATA\EduPlayPowerPointAddin" -Recurse

# 4. Đăng ký add-in
$regPath = "HKCU:\Software\Microsoft\Office\PowerPoint\Addins\EduPlayPowerPointAddin"
New-Item -Path $regPath -Force
Set-ItemProperty -Path $regPath -Name "FriendlyName" -Value "EduPlay PowerPoint Add-in"
Set-ItemProperty -Path $regPath -Name "Description" -Value "EduPlay PowerPoint Add-in"
Set-ItemProperty -Path $regPath -Name "LoadBehavior" -Value 3 -Type DWord
Set-ItemProperty -Path $regPath -Name "Manifest" -Value "$env:LOCALAPPDATA\EduPlayPowerPointAddin\EduPlayPowerPointAddin.vsto|vstolocal"
```

---

## ❌ Tại sao không dùng MSI?

MSI installer sử dụng ClickOnce deployment, gây ra các vấn đề:
1. **Lock timeout** - Cache bị lock, không cài được
2. **Manifest signature errors** - Chữ ký manifest không hợp lệ
3. **Deployment cache conflicts** - Xung đột với installations cũ

**Giải pháp tốt nhất:** Cài thủ công bằng PowerShell script.

---

## ✅ Checklist sau khi cài

- [ ] PowerPoint mở được bình thường
- [ ] Tab EduPlay xuất hiện ở ribbon
- [ ] Click "Open EduPlay" mở được dialog
- [ ] Import HTML thành công
- [ ] HTML frame hiện trên slide
- [ ] Press F5 → HTML hiện khi trình chiếu
- [ ] Log file không có lỗi: `%LocalAppData%\EduPlayPowerPointAddin\Logs\addin.log`

---

**Lưu ý:** Nếu cần gỡ cài đặt, chạy lại `COMPLETE_CLEANUP.cmd`
