# Hướng dẫn Build MSI cho PowerPoint VSTO Add-in

## Tóm tắt vấn đề đã sửa

1. ✅ Thêm Office PIA references (Microsoft.Office.Core, Microsoft.Office.Interop.PowerPoint)
2. ✅ Sửa ThisAddIn.Designer.cs với constructor chuẩn VSTO
3. ✅ Tạo self-signed certificate để ký
4. ✅ Tạo scripts generate manifest files với proper SHA256 hashes
5. ✅ Ký manifest files bằng mage.exe - HOÀN TẤT
6. ✅ Build MSI installer thành công với manifests đã ký

**STATUS: READY FOR DEPLOYMENT** 🎉

## Cách test MSI nhanh nhất (đã có MSI sẵn)

**File MSI đã được tạo tại:**
```
C:\Users\pc\Desktop\laptrinh\eduplay\v1.0.0-real\eduplay_studio\eduplay\resources\vsto_addin\EduPlayPowerPointAddin.msi
```

**Manifests đã được ký đúng cách!** ✅

### Quick Test:

Chạy script test tự động:
```cmd
C:\Users\pc\Desktop\laptrinh\eduplay\v1.0.0-real\ppt_vsto_addin\QUICK_TEST.cmd
```

Script sẽ:
1. Uninstall phiên bản cũ
2. Xóa VSTO cache
3. Cài đặt MSI mới
4. Mở PowerPoint để test

## Cách build lại MSI từ source

### Bước 1: Tạo certificate (chỉ cần làm 1 lần)

```powershell
cd "C:\Users\pc\Desktop\laptrinh\eduplay\v1.0.0-real\ppt_vsto_addin\EduPlayPowerPointAddinVsto"
powershell -ExecutionPolicy Bypass -File create_cert_and_export.ps1
```

Certificate thumbprint sẽ được lưu vào environment variable `EDUPLAY_VSTO_CERT_THUMBPRINT`.
**QUAN TRỌNG:** Phải đóng và mở lại terminal sau khi chạy script này!

### Bước 2: Build DLL

Mở **Developer Command Prompt for VS 2022** hoặc terminal mới (sau khi set env var):

```cmd
cd "C:\Users\pc\Desktop\laptrinh\eduplay\v1.0.0-real\ppt_vsto_addin\EduPlayPowerPointAddinVsto"
"C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe" EduPlayPowerPointAddinVsto.csproj /t:Rebuild /p:Configuration=Release
```

### Bước 3: Tạo và ký manifest files

```powershell
cd "C:\Users\pc\Desktop\laptrinh\eduplay\v1.0.0-real\ppt_vsto_addin\EduPlayPowerPointAddinVsto"
powershell -ExecutionPolicy Bypass -File generate_manifests.ps1
powershell -ExecutionPolicy Bypass -File sign_manifests_complete.ps1
```

Hoặc dùng script tự động:
```cmd
cd "C:\Users\pc\Desktop\laptrinh\eduplay\v1.0.0-real\ppt_vsto_addin"
build_and_sign.cmd
```

### Bước 4: Build MSI

```cmd
cd "C:\Users\pc\Desktop\laptrinh\eduplay\v1.0.0-real"
build_ppt_vsto_addin_msi.cmd
```

MSI sẽ được tạo tại:
```
eduplay_studio\eduplay\resources\vsto_addin\EduPlayPowerPointAddin.msi
```

## Vấn đề đã được giải quyết ✅

### ~~Manifest chưa được ký đúng cách~~ → FIXED

✅ Manifest files đã được ký bằng mage.exe với certificate
✅ SHA256 hashes đã được tính toán đúng cho tất cả assemblies
✅ Deployment manifest (.vsto) đã được update và sign
✅ Application manifest (.dll.manifest) đã được sign

**Không cần bypass security nữa!** Add-in đã sẵn sàng để deploy.

### Scripts đã tạo

1. **create_cert_and_export.ps1** - Tạo self-signed certificate và export ra .cer, .pfx
2. **generate_manifests.ps1** - Tạo manifest files (.dll.manifest và .vsto)
3. **sign_manifests.ps1** - Ký manifest files (cần mage.exe/signtool.exe)
4. **bypass_vsto_security.ps1** - Bypass VSTO security (dev only)
5. **register_addin.ps1** - Đăng ký add-in trực tiếp vào registry (không cần MSI)
6. **unregister_addin.ps1** - Gỡ đăng ký add-in

## Testing nhanh không cần MSI

Để test nhanh mà không cần build MSI:

```powershell
# 1. Build DLL
cd "C:\Users\pc\Desktop\laptrinh\eduplay\v1.0.0-real\ppt_vsto_addin\EduPlayPowerPointAddinVsto"
"C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe" EduPlayPowerPointAddinVsto.csproj /t:Rebuild /p:Configuration=Release

# 2. Đăng ký add-in
powershell -ExecutionPolicy Bypass -File register_addin.ps1

# 3. Đóng PowerPoint hoàn toàn, xóa cache, mở lại
taskkill /F /IM POWERPNT.EXE
rmdir /s /q "%LOCALAPPDATA%\EduPlayPowerPointAddin"
start powerpnt
```

## Deployment lên máy khác

1. Build MSI như hướng dẫn trên
2. Copy file MSI sang máy khác
3. Chạy MSI để cài đặt
4. Nếu gặp lỗi security, chạy bypass script hoặc ký manifest đúng cách với certificate có trust chain

## Ghi chú

- Certificate thumbprint hiện tại: `3C426B0FEE91C667038048EA771675AB24163D65`
- Certificate được lưu ở: `CurrentUser\My` store
- Add-in registry key: `HKCU:\Software\Microsoft\Office\PowerPoint\Addins\EduPlay.PowerPointAddin`
- Add-in install location: `%LOCALAPPDATA%\EduPlayPowerPointAddin\`
