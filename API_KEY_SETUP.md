# KanoonVault API Key Setup

This document explains the first-run API key configuration and validation system for KanoonVault.

## Overview

When a user launches KanoonVault for the first time, they are prompted to configure their OpenRouter API key before accessing the application. This ensures that:

1. ✅ Users are guided through the setup process
2. ✅ API keys are validated before being saved
3. ✅ Keys are stored securely using Windows Credential Manager
4. ✅ Users get immediate feedback on connection issues
5. ✅ The app provides helpful error messages

## User Flow

### First Launch

1. User runs `KanoonVault.exe`
2. Browser opens to `http://127.0.0.1:8000`
3. Setup check runs → API key not configured
4. Redirect to `/setup.html`

### Setup Screen

User sees:

```
        Set Up AI Assistance

OpenRouter API Key
┌──────────────────────────────┐
│ sk-or-v1-••••••••••••••       │ (password input)
└──────────────────────────────┘

[ Test Connection ]

Don't have an API key yet?
1. Go to openrouter.ai
2. Sign up for free
3. Get your API key
4. Paste it above
```

### Test Connection

User clicks "Test Connection"

**Actions**:
1. Frontend sends API key to `/api/setup/test-api-key`
2. Backend makes minimal test request to OpenRouter
3. Distinguishes between error types:
   - **Invalid key** → `❌ API key was rejected`
   - **No internet** → `🌐 No internet connection`
   - **Provider down** → `⚠️ AI provider temporarily unavailable`
   - **No credits** → `💳 Your account doesn't have enough credits`
   - **Success** → `✅ Connection successful`

### Save and Continue

Once test passes:

1. "Continue" button becomes enabled
2. User clicks "Continue"
3. API key is sent to `/api/setup/save-api-key`
4. Backend saves key to Windows Credential Manager
5. Redirect to main app `/`

## Technical Implementation

### Components

#### 1. Frontend: `frontend/setup.html`

Provides the setup UI with:
- API key input (password field with show/hide toggle)
- Test Connection button
- Status messages with detailed error information
- Helpful hints for new users
- Auto-redirect if setup already complete

**Features**:
- Prevents form submission without testing first
- Shows loading spinner during test
- Displays error messages inline
- Accessible keyboard navigation (Enter to test)

#### 2. Backend: `services/api_key_service.py`

Tests OpenRouter API keys:

```python
async def test_api_key_async(api_key, model, timeout) -> APIKeyTestResult
```

**Error Detection**:
- HTTP 200 → Valid ✅
- HTTP 401 → Invalid key ❌
- HTTP 429 → Rate limited 💳
- HTTP 402 → Insufficient credits 💳
- HTTP 5xx → Provider unavailable ⚠️
- Connection timeout → No internet 🌐
- Socket error → No internet 🌐

**Security**:
- Makes minimal test requests (single message, max_tokens=1)
- Doesn't consume meaningful credits (uses free tier)
- No credentials stored during testing

#### 3. Backend: `credentials.py`

Manages secure credential storage:

```python
save_api_key(key_type, api_key)  # Store securely
load_api_key(key_type)            # Retrieve securely
delete_api_key(key_type)          # Remove safely
is_api_key_configured(key_type)   # Check if set
```

**Storage Strategy**:

**Windows (Recommended)**:
- Uses `keyring` Python library
- Stores in Windows Credential Manager (DPAPI encrypted)
- Credentials survive updates and uninstalls
- No plain-text files

**Fallback** (non-Windows or if keyring fails):
- Stores in `%APPDATA%\KanoonVault\.env`
- Still not ideal but better than bundled app

#### 4. Backend: `main.py`

Three new API endpoints:

```python
GET  /api/setup/status
     # Is setup complete? Returns: { setup_complete, has_openrouter_key }

POST /api/setup/test-api-key?api_key=...
     # Test the key without saving. Returns: { valid, status, message, details }

POST /api/setup/save-api-key?api_key=...&key_type=OPENROUTER
     # Save validated key to secure storage. Returns: { ok, message }
```

#### 5. Frontend: `frontend/index.html`

Modified to check setup status on load:

```javascript
async function checkSetupAndInitialize() {
  const response = await fetch('/api/setup/status');
  if (!data.setup_complete) {
    window.location.href = '/static/setup.html';
    return;
  }
  loadMainApp(); // Load app.js
}
```

## Error Handling

### API Key Test Errors

The system distinguishes between:

#### Invalid/Revoked Key
- **Status Code**: 401 Unauthorized
- **Message**: "❌ API key was rejected\n\nThe key doesn't match OpenRouter records.\nPlease check that you copied the key correctly."
- **Action**: User re-enters key, tries again

#### No Internet Connection
- **Error**: Connection timeout, socket error, DNS failure
- **Message**: "🌐 No internet connection\n\nCheck your network connection and try again."
- **Action**: User checks network, tries again

#### Provider Unavailable
- **Status Code**: 500+ server error
- **Message**: "⚠️ AI provider temporarily unavailable\n\nOpenRouter is experiencing issues.\nPlease try again in a few moments."
- **Action**: User waits and retries

#### Insufficient Credits
- **Status Code**: 402 Payment Required
- **Message**: "💳 Account is out of credits\n\nYour OpenRouter account doesn't have\navailable credits. Please add payment method."
- **Action**: User logs into OpenRouter to add credits

