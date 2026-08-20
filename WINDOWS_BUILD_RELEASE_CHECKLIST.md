# KanoonVault Windows Build & Release - Complete Checklist

**Status:** Ready to build on Windows machine with Python 3.10.20

---

## Prerequisites Check ✅

Before starting, verify on your Windows machine:

- [ ] **Windows 10 or later** (64-bit)
- [ ] **Python 3.10.20** installed
  ```powershell
  python --version  # Should show: Python 3.10.20
  ```
- [ ] **Git for Windows** installed
  ```powershell
  git --version
  ```
- [ ] **Inno Setup 6.2.4** installed to default location
  ```powershell
  Test-Path 'C:\Program Files (x86)\Inno Setup 6'  # Should show: True
  ```
- [ ] **4+ GB RAM** available
- [ ] **2+ GB disk space** (for build artifacts)
- [ ] **Internet connection** (for downloading dependencies)

---

## Phase 1: Setup (5 minutes)

### Step 1.1: Clone/Pull Repository
```powershell
# Navigate to your workspace
cd F:\KanoonVault  # or your desired location

# Ensure you have the feature branch
git fetch origin
git checkout feature/windows-packaging
git pull origin feature/windows-packaging
```

**Expected:** 
```
Switched to branch 'feature/windows-packaging'
Your branch is up to date with 'origin/feature/windows-packaging'.
```

### Step 1.2: Verify Code Files Exist
```powershell
# Check critical files are present
$files = @(
    'launcher.py',
    'kanoonvault.spec',
    'kanoonvault-installer.iss',
    'build_windows_package.bat',
    'credentials.py',
    'storage_manager.py'
)

foreach ($file in $files) {
    if (Test-Path $file) { Write-Host "✅ $file" }
    else { Write-Host "❌ MISSING: $file" }
}
```

**Expected:** All 6 files show ✅

### Step 1.3: Verify Python 3.10
```powershell
python --version

# Also verify pip works
pip --version

# Verify you can import critical packages (install if needed)
python -m pip install --upgrade pip
```

**Expected:**
```
Python 3.10.20
pip 24.x.x from C:\Python310\lib\site-packages\pip (python 3.10)
```

---

## Phase 2: Build (30-45 minutes)

### Step 2.1: Install PyInstaller
```powershell
pip install pyinstaller==6.1.0

# Verify installation
pyinstaller --version  # Should show: 6.1.0
```

### Step 2.2: Install Application Dependencies
```powershell
# Install all required packages
pip install -r requirements.txt

# This will take 5-10 minutes (includes OCR models, ChromaDB, FastAPI, etc.)
# You'll see many packages being downloaded and installed
```

**Expected:** Completes without errors. Final message should be:
```
Successfully installed [list of packages]
```

### Step 2.3: Run Build Script
```powershell
# Execute the build automation script
.\build_windows_package.bat

# This will take 15-30 minutes (bundling dependencies)
# You'll see progress messages for each step
```

**Expected Output:**
```
========================================
  KanoonVault Windows Packaging Builder
========================================

[1/5] Checking Python 3.10...
      [OK] Python 3.10.20 found

[2/5] Installing PyInstaller...
      [OK] PyInstaller installed

[3/5] Building with PyInstaller...
      Analyzing launcher.py...
      Collecting imports...
      [OK] Build completed: dist\KanoonVault\

[4/5] Creating Inno Setup installer...
      Building KanoonVault-Setup.exe...
      [OK] Installer generated

[5/5] Build Complete!
      📦 Installer: installer-output\KanoonVault-Setup.exe
      📊 Size: 500-700 MB
      ✅ Ready for distribution!
```

### Step 2.4: Verify Build Output
```powershell
# Check installer was created
Get-Item "installer-output\KanoonVault-Setup.exe" | Select-Object Name, Length

# Expected output:
# Name                      Length
# ----                      ------
# KanoonVault-Setup.exe     524288000  (500-700 MB)
```

- [ ] Installer exists: `installer-output\KanoonVault-Setup.exe`
- [ ] Size is 500-700 MB (not compressed)
- [ ] Build directory has no errors

**If build fails:**
- Check Python 3.10 version
- Verify all dependencies installed correctly
- See troubleshooting section below

---

## Phase 3: Testing (1-2 hours)

