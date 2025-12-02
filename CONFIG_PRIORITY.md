# Configuration Priority and Security

## Configuration Priority Order

The application loads configuration in the following priority order:

### 1. Environment Variables (`.env` file) - **HIGHEST PRIORITY**
- **ALWAYS used for API keys** (required for security)
- Takes precedence over all other sources
- Recommended for all sensitive data

### 2. JSON Config Files (`llm_config.json`) - **FALLBACK ONLY**
- Only used for **non-sensitive settings** (provider, endpoint, model)
- **API keys are NEVER read from JSON files**
- Used only if environment variable is not set

## Security Rules

### ✅ DO:
- Store API keys in `.env` file
- Add `.env` to `.gitignore` (already done)
- Use environment variables for all sensitive data
- Use JSON files only for non-sensitive defaults

### ❌ DON'T:
- Store API keys in JSON files
- Commit `.env` file to version control
- Put real API keys in `llm_config.json*` files

## How It Works

### Example: OpenAI Configuration

**Priority 1: Environment Variables (`.env`)**
```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-real-key-here  # ✅ Used
OPENAI_ENDPOINT=https://api.openai.com/v1/chat/completions
OPENAI_MODEL=gpt-4
```

**Priority 2: JSON File (`llm_config.json.openai`)**
```json
{
  "provider": "openai",
  "endpoint": "https://api.openai.com/v1/chat/completions",
  "model": "gpt-4"
  // ❌ api_key field is IGNORED even if present
}
```

**Result:** The application will use:
- Provider: From `.env` (or JSON if not in `.env`)
- API Key: **ONLY from `.env`** (never from JSON)
- Endpoint: From `.env` (or JSON if not in `.env`)
- Model: From `.env` (or JSON if not in `.env`)

## Code Behavior

The code explicitly:
1. **Never reads API keys from JSON files** - even if present, they are ignored
2. **Warns if API keys are found in JSON files** - security warning printed
3. **Only uses environment variables for API keys** - `.env` file is the source of truth

## Migration from JSON to .env

If you have API keys in JSON files:

1. **Move them to `.env` file:**
   ```bash
   # .env
   OPENAI_API_KEY=your-actual-key-here
   ```

2. **Remove from JSON files:**
   - The JSON files have been updated to not include API keys
   - If you have old JSON files with keys, remove the `api_key` field

3. **Verify:**
   - Check that `.env` is in `.gitignore`
   - Restart the application
   - Check logs for security warnings

## Verification

When the application starts, it will:
- Print configuration source information
- Warn if API keys are found in JSON files
- Show which provider is being used
- Indicate if API keys are missing (for providers that require them)

## Example Log Output

```
[llm_config] Loaded configuration:
  Provider: openai (from .env)
  API Key: Set (from .env) ✅
  Endpoint: https://api.openai.com/v1/chat/completions (from .env)
  Model: gpt-4 (from .env)
```

Or if API key found in JSON:
```
[llm_config] ⚠️  SECURITY WARNING: API key found in llm_config.json!
[llm_config] ⚠️  API keys should ONLY be stored in .env file, not in JSON files.
[llm_config] ⚠️  The API key from JSON will be IGNORED. Please move it to .env file.
```

