## Manifest signing (VSTO)

Project này sẽ tự bật `SignManifests=true` nếu có certificate trong Windows Certificate Store và bạn set thumbprint qua env var:

`EDUPLAY_VSTO_CERT_THUMBPRINT`

### 1) Dùng certificate thật (khuyến nghị cho production)

- Import code-signing certificate vào `CurrentUser\My`
- Set env var `EDUPLAY_VSTO_CERT_THUMBPRINT` = thumbprint của cert đó
- Build: `msbuild EduPlayPowerPointAddinVsto.sln /p:Configuration=Release`

### 2) Dùng self-signed (chỉ phù hợp nội bộ/dev)

- Tạo code-signing cert ở `CurrentUser\My`
- Set env var `EDUPLAY_VSTO_CERT_THUMBPRINT`
- Khi đóng gói MSI, nên kèm file public cert để installer tự import cho user:
  - `EduPlayPowerPointAddinVsto/certs/EduPlayPowerPointAddinVsto.cer`
