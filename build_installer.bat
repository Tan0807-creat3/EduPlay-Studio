@echo off
cd /d "%~dp0"

if not exist "installer" mkdir "installer"

set "ISCC="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"

if not defined ISCC (
  echo Inno Setup (ISCC.exe) not found. Please install Inno Setup 6.
  pause
  exit /b 2
)

"%ISCC%" "setup.iss"
pause
