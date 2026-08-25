# KanoonVault Windows Build & Test Guide

## Prerequisites

**Install on Windows machine:**

1. **Python 3.10.20** (Required for PaddleOCR compatibility)
   - Download: https://www.python.org/downloads/release/python-3-1020/
   - Check "Add Python to PATH" during installation
   - Verify: `python --version` → should show `3.10.20`

2. **Inno Setup 6.2.4** (Windows installer generator)
   - Download: https://jrsoftware.org/isdl.php
   - Install to default location: `C:\Program Files (x86)\Inno Setup 6`

3. **Git for Windows** (for repository access)
   - Download: https://git-scm.com/download/win

## Phase 1: Build Process

### Step 1: Prepare Repository

```powershell
cd F:\KanoonVault
git checkout feature/windows-packaging
git pull origin feature/windows-packaging
```

### Step 2: Verify Dependencies

```powershell
# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements.txt
pip install PyInstaller==6.1.0

# Verify key packages
pip list | Select-String "PyInstaller|paddleocr|fastapi|uvicorn|keyring"

# Deactivate for clean build
deactivate
```

### Step 3: Run Build Script

```powershell
# Run from repository root
.\build_windows_package.bat
```

**Expected Output:**
```
[1/5] Checking Python 3.10...     [OK] Python 3.10.20 found
[2/5] Installing PyInstaller...   [OK] PyInstaller installed
[3/5] Building with PyInstaller...
      Analyzing launcher.py...
      [OK] Build completed: dist\KanoonVault\
[4/5] Creating Inno Setup installer...
      [OK] Building KanoonVault-Setup.exe...
[5/5] Build Complete!
      📦 Installer: installer-output\KanoonVault-Setup.exe
      📊 Size: ~500-700 MB (includes all dependencies)
```

**Build Artifacts Created:**
- `dist/KanoonVault/` - Bundled application directory
- `build/` - PyInstaller build artifacts
- `installer-output/KanoonVault-Setup.exe` - Final Windows installer (~500-700 MB)

---

## Phase 2: Functional Testing

### Test 1: Installer Execution

1. **Locate Installer**
   ```powershell
   Get-Item "F:\KanoonVault\installer-output\KanoonVault-Setup.exe"
   ```

2. **Run Installer**
   - Double-click `KanoonVault-Setup.exe`
   - Expected: Inno Setup wizard opens
   
