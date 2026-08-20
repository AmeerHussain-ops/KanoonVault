# KanoonVault First-Launch Flow

This document describes the complete first-launch experience for new users.

## Overview

When users open KanoonVault for the first time, they go through a guided setup process:

1. **Welcome Screen** — Introduction to KanoonVault
2. **Storage Location Selection** — Choose where to store data
3. **API Key Configuration** — Enter and validate OpenRouter API key
4. **Main Application** — Ready to use

## User Experience Flow

### Step 1: Welcome Screen

**URL**: `/static/welcome.html`

**What users see**:
```
                    ⚖️

            Welcome to KanoonVault
        Your private, local-first legal case vault.
        Your case data is stored on your computer.

    ✓ Upload and OCR legal documents
    ✓ Automatic case timeline extraction
    ✓ AI-powered case chat grounded in your documents
    ✓ No cloud storage—everything stays on your computer

                [ Get Started ]
```

**User action**: Click "Get Started"

**Backend**: None needed for this screen

### Step 2: Storage Location Selection

**URL**: `/static/storage-selection.html`

**What users see**:
```
        Choose Storage Location

    Where should KanoonVault store your data?
    This includes your cases, uploaded documents,
    search index, and application settings.

    Storage Location
    ┌─────────────────────────────────────────┐
    │ 📁 C:\Users\YourName\AppData\Local\...   │
    └─────────────────────────────────────────┘

    Storage Information:
    Available space:  450 GB free
    Existing data:    0 MB (0 files)

    You can change this later in Settings.
    Your existing documents will be preserved.

    [  📁 Change Location  ]  [  Continue  ]

    Default location: %APPDATA%\Local\KanoonVault
```

**Features**:

1. **Default Location**
   - Shows current or default storage path
   - Calculates available disk space
   - Displays any existing data

2. **Change Location Button**
   - Opens native folder browser dialog
   - Validates selected path
   - Shows confirmation dialog
   - Can cancel to keep current location

3. **Data Migration**
   - If user changes location and has existing data
   - Automatically migrates database, documents, and embeddings
   - Creates backup of new location if it has content
   - Logs migration results

**User actions**:
- Click "Change Location" (optional) → Select folder → Confirm
- Click "Continue" → Proceed to API key setup

**Backend endpoints**:

```
GET /api/setup/storage-location
  Returns: { default_storage_dir, first_run_complete }

GET /api/setup/storage-info?path=...
  Returns: { path, valid, disk_space, existing_data }

POST /api/setup/browse-storage-location
  Returns: { selected_path, cancelled, error }

POST /api/setup/confirm-storage-location
  Params: { storage_dir }
  Returns: { ok, storage_dir, migration, error }
```

### Step 3: API Key Configuration

**URL**: `/static/setup.html`

**What users see**:
```
              Set Up AI Assistance

    OpenRouter API Key
    ┌──────────────────────────────┐
    │ sk-or-v1-••••••••••••••   👁️  │
    └──────────────────────────────┘

    [ Test Connection ]

    ✅ Connection successful
    Your AI provider is connected and ready.

    Your key is stored securely on your computer.
    Never shared with anyone.

    Don't have an API key yet?
    1. Go to openrouter.ai
    2. Sign up for free
    3. Get your API key
    4. Paste it above and test
```

**Features**:

1. **API Key Input**
   - Password field with show/hide toggle
   - Accepts any API key format

2. **Test Connection**
   - Makes minimal test request to OpenRouter
   - Distinguishes error types:
     - Invalid key → "❌ API key was rejected"
     - No internet → "🌐 No internet connection"
     - Provider down → "⚠️ AI provider temporarily unavailable"
     - No credits → "💳 Your account doesn't have enough credits"
     - Success → "✅ Connection successful"

3. **Secure Storage**
   - Uses Windows Credential Manager (DPAPI)
   - Falls back to encrypted .env file
   - Never sent to external services
   - Only tested, not stored, during test phase

**User actions**:
- Enters API key
- Click "Test Connection"
- If valid, click "Continue"
- If not valid, adjust key and retry

**Backend endpoints**:

```
GET /api/setup/status
  Returns: { setup_complete, has_openrouter_key }

POST /api/setup/test-api-key?api_key=...
  Returns: { valid, status, message, details }

POST /api/setup/save-api-key?api_key=...&key_type=OPENROUTER
  Returns: { ok, message, error }
```

### Step 4: Main Application

**URL**: `/` (index.html)

**What happens**:
1. Startup check verifies:
   - First-run setup complete ✓
   - API key configured ✓
2. Loads main app (`/static/app.js`)
3. User can now:
   - Create cases
   - Upload documents
   - Chat with AI
   - Manage timeline

## Automatic Flow Prevention

At each step, the app checks if earlier steps are complete:

```
welcome.html
    ↓ (checks first-run not complete)
storage-selection.html
    ↓ (checks first-run + storage not set)
setup.html (API key)
    ↓ (checks API key not configured)
index.html → Main App
```

If a user directly visits a step they've already completed, they're redirected forward.

Example:
- User completes storage setup
- User tries to visit `/static/welcome.html` again
- Auto-redirects to `/static/setup.html` (next incomplete step)

## Storage Configuration Details

### Default Locations

**Windows**:
```
C:\Users\{Username}\AppData\Local\KanoonVault
```

**Linux**:
```
~/.KanoonVault
```

**macOS**:
```
~/.KanoonVault
```

### Directory Structure

