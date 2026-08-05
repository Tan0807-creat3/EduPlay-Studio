@echo off
setlocal EnableExtensions
set "AUTO_PAUSE="
echo %CMDCMDLINE% | find /i "/c" >nul && set "AUTO_PAUSE=1"

echo ====================================
echo Building and Signing VSTO Add-in
echo ====================================
echo.

set "ADDIN_DIR=%~dp0EduPlayPowerPointAddinVsto"
set "CSPROJ=%ADDIN_DIR%\EduPlayPowerPointAddinVsto.csproj"
set "MSBUILD="
set "PFX_FILE=%ADDIN_DIR%\certs\EduPlayPowerPointAddinVsto.pfx"
set "PFX_PASSWORD=test123"
set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
if exist "%VSWHERE%" (
  for /f "usebackq delims=" %%i in (`"%VSWHERE%" -latest -products * -requires Microsoft.Component.MSBuild -find MSBuild\**\Bin\MSBuild.exe`) do (
    set "MSBUILD=%%i"
    goto :msbuild_found
  )
)
for /f "usebackq delims=" %%i in (`where msbuild 2^>nul`) do (
  set "MSBUILD=%%i"
  goto :msbuild_found
)
:msbuild_found
if not defined MSBUILD (
  echo Error: MSBuild not found. Install Visual Studio with MSBuild.
  if defined AUTO_PAUSE pause
  exit /b 1
)

if not defined EDUPLAY_VSTO_CERT_THUMBPRINT (
  for /f "usebackq delims=" %%i in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "& { $cert = Get-ChildItem Cert:\CurrentUser\My | Where-Object { $_.FriendlyName -eq 'EduPlay VSTO' -or $_.Subject -eq 'CN=EduPlay' } | Sort-Object NotAfter -Descending | Select-Object -First 1; if ($cert) { Write-Output $cert.Thumbprint } }"`) do (
    set "EDUPLAY_VSTO_CERT_THUMBPRINT=%%i"
  )
)

if not defined EDUPLAY_VSTO_CERT_THUMBPRINT if exist "%PFX_FILE%" (
  echo Importing signing certificate into CurrentUser\My for this build...
  for /f "usebackq delims=" %%i in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "& { $pwd = ConvertTo-SecureString '%PFX_PASSWORD%' -AsPlainText -Force; $cert = Import-PfxCertificate -FilePath '%PFX_FILE%' -CertStoreLocation 'Cert:\CurrentUser\My' -Password $pwd; if ($cert) { Write-Output $cert.Thumbprint } }"`) do (
    set "EDUPLAY_VSTO_CERT_THUMBPRINT=%%i"
  )
)

if defined EDUPLAY_VSTO_CERT_THUMBPRINT (
  echo Using signing certificate thumbprint: %EDUPLAY_VSTO_CERT_THUMBPRINT%
)

echo Step 1: Building DLL...
echo Restoring NuGet packages...
"%MSBUILD%" "%CSPROJ%" /t:Restore /p:Configuration=Release /p:Platform=AnyCPU /p:RuntimeIdentifier=win
if errorlevel 1 (
    echo Restore failed!
    if defined AUTO_PAUSE pause
    exit /b 1
)
echo.
"%MSBUILD%" "%CSPROJ%" /t:Rebuild /p:Configuration=Release /p:Platform=AnyCPU /p:RuntimeIdentifier=win
if errorlevel 1 (
    echo Build failed!
    if defined AUTO_PAUSE pause
    exit /b 1
)
echo ✓ Build successful
echo.

echo Step 2: Generating manifests...
powershell -ExecutionPolicy Bypass -File "%ADDIN_DIR%\generate_manifests.ps1"
if errorlevel 1 (
    echo Manifest generation failed!
    if defined AUTO_PAUSE pause
    exit /b 1
)
echo ✓ Manifests generated
echo.

echo Step 3: Signing manifests...
powershell -ExecutionPolicy Bypass -File "%ADDIN_DIR%\sign_manifests_complete.ps1"
if errorlevel 1 (
    echo Signing failed!
    if defined AUTO_PAUSE pause
    exit /b 1
)
echo ✓ Manifests signed
echo.

echo ====================================
echo Build and Sign Complete!
echo ====================================
echo.
echo Run build_ppt_vsto_addin_msi.cmd to create MSI installer
echo.
if defined AUTO_PAUSE pause