3. **Test Installer Options**
   - ✅ Accept license agreement
   - ✅ Select installation location (default: `C:\Program Files\KanoonVault\`)
   - ✅ Choose shortcuts (Start Menu, optional Desktop)
   - ✅ Click "Install"
   - ✅ Wait for installation to complete (~2-3 minutes)
   - ✅ Verify "Finish" button appears
   - ✅ Optional: Check "Launch KanoonVault" and click Finish

---

### Test 2: First-Launch Wizard

#### Screen 1: Welcome Screen
- **Expected**: Clean welcome page with KanoonVault logo
- **Content**: 
  - App description
  - Feature list (cases, documents, OCR, etc.)
  - "Get Started" button (blue)
- **Action**: Click "Get Started"
- **Verification**: ✅ Redirects to Storage Selection screen

#### Screen 2: Storage Location Selection
- **Expected**: Shows current/default storage path
- **Content**:
  - Storage path input: `C:\Users\<Username>\AppData\Local\KanoonVault`
  - Available disk space (e.g., "156.5 GB available")
  - File count in default location (e.g., "0 files found")
  - "Change Location" button (folder icon)
- **Test 2a: Default Storage**
  - Click "Continue"
  - **Verification**: ✅ Initializes storage directory structure
  - **Verification**: ✅ Config saved to `%APPDATA%\Roaming\.kanoonvault\storage-config.json`
  
- **Test 2b: Custom Storage Location** (if desired)
  - Click "Change Location"
  - **Expected**: Native Windows folder browser opens
  - Select external drive (e.g., `D:\MyLegalFiles\`)
  - Click OK
  - **Expected**: Shows error/warning if path invalid (parent of Program Files, insufficient permissions, etc.)
  - Click "Continue"
  - **Verification**: ✅ Creates new location and initializes directories
  - **Verification**: ✅ Config updated with new path
  - **Verification**: ✅ Creates backup if old data exists (e.g., `storage-config-backup-TIMESTAMP.json`)

#### Screen 3: API Key Configuration
- **Expected**: Clean setup form with password input
- **Content**:
  - Input: "OpenRouter API Key" (masked password field with eye toggle)
  - Button: "Test Connection" (gray, disabled until key entered)
  - Status area (initially empty)
  - Button: "Continue" (disabled until test passes)
  
- **Test 3a: Valid API Key**
  1. Paste valid OpenRouter API key (with sufficient credits)
  2. Click "Test Connection"
  3. **Expected**: Loading spinner → "✓ API key valid" (green)
  4. **Verify**: "Continue" button becomes enabled (blue)
  5. Click "Continue"
  6. **Verification**: ✅ Key stored in Windows Credential Manager
  7. **Verification**: ✅ Redirects to main application

- **Test 3b: Invalid API Key**
  1. Enter random string (e.g., `sk-invalid-key-12345`)
  2. Click "Test Connection"
  3. **Expected**: "Invalid API key. Please check and try again." (red)
  4. **Verify**: "Continue" button remains disabled
  5. Clear and re-enter valid key
  6. Test passes, proceed

- **Test 3c: Insufficient Credits**
  1. Use valid API key that's out of credits
  2. Click "Test Connection"
  3. **Expected**: "Insufficient credits. Please add funds to your OpenRouter account." (orange)
  4. **Verify**: "Continue" button remains disabled
  5. Provide funded key to proceed

- **Test 3d: Network Error**
  1. Disconnect internet (or use invalid network)
  2. Enter valid-format API key
  3. Click "Test Connection"
  4. **Expected**: "No internet connection. Please check your network." (gray)
  5. **Verify**: "Continue" remains disabled
  6. Reconnect and retry

---

### Test 3: Main Application Launch

- **Expected**: Browser opens to `http://127.0.0.1:8000`
- **Content**: Main KanoonVault dashboard
- **Verification**: ✅ FastAPI server running on localhost only (no network exposure)
- **Verify**: Can upload documents, perform OCR, create cases, search

---

### Test 4: Storage Persistence

#### Verify Data Directory Structure
```powershell
# Check storage config
$config = Get-Content "$env:APPDATA\Roaming\.kanoonvault\storage-config.json" | ConvertFrom-Json
$storageDir = $config.storage_dir

# Should show subdirectories:
Get-ChildItem -Path $storageDir

# Expected output:
# Mode Name
# ---- ----
# d---- databases
# d---- documents
# d---- uploads
# d---- vector_db
```

#### Test 4a: Close & Reopen App
1. Close KanoonVault and browser
2. Click Start Menu → KanoonVault
3. **Verification**: ✅ Skips setup screens (first-run complete)
4. **Verification**: ✅ Loads main app directly
5. **Verification**: ✅ All previous data/cases present

#### Test 4b: Verify API Key Persistence
1. Close application
2. Reopen application
3. **Verification**: ✅ No API key prompt (stored in Credential Manager)
4. **Verification**: ✅ Can still make API calls (key working)

---

### Test 5: Data Migration

#### Scenario: Change Storage Location After Setup

1. **Prepare Initial Setup**
   - Complete first installation with default location
   - Upload a document → create a case → perform OCR
   - Record document count and file size

2. **Open App Again**
   - Click menu/settings (if available) or manually trigger migration
   - Or: Edit `storage-config.json` to change `storage_dir` to new location

3. **Trigger Migration** (via API or UI)
   - If API: `POST /api/setup/confirm-storage-location` with new path
   - If UI: Re-run setup flow (delete `first_run_complete` flag in JSON)

4. **Verify Migration Process**
   - **Backup Created**: Check original location for `storage-config-backup-TIMESTAMP.json`
   - **Files Copied**: New location should have all databases, documents, embeddings
   - **Data Integrity**: 
     - Same number of documents in new location
     - Same file sizes (byte-for-byte match)
     - Vector DB still functions (search still works)
   - **No Data Loss**: Original files remain (can be manually deleted after verification)

---

## Phase 3: GitHub Release

### Step 1: Prepare Release Files

```powershell
# Navigate to repository
cd F:\KanoonVault

# Verify installer exists and get file size
Get-Item "installer-output\KanoonVault-Setup.exe" | Select-Object Name, Length

# Optional: Create checksum for integrity verification
certutil -hashfile "installer-output\KanoonVault-Setup.exe" SHA256 | Tee-Object -FilePath "installer-output\CHECKSUM.txt"
```

### Step 2: Create GitHub Release

#### Option A: GitHub Web UI
1. Go to: https://github.com/AmeerHussain-ops/KanoonVault/releases
2. Click "Draft a new release"
3. **Tag Version**: `v1.0.0-windows` or `v1.0.0`
4. **Release Title**: "KanoonVault Windows v1.0.0"
5. **Description**:
   ```markdown
   # KanoonVault Windows Setup

   **One-click Windows installation for KanoonVault**

   ## What's Included
   - ✅ Python environment bundled (no installation needed)
   - ✅ FastAPI backend server
   - ✅ Full-featured OCR (PaddleOCR, PyMuPDF, Tesseract)
   - ✅ Vector embeddings with ChromaDB
   - ✅ Secure API key management (Windows Credential Manager)
   - ✅ Local-first architecture (data on your machine only)

   ## Installation
   1. Download `KanoonVault-Setup.exe`
   2. Run installer (administrator rights may be required)
   3. Follow the first-launch wizard:
      - Welcome screen → overview of features
      - Storage location → choose where to store cases and documents
      - API key setup → enter OpenRouter API key (tap into AI features)
      - Done! Application launches automatically
   
   ## System Requirements
   - Windows 10 or later (64-bit)
   - 4 GB RAM minimum (8 GB recommended)
   - 2 GB disk space
   - Internet connection (for OpenRouter API calls)

   ## First-Launch Flow
   When you first run KanoonVault:
   1. Welcome screen with feature overview
   2. Select storage location for your legal documents (default: `C:\Users\YourName\AppData\Local\KanoonVault`)
   3. Enter OpenRouter API key for AI features (optional to proceed, required for AI)
   4. App launches → start managing your cases!

   ## Data Storage
   - **Your Data**: Stored locally in `C:\Users\YourName\AppData\Local\KanoonVault` (configurable)
   - **Application**: Installed in `Program Files\KanoonVault` (optional on uninstall)
   - **Database**: SQLite3 for case management
   - **Vector Store**: ChromaDB for semantic search
   - **No Cloud**: All processing happens on your machine

   ## API Key Setup
   - Sign up free at https://openrouter.ai/
   - Get your API key from settings
   - Supports models: Claude 3, GPT-4, Llama 2, and 200+ others
   - Only charged when you use AI features
   - Key stored securely in Windows Credential Manager

   ## Troubleshooting
   - **Application won't start**: Run as Administrator
   - **OCR not working**: Check internet connection (for model downloads)
   - **Memory issues**: Use "Change Storage Location" to move to faster drive
   - **Lost API key**: Re-enter in settings, key saved in Credential Manager

   ## Build Information
   - **Version**: 1.0.0
   - **Built with**: PyInstaller 6.1.0, Inno Setup 6.2.4
   - **Python**: 3.10.20 (bundled)
   - **Size**: ~500-700 MB
   - **Release Date**: 2026-08-20

   ## Support
   - GitHub Issues: Report bugs or request features
   - Documentation: See WINDOWS_BUILD_GUIDE.md in repository
   ```

6. **Attach Files**:
   - Drag `KanoonVault-Setup.exe` into the upload area
   - Optional: Attach `CHECKSUM.txt`
   - Optional: Attach `WINDOWS_PACKAGING_SUMMARY.md` and `FIRST_LAUNCH_FLOW.md`

7. **Publish Release**:
   - Check "This is a pre-release" if testing
   - Click "Publish release"

#### Option B: GitHub CLI (if installed)
```powershell
# Install GitHub CLI if needed
# choco install gh

# Authenticate
gh auth login

# Create release
gh release create v1.0.0 `
  --title "KanoonVault Windows v1.0.0" `
  --notes-file .\RELEASE_NOTES.md `
  "installer-output/KanoonVault-Setup.exe"
```

#### Option C: PowerShell Script for Release
Create `create-github-release.ps1`:
```powershell
param(
    [string]$Version = "1.0.0",
    [string]$InstallerPath = ".\installer-output\KanoonVault-Setup.exe"
)

# Validate installer exists
if (-not (Test-Path $InstallerPath)) {
    Write-Error "Installer not found: $InstallerPath"
    exit 1
}

# Get file info
$fileSize = (Get-Item $InstallerPath).Length / 1MB
Write-Host "Installer size: $($fileSize)MB"

# Create checksum
certutil -hashfile $InstallerPath SHA256 | Tee-Object -FilePath "CHECKSUM.txt"

# Create tag
git tag -a "v$Version" -m "Release: KanoonVault Windows v$Version"
git push origin "v$Version"

Write-Host "✅ Tag created and pushed. Now create release on GitHub web UI."
```

### Step 3: Publish and Share

1. **Verify Release Page**:
   - Go to https://github.com/AmeerHussain-ops/KanoonVault/releases/latest
   - Confirm `.exe` file is downloadable
   - Verify file size (~500-700 MB)

2. **Test Download**:
   - Download from GitHub Release page
   - Verify checksum matches (if provided)
   - Test installation on clean Windows VM

3. **Share with Users**:
   - Update README.md with download link
   - Update website/documentation with release info
   - Announce on channels (social media, forums, emails, etc.)

---

## Testing Checklist

- [ ] **Build Phase**
  - [ ] Python 3.10 verified
  - [ ] PyInstaller installed
  - [ ] Inno Setup installed
  - [ ] Build script completed without errors
  - [ ] `KanoonVault-Setup.exe` created (~500-700 MB)

- [ ] **Installation Phase**
  - [ ] Installer runs without UAC issues
  - [ ] Accepts license agreement
  - [ ] Allows location selection
  - [ ] Creates shortcuts successfully
  - [ ] Installation completes in 2-3 minutes

- [ ] **First-Launch Wizard**
  - [ ] Welcome screen displays correctly
  - [ ] Storage selection allows default and custom locations
  - [ ] Native folder browser opens when requested
  - [ ] Path validation works (rejects invalid paths)
  - [ ] API key input accepts and tests keys
  - [ ] Correct error messages for invalid/expired keys
  - [ ] Continue button only enables after valid key
  - [ ] Config file created in %APPDATA%\.kanoonvault\

- [ ] **Application Launch**
  - [ ] App launches without Python terminal visible
  - [ ] Browser opens to 127.0.0.1:8000
  - [ ] Main dashboard displays
  - [ ] Upload/OCR/search functionality works

- [ ] **Data Persistence**
  - [ ] Close and reopen app → uses existing setup
  - [ ] No second setup wizard
  - [ ] API key still works (stored in Credential Manager)
  - [ ] Data directory maintained

- [ ] **Data Migration**
  - [ ] Can change storage location
  - [ ] Files copied to new location
  - [ ] Backup created of old config
  - [ ] No data loss during migration
  - [ ] Vector DB index still works (search functional)

- [ ] **GitHub Release**
  - [ ] Release created with proper version tag
  - [ ] Installer file attached and downloadable
  - [ ] Description includes setup instructions
  - [ ] System requirements documented
  - [ ] Release marked as latest

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Python 3.10 not found" | Install from https://www.python.org/downloads/release/python-3-1020/ |
| PyInstaller fails with "ModuleNotFoundError" | Run `pip install -r requirements.txt` in clean venv |
| Inno Setup not found | Install from https://jrsoftware.org/isdl.php to default location |
| Installer large (>1GB) | Normal - includes OCR models. Clean /dist/build/ and rebuild if needed |
| First-launch wizard doesn't appear | Delete `%APPDATA%\Roaming\.kanoonvault\storage-config.json` and restart |
| API key test fails but key is valid | Check internet connectivity, ensure OpenRouter API is accessible |
| Data migration fails | Ensure target location has write permissions, disk space ≥ current usage |

---

## Next Steps After Release

1. **Monitor Issues**: Watch GitHub Issues for user reports
2. **Collect Feedback**: Ask users about their experience
3. **Plan Updates**: 
   - Auto-update mechanism (optional)
   - Settings GUI (optional)
   - Integration with cloud storage (optional)
4. **Create Installers for Updates**: Rebuild and release new versions with version number increments
