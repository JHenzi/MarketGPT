# MarketGPT Architecture & Functionality Audit

## Overview
MarketGPT is a Flask-based web application that aggregates financial news from RSS feeds, analyzes them using LLMs, and provides stock recommendations. The system uses ChromaDB for article storage and SQLite for recommendation storage.

## System Architecture

### Core Components

1. **Flask Web Application** (`app.py`)
   - Main application server
   - Handles HTTP requests and routes
   - Manages background tasks

2. **ChromaDB** (Vector Database)
   - Stores article embeddings and metadata
   - Enables semantic search over articles
   - Collection: "marketwatch"

3. **SQLite Database** (`recommendations.sqlite`)
   - Stores stock recommendations
   - Managed by `db_utils.py`
   - Schema: recommendations table with ticker, recommendation type, confidence, etc.

4. **LLM Integration**
   - Supports multiple providers: OpenAI, Claude, Ollama, Local
   - Configuration via environment variables (`.env`) or JSON files
   - Used for article analysis and recommendation extraction

5. **Sentence Transformers**
   - Model: `all-MiniLM-L6-v2`
   - Generates embeddings for semantic search

## Data Flow

### 1. RSS Feed Fetching (`fetch_and_store`)
```
RSS Feeds (news_sources.json) 
  → Batch Processing (configurable batch size)
  → Feed Parser
  → Article Extraction (trafilatura)
  → Embedding Generation
  → ChromaDB Storage
```

**Features:**
- Batch processing to avoid overwhelming the system
- Duplicate detection (by URL)
- Configurable delays between batches and feeds
- Full article content extraction when available

### 2. Market Report Generation (`generate_market_report`)
```
Today's Articles (from ChromaDB)
  → Category Classification (using embeddings)
  → Similarity Scoring
  → Report Generation (Markdown)
  → File Output (market_report.md)
```

**Categories:**
- Monetary Policy & Inflation
- Stock Market Indices
- Specific Industry & Sector Performance
- Fixed Income & Debt Markets
- Innovation & Corporate Growth Events
- Corporate Challenges & Market Weakness
- International Trade & Global Economics

### 3. Stock Recommendation Extraction (`extract_stock_recommendations`)
```
Today's Articles (from ChromaDB)
  → Batch Processing (5 articles per batch)
  → LLM Analysis
  → JSON Parsing
  → SQLite Storage
```

**Recommendation Format:**
- Company name
- Ticker symbol
- Recommendation (BUY/SELL)
- Reason
- Confidence (HIGH/MEDIUM/LOW)
- Source article information

### 4. Market Summary Generation (`summarize_market_report`)
```
market_report.md
  → LLM Analysis
  → Summary Generation
  → File Output (market_summary.md)
```

## API Endpoints

### Web Routes
- `/` - Home page
- `/report` - View market report (rendered from markdown)
- `/sources` - Search articles by query
- `/ask` - Chat interface for asking questions about the market
- `/recommendations` - View stock recommendations (defaults to today)

### API Routes
- `/api/recommendations/today` - JSON endpoint for today's recommendations
- `/api/recommendations/date/<date_str>` - JSON endpoint for specific date
- `/recommendations/delete` - POST endpoint to mark recommendations inactive

## Configuration

### Environment Variables (`.env`)
```
LLM_PROVIDER=local|openai|claude|ollama
OPENAI_API_KEY=...
OPENAI_ENDPOINT=...
OPENAI_MODEL=...
CLAUDE_API_KEY=...
CLAUDE_ENDPOINT=...
CLAUDE_MODEL=...
OLLAMA_ENDPOINT=...
OLLAMA_MODEL=...
LOCAL_LLM_ENDPOINT=...
LOCAL_LLM_MODEL=...
```

### News Sources (`news_sources.json`)
```json
{
  "sources": ["url1", "url2", ...],
  "batch_size": 5,
  "delay_between_batches": 2.0,
  "delay_between_feeds": 1.0
}
```

### LLM Config (Backward Compatibility)
- `llm_config.json` - Still supported but deprecated
- Environment variables take precedence

## Background Tasks

### Periodic Task (`periodic_fetch_and_report`)
Runs in a background thread with the following cycle:
1. Fetch and store new articles (every 15 minutes)
2. Generate market report
3. Summarize market report
4. Extract stock recommendations
5. Cleanup old recommendations (older than 3 days)

**Interval:** 15 minutes (configurable in code)

## Data Storage

### ChromaDB
- **Purpose:** Article storage and semantic search
- **Location:** `./chroma/`
- **Schema:** Documents with embeddings and metadata (link, published_date, title, source, length)

### SQLite
- **Purpose:** Recommendation storage
- **Location:** `recommendations.sqlite`
- **Schema:** 
  - `id` (PRIMARY KEY): `{ticker}_{date}_{recommendation}`
  - `company`, `ticker`, `recommendation`, `reason`, `confidence`
  - `article_title`, `article_url`, `date`, `timestamp`
  - `active` (boolean flag for soft deletion)

## Key Features

### 1. Batch Processing
- RSS feeds processed in configurable batches
- Articles processed in batches during recommendation extraction
- Prevents system overload and API rate limiting

### 2. Duplicate Detection
- URLs checked before storage
- Duplicate sources removed from configuration
- Prevents redundant processing

### 3. Soft Deletion
- Recommendations marked as inactive rather than deleted
- Enables historical tracking
- Automatic cleanup of old recommendations

### 4. Multi-Provider LLM Support
- OpenAI (GPT models)
- Claude (Anthropic)
- Ollama (local models)
- Local LLM (LM Studio, etc.)

### 5. Semantic Search
- Vector embeddings for article similarity
- Category-based classification
- Query-based article retrieval

## Recent Improvements (2025)

1. **Environment Variable Support**
   - API keys moved to `.env` file
   - Improved security and configuration management

2. **Ollama Integration**
   - Added support for Ollama LLM provider
   - Enables local model usage

3. **News Sources Configuration**
   - External JSON file for easy editing
   - Automatic duplicate removal
   - Configurable batch processing parameters

4. **Batch Processing**
   - Intelligent batching for RSS feeds
   - Configurable delays and batch sizes
   - Better resource management

5. **SQLite Migration**
   - Recommendations fully migrated to SQLite
   - Improved query performance
   - Better data persistence

## File Structure

```
MarketGPT/
├── app.py                 # Main Flask application
├── db_utils.py            # SQLite database utilities
├── news_sources.json      # RSS feed configuration
├── llm_config.json       # LLM config (deprecated, use .env)
├── .env                   # Environment variables (not in repo)
├── requirements.txt      # Python dependencies
├── recommendations.sqlite # SQLite database
├── chroma/               # ChromaDB storage
├── templates/            # HTML templates
├── static/               # CSS and static files
└── scripts/              # Utility scripts
```

## Dependencies

- Flask: Web framework
- ChromaDB: Vector database
- Sentence Transformers: Embedding generation
- Trafilatura: Article extraction
- Feedparser: RSS parsing
- SQLite3: Recommendation storage
- Python-dotenv: Environment variable management

## Future Improvements

1. Add authentication/authorization
2. Implement caching for frequently accessed data
3. Add more news sources beyond CNBC
4. Implement recommendation confidence scoring improvements
5. Add real-time notifications for new recommendations
6. Implement user preferences and watchlists
7. Add data export functionality
8. Implement API rate limiting
9. Add comprehensive error handling and retry logic
10. Implement logging system

