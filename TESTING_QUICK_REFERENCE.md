# KanoonVault Windows Testing Quick Reference

## Build in 4 Steps

```powershell
# 1. Ensure you're on feature/windows-packaging branch
git checkout feature/windows-packaging
git pull origin feature/windows-packaging

# 2. Verify Python 3.10 & requirements
python --version  # Should show 3.10.x
pip install -r requirements.txt

# 3. Run build script
.\build_windows_package.bat

# 4. Verify output
Get-Item "installer-output\KanoonVault-Setup.exe"  # ~500-700 MB
```

---

## Test Workflow (Copy-Paste Friendly)

### Test 1: Fresh Install
```
Action: Double-click KanoonVault-Setup.exe
Expected: Inno Setup wizard → Next → Next → Next → Install
Result: Application appears in Start Menu
Verify: C:\Program Files\KanoonVault\ contains launcher.exe
```

### Test 2: First-Launch Wizard
```
Screen 1 - Welcome
  ✅ See KanoonVault logo and features
  ✅ Click "Get Started"

Screen 2 - Storage Location
  ✅ Shows C:\Users\<Name>\AppData\Local\KanoonVault
  ✅ Shows available disk space
  ✅ Click "Continue" (or test "Change Location" first)

Screen 3 - API Key Setup
  ✅ Paste OpenRouter API key
  ✅ Click "Test Connection"
  ✅ Wait for green "✓ API key valid"
  ✅ Click "Continue"
  ✅ Browser opens to 127.0.0.1:8000
```

### Test 3: Main Application
```
Dashboard loads with:
  ✅ Case management interface
  ✅ Document upload button
  ✅ OCR functionality
  ✅ Search/embedding features
```

### Test 4: Data Persistence
```
1. Close app completely
2. Start → KanoonVault
3. Verified:
   ✅ No setup wizard (first-run marked complete)
   ✅ API key works (not re-prompted)
   ✅ All uploaded documents still present
   ✅ Cases and data intact
```

### Test 5: Storage Directory Check
```powershell
# Check storage config exists
$config = Get-Content "$env:APPDATA\Roaming\.kanoonvault\storage-config.json" -Raw
$json = $config | ConvertFrom-Json

Write-Host "Storage location: $($json.storage_dir)"
Write-Host "First run complete: $($json.first_run_complete)"
Write-Host "API key set: $(if($json.api_key_set) { 'Yes' } else { 'No' })"

# List storage subdirectories
Get-ChildItem -Path $json.storage_dir | Select-Object Name, FullName
```

---

## GitHub Release Quick Steps

1. **Get Installer Size & Checksum**
   ```powershell
   $file = Get-Item "installer-output\KanoonVault-Setup.exe"
   Write-Host "Size: $($file.Length) bytes (~$([math]::Round($file.Length/1MB))MB)"
   ```

2. **Go to GitHub**
   - https://github.com/AmeerHussain-ops/KanoonVault/releases/new

3. **Fill Release Form**
   - Tag: `v1.0.0` (or next version)
   - Title: `KanoonVault Windows v1.0.0`
   - Description: [Copy from BUILD_AND_TEST_GUIDE.md Release Description]
   - Attach file: `KanoonVault-Setup.exe`

4. **Publish**
   - Click "Publish release"
   - Share link: https://github.com/AmeerHussain-ops/KanoonVault/releases

---

## Common Issues & Fixes

| Problem | Fix |
|---------|-----|
| Setup wizard appears twice | Delete `%APPDATA%\Roaming\.kanoonvault\storage-config.json` |
| "Test Connection" fails but key is valid | Check internet, verify OpenRouter status at https://status.openrouter.ai/ |
| App won't start after install | Run `C:\Program Files\KanoonVault\launcher.exe` as Administrator |
| Can't change storage location | Ensure target folder exists and you have write permissions |
| Port 8000 already in use | Close other applications using port 8000, or edit launcher.py PORT setting |

---

## Files to Keep for Reference

For release documentation, keep these files accessible:
- `WINDOWS_BUILD_GUIDE.md` - Comprehensive build guide
- `WINDOWS_PACKAGING_SUMMARY.md` - Architecture overview  
- `FIRST_LAUNCH_FLOW.md` - UX flow documentation
- `API_KEY_SETUP.md` - API key system details
- `BUILD_AND_TEST_GUIDE.md` - This complete guide