```
KanoonVault/
├── kanoonvault.db           (Local SQLite database)
├── kanoonvault.db-shm       (SQLite shared memory)
├── kanoonvault.db-wal       (SQLite write-ahead log)
├── uploads/                 (User's uploaded documents)
│   ├── document1.pdf
│   ├── document2.jpg
│   └── ...
├── chroma_db/               (Vector embeddings for search)
│   ├── chroma.sqlite3
│   └── index_metadata.db
├── logs/                    (Application logs)
│   └── kanoonvault.log
└── .env                     (API key configuration)
```

### Data Migration

When users change storage location:

1. **Backup Creation**
   - New location backed up if it contains files
   - Backup timestamp: `{folder}_backup_{timestamp}`

2. **File Migration**
   - Database files copied
   - Documents copied
   - Embeddings copied
   - Configuration copied

3. **Merge Strategy**
   - Respects existing files in new location
   - Doesn't overwrite (preserves any new data)
   - Details logged in migration result

4. **Validation**
   - Checks both source and destination are accessible
   - Validates available disk space
   - Ensures proper permissions

## Configuration Persistence

### Storage Config File

**Location**: `%APPDATA%\Roaming\.kanoonvault\storage-config.json`

**Content**:
```json
{
  "storage_dir": "C:\\Users\\YourName\\AppData\\Local\\KanoonVault",
  "first_run_complete": true,
  "created_at": "2024-08-20T10:30:00",
  "updated_at": "2024-08-20T10:35:00"
}
```

### Settings Later (Future)

Users can change settings in app settings panel:

**Settings → Storage**:
```
Storage Location
┌────────────────────────────────────────┐
│ D:\MyKanoonVault                       │  [ Change ]
└────────────────────────────────────────┘

[ Open Folder ]   [ Move Existing Data ]

Available space: 250 GB free
Current files: 3,450 MB (158 files)
```

Options:
- **Change**: Opens folder dialog to pick new location
- **Open Folder**: Opens Windows Explorer to current storage
- **Move Existing Data**: Migrates database/documents if location changed

## Error Handling

### Path Validation Errors

| Error | Cause | Solution |
|-------|-------|----------|
| Path doesn't exist | Typed manually | Create it automatically |
| Not writable | Insufficient permissions | Choose different location |
| In Program Files | Shared system directory | Use user directory (recommend) |
| Network drive | Performance issues | Use local drive (warn) |
| Invalid path | Path is relative or malformed | Request absolute path |

### Storage Errors

| Error | Cause | Solution |
|-------|-------|----------|
| No disk space | Drive is full | Choose different drive |
| Migration failed | Copy operation error | Check permissions, retry |
| Can't access source | Old directory deleted | Use default + recreate cases |
| Database locked | App running on old location | Close app, then continue |

## Testing Checklist

- [ ] First launch shows welcome screen
- [ ] Welcome screen has correct branding
- [ ] "Get Started" button leads to storage selection
- [ ] Storage selection shows default location
- [ ] Storage location displays available disk space
- [ ] "Change Location" opens folder browser
- [ ] Can select new folder and confirm
- [ ] Confirmation dialog shows selected path
- [ ] Can cancel folder selection (reverts to previous)
- [ ] Proceeding creates storage directories
- [ ] Redirects to API key setup
- [ ] API key setup accepts key
- [ ] Test connection validates key
- [ ] Invalid key shows error
- [ ] Valid key shows success
- [ ] "Continue" button is only enabled after validation
- [ ] API key is saved securely
- [ ] Redirects to main app
- [ ] Main app loads successfully
- [ ] Second launch skips setup screens
- [ ] Closing and reopening app remembers settings

## Edge Cases

### Changing Storage After Setup

1. User opens app with existing cases
2. Goes to Settings → Storage
3. Clicks "Change Location"
4. Selects new folder
5. Clicks "Move Existing Data"
6. App:
   - Validates new location
   - Backs up current data
   - Migrates all files
   - Updates configuration
   - Restarts backend with new paths
   - Reloads UI

### Deleting Storage Directory

If user deletes the storage directory while app is running:
- App doesn't crash
- Operations fail gracefully
- Restarting app recreates directory structure
- Can configure new location if desired

### Using Cloud Drive

If user selects OneDrive, Dropbox, or Google Drive:
- App allows it (not prevented)
- Shows warning about performance
- Works but may be slow
- Real-time sync may cause issues

## Security Considerations

### Storage Permissions

- Storage directory should be user-writable
- No network access needed (local-only)
- Permission inheritance from parent directory

### Backups

- User responsible for backups
- Recommend backup-before-migration
- Storage directory can be backed up normally
- Database is SQLite (safe to copy)

### Data Migration

- No data is deleted from source until confirmed success
- Backup of destination before migration
- Rollback possible (restore from backup)

## Performance Considerations

### Path Choices Impact

| Path Type | Performance | Notes |
|-----------|-------------|-------|
| Local SSD | ★★★★★ Best | Recommended |
| Local HDD | ★★★☆☆ Good | Works fine |
| USB stick | ★★☆☆☆ Slow | Functional but laggy |
| Network drive | ★☆☆☆☆ Very slow | Avoid |

### Database Performance

- SQLite uses memory-mapped I/O
- Local drives much faster
- Network drives see increased latency
- Embeddings (ChromaDB) benefit from IOPS

## Future Enhancements

Possible improvements not yet implemented:

- [ ] Multiple storage profiles
- [ ] Scheduled backups
- [ ] Cloud sync (OneDrive, iCloud, etc.)
- [ ] Portable mode (USB stick)
- [ ] Import from previous version
- [ ] Profile migration tool
- [ ] Storage encryption
- [ ] Compression for archives

---

**Last Updated**: August 20, 2026

**Status**: Ready for implementation and testing
