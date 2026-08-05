## Dong goi / publish VSTO (MSI)

### Yeu cau

- Visual Studio 2022 (workload Office/SharePoint development) de co VSTO assemblies va MSBuild.
- PowerPoint dung kien truc nao (x86/x64) thi MSI se tu chon arch theo registry.
- Internet (de tai Microsoft Edge WebView2 Runtime bootstrapper trong luc build MSI).

### Build + ky manifest

- Chay:
  - `ppt_vsto_addin\\build_and_sign.cmd`

Script se build Release, generate manifest, ky manifest.

### Tao MSI de cai tren may khac

- Chay:
  - `build_ppt_vsto_addin_msi.cmd`

Output:
- `eduplay_studio\\eduplay\\resources\\vsto_addin\\EduPlayPowerPointAddin.msi`

MSI se:
- Copy add-in vao `%LocalAppData%\\EduPlayPowerPointAddin`
- Dang ky add-in vao registry (HKCU)
- Import cert vao `TrustedPublisher` va `Root` cua current user
- Chay WebView2 bootstrapper `/silent /install` sau khi cai (async), de dam bao may nguoi dung co WebView2 Runtime

