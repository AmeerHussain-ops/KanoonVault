# KanoonVault Windows Installation Guide

## For End Users - Simple Installation

### Step 1: Download

1. Go to: **https://github.com/AmeerHussain-ops/KanoonVault/releases**
2. Find the latest release (look for green tag like `v1.0.0`)
3. Click **KanoonVault-Setup.exe** to download
4. File size: ~500-700 MB (be patient, large file!)

### Step 2: Run Installer

1. Find downloaded file (usually in `Downloads` folder)
2. Double-click **KanoonVault-Setup.exe**
3. Windows may ask "Do you want to allow this app to make changes?" → Click **Yes**

### Step 3: Follow Setup Wizard

The installer will show several screens:

**Screen 1: Welcome**
- Read about KanoonVault
- Click **Next**

**Screen 2: License Agreement**
- Read and accept the license
- Click **I Agree**

**Screen 3: Choose Installation Location**
- Shows: `C:\Program Files\KanoonVault\`
- This is fine - click **Next**
- (Advanced: you can change it, but default is recommended)

**Screen 4: Additional Tasks**
- Checkboxes appear for:
  - ☑ Create Start Menu shortcuts (keep checked)
  - ☑ Create Desktop shortcut (optional)
- Click **Next**

**Screen 5: Ready to Install**
- Review the information
- Click **Install**
- **Wait 2-3 minutes** while it unpacks files

**Screen 6: Installation Complete**
- Click **Finish**
- ☑ "Launch KanoonVault" checkbox is checked (optional)
- App will start automatically if checkbox is checked

---

## First Time You Run KanoonVault

After installation completes, the app launches automatically and shows **First-Launch Setup**:

### Screen 1: Welcome Screen
- See KanoonVault logo and features
- Read about the app capabilities
- Click blue **"Get Started"** button

### Screen 2: Choose Where to Store Your Files

**Where will my files be stored?**
- Default location: `C:\Users\YourName\AppData\Local\KanoonVault`
  - This is on your computer
  - Your files stay private on your machine
  - You can change this location if desired

**Two options:**

**Option A: Use Default Location (Recommended)**
1. See the default path displayed
2. Click **"Continue"** button
3. App initializes your storage
4. Proceeds to next screen

**Option B: Choose Custom Location (Advanced)**
1. Click **"Change Location"** button
2. Windows folder browser opens
3. Navigate to desired folder (e.g., external drive like `D:\MyLegalFiles\`)
4. Click **OK**
5. See new path displayed
6. Click **"Continue"**
7. App initializes new location

**Note**: All your legal documents, cases, and data will be stored in this location.

### Screen 3: Enter API Key

**What's an API Key?**
- Enables AI features (summarization, analysis, insights)
- You get it from OpenRouter (free to sign up)
- **Optional** - app works without it (but AI features disabled)

**Steps:**

**If you HAVE an API key:**
1. Copy your OpenRouter API key
2. Paste into the password field
3. Click blue **"Test Connection"** button
4. **Wait 5-10 seconds** for validation
5. If successful: Green checkmark ✓ appears
6. Click blue **"Continue"** button
7. App launches!

**If you DON'T have an API key:**
1. Skip this step by closing the screen (optional)
   - Or come back to settings later
2. App launches with basic features only
3. Can add API key later in settings

**How to get a FREE API Key:**
1. Go to: https://openrouter.ai/
2. Click **"Sign Up"** (free account)
3. Verify email
4. Go to **Settings** → **API Keys**
5. Click **"Create Key"**
6. Copy the key (starts with `sk-...`)
7. Add some credits ($5 free trial available)
8. Use this key in KanoonVault setup

---

## After Installation

### First Launch
- Click **Start Menu** → Search for **KanoonVault**
- Or double-click **Desktop shortcut** if you created one
- App opens in your browser (127.0.0.1:8000)

### Next Launches
- No more setup screens
- App launches directly to dashboard
- Your files and settings are saved

### What You Can Do
- Upload legal documents (PDF, Word, images, etc.)
- Organize into cases
- Use OCR to extract text from images
- Search all documents
- (If API key added) Use AI to summarize and analyze documents

---

## Common Questions

### Q: Where are my files stored?
**A:** In the location you chose during setup (default: `C:\Users\YourName\AppData\Local\KanoonVault`). Your files never leave your computer.

### Q: Is there a cost?
**A:** 
- KanoonVault app: **Free**
- OpenRouter API key: **Free to start** ($5 credit), then pay as you use AI features

### Q: Can I move my files later?
**A:** Yes! You can change the storage location in Settings (feature coming soon). Your files can be migrated to a new location.

### Q: What if setup fails?
**A:** See troubleshooting section below.

### Q: Can I uninstall it?
**A:** Yes, use Windows Control Panel → Uninstall. Your files are preserved - they won't be deleted!

### Q: Does it need internet?
**A:** 
- Local features (file upload, OCR, search): No internet needed
- AI features (summarization, analysis): Requires internet for OpenRouter API

### Q: Is it safe?
**A:** 
- Your files stay on YOUR computer (not uploaded to cloud)
- API key stored securely in Windows Credential Manager
- Source code is open - you can review it on GitHub

---

## Troubleshooting

### Installer Won't Run

**"Windows protected your PC"**
- Click **"More info"**
- Click **"Run anyway"**
- (This is normal for unsigned installers)

**"Not a valid Win32 application"**
- Restart your computer
- Re-download the installer
- Contact support with error details

### App Won't Start After Installation

**Solution:**
1. Go to: `C:\Program Files\KanoonVault\`
2. Right-click **launcher.exe**
3. Select **"Run as administrator"**
4. Should open normally now

**Alternative:**
- Uninstall (Control Panel → Programs → Uninstall)
- Restart computer
- Reinstall from scratch

### First-Launch Setup Appears Multiple Times

**Solution:**
1. Close the app
2. Open File Explorer
3. Navigate to: `%APPDATA%\Roaming\.kanoonvault\`
   - Tip: Paste in address bar to go there quickly
4. Delete file: **storage-config.json**
5. Relaunch app
6. Setup wizard appears fresh

### API Key Test Fails (but key is valid)

**Check:**
1. Internet connection is working
2. Copy-paste key carefully (no extra spaces)
3. Key is for OpenRouter (not ChatGPT or Claude directly)
4. Account has credits remaining

**If still fails:**
1. Try different API key
2. Check OpenRouter status: https://status.openrouter.ai/
3. Contact support with exact error message

### "Port 8000 already in use"

**Solution:**
1. Close other applications using port 8000
2. Restart your computer
3. Relaunch KanoonVault

### Files Missing After Uninstall & Reinstall

**This shouldn't happen!** Your files are stored separately:
- App installed in: `C:\Program Files\KanoonVault\` (removed on uninstall)
- Your files in: `C:\Users\YourName\AppData\Local\KanoonVault\` (preserved!)

**Recovery:**
1. Navigate to: `C:\Users\YourName\AppData\Local\KanoonVault\`
2. Your documents folder should have all files
3. If missing, check backups or contact support

---

## System Requirements

Before installing, verify your computer has:

- **Windows Version**: Windows 10 or later (64-bit)
- **RAM**: 4 GB minimum (8 GB recommended)
- **Disk Space**: 2 GB free space (plus space for your documents)
- **Internet**: Needed for AI features, optional for local features
- **Administrator Access**: To install (but not required to run)

**Check your specs:**
1. Right-click **"This PC"** or **"My Computer"**
2. Click **"Properties"**
3. Look for "Windows 10" or "Windows 11"
4. Look for "64-bit" (should say this)

---

## Getting Help

### Documentation
- Full guide: See `WINDOWS_BUILD_GUIDE.md` in GitHub repository
- API setup: See `API_KEY_SETUP.md`
- First-launch flow: See `FIRST_LAUNCH_FLOW.md`

### Report Issues
- GitHub Issues: https://github.com/AmeerHussain-ops/KanoonVault/issues
- Include: Windows version, what you were doing, exact error message

### Contact
- (Support contact information to be added)

---

## Next Steps After Installation

1. **Upload Documents**
   - Drag & drop PDFs, images, Word docs
   - Or use "Upload" button

2. **Create Cases**
   - Organize documents by legal case
   - Add case details and notes

3. **Use OCR**
   - Convert scanned documents to searchable text
   - Extract text from images

4. **Search & Analyze**
   - Search all documents at once
   - (With API key) Use AI to summarize long documents

5. **Backup Your Files**
   - Files are in: `C:\Users\YourName\AppData\Local\KanoonVault\`
   - Regularly backup this folder to external drive

---

## Uninstallation (If Needed)

**To remove KanoonVault:**
1. Open **Control Panel**
2. Go to **Programs** → **Uninstall a program**
3. Find **KanoonVault** in the list
4. Click **Uninstall**
5. Follow wizard (your files will be preserved)

**Your files will NOT be deleted** - they're stored separately in `AppData\Local\KanoonVault\`

**To completely clean up:**
1. Uninstall as above
2. (Optional) Navigate to `C:\Users\YourName\AppData\Local\KanoonVault\`
3. Delete the folder if you don't want files anymore
4. Manual cleanup: `%APPDATA%\Roaming\.kanoonvault\` (config files)

---

## Tips for Best Experience

✅ **DO:**
- Keep your Windows updated
- Regularly backup your documents folder
- Verify API key before adding (to avoid failed tests)
- Create cases to organize documents by matter
- Use descriptive names for documents

❌ **DON'T:**
- Move `AppData` folder manually (use built-in migration from settings)
- Share API key with others (it's like a password)
- Delete files from storage folder directly (use the app)
- Assume internet isn't needed (some features require it)

---

## Quick Start Checklist

- [ ] Download `KanoonVault-Setup.exe` from GitHub Releases
- [ ] Run installer (double-click, click through)
- [ ] Wait for installation to complete (2-3 minutes)
- [ ] App launches automatically
- [ ] Choose storage location (use default or custom)
- [ ] Enter API key (optional but recommended)
- [ ] See dashboard appear
- [ ] Upload your first document
- [ ] Success! 🎉

---

**Installation complete! Start managing your legal documents locally on your machine.**

Need help? See the troubleshooting section above or create a GitHub issue.
