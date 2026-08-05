@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
set "PIP_NO_CACHE_DIR=1"
set "PIP_DISABLE_PIP_VERSION_CHECK=1"

echo ============================================================
echo  EduPlay Studio - Release Build Script
echo ============================================================
echo.

:: 1. Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+.
    exit /b 1
)

:: 2. Prepare local build venv
set "BUILD_VENV=%CD%\.venv_build"
set "BUILD_PY=%BUILD_VENV%\Scripts\python.exe"
if not exist "%BUILD_PY%" (
    echo [INFO] Creating local build venv...
    python -m venv "%BUILD_VENV%"
    if errorlevel 1 (
        echo [ERROR] Failed to create local venv.
        exit /b 1
    )
)

:: 3. Check / install PyInstaller
"%BUILD_PY%" -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing PyInstaller...
    "%BUILD_PY%" -m pip install --upgrade pip --quiet
    "%BUILD_PY%" -m pip install pyinstaller --quiet
    if errorlevel 1 exit /b 1
)

:: 3b. Check / install PyArmor + cryptography
"%BUILD_PY%" -c "import pyarmor" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing PyArmor...
    "%BUILD_PY%" -m pip install pyarmor --quiet
    if errorlevel 1 exit /b 1
)
"%BUILD_PY%" -c "from cryptography.hazmat.primitives.ciphers.aead import AESGCM" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing cryptography...
    "%BUILD_PY%" -m pip install cryptography --quiet
    if errorlevel 1 exit /b 1
)

:: 3c. Install project runtime dependencies into build venv
if exist "requirements.txt" (
    echo [INFO] Installing project runtime dependencies...
    "%BUILD_PY%" -m pip install -r requirements.txt --quiet
    if errorlevel 1 exit /b 1
)

:: 4. Check UPX
where upx >nul 2>&1
if errorlevel 1 (
    echo [WARN] UPX not found in PATH. Compression will be skipped.
    echo        Download from https://github.com/upx/upx/releases
)

:: 5. Clean previous build
echo [STEP 1] Cleaning previous build...
if exist "eduplay_studio\dist\EduPlayStudio" (
    rmdir /s /q "eduplay_studio\dist\EduPlayStudio"
)
if exist "eduplay_studio\build" (
    rmdir /s /q "eduplay_studio\build"
)
if exist "eduplay_studio\.secure_build" (
    rmdir /s /q "eduplay_studio\.secure_build"
)
echo        Done.

:: 6. Obfuscate source with PyArmor
echo [STEP 2] Obfuscating Python sources with PyArmor...
cd eduplay_studio
set "SECURE_ROOT=%CD%\.secure_build"
set "OBF_ROOT=%SECURE_ROOT%\obf"
set "USE_PYARMOR=1"
mkdir "%SECURE_ROOT%" >nul 2>&1
set "PYARMOR_HOME=%SECURE_ROOT%\.pyarmor_home"
if not defined PYARMOR_PRODUCT set "PYARMOR_PRODUCT=EduPlayStudio"
if defined PYARMOR_REGFILE (
    if exist "%PYARMOR_REGFILE%" (
        "%BUILD_PY%" -m pyarmor.cli --home "%PYARMOR_HOME%" reg -p "%PYARMOR_PRODUCT%" "%PYARMOR_REGFILE%" >nul 2>&1
    )
)
"%BUILD_PY%" -m pyarmor.cli --home "%PYARMOR_HOME%" gen -r --enable-jit --mix-str --assert-call --assert-import -O "%OBF_ROOT%" app.py eduplay 2>&1
if errorlevel 1 (
    echo [WARN] PyArmor obfuscation failed or license is unavailable.
    echo [WARN] Falling back to optimized PyInstaller build without source obfuscation.
    set "USE_PYARMOR=0"
)
if "%USE_PYARMOR%"=="1" (
    echo        Done.
) else (
    echo        Skipped.
)

