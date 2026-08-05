# 🎯 HƯỚNG DẪN CÀI ĐẶT CUỐI CÙNG - v1.0.10

## ⚠️ QUAN TRỌNG: Không dùng MSI!

MSI Installer có lỗi với ClickOnce deployment. Sử dụng script PowerShell thay thế.

---

## 📋 CÁCH CÀI ĐẶT (3 BƯỚC)

### ✅ Bước 1: Cleanup hoàn toàn

**Chuột phải → Run as Administrator** trên file:
```
ppt_vsto_addin\COMPLETE_CLEANUP.cmd
```

Hoặc chạy PowerShell as Admin:
```powershell
Stop-Process -Name POWERPNT -Force -ErrorAction SilentlyContinue
Remove-Item "$env:LOCALAPPDATA\EduPlayPowerPointAddin" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "$env:LOCALAPPDATA\Apps\2.0" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "HKCU:\Software\Microsoft\Office\PowerPoint\Addins\EduPlayPowerPointAddin" -Recurse -Force -ErrorAction SilentlyContinue
```

### ✅ Bước 2: Cài đặt bằng script PowerShell

**Chuột phải → Run as Administrator** trên file:
```
ppt_vsto_addin\SIMPLE_INSTALL_NO_MSI.ps1
```

Script sẽ:
1. Đóng PowerPoint
2. Copy files vào `%LOCALAPPDATA%\EduPlayPowerPointAddin\`
3. Cài certificate
4. Đăng ký add-in
5. Thêm vào resiliency list (chống bị disable)

### ✅ Bước 3: Mở PowerPoint

- Mở PowerPoint
- Tab **"EduPlay"** sẽ xuất hiện
- Click **"Open EduPlay"** để import HTML

---

## 🔍 KIỂM TRA SAU KHI CÀI

### 1. Kiểm tra files đã được copy

Mở folder:
```
%LOCALAPPDATA%\EduPlayPowerPointAddin\
```

Phải có **đầy đủ** các files (11 files):
```
✅ EduPlayPowerPointAddin.dll
✅ EduPlayPowerPointAddin.dll.manifest
✅ EduPlayPowerPointAddin.vsto  
✅ Microsoft.Office.Tools.Common.v4.0.Utilities.dll
✅ Microsoft.Web.WebView2.Core.dll ← QUAN TRỌNG
✅ Microsoft.Web.WebView2.WinForms.dll ← QUAN TRỌNG
✅ Microsoft.Web.WebView2.Wpf.dll ← QUAN TRỌNG
✅ MicrosoftEdgeWebView2Bootstrapper.exe
✅ runtimes\win-x64\native\WebView2Loader.dll
✅ runtimes\win-x86\native\WebView2Loader.dll
✅ runtimes\win-arm64\native\WebView2Loader.dll
```

### 2. Kiểm tra PowerPoint Options

File → Options → Add-ins:
- **"EduPlay PowerPoint Add-in"** phải có trong danh sách
- **Type:** COM Add-in
- **Location:** `%LOCALAPPDATA%\EduPlayPowerPointAddin\...`
- Nếu không tích ✅: Click **"Go..."** (ở Manage COM Add-ins) → Tích ✅ EduPlay

### 3. Kiểm tra log

```
%LOCALAPPDATA%\EduPlayPowerPointAddin\Logs\addin.log
```

Log thành công:
```
[2026-06-09 HH:MM:SS] Startup begin.
[2026-06-09 HH:MM:SS] PowerPoint version: 16.0
[2026-06-09 HH:MM:SS] Startup completed successfully.
```

**KHÔNG được có lỗi:**
```
❌ FileNotFoundException: Microsoft.Web.WebView2.WinForms
❌ Lock timeout exception
❌ Manifest signature invalid
```

---

## 🧪 TEST IMPORT HTML

1. Mở PowerPoint, tạo slide mới
2. Click tab **EduPlay** → **Open EduPlay**
3. Chọn file HTML từ EduPlay Studio
4. HTML frame sẽ xuất hiện trên slide (có viền xanh)
5. Nhấn **F5** để trình chiếu
6. **HTML phải hiện lên khi trình chiếu!**

---

## ❌ NẾU GẶP VẤN ĐỀ

### Vấn đề 1: PowerPoint không mở được

**Nguyên nhân:** Add-in đang crash khi startup

**Giải pháp:**
```powershell
# Disable add-in tạm thời
Set-ItemProperty -Path "HKCU:\Software\Microsoft\Office\PowerPoint\Addins\EduPlayPowerPointAddin" -Name "LoadBehavior" -Value 2
```

Sau đó mở PowerPoint, check log xem lỗi gì.

### Vấn đề 2: Không thấy tab EduPlay

**Nguyên nhân:** Add-in chưa được enable

**Giải pháp:**
- File → Options → Add-ins
- Manage: **COM Add-ins** → Click **Go...**
- Tích ✅ **"EduPlay PowerPoint Add-in"**
- Click OK

### Vấn đề 3: HTML không hiện lên khi trình chiếu

**Nguyên nhân:** Thiếu WebView2 DLLs

**Giải pháp:**
```powershell
# Re-run install script
.\ppt_vsto_addin\SIMPLE_INSTALL_NO_MSI.ps1
```

Kiểm tra lại files trong `%LOCALAPPDATA%\EduPlayPowerPointAddin\`

### Vấn đề 4: Lỗi "FileNotFoundException: Microsoft.Web.WebView2.WinForms"

**Nguyên nhân:** DLLs không được copy

**Giải pháp:**
```powershell
# Manual copy
$source = "ppt_vsto_addin\EduPlayPowerPointAddinVsto\bin\Release"
$dest = "$env:LOCALAPPDATA\EduPlayPowerPointAddin"

