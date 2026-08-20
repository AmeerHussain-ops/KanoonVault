# KanoonVault GitHub Release Guide

## Prerequisites ⚠️

Before releasing on GitHub, you MUST have:

1. **Built the installer** on Windows with Python 3.10.20
   - Creates: `KanoonVault-Setup.exe` (~500-700 MB)
   - Location: `installer-output/KanoonVault-Setup.exe`

2. **Generated checksum** for file integrity
   - Creates: `installer-output/CHECKSUM.txt`
   - Command: `certutil -hashfile installer-output\KanoonVault-Setup.exe SHA256`

3. **GitHub repository access**
   - You own or have push access to: https://github.com/AmeerHussain-ops/KanoonVault

4. **Git on your machine**
   - Can push tags and commits

---

## Step 1: Build the Installer (if not done yet)

**On a Windows machine with Python 3.10.20:**

```powershell
# Get the latest code
cd F:\KanoonVault
git checkout feature/windows-packaging
git pull origin feature/windows-packaging

# Build the installer
pip install -r requirements.txt
pip install pyinstaller==6.1.0
.\build_windows_package.bat

# Verify installer created
Get-Item "installer-output\KanoonVault-Setup.exe"  # Should show ~500-700 MB
```

**If build succeeds, you'll see:**
```
✅ Build Complete!
📦 Installer: installer-output\KanoonVault-Setup.exe
📊 Size: ~567 MB
✅ Ready for distribution!
```

---

## Step 2: Generate Checksum

```powershell
# Generate SHA256 checksum
certutil -hashfile "installer-output\KanoonVault-Setup.exe" SHA256 | Tee-Object -FilePath "installer-output\CHECKSUM.txt"

# View the checksum
Get-Content "installer-output\CHECKSUM.txt"

# Should output something like:
# SHA256 hash of installer-output\KanoonVault-Setup.exe:
# a3f5b2c8d1e4f6g9h2j5k8l1m4n7q0r3s6t9u2v5w8x1y4z7a0b3c6d9e2f5
```

Save this checksum - you'll need it for the release notes.

---

## Step 3: Commit and Tag the Release

```powershell
# Add any final changes (if needed)
git add -A

# Commit the release preparation
git commit -m "chore: prepare v1.0.0 release

- Windows installer: KanoonVault-Setup.exe
- Include checksum for integrity verification
- All testing complete and documented"

# Create release tag
git tag -a v1.0.0 -m "KanoonVault Windows v1.0.0

Release includes complete Windows packaging with:
- One-click installer (no Python required)
- First-launch setup wizard
- Secure API key management
- Local-first architecture (data on your machine)

Download: KanoonVault-Setup.exe (~500-700 MB)"

# Push commits and tag to GitHub
git push origin feature/windows-packaging
git push origin v1.0.0
```

**Verify tag was created:**
```powershell
git tag -l v1.0.0
git show v1.0.0
```

---

## Step 4: Create GitHub Release

### Option A: GitHub Web UI (Recommended - No Special Tools Needed)

1. **Open GitHub in Browser**
   ```
   https://github.com/AmeerHussain-ops/KanoonVault/releases
   ```

2. **Click "Draft a new release"**
   - Button is usually green/blue

3. **Fill in Release Form**

   **Choose a tag:**
   - Type or select: `v1.0.0`
   - (Must match the tag you created with git)

   **Release title:**
   ```
   KanoonVault Windows v1.0.0
   ```

   **Description:**
   Copy and paste the template below (customize as needed)

4. **Upload Installer File**
   - Scroll down to "Attach binaries by dropping them here..."
   - Drag `KanoonVault-Setup.exe` into the area
   - **Wait** for upload (5-10 min, large file)
   - Should see file appear in "Assets"

5. **Publish Release**
   - Click **"Publish release"** (not "Save as draft")
   - GitHub creates the release tag+commit if not done yet
   - Release is now public and downloadable

### Option B: GitHub CLI (If Installed)