:: 7. Run PyInstaller
echo [STEP 3] Running PyInstaller (onedir)...
if "%USE_PYARMOR%"=="1" (
    set "EDUPLAY_OBF_ROOT=%OBF_ROOT%"
) else (
    set "EDUPLAY_OBF_ROOT=%CD%"
)
"%BUILD_PY%" -m PyInstaller EduPlayStudio.spec --noconfirm --clean 2>&1
if errorlevel 1 (
    echo [ERROR] PyInstaller failed.
    cd ..
    exit /b 1
)
set "EDUPLAY_OBF_ROOT="
cd ..
echo        Done.

:: 8. Remove junk files from dist
echo [STEP 4] Removing unnecessary files from dist...
set "DIST=eduplay_studio\dist\EduPlayStudio"
set "PAYLOAD_ROOT=%DIST%"
if exist "%DIST%\_internal" set "PAYLOAD_ROOT=%DIST%\_internal"
if exist "%PAYLOAD_ROOT%\eduplay\resources\firebase_hosting" rmdir /s /q "%PAYLOAD_ROOT%\eduplay\resources\firebase_hosting"

:: Remove Python source files (should not be there but just in case)
for /r "%PAYLOAD_ROOT%" %%f in (*.py) do del /q "%%f"

:: Remove test files
for /r "%PAYLOAD_ROOT%" %%f in (test_*.pyc) do del /q "%%f"
if exist "%PAYLOAD_ROOT%\tests" rmdir /s /q "%PAYLOAD_ROOT%\tests"

:: Remove __pycache__ folders
for /d /r "%PAYLOAD_ROOT%" %%d in (__pycache__) do (
    if exist "%%d" rmdir /s /q "%%d"
)

:: Remove .spec, .bat, build artifacts
for /r "%PAYLOAD_ROOT%" %%f in (*.spec *.bat *.cmd *.log *.pdb *.map *.pyi) do del /q "%%f"

:: Remove Tcl/Tk (not used)
if exist "%PAYLOAD_ROOT%\tcl" rmdir /s /q "%PAYLOAD_ROOT%\tcl"
if exist "%PAYLOAD_ROOT%\tk" rmdir /s /q "%PAYLOAD_ROOT%\tk"

:: Remove unused Qt plugins
if exist "%PAYLOAD_ROOT%\PySide6\plugins\sqldrivers" rmdir /s /q "%PAYLOAD_ROOT%\PySide6\plugins\sqldrivers"
if exist "%PAYLOAD_ROOT%\PySide6\plugins\position" rmdir /s /q "%PAYLOAD_ROOT%\PySide6\plugins\position"
if exist "%PAYLOAD_ROOT%\PySide6\plugins\texttospeech" rmdir /s /q "%PAYLOAD_ROOT%\PySide6\plugins\texttospeech"
if exist "%PAYLOAD_ROOT%\PySide6\plugins\geoservices" rmdir /s /q "%PAYLOAD_ROOT%\PySide6\plugins\geoservices"

echo        Done.

:: 9. Encrypt assets with exe-bound AES wrapping (DISABLED for now)
echo [STEP 5] Skipping asset encryption...
rem "%BUILD_PY%" "%~dp0tools\obfuscate_assets.py" "%DIST%" "%DIST%\EduPlayStudio.exe"
rem if errorlevel 1 (
rem     echo [WARN] Asset encryption failed or skipped.
rem ) else (
rem     echo        Done.
rem )
echo        Skipped.

:: 10. Cleanup secure staging
if exist "eduplay_studio\.secure_build" rmdir /s /q "eduplay_studio\.secure_build"

:: 11. Report output size
echo.
echo [DONE] Build complete.
echo Output: %DIST%
echo.
for /f "tokens=3" %%a in ('dir /s "%DIST%" ^| findstr "File(s)"') do (
    echo Total files size: %%a bytes
)
echo.
exit /b 0
