# EduPlay PowerPoint COM Add-in (x64)

Mục tiêu:
- Tự động có nút **Insert → EduPlay → Import EduPlay** để nhập HTML (single-file) và nhúng vào slide hiện tại.
- Khi trình chiếu, hiển thị game bằng **WebView2 overlay** đúng vị trí placeholder trên slide.
- Dữ liệu HTML được nén (gzip) và lưu trong **CustomXMLParts** của chính file PPTX để mang đi máy khác vẫn chạy.

## Build (developer)

Yêu cầu:
- Windows
- Visual Studio (hoặc MSBuild) có workload .NET Framework
- .NET Framework 4.8 Developer Pack

Build:
- Mở solution: `ppt_com_addin/EduPlayPowerPointAddin.sln`
- Build cấu hình `Release|x64`

Output dự kiến:
- `ppt_com_addin/EduPlayPowerPointAddin/bin/Release/net48/`

## Deploy (installer)

Add-in dạng COM cần 2 phần:
1) COM registration (regasm) cho DLL
2) Registry key để PowerPoint tự load add-in:
   - `HKCU\Software\Microsoft\Office\PowerPoint\Addins\EduPlay.PowerPointAddin.Connect`
     - `LoadBehavior` (DWORD) = `3`
     - `FriendlyName` (string) = `EduPlay`
     - `Description` (string) = `EduPlay PowerPoint Add-in`

Ngoài ra cần WebView2 Runtime (Evergreen) trên máy người dùng.

