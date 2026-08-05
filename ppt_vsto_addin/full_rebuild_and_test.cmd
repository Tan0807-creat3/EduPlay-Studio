@echo off
echo ============================================
echo FULL REBUILD AND TEST - EduPlay VSTO Add-in
echo ============================================
echo.

set "ROOT=C:\Users\pc\Desktop\laptrinh\eduplay\v1.0.0-real"

echo [1/7] Closing PowerPoint...
taskkill /F /IM POWERPNT.EXE >nul 2>&1
timeout /t 2 /nobreak >nul

echo [2/7] Clearing cache...
taskkill /F /IM dfsvc.exe >nul 2>&1
rundll32 dfshim.dll,CleanOnlineAppCache >nul 2>&1
rmdir /s /q "%LOCALAPPDATA%\Apps\2.0" >nul 2>&1
rmdir /s /q "%LOCALAPPDATA%\EduPlayPowerPointAddin" >nul 2>&1

echo [3/7] Building and signing DLL...
cd "%ROOT%\ppt_vsto_addin"
call build_and_sign.cmd

echo [4/7] Building MSI...
cd "%ROOT%"
call build_ppt_vsto_addin_msi.cmd

echo [5/7] Uninstalling old version...
wmic product where "name like '%%EduPlay%%PowerPoint%%'" call uninstall /nointeractive >nul 2>&1
timeout /t 2 /nobreak >nul

echo [6/7] Installing new MSI...
msiexec /i "%ROOT%\eduplay_studio\eduplay\resources\vsto_addin\EduPlayPowerPointAddin.msi" /qn /l*v "%TEMP%\eduplay_msi_install.log"
if errorlevel 1 (
    echo ERROR: MSI installation failed!
    echo Check log: %TEMP%\eduplay_msi_install.log
    pause
    exit /b 1
)
timeout /t 3 /nobreak >nul

echo [7/7] Starting PowerPoint...
start "" "C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE"

echo.
echo ============================================
echo Installation complete!
echo ============================================
echo.
echo Check the EduPlay tab in the ribbon and the startup log file if needed.
echo If not, check:
echo   1. Event Viewer: Windows Logs ^> Application
echo   2. MSI log: %TEMP%\eduplay_msi_install.log
echo   3. Add-in log: %LOCALAPPDATA%\EduPlayPowerPointAddin\Logs\addin.log
echo   4. Registry: HKCU\Software\Microsoft\Office\PowerPoint\Addins
echo.
pause