#### Rate Limited
- **Status Code**: 429 Too Many Requests
- **Message**: "💳 Account limit exceeded\n\nYou've reached your account's usage limit.\nPlease check your OpenRouter account settings."
- **Action**: User checks account limits

### Edge Cases

**Empty key**:
- Frontend validation: Prevents sending empty string
- Server validation: Returns error if empty

**Whitespace**:
- Frontend trim: `.trim()` removes leading/trailing whitespace
- Server trim: Validates trimmed version

**Very long keys**:
- Frontend accepts any length
- Server sends to OpenRouter (it validates length)

**Special characters**:
- Sent as-is (URL-encoded in query parameter)
- OpenRouter validates format

## Security Considerations

### What We Do Well ✅

1. **Never hardccode keys**
   - Keys must be user-provided
   - Never bundled in executable

2. **Secure storage**
   - Windows Credential Manager (DPAPI encryption)
   - Falls back to encrypted environment file if needed
   - Never stored as plain text in source code

3. **Minimal test requests**
   - Single message, minimal tokens
   - Doesn't consume meaningful credits
   - No data sent except the key

4. **Direct API calls**
   - Frontend talks directly to OpenRouter
   - Backend receives tested key only
   - Server never handles untested keys

5. **Clear error messages**
   - Users understand what went wrong
   - Doesn't expose sensitive details
   - Suggests how to fix problems

### What Users Should Know 🔒

1. **API key is sensitive**
   - Treat like a password
   - Don't share or paste in screenshots
   - Guard in credential manager

2. **Local storage is safe**
   - Windows Credential Manager protects it
   - Not sent to cloud (unless configured)
   - User controls all access

3. **Test connection telemetry**
   - Makes one request to OpenRouter
   - OpenRouter logs this (like any API call)
   - Similar to entering key manually

## Configuration Paths

### Alternative: Pre-configured .env

If deploying in an enterprise environment, you can provide a `.env` file:

```
%APPDATA%\KanoonVault\.env

OPENROUTER_API_KEY=sk-or-v1-...
```

The setup screen will detect the key and skip to the main app.

### API Key Types Supported

1. **OPENROUTER** (required for chat)
   - Used for: Case chat, AI responses
   - Free tier available: Yes
   - Setup screen: Shown on first launch

2. **OCR_VISION** (optional, for vision OCR)
   - Used for: Document OCR with image understanding
   - Free tier available: Yes
   - Setup screen: Not shown (uses OPENROUTER as fallback)

3. **TIMELINE** (optional, for timeline extraction)
   - Used for: Automatic timeline event extraction
   - Free tier available: Yes
   - Setup screen: Not shown (uses heuristics fallback)

## Troubleshooting

### Issue: "Connection successful" but app still doesn't work

**Cause**: Key is valid for test but something else is wrong

**Debug**:
1. Check internet connection
2. Try a simple chat query
3. Check browser console for errors
4. Look for logs in `%APPDATA%\KanoonVault\logs\`

### Issue: Setup screen won't disappear

**Cause**: Key didn't actually save

**Solution**:
1. Check Windows permissions on `%APPDATA%\KanoonVault\`
2. Make sure folder is writable
3. Try deleting `.env` file and re-entering key
4. Check credential manager: `Manage user credentials` → Look for KanoonVault

### Issue: "No internet connection" on local network

**Cause**: Firewall or DNS blocking OpenRouter

**Solution**:
1. Check Windows Firewall settings
2. Ensure OpenRouter domain is not blocked
3. Try from different network
4. Check corporate proxy settings

## Testing

### Manual Testing Checklist

- [ ] Launch app, see setup screen
- [ ] Enter valid API key, test connection passes
- [ ] Click continue, redirected to main app
- [ ] Close and reopen app, doesn't show setup screen
- [ ] Can use chat functionality
- [ ] API key is in Windows Credential Manager

### Testing Different Errors

```bash
# Test with invalid key
curl -X POST "http://localhost:8000/api/setup/test-api-key?api_key=invalid-key"

# Test with no internet (disconnect network)
# Setup.html shows: "No internet connection"

# Test with rate limited account
# (Create account with no credits)
# Setup.html shows: "Account doesn't have enough credits"
```

## Future Enhancements

Possible future improvements:

- [ ] Support for other LLM providers (Anthropic, OpenAI, local LLMs)
- [ ] Settings UI to change API keys after setup
- [ ] Multiple API key profiles for different use cases
- [ ] API key rotation/expiration warnings
- [ ] Key usage analytics and limits
- [ ] Automatic fallback to alternative providers
- [ ] Environment variable override support
- [ ] Kubernetes/Docker secret integration

## Related Files

- `frontend/setup.html` — Setup UI
- `services/api_key_service.py` — API key testing logic
- `credentials.py` — Secure credential storage
- `main.py` — Setup API endpoints (lines 228-310)
- `frontend/index.html` — Setup check on app load
- `requirements.txt` — Includes `keyring` library
- `WINDOWS_PACKAGING_SUMMARY.md` — Overall architecture

---

**Last Updated**: August 20, 2026

**Status**: Ready for testing
