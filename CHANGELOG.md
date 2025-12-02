# Changelog - Modernization Update

## Summary of Changes

This update modernizes the MarketGPT project with improved configuration management, batch processing, and additional LLM provider support.

## Completed Improvements

### 1. ✅ Audit Functionality/Flows
- Created comprehensive architecture documentation (`ARCHITECTURE.md`)
- Documented all data flows, API endpoints, and system components
- Added environment setup guide (`ENV_SETUP.md`)

### 2. ✅ Recommendations Migration to SQLite
- **Status:** Already complete
- Recommendations are fully stored in SQLite database
- All recommendation queries use SQLite
- Soft deletion implemented (active/inactive flags)

### 3. ✅ Ollama LLM Provider Support
- Added Ollama as a supported LLM provider
- Supports OpenAI-compatible API endpoints
- Configuration via environment variables:
  - `OLLAMA_ENDPOINT` (default: `http://localhost:11434/v1/chat/completions`)
  - `OLLAMA_MODEL` (default: `llama3.2`)
- No API key required (typical Ollama setup)

### 4. ✅ Environment Variable Configuration
- **API Keys Moved to `.env` File**
  - All API keys now loaded from environment variables
  - Supports: `OPENAI_API_KEY`, `CLAUDE_API_KEY`
  - Backward compatible with `llm_config.json` (deprecated)
  - Environment variables take precedence over JSON config

- **New Environment Variables:**
  - `LLM_PROVIDER`: Select provider (local, openai, claude, ollama)
  - Provider-specific endpoints and models
  - See `ENV_SETUP.md` for complete list

- **Added `python-dotenv` dependency**
  - Automatically loads `.env` file on startup
  - Graceful fallback if package not installed

### 5. ✅ News Sources External Configuration
- **Created `news_sources.json`**
  - All RSS feed URLs moved to external JSON file
  - Easy to edit without code changes
  - Automatic duplicate removal on load
  - Configurable batch processing parameters:
    - `batch_size`: Number of feeds per batch
    - `delay_between_batches`: Delay between batch processing
    - `delay_between_feeds`: Delay between individual feeds

- **Automatic Duplicate Detection**
  - Duplicates removed when loading configuration
  - Preserves order of first occurrence

### 6. ✅ Intelligent Batch Processing
- **RSS Feed Fetching**
  - Processes feeds in configurable batches
  - Configurable delays between batches and feeds
  - Progress logging for batch processing
  - Prevents system overload

- **Article Processing**
  - Articles processed in batches during storage
  - Configurable batch sizes
  - Better resource management

### 7. ✅ CNBC Link Validation & Deduplication
- **Removed Duplicate URLs**
  - Original list had 24 URLs with 3 duplicates
  - New list has 21 unique URLs
  - Duplicates removed:
    - `id=10001147` (appeared twice)
    - `id=20910258` (appeared twice)
    - `id=10000664` (appeared twice)

- **Automatic Validation**
  - Code automatically removes duplicates on load
  - Prevents future duplicate issues

## Files Modified

1. **`app.py`**
   - Updated LLM configuration loading (environment variables + JSON fallback)
   - Added Ollama provider support
   - Implemented batch processing for RSS feeds
   - Added news sources loading from JSON file
   - Improved error handling and logging

2. **`requirements.txt`**
   - Added `python-dotenv==1.0.0`

3. **`news_sources.json`** (NEW)
   - External configuration for RSS feeds
   - Batch processing parameters

## Files Created

1. **`ARCHITECTURE.md`**
   - Comprehensive system architecture documentation
   - Data flow diagrams
   - API endpoint documentation
   - Configuration guide

2. **`ENV_SETUP.md`**
   - Environment variable setup guide
   - Provider-specific configuration examples
   - Security best practices

3. **`CHANGELOG.md`** (this file)
   - Summary of all changes

## Migration Guide

### For Existing Users

1. **Install new dependency:**
   ```bash
   pip install python-dotenv
   ```

2. **Create `.env` file:**
   ```bash
   # Copy your API keys from llm_config.json to .env
   LLM_PROVIDER=openai  # or claude, ollama, local
   OPENAI_API_KEY=your-key-here
   ```

3. **Update news sources:**
   - Edit `news_sources.json` to customize RSS feeds
   - Duplicates will be automatically removed

4. **Restart application:**
   ```bash
   python app.py
   ```

### Backward Compatibility

- `llm_config.json` still supported but deprecated
- Environment variables take precedence
- Existing functionality unchanged
- No breaking changes to API endpoints

## Configuration Examples

### Using Ollama
```bash
# .env
LLM_PROVIDER=ollama
OLLAMA_ENDPOINT=http://localhost:11434/v1/chat/completions
OLLAMA_MODEL=llama3.2
```

### Using OpenAI
```bash
# .env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4
```

### Custom News Sources
```json
// news_sources.json
{
  "sources": [
    "https://example.com/feed1.xml",
    "https://example.com/feed2.xml"
  ],
  "batch_size": 10,
  "delay_between_batches": 3.0,
  "delay_between_feeds": 0.5
}
```

## Benefits

1. **Security:** API keys no longer in code or JSON files
2. **Flexibility:** Easy to switch between LLM providers
3. **Performance:** Batch processing prevents system overload
4. **Maintainability:** External configuration files
5. **Reliability:** Duplicate detection and validation
6. **Documentation:** Comprehensive architecture docs

## Next Steps (Future Improvements)

- Add authentication/authorization
- Implement caching layer
- Add more news sources
- Improve recommendation confidence scoring
- Add real-time notifications
- Implement user preferences
- Add data export functionality

