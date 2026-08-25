@echo off
REM KanoonVault Windows Packaging Build Script
REM This script builds KanoonVault-Setup.exe
REM
REM Requirements:
REM - Python 3.10+
REM - PyInstaller
REM - Inno Setup installed to its default location
REM

setlocal enabledelayedexpansion

title KanoonVault Windows Build

echo.
echo  ========================================
echo    KanoonVault Windows Packaging Builder
echo  ========================================
echo.

REM Get the script directory
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM ============================================================================
REM Step 1: Check Python 3.10
REM ============================================================================
echo [1/5] Checking Python 3.10...

set "PYTHON=python"
for /f "tokens=2 delims= " %%A in ('py -3.10 --version 2^>^&1') do set "PY_VERSION=%%A"

if not defined PY_VERSION (
    for /f "tokens=2 delims= " %%A in ('%PYTHON% --version 2^>^&1') do set "PY_VERSION=%%A"
)

if /i not "%PY_VERSION:~0,4%"=="3.10" (
    echo [ERROR] Python 3.10.x is required. Found: %PY_VERSION%
    echo Install Python 3.10.20 from https://www.python.org/downloads/
    pause
    exit /b 1
)
echo [OK] Python %PY_VERSION% found

REM ============================================================================
REM Step 2: Install PyInstaller
REM ============================================================================
echo.
echo [2/5] Installing PyInstaller...

%PYTHON% -m pip install pyinstaller --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install PyInstaller
    pause
    exit /b 1
)
echo [OK] PyInstaller installed

REM ============================================================================
REM Step 3: Check Inno Setup
REM ============================================================================
echo.
echo [3/5] Checking Inno Setup...

set "INNO_PATH=C:\Program Files (x86)\Inno Setup 6\iscc.exe"
if not exist "!INNO_PATH!" (
    set "INNO_PATH=C:\Program Files\Inno Setup 6\iscc.exe"
)
if not exist "!INNO_PATH!" (
    echo [WARN] Inno Setup not found at expected locations
    echo [WARN] Install from: https://jrsoftware.org/isdl.php
    set "BUILD_INSTALLER=0"
) else (
    echo [OK] Inno Setup found at !INNO_PATH!
    set "BUILD_INSTALLER=1"
)

REM ============================================================================
REM Step 4: Build PyInstaller executable
REM ============================================================================
echo.
echo [4/5] Building PyInstaller executable...
echo [*] This may take several minutes...

REM Remove old build/dist directories
if exist "build" rmdir /s /q "build" >nul 2>&1
if exist "dist" rmdir /s /q "dist" >nul 2>&1

%PYTHON% -m PyInstaller kanoonvault.spec --distpath=dist --buildpath=build --noconfirm

if errorlevel 1 (
    echo [ERROR] PyInstaller build failed
    pause
    exit /b 1
)
echo [OK] PyInstaller build completed

REM Verify the build
if not exist "dist\KanoonVault\KanoonVault.exe" (
    echo [ERROR] KanoonVault.exe not found in dist directory
    pause
    exit /b 1
)
echo [OK] KanoonVault.exe created successfully

REM ============================================================================
REM Step 5: Build Inno Setup installer (if available)
REM ============================================================================
if "!BUILD_INSTALLER!"=="1" (
    echo.
    echo [5/5] Building Inno Setup installer...
    echo [*] This may take a minute...

    if not exist "installer-output" mkdir "installer-output"
    
    "!INNO_PATH!" /O"installer-output" /F"KanoonVault-Setup" kanoonvault-installer.iss
    
    if errorlevel 1 (
        echo [ERROR] Inno Setup build failed
        pause
        exit /b 1
    )
    echo [OK] Installer created successfully
    
    if exist "installer-output\KanoonVault-Setup.exe" (
        for /f "tokens=*" %%f in ('dir /b /s "installer-output\KanoonVault-Setup.exe"') do (
            set "SETUP_FILE=%%f"
        )
        echo.
        echo  ========================================
        echo    Build Complete!
        echo  ========================================
        echo.
        echo  Installer location:
        echo  !SETUP_FILE!
        echo.
        echo  Next steps:
        echo  1. Test the installer on a Windows machine
        echo  2. Verify the app starts correctly
        echo  3. Check that user data is stored in %%APPDATA%%\KanoonVault
        echo.
    )
) else (
    echo.
    echo  ========================================
    echo    Build Complete (PyInstaller Only)
    echo  ========================================
    echo.
    echo  The packaged application is at:
    echo  dist\KanoonVault\
    echo.
    echo  You can:
    echo  1. Run directly: dist\KanoonVault\KanoonVault.exe
    echo  2. Manually create an Inno Setup installer after installing Inno Setup
    echo  3. Download Inno Setup from: https://jrsoftware.org/isdl.php
    echo.
)

pause
exit /b 0
