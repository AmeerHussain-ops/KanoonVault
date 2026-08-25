# KanoonVault Windows Packaging Guide

This guide explains how to build and package KanoonVault into a Windows `.exe` installer.

## Table of Contents

- [System Requirements](#system-requirements)
- [Quick Build](#quick-build)
- [Step-by-Step Build](#step-by-step-build)
- [Configuration](#configuration)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

## System Requirements

### Build System Requirements

To **build** KanoonVault for Windows, you need:

- **Windows 10 or later** (build system must be Windows)
- **Python 3.10.x** (3.10.20 recommended)
- **PyInstaller** (automatically installed by the build script)
- **Inno Setup 6** (optional, for creating the `.exe` installer)
  - Download: https://jrsoftware.org/isdl.php
  - Default installation path: `C:\Program Files (x86)\Inno Setup 6\`

### End-User Requirements

Users who install KanoonVault do **NOT** need:

- Python installed
- Virtual environment
- Any command-line experience
- Docker
- External dependencies (all bundled)

## Quick Build

### Option 1: Automatic Build (Recommended)

```bash
.\build_windows_package.bat
```

This script will:

1. ✓ Verify Python 3.10 is installed
2. ✓ Install PyInstaller
3. ✓ Build the PyInstaller bundle
4. ✓ Create the Windows installer (if Inno Setup is installed)

### Option 2: Manual Build

See [Step-by-Step Build](#step-by-step-build) below.

## Step-by-Step Build

### Step 1: Verify Python 3.10

```bash
py -3.10 --version
```

Expected output: `Python 3.10.x`

If not found, install from: https://www.python.org/downloads/

### Step 2: Install PyInstaller

```bash
py -3.10 -m pip install pyinstaller
```

### Step 3: Build the PyInstaller Bundle

```bash
py -3.10 -m PyInstaller kanoonvault.spec --distpath=dist --buildpath=build --noconfirm
```

This creates: `dist\KanoonVault\KanoonVault.exe`

You can test the executable directly:

```bash
.\dist\KanoonVault\KanoonVault.exe
```

### Step 4: Install Inno Setup (Optional)

To create the Windows installer `.exe` file:

1. Download Inno Setup 6: https://jrsoftware.org/isdl.php
2. Run the installer
3. Accept default installation path: `C:\Program Files (x86)\Inno Setup 6\`

### Step 5: Build the Windows Installer

```bash
"C:\Program Files (x86)\Inno Setup 6\iscc.exe" /O"installer-output" /F"KanoonVault-Setup" kanoonvault-installer.iss
```

This creates: `installer-output\KanoonVault-Setup.exe`

## Configuration

### Launcher Configuration

The launcher (`launcher.py`) manages:

- Creating user data directories in `%APPDATA%\KanoonVault\`
- Starting the FastAPI backend on `127.0.0.1:8000`
- Automatically opening the browser to the web interface
- Graceful shutdown on application close

### User Data Storage

All user data is stored in: `%APPDATA%\KanoonVault\`

This includes:

- `kanoonvault.db` — SQLite database
- `uploads/` — uploaded documents
- `chroma_db/` — vector embeddings
- `.env` — API keys and configuration

This ensures:

- ✓ User data survives application updates
- ✓ User data is never bundled in the executable
- ✓ Multiple users can use the same installation
- ✓ Complies with Windows application standards

### Environment Configuration

Users can configure API keys by editing: `%APPDATA%\KanoonVault\.env`

The launcher automatically creates a template `.env` file on first run.

Example:

```
OPENROUTER_API_KEY=your_key_here
OCR_VISION_API_KEY=your_key_here
TIMELINE_API_KEY=your_key_here
```

## PyInstaller Build Details

### Spec File: `kanoonvault.spec`

The PyInstaller spec file configures:

- **Entry point**: `launcher.py`
- **Data files**: Frontend static files, `.env.example`
- **Hidden imports**: OCR, PDF, database, LLM libraries
- **Mode**: `--onedir` (better for complex dependencies)
- **Output**: Single executable directory with all dependencies

### Build Artifacts

After building, the following directories are created:

```
dist/
  KanoonVault/
    KanoonVault.exe          (main executable)
    launcher.py              (included)
    main.py, models.py, ...  (bundled Python modules)
    frontend/                (static files)
    services/                (bundled services)
    _internal/               (dependencies)
      # All Python packages, DLLs, and OCR models

build/
  (temporary build artifacts - can be deleted)
```

## Inno Setup Builder Details

### Installer Configuration: `kanoonvault-installer.iss`

The Inno Setup script configures:

- **Install location**: `Program Files\KanoonVault\`
- **Shortcuts**: Start Menu and optional Desktop
- **Registry**: Application entry in Add/Remove Programs
- **Uninstall**: Preserves user data in `%APPDATA%\KanoonVault\`

### Installer Features

- ✓ Standard Windows installer (`.exe`)
- ✓ One-click installation
- ✓ Automatic Start Menu shortcut
- ✓ Optional Desktop shortcut
- ✓ Standard uninstall through Control Panel
- ✓ Upgrades preserve user data
- ✓ Lightweight (`~800MB` including all dependencies)

## Testing

### Test #1: Verify PyInstaller Build

```bash
.\dist\KanoonVault\KanoonVault.exe
```

Expected:

- ✓ Console window opens
- ✓ "Starting KanoonVault on 127.0.0.1:8000" message
- ✓ Browser opens to `http://127.0.0.1:8000`
- ✓ Web interface loads
- ✓ User data created in `%APPDATA%\KanoonVault\`

### Test #2: Verify Installer

On a clean Windows machine (or virtual machine):

```bash
.\installer-output\KanoonVault-Setup.exe
```

Expected:

- ✓ Installer wizard opens
- ✓ Application installs to `Program Files\KanoonVault\`
- ✓ Shortcuts created in Start Menu
- ✓ Application launches after installation
- ✓ Browser opens automatically
- ✓ Web interface is accessible

### Test #3: Verify User Data

1. Create a test case
2. Upload a PDF
3. Close the application
4. Reopen the application
5. Verify the case and document still exist

Expected:

- ✓ User data persists between sessions
- ✓ Database is stored in `%APPDATA%\KanoonVault\kanoonvault.db`

### Test #4: API Key Configuration

1. Open `%APPDATA%\KanoonVault\.env`
2. Add your OpenRouter API key
3. Restart the application
4. Test chat with a document

Expected:

- ✓ API key is read from `.env`
- ✓ Chat functionality works

## Troubleshooting

### Issue: PyInstaller Build Fails

**Symptom**: `PyInstaller build failed`

**Solution**:

1. Update pip: `py -3.10 -m pip install --upgrade pip`
2. Reinstall dependencies: `py -3.10 -m pip install -r requirements.txt`
3. Clean build: Delete `build/` and `dist/` directories
4. Rebuild: `py -3.10 -m PyInstaller kanoonvault.spec --distpath=dist --buildpath=build --noconfirm`

### Issue: "KanoonVault.exe not found"

**Symptom**: Build completes but `KanoonVault.exe` is missing

**Solution**:

1. Check the `dist/KanoonVault/` directory exists
2. Look for`launcher.py` in the output
3. Ensure the spec file path is correct

### Issue: Inno Setup Not Found

**Symptom**: "Inno Setup not found at expected locations"

**Solution**:

1. Install Inno Setup: https://jrsoftware.org/isdl.php
2. Verify installation path:
   - `C:\Program Files (x86)\Inno Setup 6\iscc.exe` (default for 32-bit OS)
   - `C:\Program Files\Inno Setup 6\iscc.exe` (some 64-bit systems)

3. Update `build_windows_package.bat` if your path differs

### Issue: Application Crashes on Startup

**Symptom**: `KanoonVault.exe` starts but crashes immediately

**Cause**: Missing dependency or incorrect data path

**Solution**:

1. Run the executable from command line to see error messages:
   ```bash
   cd dist\KanoonVault
   .\KanoonVault.exe
   ```

2. Check for error messages about missing modules
3. Ensure `frontend/` directory is in the bundle
4. Verify `%APPDATA%\KanoonVault\` is writable

### Issue: Browser Doesn't Open Automatically

**Symptom**: Application runs but browser doesn't launch

**Cause**: Server startup delay or network binding issue

**Solution**:

1. Manually open `http://127.0.0.1:8000` in your browser
2. Check Windows Firewall settings:
   - Allow `KanoonVault.exe` for localhost connections
3. Verify port 8000 is not in use: `netstat -ano | findstr :8000`

### Issue: File Not Found Errors

**Symptom**: "Frontend files not found" or similar errors

**Cause**: `frontend/` directory not included in PyInstaller bundle

**Solution**:

1. Verify `kanoonvault.spec` includes frontend data:
   ```python
   ('frontend', 'frontend'),
   ```

2. Verify `frontend/` directory contents:
   ```bash
   ls -la frontend/
   ```

3. Rebuild: `py -3.10 -m PyInstaller kanoonvault.spec --noconfirm`

### Issue: "Port Already in Use"

**Symptom**: Application won't start, "Address already in use"

**Cause**: Port 8000 is occupied by another application

**Solution**:

1. Find the process: `netstat -ano | findstr :8000`
2. Kill the process: `taskkill /PID <pid> /F`
3. Or change the port in the launcher environment variable

## Advanced Building

### Building on Non-Windows Systems

To build for Windows on macOS or Linux:

1. Use a Windows virtual machine
2. Or use Windows Subsystem for Linux (WSL) with Windows tools

### Customizing the Installer

Edit `kanoonvault-installer.iss`:

- Change installation directory (line: `DefaultDirName`)
- Add custom shortcuts or steps
- Modify installer artwork or messages
- Change uninstall behavior

### Disabling the Console Window

To hide the console window in the packaged application:

Edit `kanoonvault.spec`:

```python
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
    console=False,  # Change this to False
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```

Then rebuild with PyInstaller.

## Continuous Integration / Deployment

To automate builds in CI/CD:

1. Add a Windows build agent to your CI system
2. Schedule the build to run on a Windows machine
3. Store artifacts (`.exe` files) for download
4. Use GitHub Releases to distribute installers

Example GitHub Actions workflow snippet:

```yaml
jobs:
  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install Inno Setup
        # Install Inno Setup via chocolatey or direct download
      - name: Build
        run: .\build_windows_package.bat
      - name: Upload Artifact
        uses: actions/upload-artifact@v3
        with:
          name: KanoonVault-Setup.exe
          path: installer-output/KanoonVault-Setup.exe
```

## Support

For build issues, please:

1. Check the Troubleshooting section above
2. Review build script output carefully
3. Open a GitHub issue with:
   - OS version (Windows 10/11)
   - Python version: `py --version`
   - Error messages (full console output)
   - Steps to reproduce

---

**Last Updated**: August 20, 2026

For more information, see the main [README.md](README.md)