```powershell
# Install GitHub CLI (if needed)
# choco install gh  (using Chocolatey)
# or download: https://cli.github.com/

# Login to GitHub
gh auth login

# Create release with file
gh release create v1.0.0 `
  --title "KanoonVault Windows v1.0.0" `
  --notes-file RELEASE_NOTES.md `
  "installer-output/KanoonVault-Setup.exe"
```

### Option C: PowerShell Script

```powershell
# Save as: create-release.ps1

param(
    [string]$Version = "1.0.0",
    [string]$Title = "KanoonVault Windows v1.0.0",
    [string]$InstallerPath = "installer-output\KanoonVault-Setup.exe"
)

# Verify installer exists
if (-not (Test-Path $InstallerPath)) {
    Write-Error "Installer not found: $InstallerPath"
    exit 1
}

# Get checksum
$checksum = (Get-Content "installer-output\CHECKSUM.txt" | Select-String "^[a-f0-9]{64}")[0].ToString()

# Create release notes
$releaseNotes = @"
# KanoonVault Windows v$Version

One-click Windows installation for KanoonVault - manage legal cases with local-first architecture.

## Download

**File:** KanoonVault-Setup.exe (~500-700 MB)
**Checksum (SHA256):** $checksum

## What's Included

- ✅ Complete bundled application (no Python installation needed)
- ✅ FastAPI backend server
- ✅ Full OCR capabilities (PaddleOCR, PyMuPDF, Tesseract)
- ✅ Semantic search with ChromaDB vector DB
- ✅ Secure API key management (Windows Credential Manager)
- ✅ Local-first architecture (your data stays on your machine)
- ✅ First-launch setup wizard

## Quick Installation

1. Download **KanoonVault-Setup.exe**
2. Run installer (double-click)
3. Follow setup wizard:
   - Welcome screen
   - Choose storage location
   - Enter OpenRouter API key (optional)
4. Start managing your legal documents!

## System Requirements

- Windows 10 or later (64-bit)
- 4 GB RAM minimum (8 GB recommended)
- 2 GB free disk space
- Internet connection (for AI features)

## First-Launch Experience

On first run:
1. **Welcome Screen** - Overview of features
2. **Storage Location** - Where to store your documents (default: C:\Users\YourName\AppData\Local\KanoonVault)
3. **API Key Setup** - Enter OpenRouter API key for AI features (optional)
4. **Dashboard** - Ready to upload and manage documents

Your files are stored locally on your machine - never uploaded to cloud.

## Features

- **Case Management** - Organize documents by legal case
- **Document Upload** - Support for PDF, Word, images, more
- **OCR** - Extract text from scanned documents
- **Full-Text Search** - Instant search across all documents
- **Vector Search** - Semantic search with AI (requires API key)
- **Local Storage** - All data on your machine, encrypted
- **Secure Credentials** - API keys stored in Windows Credential Manager

## Data Privacy

✅ Your legal documents **stay on YOUR computer**
✅ Local database (SQLite3) - no cloud sync
✅ Vector embeddings (ChromaDB) - local only
✅ No telemetry or usage tracking
✅ Source code open for review

Optional API calls:
- OpenRouter (only for AI features, with your API key)
- No other external services

## Getting Started

1. **Installation** - See INSTALL_GUIDE.md in repository
2. **First Launch** - See FIRST_LAUNCH_FLOW.md
3. **Troubleshooting** - See BUILD_AND_TEST_GUIDE.md
4. **Architecture** - See WINDOWS_PACKAGING_SUMMARY.md

## Release Information

- **Built with:** PyInstaller 6.1.0, Inno Setup 6.2.4
- **Python Runtime:** 3.10.20 (bundled)
- **Release Date:** August 20, 2026
- **Installation Size:** ~700 MB
- **Runtime Memory:** 500-1000 MB

## Support & Issues

- GitHub Issues: Report bugs
- GitHub Discussions: Ask questions
- Source code: Open and reviewable

