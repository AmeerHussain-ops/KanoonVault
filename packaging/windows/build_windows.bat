@echo off
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

echo.
echo =====================================================
echo   KanoonVault Windows Packaging Builder
echo =====================================================
echo.

echo [1/4] Checking Python 3.10...
set "PYTHON_CMD=python"
set "PYTHON_VERSION="
for /f "tokens=2 delims= " %%A in ('py -3.10 --version 2^>^&1') do set "PYTHON_VERSION=%%A"
if not defined PYTHON_VERSION (
    for /f "tokens=2 delims= " %%A in ('python --version 2^>^&1') do set "PYTHON_VERSION=%%A"
)
if /i not "%PYTHON_VERSION:~0,4%"=="3.10" (
    echo [ERROR] Python 3.10.x is required. Found: %PYTHON_VERSION%
    echo Install Python 3.10.20 from https://www.python.org/downloads/
    pause
    exit /b 1
)

if defined PYTHON_VERSION (
    echo [OK] Python %PYTHON_VERSION% found
)

if not exist "%REPO_ROOT%\.venv" (
    echo [2/4] Creating virtual environment...
    py -3.10 -m venv .venv
)

call "%REPO_ROOT%\.venv\Scripts\activate.bat"

echo [3/4] Installing dependencies...
python -m pip install --upgrade pip >nul
python -m pip install -r "%REPO_ROOT%\requirements.txt" >nul
python -m pip install pyinstaller==6.1.0 >nul

if not exist "%REPO_ROOT%\dist\KanoonVault" (
    echo [4/4] Building PyInstaller bundle...
    python -m PyInstaller "%SCRIPT_DIR%\KanoonVault.spec" --distpath "%REPO_ROOT%\dist" --workpath "%SCRIPT_DIR%\build" --noconfirm
) else (
    echo [4/4] Reusing existing PyInstaller build output...
)

if not exist "%REPO_ROOT%\dist\KanoonVault\KanoonVault.exe" (
    echo [ERROR] PyInstaller build output missing.
    pause
    exit /b 1
)

if not exist "%REPO_ROOT%\installer" mkdir "%REPO_ROOT%\installer"

set "INNO_PATH=C:\Program Files (x86)\Inno Setup 6\iscc.exe"
if not exist "%INNO_PATH%" set "INNO_PATH=C:\Program Files\Inno Setup 6\iscc.exe"

if exist "%INNO_PATH%" (
    echo [*] Building installer with Inno Setup...
    "%INNO_PATH%" /O"%REPO_ROOT%\installer" /F"KanoonVault-Setup" "%SCRIPT_DIR%\KanoonVault.iss"
    if errorlevel 1 (
        echo [ERROR] Inno Setup build failed.
        pause
        exit /b 1
    )
    echo.
    echo ========================================
    echo  Build complete
    echo ========================================
    echo.
    echo Output:
    echo %REPO_ROOT%\installer\KanoonVault-Setup.exe
    echo.
    pause
    exit /b 0
) else (
    echo [WARN] Inno Setup not installed. PyInstaller bundle created at:
    echo %REPO_ROOT%\dist\KanoonVault
    echo.
    echo To create the installer later, install Inno Setup and run:
    echo   "%SCRIPT_DIR%\build_windows.bat"
    pause
    exit /b 0
)