### Test 3.1: Pre-Installation Verification

```powershell
# Generate and verify checksum
certutil -hashfile "installer-output\KanoonVault-Setup.exe" SHA256 | Tee-Object -FilePath "installer-output\CHECKSUM.txt"
```

Save the checksum for later verification.

- [ ] Checksum saved to `CHECKSUM.txt`

### Test 3.2: Installer Execution

1. **Open File Explorer**
   - Navigate to: `installer-output\`
   - Double-click: `KanoonVault-Setup.exe`

2. **Inno Setup Wizard Appears**
   - [ ] See welcome screen with KanoonVault logo
   - [ ] Can read installer information
   - Click **Next**

3. **Select Destination Location**
   - Default: `C:\Program Files\KanoonVault\`
   - [ ] Path shown correctly
   - [ ] Can change if desired (optional)
   - Click **Next**

4. **Select Additional Tasks**
   - [ ] Option to create Start Menu shortcuts
   - [ ] Option to create Desktop shortcut
   - [ ] Leave defaults selected
   - Click **Next**

5. **Ready to Install**
   - [ ] Summary shows installation details
   - Click **Install**
   - **Wait 2-3 minutes** for installation (unpacking dependencies)

6. **Installation Complete**
   - [ ] See "Installation Complete" screen
   - [ ] Checkbox: "Launch KanoonVault" is checked
   - Click **Finish**

- [ ] Installer ran without errors
- [ ] Installation completed successfully
- [ ] Application directory created in Program Files

### Test 3.3: First-Launch Wizard - Welcome Screen

**Expected:** Browser opens, you see welcome page

1. **Welcome Screen Content**
   - [ ] KanoonVault logo displayed prominently
   - [ ] Clear description of application purpose
   - [ ] Feature list visible (Cases, Documents, OCR, etc.)
   - [ ] Blue "Get Started" button active

2. **Interact with Welcome**
   - Click the **"Get Started"** button
   - **Expected:** Redirects to Storage Selection screen

- [ ] Welcome screen displays correctly
- [ ] Navigation works

### Test 3.4: First-Launch Wizard - Storage Location Screen

**Expected:** You see storage location selection UI

1. **Storage Location Display**
   - [ ] Current/default path shown: `C:\Users\<YourName>\AppData\Local\KanoonVault`
   - [ ] Folder icon next to path
   - [ ] Display of available disk space (e.g., "156.5 GB free")
   - [ ] File count shown (should be 0 for fresh install)

2. **Test Default Storage (Recommended)**
   - [ ] Click **"Continue"** button
   - **Expected:** Storage directory initialized, redirects to API Key screen
   - [ ] Check directory created: `C:\Users\<YourName>\AppData\Local\KanoonVault\`

3. **Test Custom Storage (Optional)**
   - Go back (or re-run app, delete config)
   - [ ] Click **"Change Location"** button
   - **Expected:** Native Windows folder browser opens
   - Select an alternate drive/location (e.g., `D:\MyLegalFiles\`)
   - [ ] Click **OK**
   - [ ] Screen shows new selected path
   - [ ] Click **"Continue"**
   - **Expected:** Initialization with new path, redirects to API Key screen

- [ ] Storage selection works
- [ ] Directory structure created
- [ ] Config file created: `%APPDATA%\Roaming\.kanoonvault\storage-config.json`

### Test 3.5: First-Launch Wizard - API Key Setup Screen

**Expected:** Clean form with password input

1. **API Key Form Display**
   - [ ] Input field labeled "OpenRouter API Key" 
   - [ ] Input is masked (password type)
   - [ ] Eye icon to toggle visibility
   - [ ] "Test Connection" button (initially gray/disabled)
   - [ ] Status area (initially empty)
   - [ ] "Continue" button (disabled until valid key)

2. **Test Valid API Key** (recommended - use your actual OpenRouter key)
   - [ ] Paste your OpenRouter API key into input
   - Ensure you have:
     - Valid key format (starts with `sk-...`)
     - Account has credits remaining
     - Account is active

   - [ ] Click **"Test Connection"**
   - **Wait 5-10 seconds** for API response
   - **Expected:** 
     ```
     ✓ API key valid
     (green checkmark, green text)
     ```
   - [ ] "Continue" button becomes enabled (blue)
   - [ ] Click **"Continue"**
   - **Expected:** Redirects to main application

3. **Test Invalid API Key** (optional, use fake key)
   - [ ] Enter random string (e.g., `sk-invalid-key-12345`)
   - [ ] Click "Test Connection"
   - **Expected:** Error message in red
     ```
     ❌ Invalid API key. Please check and try again.
     ```
   - [ ] "Continue" button stays disabled
   - [ ] Clear and re-enter valid key to proceed

4. **Error Scenarios** (optional testing)
   - **No Internet**: Disconnect WiFi, test key
     - **Expected**: Gray error "No internet connection"
   - **Insufficient Credits**: Use key that's out of money
     - **Expected**: Orange warning "Insufficient credits"

- [ ] API key validation works correctly
- [ ] Only enables continue after valid key
- [ ] Error messages are clear and appropriate

### Test 3.6: Application Launch

1. **Main Dashboard Loads**
   - [ ] Browser shows main KanoonVault dashboard
   - [ ] URL: `http://127.0.0.1:8000`
   - [ ] No Python terminal visible (wrapped in Windows app)
   - [ ] Dashboard UI loads completely