## What's New in v1.0.0

Initial Windows Release:
- ✨ Complete Windows packaging with installer
- ✨ One-click installation (no Python required)
- ✨ First-launch wizard with setup flow
- ✨ Secure credential storage
- ✨ Native folder browser integration
- ✨ Data migration support
- ✨ Comprehensive documentation

## Verification

**To verify file integrity:**
```
certutil -hashfile KanoonVault-Setup.exe SHA256
```
Compare the output with the checksum above.

## Installation Help

Having issues? Check out:
- INSTALL_GUIDE.md - Complete installation guide
- INSTALL_QUICK_START.md - Quick visual reference
- Troubleshooting section in INSTALL_GUIDE.md

## License

License: (Specify your license - see repository)

---

**Ready to manage your legal documents locally?**

Download KanoonVault-Setup.exe and get started in 5 minutes!
"@

Write-Host "Release Notes:" -ForegroundColor Cyan
Write-Host $releaseNotes

# Display commands to run
Write-Host ""
Write-Host "To create release on GitHub:" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Go to: https://github.com/AmeerHussain-ops/KanoonVault/releases/new"
Write-Host "2. Tag: v$Version"
Write-Host "3. Title: $Title"
Write-Host "4. Description: [Paste above release notes]"
Write-Host "5. Attach file: $InstallerPath"
Write-Host "6. Click 'Publish release'"
```

Run it:
```powershell
.\create-release.ps1
```

---

## Release Notes Template

Use this template for your GitHub Release:

```markdown
# KanoonVault Windows v1.0.0

One-click Windows installation for KanoonVault - manage legal cases with local-first architecture.

## Download

**KanoonVault-Setup.exe** (~500-700 MB)

**Checksum (SHA256):**
[PASTE YOUR CHECKSUM HERE]

## What's New

✨ **Windows Installer** - Complete one-click installation
✨ **First-Launch Wizard** - Setup storage location and API key
✨ **Secure Credentials** - API keys stored in Windows Credential Manager
✨ **Local-First** - All your data stays on your machine
✨ **No Python Required** - Everything bundled
✨ **OCR Included** - Complete document processing

## Installation

1. Download `KanoonVault-Setup.exe`
2. Double-click to run
3. Follow setup wizard (5 minutes total)
4. Start managing legal documents!

## System Requirements

- Windows 10+ (64-bit)
- 4 GB RAM
- 2 GB disk space
- Internet (for optional AI features)

## Features

- 📋 Case management
- 📁 Document upload & storage
- 🔍 Full-text search
- 🧠 AI analysis (optional with API key)
- 🔒 Local encryption
- 🚀 One-click installation

## Documentation

- Installation: [INSTALL_GUIDE.md](INSTALL_GUIDE.md)
- Quick Start: [INSTALL_QUICK_START.md](INSTALL_QUICK_START.md)
- Build Guide: [WINDOWS_BUILD_GUIDE.md](WINDOWS_BUILD_GUIDE.md)
- Architecture: [WINDOWS_PACKAGING_SUMMARY.md](WINDOWS_PACKAGING_SUMMARY.md)

## Support

