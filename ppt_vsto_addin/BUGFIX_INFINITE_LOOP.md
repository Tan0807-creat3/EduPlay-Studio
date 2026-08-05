# BUG FIX: Infinite Loop & File Reading Issues

## Vấn đề (Problems)

### 1. Vòng lặp vô hạn (Infinite Loop)
Add-in PowerPoint VSTO bị **vòng lặp vô hạn** khiến PowerPoint "Not Responding" và crash.

### 2. Lỗi đọc file (File Reading Error)
SEHException khi đọc nhiều file từ folder HTML (app chỉ export 1 file HTML duy nhất).

## Nguyên nhân (Root Causes)

### Vòng lặp vô hạn:
1. **Timer Refresh quá nhanh (350ms)** - gọi refresh liên tục
2. **Logic kiểm tra `needsRebuild` có lỗi** - trigger rebuild không cần thiết
3. **Không có Exception Handling** - crash PowerPoint khi có lỗi
4. **Không có Rate Limiting** - event WindowSelectionChange fire hàng chục lần/giây

### Lỗi đọc file:
1. **Đọc toàn bộ folder thay vì 1 file** - app chỉ export self-contained HTML
2. **Không có retry logic** - file bị lock bởi process khác
3. **Đọc file trong vòng lặp LINQ** - SEHException khi file đang được access

## Giải pháp (Solutions)

### ✅ 1. Tăng timer interval: 350ms → 1000ms
```csharp
private const int RefreshIntervalMs = 1000;
```

### ✅ 2. Thêm Debouncing Mechanism
```csharp
private bool _isRefreshing;
private DateTime _lastRefreshTime = DateTime.MinValue;
private const int MinRefreshIntervalMs = 500;
```

### ✅ 3. Sửa logic SequenceEqual
```csharp
// SAI:  == false
// ĐÚNG: !_items.Select(...).SequenceEqual(...)
```

### ✅ 4. Thêm Try-Catch cho tất cả event handlers
Tất cả handlers đều có exception handling và logging.

### ✅ 5. Đọc chỉ 1 file HTML với retry logic
```csharp
private static HtmlBundle CreateBundleFromHtmlPath(string htmlPath)
{
    // Chỉ đọc 1 file HTML duy nhất (self-contained)
    for (int retry = 0; retry < 3; retry++)
    {
        try
        {
            htmlBytes = File.ReadAllBytes(htmlPath);
            break;
        }
        catch (IOException ex) when (retry < 2)
        {
            Thread.Sleep(100);
        }
    }
}
```

## Kết quả (Results)
- ✅ Không còn vòng lặp vô hạn
- ✅ Timer chạy chậm hơn, ít tốn CPU
- ✅ Có debouncing ngăn refresh liên tục
- ✅ Exception được catch và log
- ✅ Đọc file đúng cách (1 file, có retry)
- ✅ Performance tốt hơn nhiều

## Cách cài đặt (Installation)

### Bước 1: Gỡ cài đặt phiên bản cũ
```cmd
Control Panel → Programs → Uninstall EduPlay PowerPoint Add-in
```

### Bước 2: Cài đặt phiên bản mới
```cmd
eduplay_studio\eduplay\resources\vsto_addin\EduPlayPowerPointAddin.msi
```

### Bước 3: Khởi động lại PowerPoint

## Cách kiểm tra (How to Test)
1. Mở PowerPoint
2. Import file HTML từ EduPlay Studio
3. Kiểm tra log: `%LocalAppData%\EduPlayPowerPointAddin\Logs\addin.log`
4. Di chuyển chuột, thay đổi slide → Không còn freeze

## MSI Location
```
eduplay_studio\eduplay\resources\vsto_addin\EduPlayPowerPointAddin.msi
```

## Log Location
```
%LocalAppData%\EduPlayPowerPointAddin\Logs\addin.log
```

---
**Fixed Date:** June 9, 2026  
**Version:** 1.0.10.0  
**Build:** Release

