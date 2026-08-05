@echo off
echo ========================================
echo COMPLETE CLEANUP - EduPlay PowerPoint Add-in
echo ========================================
echo.

echo Step 1: Killing all PowerPoint processes...
taskkill /F /IM POWERPNT.EXE >nul 2>&1
timeout /t 2 >nul

echo Step 2: Removing add-in installation folder...
rmdir /s /q "%LocalAppData%\EduPlayPowerPointAddin" >nul 2>&1

echo Step 3: Cleaning ClickOnce cache...
rmdir /s /q "%LocalAppData%\Apps\2.0" >nul 2>&1

echo Step 4: Removing registry keys...
reg delete "HKCU\Software\Microsoft\Office\PowerPoint\Addins\EduPlayPowerPointAddin" /f >nul 2>&1

echo Step 5: Cleaning temp files...
del /q "%TEMP%\EduPlay*" >nul 2>&1
rmdir /s /q "%TEMP%\EduPlayPowerPointAddin" >nul 2>&1

echo.
echo ========================================
echo Cleanup complete!
echo ========================================
echo.
echo Now you can:
echo 1. Install MSI again
echo 2. Or run PowerPoint without the add-in
echo.
pause
