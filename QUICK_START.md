# Quick Start Guide

## Setup (First Time)

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Create `.env` file:**
   ```bash
   cp .env.example .env
   # Edit .env with your preferred editor
   ```
   
   Or manually create `.env` with:
   ```bash
   # Choose your LLM provider
   LLM_PROVIDER=ollama  # or openai, claude, local
   
   # For Ollama (recommended for local use)
   OLLAMA_ENDPOINT=http://localhost:11434/v1/chat/completions
   OLLAMA_MODEL=llama3.2
   
   # For OpenAI
   # OPENAI_API_KEY=sk-your-key-here
   # OPENAI_MODEL=gpt-4
   
   # Application port (default: 5070)
   PORT=5070
   ```

3. **Configure news sources (optional):**
   - Edit `news_sources.json` to add/remove RSS feeds
   - Adjust batch processing settings if needed

4. **Run the application:**
   ```bash
   python app.py
   ```

5. **Access the web interface:**
   - Open http://localhost:5070 in your browser (or the port specified in `.env`)

## Common Tasks

### Switch LLM Provider
Edit `.env` file:
```bash
LLM_PROVIDER=ollama  # Change to: openai, claude, or local
```

### Add News Sources
Edit `news_sources.json`:
```json
{
  "sources": [
    "https://your-feed-url.com/rss"
  ]
}
```

### Adjust Batch Processing
Edit `news_sources.json`:
```json
{
  "batch_size": 10,              # Feeds per batch
  "delay_between_batches": 3.0,  # Seconds between batches
  "delay_between_feeds": 0.5      # Seconds between feeds
}
```

## Troubleshooting

### "python-dotenv not installed"
```bash
pip install python-dotenv
```

### "LLM endpoint not reachable"
- For Ollama: Make sure Ollama is running (`ollama serve`)
- For Local: Make sure your local LLM server is running
- Check the endpoint URL in `.env`

### "No articles found"
- Check that RSS feeds in `news_sources.json` are valid
- Wait for the background task to fetch articles (runs every 15 minutes)
- Manually trigger: The app fetches on startup

## Key Files

- `.env` - Environment variables (API keys, LLM config)
- `news_sources.json` - RSS feed configuration
- `app.py` - Main application
- `recommendations.sqlite` - Database (auto-created)

## Documentation

- `ARCHITECTURE.md` - System architecture and data flows
- `ENV_SETUP.md` - Detailed environment setup
- `CHANGELOG.md` - List of changes and improvements

