@echo off
setlocal EnableExtensions

set "AUTO_PAUSE="
echo %CMDCMDLINE% | find /i "/c" >nul && set "AUTO_PAUSE=1"

set "ROOT=%~dp0"
pushd "%ROOT%"
set "CSPROJ=%ROOT%ppt_vsto_addin\EduPlayPowerPointAddinVsto\EduPlayPowerPointAddinVsto.csproj"
set "MSI_OUTDIR=%ROOT%eduplay_studio\eduplay\resources\vsto_addin"
set "MSI=%MSI_OUTDIR%\EduPlayPowerPointAddin.msi"
set "STAGING=%ROOT%ppt_vsto_addin\installer_wix\staging"
set "WXS=%ROOT%ppt_vsto_addin\installer_wix\EduPlayPowerPointAddin.wxs"
set "WIXEXE=%USERPROFILE%\.dotnet\tools\wix.exe"
set "WIXVER=4.0.6"
set "WIX_ARCH="
set "MSBUILD_EXE="
set "PRODUCT_VERSION="
set "CER=%ROOT%ppt_vsto_addin\EduPlayPowerPointAddinVsto\certs\EduPlayPowerPointAddinVsto.cer"
set "PFX=%ROOT%ppt_vsto_addin\EduPlayPowerPointAddinVsto\certs\EduPlayPowerPointAddinVsto.pfx"
set "BUILDOUT1=%ROOT%ppt_vsto_addin\EduPlayPowerPointAddinVsto\bin\Release"
set "BUILDOUT=%BUILDOUT1%"
set "WV2_BOOTSTRAPPER_URL=https://go.microsoft.com/fwlink/p/?LinkId=2124703"
set "WV2_BOOTSTRAPPER=%STAGING%\MicrosoftEdgeWebView2Bootstrapper.exe"

if not exist "%CSPROJ%" (
  echo Missing csproj: %CSPROJ%
  goto :fail
)

set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
if exist "%VSWHERE%" (
  for /f "usebackq delims=" %%i in (`"%VSWHERE%" -latest -products * -requires Microsoft.Component.MSBuild -find MSBuild\**\Bin\MSBuild.exe`) do (
    set "MSBUILD_EXE=%%i"
    goto :msbuild_found
  )
)
for /f "usebackq delims=" %%i in (`where msbuild 2^>nul`) do (
  set "MSBUILD_EXE=%%i"
  goto :msbuild_found
)
:msbuild_found
if not defined MSBUILD_EXE (
  echo msbuild not found. Install Visual Studio with Office/SharePoint development workload.
  goto :fail
)

if not exist "%PFX%" (
  if not defined EDUPLAY_VSTO_CERT_THUMBPRINT (
    echo Missing signing certificate file: %PFX%
    echo and EDUPLAY_VSTO_CERT_THUMBPRINT is not set.
    echo Run:
    echo   powershell -ExecutionPolicy Bypass -File ppt_vsto_addin\EduPlayPowerPointAddinVsto\create_cert_and_export.ps1
    goto :fail
  )
)

if not exist "%CER%" (
  echo Missing public certificate file: %CER%
  echo Create it from the same signing certificate and save to:
  echo   ppt_vsto_addin\EduPlayPowerPointAddinVsto\certs\EduPlayPowerPointAddinVsto.cer
  goto :fail
)

