# EduPlay Studio - Professional Installer Features

## 🎯 Overview
This is a professional-grade installer built with Inno Setup, optimized for clean installation, upgrade scenarios, and complete uninstallation.

## ✨ Key Features

### 1. **Smart Version Detection**
- Automatically detects previous installations
- Offers **Clean Install** vs **Upgrade** options
- Clean Install: Removes all data and settings before installing
- Upgrade: Preserves projects, settings, and user data

### 2. **Running Application Management**
- Detects if EduPlay Studio is currently running
- Prompts user to close the application
- Automatically terminates the process if needed
- Prevents installation conflicts

### 3. **File Association (.eduplay)**
- Optional task to register `.eduplay` file extension
- Double-click `.eduplay` files to open in EduPlay Studio
- Custom icon for `.eduplay` files in Windows Explorer
- Registers in both HKLM and HKCU for maximum compatibility

### 4. **PATH Environment Variable**
- Optional task to add EduPlay Studio to system PATH
- Allows running the application from command line
- Automatic cleanup on uninstall

### 5. **Windows Firewall Exception**
- Optional task to add firewall rule
- Allows network connectivity for online features
- Automatic rule removal on uninstall

### 6. **Smart Uninstallation**
- Three-level data deletion options:
  1. **Keep Everything** (default): Only removes application files
  2. **Remove App Data**: Removes settings and cache
  3. **Remove Projects**: Removes all user projects (requires confirmation)
- Separate prompts for app data vs projects
- Complete registry cleanup
- Removes all shortcuts and file associations

### 7. **Modern UI**
- Resizable wizard window (120% size)
- Modern visual style
- Multi-language support (English & Vietnamese)
- Custom messages and prompts
- Progress indicators

### 8. **Ultra Compression**
- LZMA2 ultra64 compression
- Significantly smaller installer size
- Fast decompression during installation
- Solid compression for optimal results

### 9. **Complete Registry Management**
- Application registration in HKLM
- Version tracking
- Uninstall information
- App Paths registration (allows running from Run dialog)
- Clean removal of all registry entries on uninstall

### 10. **User Data Protection**
- Preserves user projects by default
- Separate directories for:
  - Projects: `Documents\EduPlay\Projects`
  - Exports: `Documents\EduPlay\Exports`
  - Cache: `LocalAppData\EduPlay Studio\Cache`
  - Logs: `LocalAppData\EduPlay Studio\Logs`
- Proper permissions set for all directories

## 📋 Installation Options

### During Installation:
- ✅ Create desktop shortcut (checked by default)
- ⬜ Create Quick Launch shortcut
- ⬜ Register .eduplay file association
- ⬜ Add to PATH environment variable
- ⬜ Add Windows Firewall exception

## 🗑️ Uninstallation Behavior

### Default (Safe Uninstall):
- Removes application files only
- **Keeps** user projects
- **Keeps** settings and cache
- User data is safe for reinstallation

### Custom Uninstall:
1. First prompt: Remove app data? (cache, settings)
2. Second prompt: Remove projects? (user files)
3. Always removes: registry entries, shortcuts, file associations

## 🔧 Technical Details

### Requirements:
- Windows 10 version 1809 (build 17763) or later
- 64-bit architecture
- Administrator privileges (can be overridden via command line)

### Installation Locations:
- **Application**: `C:\Program Files\EduPlay Studio\`
- **Projects**: `%USERPROFILE%\Documents\EduPlay\`
- **Settings**: `%LOCALAPPDATA%\EduPlay Studio\`
- **Shared Data**: `%PROGRAMDATA%\EduPlay Studio\`

### Registry Keys:
- `HKLM\Software\EduPlay Studio\EduPlay Studio`
- `HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall\{EDUPLAY-STUDIO-APP-2026}_is1`
- `HKLM\Software\Microsoft\Windows\CurrentVersion\App Paths\EduPlayStudio.exe`
- `HKCR\.eduplay` (if file association enabled)
- `HKCR\EduPlayProject` (if file association enabled)

### Command Line Options:
```bash
# Silent installation
EduPlay-Studio-v1.0.0-Setup.exe /SILENT

# Very silent (no UI)
EduPlay-Studio-v1.0.0-Setup.exe /VERYSILENT

# Specify install directory
EduPlay-Studio-v1.0.0-Setup.exe /DIR="C:\MyApps\EduPlay"

# Silent uninstall
unins000.exe /SILENT

# Force remove all data
unins000.exe /VERYSILENT /FORCEREMOVE

# Create installation log
EduPlay-Studio-v1.0.0-Setup.exe /LOG="install.log"
```

## 🌐 Multi-Language Support

### English (Default)
- Complete UI translation
- Custom messages
- Error messages

### Vietnamese (Tiếng Việt)
- Full Vietnamese translation
- Localized prompts
- Native language support

## 🛡️ Security Features

- Administrator privileges required for system-wide installation
- Can downgrade to user-level install via command line
- Process verification before termination
- Safe file handling
- Registry protection

## 📝 Changelog Tracking

- Version info embedded in installer
- Version comparison for upgrade detection
- Installation date tracking
- Publisher information

## 🎨 Removed/Optimized

### Removed (Not Needed):
- ❌ README.md (users don't open it from installed apps)
- ❌ CHANGELOG.md (users don't need this in program files)
- ❌ LICENSE file (users won't read it post-install)
- ❌ Quick Launch for Windows 8+ (deprecated feature)

### Optimized:
- ✅ Minimal installer size
- ✅ Fast installation
- ✅ Clean uninstallation
- ✅ No bloat files

## 🚀 Best Practices

### For Users:
1. Always choose "Upgrade" when updating unless you want to start fresh
2. Keep projects backed up separately
3. Don't delete projects on uninstall unless you're sure
4. Use default installation directory

### For Developers:
1. Test both clean install and upgrade scenarios
2. Verify all registry keys are cleaned up
3. Check firewall rules after uninstall
4. Test with and without admin privileges
5. Verify PATH cleanup

## 📞 Support

- Website: https://eduplay-game.web.app
- Support: https://eduplay-game.web.app/support
- Email: eduplay.line@hotmail.com
- Reddit: u/Mindless_Town_8994

## 📄 License

Copyright (C) 2026 EduPlay Studio
All rights reserved.

---

**Built with ❤️ using Inno Setup**