2. **Verify Functionality**
   - [ ] Can upload document (drag-drop or file picker)
   - [ ] OCR button works (if available)
   - [ ] Can create a case
   - [ ] Search/filter works
   - [ ] API calls succeed (uses stored API key)

3. **Application Closes Cleanly**
   - [ ] Close browser
   - [ ] Application terminates properly
   - [ ] No lingering processes

- [ ] Main app launches correctly
- [ ] Functionality operational
- [ ] No errors in console (shouldn't see Python terminal)

### Test 3.7: Data Persistence

1. **Relaunch Application**
   - Click **Start Menu** → **KanoonVault**
   - **Expected:** Application launches immediately
   - [ ] NO welcome/setup screens shown
   - [ ] Dashboard appears directly
   - [ ] Browser opens to main app (not setup wizard)

2. **Verify Data**
   - [ ] Any documents uploaded in previous launches still present
   - [ ] Cases/data intact
   - [ ] API key still works (no re-prompt)

3. **Verify Configuration**
   ```powershell
   # Check config file
   $configPath = "$env:APPDATA\Roaming\.kanoonvault\storage-config.json"
   Get-Content $configPath | ConvertFrom-Json | Format-Table

   # Should show:
   # storage_dir: C:\Users\<Name>\AppData\Local\KanoonVault
   # first_run_complete: true
   # [timestamps]
   ```
   - [ ] Config file exists and is readable
   - [ ] `first_run_complete` is `true`
   - [ ] Storage path is correct

4. **Verify API Key Storage**
   - [ ] Application still works (API key accessible)
   - [ ] No error about missing credentials
   - [ ] (Key stored in Windows Credential Manager, not visible in file)

- [ ] Second launch skips setup wizard
- [ ] Data persists across sessions
- [ ] Configuration saved correctly

### Test 3.8: Data Migration (Optional Advanced Test)

**Prerequisites:** Have some data in the application

1. **Change Storage Location**
   - Manual way: Edit config file to point to new location
   - Or wait for settings UI (future feature)

2. **Trigger Migration**
   - Close application
   - Edit: `%APPDATA%\Roaming\.kanoonvault\storage-config.json`
   - Change `storage_dir` to new location (e.g., `D:\KanoonVault\`)
   - Relaunch application

3. **Verify Migration**
   - [ ] New location has all files
   - [ ] Backup created at old location
   - [ ] Vector DB still works (search functional)
   - [ ] No data corruption

- [ ] Migration works correctly
- [ ] Backup created
- [ ] Data integrity maintained

### Test 3.9: Uninstall & Reinstall (Optional Validation)

1. **Uninstall Application**
   - Open **Control Panel** → **Programs** → **Uninstall a program**
   - Find **KanoonVault**
   - Click **Uninstall**
   - [ ] Inno Setup uninstaller runs
   - [ ] Confirms removal from Program Files
   - [ ] Completes successfully

2. **Verify Data Preserved** (IMPORTANT!)
   - [ ] `C:\Users\<Name>\AppData\Local\KanoonVault\` still exists
   - [ ] All documents, database, embeddings still there
   - [ ] Config file still exists

3. **Reinstall Application**
   - Run `KanoonVault-Setup.exe` again
   - **Expected:** 
     - Installer runs normally
     - On launch: NO setup wizard (skipped because first_run_complete = true)
     - Dashboard loads with all data present
     - API key works (stored in Credential Manager persists)

- [ ] Uninstall doesn't delete user data
- [ ] Reinstall doesn't lose setup status
- [ ] Data and credentials survive reinstall

---

## Phase 4: GitHub Release (15-20 minutes)

### Step 4.1: Prepare Release Files

```powershell
# Verify installer and checksum exist
Get-Item "installer-output\KanoonVault-Setup.exe"
Get-Content "installer-output\CHECKSUM.txt"

# Create release notes (copy to clipboard)
@"
# KanoonVault Windows v1.0.0

One-click Windows installation for KanoonVault - manage legal cases and documents with local-first architecture.

## What's Included
- ✅ All dependencies bundled (no Python installation required)
- ✅ FastAPI backend server
- ✅ Full OCR capabilities (PaddleOCR, PyMuPDF, Tesseract)
- ✅ Semantic search with ChromaDB
- ✅ Secure API key management
- ✅ Local-first architecture (data on your machine)

## Installation
1. Download KanoonVault-Setup.exe
2. Run installer
3. Follow first-launch wizard:
   - Welcome → overview
   - Storage location → choose where your files live
   - API key → enable AI features (optional)
4. That's it! App launches automatically

## System Requirements
- Windows 10 or later (64-bit)
- 4 GB RAM (8 GB recommended)
- 2 GB disk space
- Internet connection (for AI features)

## First Launch
On first run, the app will:
1. Show welcome screen describing features
2. Ask where to store your legal documents (default: C:\Users\<Name>\AppData\Local\KanoonVault)
3. Request OpenRouter API key for AI features (optional, can skip)
4. Launch main dashboard

## Data Storage
- Your files stay on YOUR machine (C:\Users\<Name>\AppData\Local\KanoonVault)
- Application installed separately (C:\Program Files\KanoonVault)
- Database: SQLite3 in local storage
- Embeddings: ChromaDB in local storage
- No cloud sync by default

## Troubleshooting
- App won't start? Run as Administrator
- Need help? Check WINDOWS_BUILD_GUIDE.md in the repository
- Issues? Create a GitHub issue with:
  - Windows version
  - Python version (visible in About)
  - Error messages

## Build Details
- Built with: PyInstaller 6.1.0, Inno Setup 6.2.4
- Python runtime: 3.10.20 (bundled)
- Release date: August 20, 2026
- SHA256: [FROM CHECKSUM.txt]
"@ | Set-Clipboard
```

### Step 4.2: Create GitHub Release

**Browser Method (Recommended):**

1. **Go to GitHub**
   ```
   https://github.com/AmeerHussain-ops/KanoonVault/releases/new
   ```

2. **Fill Release Form**
   - **Choose a tag**: Type `v1.0.0` (exact - don't use existing)
   - **Release title**: `KanoonVault Windows v1.0.0`
   - **Description**: Paste the release notes you copied above

3. **Attach Installer File**
   - Scroll down to "Attach binaries by dropping them here, or selecting them"
   - Drag `installer-output\KanoonVault-Setup.exe` into the area
   - **Wait** for upload to complete (~2-5 minutes, file is large)
   - [ ] See progress bar complete
   - [ ] File appears in attachments list

4. **Publish Release**
   - Review all information
   - Click **"Publish release"** (not "Save as draft")
   - **Wait** for GitHub to process
   - [ ] See confirmation: "Release v1.0.0 published"

- [ ] Release created with version tag
- [ ] Installer file uploaded successfully
- [ ] Release is public and downloadable

### Step 4.3: Verify Release

```powershell
# Copy the release link (visible after publishing)
# Should be: https://github.com/AmeerHussain-ops/KanoonVault/releases/tag/v1.0.0

# Or go to latest releases:
Start-Process "https://github.com/AmeerHussain-ops/KanoonVault/releases/latest"
```

**Verification:**
1. On GitHub Release page:
   - [ ] Release appears with version `v1.0.0`
   - [ ] Release notes display correctly
   - [ ] Installer file is visible and downloadable
   - [ ] File size matches (~500-700 MB)
   - [ ] Download works (test on clean machine)

### Step 4.4: Test Release Download

1. **On a different computer (or clean VM):**
   - Go to: `https://github.com/AmeerHussain-ops/KanoonVault/releases/latest`
   - Click **"KanoonVault-Setup.exe"** in assets
   - **Download** completes successfully
   - [ ] File size matches original

2. **Verify Checksum** (optional but recommended)
   ```powershell
   # On the machine where you downloaded
   $downloadPath = ".\KanoonVault-Setup.exe"
   $hash = certutil -hashfile $downloadPath SHA256 | Select-Object -Index 1
   
   # Compare with original checksum from CHECKSUM.txt
   # Should match exactly
   ```
   - [ ] Checksums match (file integrity verified)

3. **Run Downloaded Installer**
   - [ ] Installer runs without issues
   - [ ] Installation completes
   - [ ] App launches and works
   - [ ] No errors or warnings

- [ ] Release download succeeds
- [ ] File integrity verified
- [ ] Clean installation works from release

---

## Phase 5: Documentation & Cleanup

### Step 5.1: Update Repository README

In the main `README.md`, add a Windows section:

```markdown
## Installation

### Windows (Recommended for most users)

**Download and run the installer** - no technical knowledge required!

1. Download latest installer: [KanoonVault-Setup.exe](https://github.com/AmeerHussain-ops/KanoonVault/releases/latest)
2. Double-click to run installer
3. Follow the wizard:
   - Welcome screen
   - Choose storage location (default: C:\Users\YourName\AppData\Local\KanoonVault)
   - Enter OpenRouter API key (optional, needed for AI features)
4. Done! Application launches automatically

**System Requirements:**
- Windows 10 or later (64-bit)
- 4 GB RAM
- 2 GB disk space
- Internet connection (for AI features)

**Data Storage:**
- Your legal documents stored locally on your machine
- Database and embeddings stay on your PC
- No cloud sync by default

### Linux/Mac (Development)

[existing instructions...]
```

### Step 5.2: Verify All Documentation

- [ ] `NEXT_STEPS.md` - Complete
- [ ] `BUILD_AND_TEST_GUIDE.md` - Complete
- [ ] `TESTING_QUICK_REFERENCE.md` - Complete  
- [ ] `WINDOWS_BUILD_GUIDE.md` - Complete
- [ ] `WINDOWS_PACKAGING_SUMMARY.md` - Complete
- [ ] `API_KEY_SETUP.md` - Complete
- [ ] `FIRST_LAUNCH_FLOW.md` - Complete

### Step 5.3: Cleanup Build Artifacts (Optional)

```powershell
# Remove to save disk space (keep installer-output\KanoonVault-Setup.exe)
Remove-Item "dist" -Recurse -Force      # ~1 GB
Remove-Item "build" -Recurse -Force     # ~500 MB

# Keep these for next version builds:
# - launcher.py
# - kanoonvault.spec
# - kanoonvault-installer.iss
# - build_windows_package.bat
# - requirements.txt
```

- [ ] Build artifacts cleaned up (optional)
- [ ] Installer preserved in `installer-output/`
- [ ] Repository remains on `feature/windows-packaging` branch

### Step 5.4: Create Pull Request (Optional, for code review)

If desired, create PR from `feature/windows-packaging` → `main`:

```powershell
# Push feature branch (already done)
git push origin feature/windows-packaging

# Then on GitHub:
# 1. Go to repository
# 2. Click "Compare & pull request"
# 3. Set: base=main, compare=feature/windows-packaging
# 4. Add description: "Production-ready Windows packaging with first-launch setup"
# 5. Create pull request
```

- [ ] PR created (optional)
- [ ] Linked to release for reference

---

## Troubleshooting

### Build Issues

| Problem | Solution |
|---------|----------|
| "Python 3.10 not found" | `python --version` should show 3.10.x. Reinstall if needed. |
| PyInstaller fails | Run: `pip install --upgrade pyinstaller==6.1.0` |
| Build takes >60 min | Normal for first build (downloading all dependencies). Subsequent builds faster. |
| "Module not found" error | Run: `pip install -r requirements.txt` again |
| Inno Setup not found | Install from: https://jrsoftware.org/isdl.php to default location |
| .exe file too large (>1GB) | This is normal - includes all OCR models and Python runtime |

### Installer Issues

| Problem | Solution |
|---------|----------|
| Installer won't run | Try running as Administrator |
| "Not a valid Win32 application" | Reinstall Python 3.10 and rebuild |
| Wrong Python version bundled | Verify `python --version` before building |

### First-Launch Issues

| Problem | Solution |
|---------|----------|
| Setup wizard appears twice | Delete `%APPDATA%\Roaming\.kanoonvault\storage-config.json` |
| API key test fails with valid key | Check internet connection. OpenRouter might be down. |
| "Test Connection" takes 30+ seconds | Normal if network is slow. API response can take time. |
| App won't start at all | Run `C:\Program Files\KanoonVault\launcher.exe` as Administrator |

### GitHub Release Issues

| Problem | Solution |
|---------|----------|
| Upload hangs | Large file (500-700 MB). Can take 5-10 minutes. Don't close browser. |
| "Release already exists" | Use different tag: `v1.0.1`, `v1.0.0-rc1`, etc. |
| Download is corrupted | Verify checksum. Re-download if needed. |

---

## Success Checklist ✅

### Build Phase
- [ ] Python 3.10.20 verified
- [ ] All dependencies installed
- [ ] Build script completed without errors
- [ ] Installer file created (~500-700 MB)
- [ ] Checksum generated

### Testing Phase
- [ ] Installer runs successfully
- [ ] Welcome screen displays
- [ ] Storage selection works (default and custom)
- [ ] API key validation works correctly
- [ ] Main application launches
- [ ] Documents can be uploaded
- [ ] OCR/search functionality works
- [ ] App closes cleanly
- [ ] Data persists on relaunch
- [ ] Second launch skips setup
- [ ] Uninstall preserves user data
- [ ] Reinstall works with existing data

### Release Phase
- [ ] GitHub release created with tag `v1.0.0`
- [ ] Release notes posted
- [ ] Installer uploaded to release
- [ ] Download verified from GitHub
- [ ] Checksum verified
- [ ] Clean installation tested
- [ ] README updated with download link

### Documentation
- [ ] All guides present and link correctly
- [ ] User instructions clear
- [ ] Troubleshooting section helpful
- [ ] Release notes descriptive

---

## Final Validation

Run this script to verify everything:

```powershell
# Verify all files present
$files = @(
    'installer-output\KanoonVault-Setup.exe',
    'installer-output\CHECKSUM.txt',
    'requirements.txt',
    'launcher.py',
    'WINDOWS_BUILD_GUIDE.md',
    'NEXT_STEPS.md'
)

Write-Host "File Verification:" -ForegroundColor Cyan
foreach ($file in $files) {
    if (Test-Path $file) { 
        $size = (Get-Item $file).Length
        Write-Host "✅ $file ($(if($size) { "$($size) bytes" } else { "Present" }))"
    } else { 
        Write-Host "❌ MISSING: $file"
    }
}

Write-Host ""
Write-Host "Installer Details:" -ForegroundColor Cyan
$installer = Get-Item "installer-output\KanoonVault-Setup.exe"
Write-Host "Size: $([math]::Round($installer.Length / 1MB)) MB"
Write-Host "Created: $($installer.CreationTime)"

Write-Host ""
Write-Host "GitHub Release:" -ForegroundColor Cyan
Write-Host "v1.0.0 ready to publish"
Write-Host "https://github.com/AmeerHussain-ops/KanoonVault/releases/latest"
```

---

## Timeline Summary

| Phase | Time | Status |
|-------|------|--------|
| Setup | 5 min | ⏳ User |
| Build | 30-45 min | ⏳ Automated |
| Testing | 1-2 hours | ⏳ User |
| Release | 15-20 min | ⏳ User |
| **Total** | **2-3 hours** | |

---

**🚀 Ready to ship KanoonVault for Windows!**

All code is production-ready. Follow this checklist to build, test, and release.

Questions? Check the documentation files:
- Quick Reference: `TESTING_QUICK_REFERENCE.md`
- Complete Guide: `BUILD_AND_TEST_GUIDE.md`
- Build Details: `WINDOWS_BUILD_GUIDE.md`