Remove-Item $dest -Recurse -Force -ErrorAction SilentlyContinue
Copy-Item $source -Destination $dest -Recurse -Force

# Verify
Get-ChildItem $dest -Recurse | Select-Object FullName
```

### Vấn đề 5: Add-in bị Office disable tự động

**Nguyên nhân:** Office nghĩ add-in đang crash

**Giải pháp:**
```powershell
# Add to resiliency list
$path = "HKCU:\Software\Microsoft\Office\16.0\PowerPoint\Resiliency\DoNotDisableAddinList"
New-Item -Path $path -Force | Out-Null
Set-ItemProperty -Path $path -Name "EduPlayPowerPointAddin" -Value 1 -Type DWord
```

Sau đó enable lại add-in trong Options.

---

## 🗑️ GỠ CÀI ĐẶT

Chạy:
```
ppt_vsto_addin\COMPLETE_CLEANUP.cmd
```

Hoặc PowerShell:
```powershell
Stop-Process -Name POWERPNT -Force -ErrorAction SilentlyContinue
Remove-Item "$env:LOCALAPPDATA\EduPlayPowerPointAddin" -Recurse -Force
Remove-Item "$env:LOCALAPPDATA\Apps\2.0" -Recurse -Force
Remove-Item "HKCU:\Software\Microsoft\Office\PowerPoint\Addins\EduPlayPowerPointAddin" -Recurse -Force
```

---

## 📊 CÁC BUG ĐÃ SỬA TRONG v1.0.10

| Bug | Triệu chứng | Đã sửa |
|-----|-------------|--------|
| Infinite loop | PowerPoint đơ, CPU 100% | ✅ Timer 350ms → 1000ms, debouncing |
| SEHException | Lỗi đọc file HTML | ✅ Đọc 1 file với retry logic |
| Missing WebView2 DLLs | HTML không hiện lên | ✅ Copy đầy đủ DLLs |
| MSI ClickOnce errors | PowerPoint không mở | ✅ Script PowerShell thay MSI |

---

## 📝 TÓM TẮT

✅ **Không dùng MSI** - Dùng script PowerShell  
✅ **Chạy COMPLETE_CLEANUP.cmd trước**  
✅ **Chạy SIMPLE_INSTALL_NO_MSI.ps1** (as Administrator)  
✅ **Mở PowerPoint và test**  

Nếu vẫn gặp vấn đề, kiểm tra log tại:
```
%LOCALAPPDATA%\EduPlayPowerPointAddin\Logs\addin.log
```

---

**Version:** 1.0.10.0  
**Build Date:** June 9, 2026  
**Install Method:** PowerShell Script (No MSI)
