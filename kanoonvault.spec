# -*- mode: python ; coding: utf-8 -*-
"""
KanoonVault Windows Application PyInstaller Spec File

Build with: pyinstaller kanoonvault.spec

This spec file:
- Bundles the FastAPI backend and all dependencies
- Includes frontend static files (HTML, CSS, JS)
- Uses --onedir format for better dependency handling
- Sets entry point to launcher.py
- Configures the application as a Windows GUI application (no console window)
"""

import os
from pathlib import Path

a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Frontend static files
        ('frontend', 'frontend'),
        # Environment template
        ('.env.example', '.'),
    ],
    hiddenimports=[
        # FastAPI and web framework
        'fastapi',
        'uvicorn',
        'starlette',
        'pydantic',
        
        # OCR and document processing
        'paddleocr',
        'paddlepaddle',
        'pytesseract',
        'fitz',  # PyMuPDF
        'PIL',
        
        # Database
        'sqlite3',
        'chromadb',
        
        # LLM services
        'httpx',
        
        # Utilities
        'aiofiles',
        'python_multipart',
        'webbrowser',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[
        # Exclude pytest and testing tools
        'pytest',
        'unittest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# Create the executable (with console window for now - can be disabled later)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='KanoonVault',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Set to False to hide console window in final build
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='KanoonVault',
)
