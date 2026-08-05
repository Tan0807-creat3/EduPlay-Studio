@echo off
setlocal

set MSBUILD="C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe"
set MAGE="C:\Program Files (x86)\Microsoft SDKs\Windows\v10.0A\bin\NETFX 4.8 Tools\mage.exe"
set PROJECT=%~dp0EduPlayPowerPointAddinVsto.csproj
set BIN=%~dp0bin\Release
set PFX=%~dp0certs\EduPlayPowerPointAddinVsto.pfx
set PASSWORD=test123

echo.
echo ============================================
echo Building VSTO Add-in
echo ============================================
echo.

REM Build the project
echo Building project...
%MSBUILD% "%PROJECT%" /p:Configuration=Release /p:Platform=AnyCPU /t:Clean,Build /v:minimal

if errorlevel 1 (
    echo.
    echo *** BUILD FAILED ***
    pause
    exit /b 1
)

echo.
echo ============================================
echo Build completed!
echo ============================================
echo.
echo Output: %BIN%
echo.
echo Next step: Run trust_and_install.ps1
echo.
pause
