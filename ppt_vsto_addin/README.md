## EduPlay PowerPoint VSTO Add-in

### 1) Mở project
- Mở solution: `ppt_vsto_addin/EduPlayPowerPointAddinVsto.sln`
- Yêu cầu: Visual Studio + workload Office/SharePoint development (VSTO)

### 2) Build
- Build project `EduPlayPowerPointAddinVsto` (Release)

### 3) Xuất MSI (để EduPlay Studio tự cài/repair)
- Tạo MSI theo 1 trong 2 cách:
  - Visual Studio Installer Projects extension (recommended): tạo Setup Project và build ra `EduPlayPowerPointAddin.msi`
  - WiX Toolset: dùng WiX v4 + file `ppt_vsto_addin/installer_wix/EduPlayPowerPointAddin.wxs`
- Đặt DisplayName: `EduPlay PowerPoint Add-in`
- Output cần copy vào app:
  - `eduplay_studio/eduplay/resources/vsto_addin/EduPlayPowerPointAddin.msi`

#### Build MSI bằng WiX (tự động)
- Script sẽ tự cài `wix` .NET tool (WiX v4.x) nếu máy chưa có.
- Chạy ở repo root:
  - `build_ppt_vsto_addin_msi.cmd`
