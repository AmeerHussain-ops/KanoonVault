@echo off
title KanoonVault - Legal Memory OS
color 0B

echo.
echo  ========================================
echo   KanoonVault - Legal Memory OS
echo  ========================================
echo.

cd /d "%~dp0"

:: Check Python and prefer Python 3.10
set "PYTHON=python"
set "PY_VERSION="
if exist "%SystemRoot%\py.exe" (
    for /f "tokens=2 delims= " %%A in ('py -3.10 --version 2^>^&1') do (
        set "PY_VERSION=%%A"
        set "PYTHON=py -3.10"
    )
)
if not defined PY_VERSION (
    for /f "tokens=2 delims= " %%A in ('%PYTHON% --version 2^>^&1') do set "PY_VERSION=%%A"
)
if /i not "%PY_VERSION:~0,4%"=="3.10" (
    echo [ERROR] Python 3.10.x is required for PaddleOCR. Found %PY_VERSION%.
    echo Install Python 3.10.20 and ensure py -3.10 is available.
    pause
    exit /b 1
)

:: Install dependencies if not already done
if not exist ".deps_installed" (
    echo [*] Installing dependencies (first run - this may take a while)...
    %PYTHON% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
    %PYTHON% -c "import fitz" 2>nul
    if errorlevel 1 (
        echo [WARN] PyMuPDF import failed. Re-run: %PYTHON% -m pip install PyMuPDF==1.24.14
    ) else (
        echo [OK] PyMuPDF ready for PDFs.
    )
    %PYTHON% -c "from paddleocr import PaddleOCR" 2>nul
    if errorlevel 1 (
        echo [WARN] PaddleOCR import failed. Re-run: %PYTHON% -m pip install paddlepaddle==2.6.2 paddleocr==2.9.1
    ) else (
        echo [OK] PaddleOCR ready.
    )
    echo. > .deps_installed
    echo [OK] Dependencies installed.
)

:: Create uploads directory
if not exist "uploads" mkdir uploads

echo [*] Starting KanoonVault on http://localhost:8000
echo [*] Press Ctrl+C to stop.
echo.
echo  Open your browser at: http://localhost:8000
echo.

:: Start FastAPI
%PYTHON% -m uvicorn main:app --host 0.0.0.0 --port 8000

pause