for /f "usebackq delims=" %%i in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "$proj = [xml](Get-Content -LiteralPath '%CSPROJ%'); $group = $proj.Project.PropertyGroup | Where-Object { $_.ApplicationVersion } | Select-Object -First 1; if (-not $group) { exit 1 }; $parts = $group.ApplicationVersion.Split('.'); if ($parts.Count -lt 3) { exit 1 }; Write-Output ($parts[0..2] -join '.')"`) do (
  set "PRODUCT_VERSION=%%i"
)
if not defined PRODUCT_VERSION (
  echo Failed to resolve MSI product version from: %CSPROJ%
  goto :fail
)

echo Building VSTO add-in and regenerating manifests...
call "%ROOT%ppt_vsto_addin\build_and_sign.cmd"
if errorlevel 1 goto :fail

if exist "%STAGING%" rmdir /s /q "%STAGING%"
mkdir "%STAGING%" >nul 2>nul

echo Staging build output...
xcopy "%BUILDOUT%\*" "%STAGING%\" /e /i /y >nul
if errorlevel 1 goto :fail

copy /y "%CER%" "%STAGING%\EduPlayPowerPointAddinVsto.cer" >nul 2>nul
if errorlevel 1 goto :fail

if not exist "%WV2_BOOTSTRAPPER%" (
  echo Downloading WebView2 bootstrapper...
  curl -L "%WV2_BOOTSTRAPPER_URL%" -o "%WV2_BOOTSTRAPPER%" >nul 2>nul
  if not exist "%WV2_BOOTSTRAPPER%" (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$p='%WV2_BOOTSTRAPPER%'; $u='%WV2_BOOTSTRAPPER_URL%'; [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile($u,$p)" >nul 2>nul
  )
)

if not exist "%WV2_BOOTSTRAPPER%" (
  echo Failed to download WebView2 bootstrapper: %WV2_BOOTSTRAPPER_URL%
  echo Please make sure the machine has internet access, or pre-download the file and place it at:
  echo   %WV2_BOOTSTRAPPER%
  goto :fail
)

if not exist "%STAGING%\EduPlayPowerPointAddin.dll" (
  echo Missing build output: %STAGING%\EduPlayPowerPointAddin.dll
  goto :fail
)
if not exist "%STAGING%\EduPlayPowerPointAddin.dll.manifest" (
  echo Missing build output: %STAGING%\EduPlayPowerPointAddin.dll.manifest
  goto :fail
)
if not exist "%STAGING%\EduPlayPowerPointAddin.vsto" (
  echo Missing build output: %STAGING%\EduPlayPowerPointAddin.vsto
  goto :fail
)

if not exist "%WIXEXE%" (
  echo Installing WiX %WIXVER%...
  dotnet tool install --global wix --version %WIXVER% >nul 2>nul
  if errorlevel 1 (
    dotnet tool uninstall --global wix >nul 2>nul
    dotnet tool install --global wix --version %WIXVER%
  )
)

if not exist "%WIXEXE%" (
  echo WiX tool not found after install. Make sure dotnet global tools are enabled.
  goto :fail
)

echo Ensuring WiX IIS extension...
"%WIXEXE%" extension add -g WixToolset.Iis.wixext/%WIXVER% >nul 2>nul

if defined EDUPLAY_WIX_ARCH (
  set "WIX_ARCH=%EDUPLAY_WIX_ARCH%"
)
if not defined WIX_ARCH (
  for /f "tokens=2,*" %%a in ('reg query "HKLM\SOFTWARE\Microsoft\Office\ClickToRun\Configuration" /v Platform 2^>nul ^| find /i "Platform"') do (
    set "WIX_ARCH=%%b"
  )
)
if /i "%WIX_ARCH%"=="x86" set "WIX_ARCH=x86"
if /i "%WIX_ARCH%"=="x64" set "WIX_ARCH=x64"
if not defined WIX_ARCH set "WIX_ARCH=x64"

mkdir "%MSI_OUTDIR%" >nul 2>nul

echo Building MSI...
"%WIXEXE%" build "%WXS%" -arch %WIX_ARCH% -ext WixToolset.Iis.wixext -d SourceDir="%STAGING%" -d ProductVersion="%PRODUCT_VERSION%" -o "%MSI%"
if errorlevel 1 goto :fail

echo MSI ready: %MSI%
echo MSI product version: %PRODUCT_VERSION%
if defined AUTO_PAUSE pause
popd
exit /b 0

:fail
echo Failed. Fix the error above then re-run.
if defined AUTO_PAUSE pause
popd
exit /b 1
