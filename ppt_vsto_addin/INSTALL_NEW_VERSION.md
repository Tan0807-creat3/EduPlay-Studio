# Hướng dẫn Cài đặt EduPlay PowerPoint Add-in v1.0.10

## ⚠️ QUAN TRỌNG: Gỡ phiên bản cũ trước

### Bước 1: Đóng tất cả cửa sổ PowerPoint
- Đảm bảo không có PowerPoint nào đang chạy

### Bước 2: Gỡ cài đặt phiên bản cũ
1. Mở **Control Panel**
2. Chọn **Programs and Features** (hoặc **Programs → Uninstall a program**)
3. Tìm **"EduPlay PowerPoint Add-in"**
4. Click chuột phải → **Uninstall**
5. Đợi gỡ cài đặt hoàn tất

### Bước 3: Xóa file log cũ (tùy chọn)
```
%LocalAppData%\EduPlayPowerPointAddin\Logs\
```
- Xóa folder này nếu muốn bắt đầu với log sạch

---

## 📦 Cài đặt phiên bản mới v1.0.10

### Bước 4: Chạy MSI installer
**Đường dẫn file MSI:**
```
eduplay_studio\eduplay\resources\vsto_addin\EduPlayPowerPointAddin.msi
```

1. Double-click file **EduPlayPowerPointAddin.msi**
2. Làm theo hướng dẫn cài đặt
3. MSI sẽ tự động:
   - Cài đặt WebView2 Runtime (nếu chưa có)
   - Đóng gói đầy đủ DLL dependencies
   - Đăng ký add-in với PowerPoint
   - Cài certificate vào Trusted Publishers

### Bước 5: Khởi động PowerPoint
- Mở PowerPoint
- Tab **"EduPlay"** sẽ xuất hiện ở ribbon
- Click **"Open EduPlay"** để import HTML

---

## ✅ Kiểm tra cài đặt thành công

### 1. Kiểm tra Add-in đã load
- Mở PowerPoint
- File → Options → Add-ins
- Tìm **"EduPlay PowerPoint Add-in"** trong danh sách
- Trạng thái: **Connected**

### 2. Kiểm tra dependencies
Mở folder cài đặt:
```
%LocalAppData%\EduPlayPowerPointAddin\
```

Phải có các file sau:
- ✅ `EduPlayPowerPointAddin.dll`
- ✅ `EduPlayPowerPointAddin.dll.manifest`
- ✅ `EduPlayPowerPointAddin.vsto`
- ✅ `Microsoft.Web.WebView2.Core.dll` ← **QUAN TRỌNG**
- ✅ `Microsoft.Web.WebView2.WinForms.dll` ← **QUAN TRỌNG**
- ✅ `Microsoft.Web.WebView2.Wpf.dll`
- ✅ `runtimes\win-x64\native\WebView2Loader.dll`
- ✅ `runtimes\win-x86\native\WebView2Loader.dll`
- ✅ `runtimes\win-arm64\native\WebView2Loader.dll`

### 3. Test import HTML
1. Mở PowerPoint, tạo slide mới
2. Click tab **EduPlay** → **Open EduPlay**
3. Chọn file HTML từ EduPlay Studio
4. HTML frame sẽ xuất hiện trên slide
5. Nhấn F5 để trình chiếu → HTML hiện lên

### 4. Kiểm tra log
```
%LocalAppData%\EduPlayPowerPointAddin\Logs\addin.log
```

Log phải có:
```
[2026-06-09 HH:MM:SS] Startup completed successfully.
[2026-06-09 HH:MM:SS] Importing HTML from: ...
[2026-06-09 HH:MM:SS] HTML imported successfully. ID: ..., Files: 1
```

**KHÔNG được có lỗi:**
- ❌ `FileNotFoundException: Microsoft.Web.WebView2.WinForms`
- ❌ `SEHException`
- ❌ `RefreshTimer_Tick failed`

---

## 🔧 Các thay đổi trong v1.0.10

### Bug Fixes:
1. ✅ **Sửa vòng lặp vô hạn** - Timer giảm từ 350ms → 1000ms
2. ✅ **Thêm debouncing** - Ngăn refresh liên tục
3. ✅ **Sửa lỗi đọc file** - Chỉ đọc 1 file HTML với retry logic
4. ✅ **Exception handling** - Không còn crash PowerPoint
5. ✅ **MSI đóng gói đầy đủ** - Bao gồm tất cả WebView2 DLLs

### Improvements:
- Timer refresh: 350ms → 1000ms
- Minimum refresh interval: 500ms
- File read retry: 3 lần với 100ms delay
- Better logging với context

---

## ❗ Nếu gặp vấn đề

### Vấn đề 1: Không thấy tab EduPlay
**Giải pháp:**
1. File → Options → Add-ins
2. Chọn **COM Add-ins** ở dropdown dưới cùng
3. Click **Go...**
4. Tìm **EduPlay PowerPoint Add-in**
5. Đảm bảo checkbox được tích ✅

### Vấn đề 2: HTML không hiện lên khi trình chiếu
**Kiểm tra:**
1. Xem log: `%LocalAppData%\EduPlayPowerPointAddin\Logs\addin.log`
2. Nếu có lỗi `FileNotFoundException: Microsoft.Web.WebView2.WinForms`:
   - Add-in thiếu DLL
   - Gỡ cài đặt và cài lại MSI mới v1.0.10

### Vấn đề 3: PowerPoint bị đơ khi import HTML
**Giải pháp:**
- Đảm bảo đã cài đặt v1.0.10 (không phải v1.0.9)
- Kiểm tra log xem có vòng lặp không
- File HTML phải là **self-contained** (tất cả JS/CSS đã inline)

### Vấn đề 4: Lỗi certificate
**Giải pháp:**
1. Mở PowerShell as Administrator
2. Chạy:
```powershell
cd ppt_vsto_addin\EduPlayPowerPointAddinVsto
.\trust_and_install.ps1
```

---

## 📞 Support

Nếu vẫn gặp vấn đề, gửi file log đến:
```
%LocalAppData%\EduPlayPowerPointAddin\Logs\addin.log
```

---

**Version:** 1.0.10.0  
**Build Date:** June 9, 2026  
**MSI Location:** `eduplay_studio\eduplay\resources\vsto_addin\EduPlayPowerPointAddin.msi`
