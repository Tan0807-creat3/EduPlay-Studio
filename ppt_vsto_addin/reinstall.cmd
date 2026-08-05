@echo off
echo ==========================================
echo Reinstalling EduPlay PowerPoint Add-in
echo ==========================================
echo.

set "MSI=C:\Users\pc\Desktop\laptrinh\eduplay\v1.0.0-real\eduplay_studio\eduplay\resources\vsto_addin\EduPlayPowerPointAddin.msi"

echo [1/5] Closing PowerPoint...
taskkill /F /IM POWERPNT.EXE >nul 2>&1
timeout /t 2 /nobreak >nul
echo Done

echo [2/5] Clearing cache...
taskkill /F /IM dfsvc.exe >nul 2>&1
rundll32 dfshim.dll,CleanOnlineAppCache >nul 2>&1
rmdir /s /q "%LOCALAPPDATA%\Apps\2.0" >nul 2>&1
rmdir /s /q "%LOCALAPPDATA%\EduPlayPowerPointAddin" >nul 2>&1
echo Done

echo [3/5] Uninstalling old version...
wmic product where "name like '%%EduPlay%%PowerPoint%%'" call uninstall /nointeractive >nul 2>&1
echo Done (ignore errors if nothing installed)

echo [4/5] Installing new MSI...
echo MSI: %MSI%
msiexec /i "%MSI%" /qb /l*v "%TEMP%\eduplay_msi_install.log"
if errorlevel 1 (
    echo.
    echo ERROR: Installation failed!
    echo Check log: %TEMP%\eduplay_msi_install.log
    pause
    exit /b 1
)
echo Done

echo [5/5] Starting PowerPoint...
timeout /t 3 /nobreak >nul
start "" "C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE" 2>nul || start powerpnt

echo.
echo ==========================================
echo Installation Complete!
echo ==========================================
echo.
echo Check PowerPoint for EduPlay tab
echo.
echo If add-in still doesn't work:
echo   1. Check Event Viewer (Windows Logs ^> Application)
echo   2. Check MSI log: %TEMP%\eduplay_msi_install.log
echo   3. Verify manifest files in: %LOCALAPPDATA%\EduPlayPowerPointAddin
echo.
pause
