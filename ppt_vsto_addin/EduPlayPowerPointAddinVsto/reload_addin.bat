@echo off
echo Closing PowerPoint...
taskkill /F /IM POWERPNT.EXE 2>nul
timeout /t 2 /nobreak >nul

echo Cleaning add-in cache...
if exist "%LOCALAPPDATA%\EduPlayPowerPointAddin" (
    rmdir /s /q "%LOCALAPPDATA%\EduPlayPowerPointAddin"
    echo Cache cleared.
) else (
    echo No cache found.
)

echo.
echo Done! Now you can open PowerPoint to test the add-in.
echo.
pause
