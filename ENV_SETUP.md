# Environment Setup Guide

## Quick Start

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Create `.env` File**
   Copy the example file and fill in your API keys:
   ```bash
   cp .env.example .env
   # Edit .env with your preferred editor
   ```
   
   The `.env.example` file contains all available configuration options with comments.

3. **Configure News Sources**
   Edit `news_sources.json` to add/remove RSS feeds

4. **Run the Application**
   ```bash
   python app.py
   ```

## Environment Variables

### LLM Provider Selection
```bash
LLM_PROVIDER=local|openai|claude|ollama
```

### OpenAI Configuration
```bash
OPENAI_API_KEY=sk-...
OPENAI_ENDPOINT=https://api.openai.com/v1/chat/completions
OPENAI_MODEL=gpt-4
```

### Claude (Anthropic) Configuration
```bash
CLAUDE_API_KEY=sk-ant-...
CLAUDE_ENDPOINT=https://api.anthropic.com/v1/messages
CLAUDE_MODEL=claude-sonnet-4-20250514
```

### Ollama Configuration
```bash
OLLAMA_ENDPOINT=http://localhost:11434/v1/chat/completions
OLLAMA_MODEL=llama3.2
```

### Local LLM Configuration (LM Studio, etc.)
```bash
LOCAL_LLM_ENDPOINT=http://localhost:1234/v1/chat/completions
LOCAL_LLM_MODEL=
```

### Application Configuration
```bash
PORT=5070
FLASK_ENV=development
```

## Example `.env` File

```bash
# LLM Configuration
LLM_PROVIDER=ollama

# Ollama Settings
OLLAMA_ENDPOINT=http://localhost:11434/v1/chat/completions
OLLAMA_MODEL=llama3.2

# Or use OpenAI
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-your-key-here
# OPENAI_MODEL=gpt-4
```

## News Sources Configuration

Edit `news_sources.json`:

```json
{
  "sources": [
    "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
    "https://example.com/feed.xml"
  ],
  "batch_size": 5,
  "delay_between_batches": 2.0,
  "delay_between_feeds": 1.0
}
```

- `sources`: Array of RSS feed URLs
- `batch_size`: Number of feeds to process at once
- `delay_between_batches`: Seconds to wait between batches
- `delay_between_feeds`: Seconds to wait between individual feeds

## Backward Compatibility

The system still supports `llm_config.json` for backward compatibility, but environment variables take precedence. It's recommended to migrate to `.env` for better security.

## Security Notes

- **Never commit `.env` file to version control**
- Add `.env` to `.gitignore`
- Keep API keys secure
- Use different keys for development and production

