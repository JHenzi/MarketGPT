# Configuration Priority Fix - Summary

## Problem Identified

There was confusion about which configuration source takes precedence:
- `llm_config.json` files contained API key placeholders
- `.env` file also contains configuration
- Unclear which one the code would use
- Security concern: API keys shouldn't be in JSON files

## Solution Implemented

### 1. Clear Priority Order
**Priority 1: Environment Variables (`.env` file)**
- **ALWAYS used for API keys** (security requirement)
- Takes precedence for all settings
- Required for sensitive data

**Priority 2: JSON Files (`llm_config.json*`)**
- Only used for **non-sensitive settings** (provider, endpoint, model)
- **API keys are NEVER read from JSON files**
- Used only as fallback if environment variable is not set

### 2. Code Changes

**Before:**
```python
# Could read API keys from JSON as fallback
config["api_key"] = os.getenv("OPENAI_API_KEY") or json_config.get("api_key")
```

**After:**
```python
# API keys ONLY from environment variables
config["api_key"] = os.getenv("OPENAI_API_KEY")  # Never from JSON
```

### 3. Security Warnings

The code now:
- Warns if API keys are found in JSON files
- Explicitly ignores API keys from JSON files
- Logs which source each setting comes from

### 4. JSON Files Updated

All `llm_config.json*` files have been updated:
- Removed API key fields (or replaced with warnings)
- Added comments warning against storing API keys
- Now safe to commit to version control

## Configuration Source Priority

| Setting | Priority 1 | Priority 2 |
|---------|------------|------------|
| **API Keys** | `.env` (REQUIRED) | ❌ Never from JSON |
| Provider | `.env` | `llm_config.json` |
| Endpoint | `.env` | `llm_config.json` |
| Model | `.env` | `llm_config.json` |

## Example: How It Works

### Scenario 1: Everything in `.env`
```bash
# .env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-real-key
OPENAI_MODEL=gpt-4
```
**Result:** All settings from `.env` ✅

### Scenario 2: Provider in `.env`, model in JSON
```bash
# .env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-real-key
# OPENAI_MODEL not set
```
```json
// llm_config.json
{
  "model": "gpt-4"
}
```
**Result:** 
- Provider: `.env` ✅
- API Key: `.env` ✅
- Model: JSON (fallback) ✅

### Scenario 3: API key in JSON (BAD)
```json
// llm_config.json
{
  "api_key": "sk-bad-practice"
}
```
**Result:**
- ⚠️ Security warning printed
- API key from JSON is **IGNORED**
- Application will fail if not in `.env`

## Verification

When you run the application, you'll see:
```
[llm_config] Configuration loaded:
  Provider: openai (from environment)
  API Key: Set (from environment (.env)) ✅
  Endpoint: https://api.openai.com/v1/chat/completions (from environment)
  Model: gpt-4 (from environment)
```

Or if API key found in JSON:
```
[llm_config] ⚠️  SECURITY WARNING: API key found in llm_config.json!
[llm_config] ⚠️  API keys should ONLY be stored in .env file, not in JSON files.
[llm_config] ⚠️  The API key from JSON will be IGNORED. Please move it to .env file.
```

## Files Changed

1. **`app.py`**
   - Updated `load_llm_config()` to never read API keys from JSON
   - Added security warnings
   - Added detailed logging of configuration sources

2. **`llm_config.json*` files**
   - Removed API key fields
   - Added security warnings in comments
   - Now safe example files

3. **New Documentation**
   - `CONFIG_PRIORITY.md` - Detailed explanation
   - `CONFIG_FIX_SUMMARY.md` - This file

## Migration Steps

If you have API keys in JSON files:

1. **Move to `.env`:**
   ```bash
   # .env
   OPENAI_API_KEY=your-actual-key-here
   ```

2. **Remove from JSON:**
   - JSON files have been cleaned up
   - If you have old files, remove `api_key` field

3. **Verify:**
   - Check startup logs
   - Ensure no security warnings
   - Test API calls work

## Security Benefits

✅ API keys never in version control (JSON files are safe)
✅ Clear separation: sensitive data in `.env`, examples in JSON
✅ Automatic warnings if misconfigured
✅ Explicit logging of configuration sources

## Best Practices

1. **Always use `.env` for API keys**
2. **Never commit `.env` to git** (already in `.gitignore`)
3. **Use JSON files only for non-sensitive defaults**
4. **Check startup logs for configuration warnings**

