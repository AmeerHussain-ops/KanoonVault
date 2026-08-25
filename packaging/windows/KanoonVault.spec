# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

repo_root = Path(__file__).resolve().parents[2]
app_root = repo_root

analysis = Analysis(
    [str(app_root / 'launcher.py')],
    pathex=[str(app_root)],
    binaries=[],
    datas=[
        (str(app_root / 'frontend'), 'frontend'),
        (str(app_root / '.env.example'), '.'),
    ],
    hiddenimports=[
        'fastapi',
        'uvicorn',
        'starlette',
        'pydantic',
        'pydantic_core',
        'httpx',
        'aiofiles',
        'python_multipart',
        'PIL',
        'fitz',
        'pytesseract',
        'paddleocr',
        'paddlepaddle',
        'chromadb',
        'sqlite3',
        'keyring',
        'webbrowser',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', 'unittest', 'ipython', 'jupyter'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(analysis.pure, analysis.zipped_data, cipher=None)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name='KanoonVault',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    analysis.binaries,
    analysis.zipfiles,
    analysis.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='KanoonVault',
)