- Issues: [GitHub Issues](https://github.com/AmeerHussain-ops/KanoonVault/issues)
- Questions: [GitHub Discussions](https://github.com/AmeerHussain-ops/KanoonVault/discussions)

---

**Ready to manage your legal documents locally? Download and install now!**
```

---

## Step 5: Verify Release Created

1. **Go to releases page:**
   ```
   https://github.com/AmeerHussain-ops/KanoonVault/releases
   ```

2. **Verify your release appears:**
   - ✅ Version tag `v1.0.0`
   - ✅ Release title shown
   - ✅ Description visible
   - ✅ File appears in Assets
   - ✅ File size shows (~500-700 MB)
   - ✅ Download link works

3. **Test download:**
   - Click download link
   - File downloads to local machine
   - Verify file size matches

4. **Verify checksum (optional but recommended):**
   ```powershell
   # After download
   certutil -hashfile .\KanoonVault-Setup.exe SHA256
   
   # Compare with checksum from release page
   # Should match exactly
   ```

---

## Step 6: Update README

In your main `README.md`, add a Windows section:

```markdown
## Quick Start - Windows

**Easiest Method: Download Installer**

1. Go to [Latest Release](https://github.com/AmeerHussain-ops/KanoonVault/releases/latest)
2. Download `KanoonVault-Setup.exe`
3. Double-click to install
4. Follow the setup wizard
5. Start managing your cases!

**Requirements:** Windows 10+, 4GB RAM, 2GB disk space

**First Launch:** Setup wizard guides you through storage location and optional API key configuration.

For detailed installation help, see [INSTALL_GUIDE.md](INSTALL_GUIDE.md).

## Linux/Mac (Development)

[existing instructions...]
```

---

## Step 7: Announce Release

Share your release:

### On GitHub
- ✅ Release page: https://github.com/AmeerHussain-ops/KanoonVault/releases/latest
- ✅ Create a GitHub Discussion to announce it

### Update README.md
- ✅ Add download link
- ✅ Update installation instructions
- ✅ Link to release notes

### Optional: Create Pull Request
- If `feature/windows-packaging` isn't merged to `main` yet
- Create PR to merge the feature branch
- Link the release in PR description

---

## Post-Release Checklist

- [ ] Installer built and tested on Windows
- [ ] Checksum generated and verified
- [ ] Git tag created (`git tag v1.0.0`)
- [ ] Tag pushed to GitHub (`git push origin v1.0.0`)
- [ ] GitHub Release created
- [ ] Installer file uploaded to release
- [ ] Release notes posted
- [ ] Checksum in release notes
- [ ] README updated with download link
- [ ] Release tested (download and install)
- [ ] Checksum verified on fresh download
- [ ] GitHub Release is marked as "Latest"

---

## Release URL

After publishing, share this:
```
https://github.com/AmeerHussain-ops/KanoonVault/releases/tag/v1.0.0
```

Or for latest release:
```
https://github.com/AmeerHussain-ops/KanoonVault/releases/latest
```

---

## Next Release (v1.0.1, etc.)

For future updates:

```powershell
# Make code changes
git add -A
git commit -m "feat: add new feature X"

# Build new installer with Python 3.10
.\build_windows_package.bat

# Tag next version
git tag -a v1.0.1 -m "Minor update: fix issue X"
git push origin v1.0.1

# Create new GitHub Release
# Follow steps above with new version number
```

---

## Troubleshooting Release Issues

| Issue | Solution |
|-------|----------|
| "Release already exists" | Use different tag name (v1.0.1, v1.0.0-rc1, etc.) |
| File upload hangs | Normal for large files. Can take 5-10 minutes. Don't close browser. |
| "Authentication failed" | Ensure GitHub auth is set up: `gh auth login` |
| Release is draft, not published | Click "Publish release" not "Save as draft" |
| Can't download from release | Refresh page, check file was uploaded completely |

---

## Complete Release Commands Cheat Sheet

```powershell
# 1. Build (Python 3.10 machine)
.\build_windows_package.bat

# 2. Generate checksum
certutil -hashfile "installer-output\KanoonVault-Setup.exe" SHA256 | Tee-Object "installer-output\CHECKSUM.txt"

# 3. Create tag
git tag -a v1.0.0 -m "KanoonVault Windows v1.0.0"

# 4. Push tag
git push origin v1.0.0

# 5. Create GitHub Release (manual via web UI)
# Go to: https://github.com/AmeerHussain-ops/KanoonVault/releases/new
# Fill form, upload installer, publish

# 6. Verify
# Go to: https://github.com/AmeerHussain-ops/KanoonVault/releases/latest
# Test download
```

---

**🚀 Ready to release KanoonVault for Windows!**

Follow the steps above, and your release will be live!

**Questions?** Check the documentation in the repository.
