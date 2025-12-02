# MarketGPT 📈

MarketGPT is a comprehensive financial news analysis platform that automatically fetches, analyzes, and summarizes market news to provide actionable insights. It uses a local Large Language Model (LLM) to power a Retrieval-Augmented Generation (RAG) system, offering features like daily reports, stock recommendations, and a conversational Q&A interface.

## ✨ Features

![Recommendations](/images/recommendations.png)

- **Automated News Aggregation**: Fetches the latest news from multiple financial RSS feeds (Bloomberg, Financial Times, Seeking Alpha, TechCrunch, and more - see `news_sources.json`). Uses intelligent feed tracking to skip recently-checked feeds and HTTP conditional requests to minimize bandwidth.
- **AI-Powered Analysis (Configurable LLM)**: The core application (`app.py`) uses a Large Language Model (LLM) for features like Q&A and stock recommendations. Supports multiple providers: OpenAI, Anthropic Claude, Ollama, or local LLM (e.g., via LM Studio). Configured via `.env` file (recommended) or `llm_config.json` (legacy).
- **Vector-Based Semantic Search**: Stores articles in a ChromaDB vector database, allowing users to search for news based on concepts, not just keywords.
- **Daily Market Report**: Automatically categorizes today's news into key market areas (e.g., "Interest Rates," "Sector News," "Global Markets") and generates a daily report.
- **AI Stock Recommendations**: The AI agent analyzes news (via `app.py` and its configured LLM) to extract potential BUY/SELL signals for specific stocks, including the reasoning and source article. Recommendations are validated to ensure they're actual tradeable stocks (not countries, sectors, or other entities).
- **Interactive Q&A**: A chat interface (`/ask`) that uses a RAG pipeline (powered by the configured LLM) to answer user questions based on the latest news, complete with source citations.
- **Web Interface**: A clean, user-friendly web UI built with Flask and Tailwind CSS for easy navigation between reports, recommendations, and search.
- **Performance Optimizations**: Feed-level tracking, conditional HTTP requests, and smart feed selection reduce processing time by 60-80% on subsequent runs.

---

## ⚙️ How It Works

The application follows a multi-step pipeline:

1. **Fetch**: A background process periodically scrapes RSS feeds for new articles. The system uses intelligent feed tracking to skip recently-checked feeds and uses HTTP conditional requests (ETags/Last-Modified) to avoid downloading unchanged feeds. The fetch interval is configurable via the `NEWS_FETCH_INTERVAL_MINUTES` environment variable (default: 30 minutes). See Configuration section below.
2. **Scrape & Store**: For each new article, it scrapes the full content, generates a vector embedding using `SentenceTransformers`, and stores the text, metadata, and embedding in a local **ChromaDB** database. The database is automatically created if it doesn't exist. If you encounter issues or want to start fresh with news articles, you can use the `delete_db.py` script (see Helper Scripts). Stock recommendations are stored in a **SQLite** database (`recommendations.sqlite`) for better querying and date-based filtering.
3. **Analyze & Recommend (via `app.py`)**:
   - The main application's background tasks analyze the day's news using the configured LLM (via `.env` or `llm_config.json`) to extract and store stock recommendations.
   - Recommendations are validated before storage to ensure they're actual stocks (not countries, sectors, or other non-tradeable entities).
   - The Q&A feature also uses this configured LLM to generate responses.
4. **Generate Report**: The system uses vector search to find the most relevant articles for predefined market categories and compiles them into a markdown report.
5. **Serve**: A **Flask** web server provides the frontend, answering user requests by querying the ChromaDB database and interacting with the LLM (as configured in `llm_config.json`) for the Q&A and recommendation features.

## Known Issues/Bugs

~~The Market Report is not outputing anything! There is a key error when we add a where. clause for today's date. Removing it still doesn't generate a file. Unsure when and how this broke but worth refactoring the entire code here.~~

- [x] Fix Market Report Generation Function

~~We need a "/" route.~~

- [x] Add "/" route

~~July 14th, 2025: **The stock recommendations needs debugged.** The logs show that the LLM is returning valid looking JSON but when we visit the page we don't see any recommendations. We should probably just make the easy pivot to storing recommendations in SQLite or something similar, it's too hard to debug ChromaDB for this usage.~~

- [x] Migrate recommendations to SQLite

**December 2nd, 2025: Today's Recommendations Showing Blank** ⚠️
- The "today's recommendations" page is currently showing blank/empty
- The system is processing recommendations and storing them in SQLite
- Root cause is under investigation
- Historical recommendations and API endpoints appear to be working
- See issue tracking for updates

---

## 🚀 Setup and Installation

### Prerequisites

- **Python 3.8+**
- **LLM Access**: Depending on your choice, you'll need:
  - Access to an OpenAI or Anthropic Claude API (and an API key).
  - Or, a local LLM server (e.g., LM Studio, Ollama) that provides an OpenAI-compatible API endpoint.

#### Tested Environment:

Tested on a Mac Mini M1 (2020). A miniconda install of Python. I'm personally not using a virtual environment, I've given up on this machine's install for now. I'm running [LM Studio](https://lmstudio.ai "LM Studio, AI toolkit"), and have found the [Gemma 3 4B ](https://huggingface.co/google/gemma-3-4b-it-qat-q4_0-gguf "Gemma 3 4B IT QAT")model to work sufficiently well.

#### Context Window Size!

**Important**: Because we feed the LLM the headline, URL and article **content** we need to ensure the `context size` (window) for our LLM is large enough to handle the RAG input (specifically for /ask). I've found good results in LM Studio at a context of 7,500 tokens.

### 1. Clone the Repository

```bash
git clone https://github.com/JHenzi/MarketGPT.git
cd MarketGPT
```

### 2. Create a Virtual Environment and Install Dependencies

It's highly recommended to use a virtual environment.

```bash
# Create the virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install the required packages
pip install -r requirements.txt
```

### 3. Configure the Application

#### LLM Configuration (Recommended: Use `.env` file)

**Preferred Method: Environment Variables**

1. **Create `.env` file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` file** with your configuration:
   ```bash
   # Choose your LLM provider
   LLM_PROVIDER=ollama  # or openai, claude, local
   
   # For Ollama
   OLLAMA_ENDPOINT=http://localhost:11434/v1/chat/completions
   OLLAMA_MODEL=llama3.2
   
   # For OpenAI
   # OPENAI_API_KEY=sk-your-key-here
   # OPENAI_MODEL=gpt-4
   
   # Application port (default: 5070)
   PORT=5070
   
   # News fetch interval in minutes (default: 30)
   NEWS_FETCH_INTERVAL_MINUTES=30
   ```

**Legacy Method: JSON Configuration**

The application also supports `llm_config.json` for backward compatibility, but **API keys should never be stored in JSON files** - use `.env` instead. See `ENV_SETUP.md` for detailed configuration options.

#### News Sources Configuration

Edit `news_sources.json` to customize RSS feeds. The default configuration includes:
- Financial news: Bloomberg, Financial Times, Seeking Alpha, Fortune, Dow Jones
- Business: Harvard Business Review, Fast Company
- Technology: TechCrunch, The Verge, Ars Technica, Wired, VentureBeat
- Crypto: CoinTelegraph, Decrypt

**Note:** The application focuses on finance, business, tech, and crypto feeds relevant for stock analysis. Entertainment, sports, and general news (politics) are excluded.

#### Fetch Interval Configuration

The background task that fetches news runs periodically. You can adjust the interval:

- **Environment Variable:** Set `NEWS_FETCH_INTERVAL_MINUTES` in your `.env` file (default: 30 minutes)
- **Recommended:** 30 minutes provides a good balance between freshness and system load
- **Adjust as needed:** For more frequent updates, set a lower value (e.g., 15 minutes). For less frequent updates, set a higher value (e.g., 60 minutes)

The fetch interval can be adjusted based on your needs:
- **More frequent (15-20 min):** Better for active trading, but higher system load
- **Moderate (30 min):** Good balance (default)
- **Less frequent (60+ min):** Lower system load, suitable for casual monitoring

### 4. Run the Application

Start the Flask web server. A background thread will automatically start to fetch news, generate reports, and find recommendations.

```bash
python app.py
```

The application will be available at `http://localhost:5070` (or the port specified in your `.env` file).

The first time you run it, the background process will begin fetching and storing articles. This may take a few minutes. Subsequent runs will be much faster as the system tracks which feeds have been recently checked and skips them. The background task will fetch new articles every 30 minutes by default (configurable via `NEWS_FETCH_INTERVAL_MINUTES` in `.env`).

**Performance Note:** On the first run, all feeds are checked. On subsequent runs, only feeds that haven't been checked within the fetch interval are processed, significantly reducing startup time (60-80% faster).

---

## 🛠️ Usage

Navigate to `http://localhost:5070` (or your configured port) in your browser.

- **📊 Report**: View the latest daily market report, categorized by topic.
- **💡 Recommendations**: See a list of stocks with AI-generated BUY/SELL recommendations based on the news.
- **🔍 Sources**: Perform a semantic search on the entire database of articles.
- **💬 Ask**: Chat with the MarketGPT assistant to ask specific questions about the market.

### Helper Scripts

- **`summarize.py`**: **(Deprecated/Broken)** This script was intended to manually summarize articles. However, it is currently not maintained, uses a hardcoded LLM endpoint (does not use `llm_config.json`), and may not function correctly. The main application (`app.py`) handles LLM interactions for its features.
  ```bash
  # python summarize.py # Not recommended for use
  ```
- **`delete_db.py`**: Deletes the `marketwatch` (news articles) collection from ChromaDB. Use this if you want to start fresh with article data or are experiencing issues with the news article index. Note: This script does **not** delete the `stock_recommendations` collection.
  ```bash
  python delete_db.py
  ```

---

## 📂 Project Structure

```
├── app.py                    # Main Flask application, routes
├── db_utils.py              # SQLite utilities for recommendations and feed metadata
├── news_sources.json        # RSS feed configuration
├── .env.example             # Environment variable template
├── recommendations.sqlite   # SQLite database for recommendations and feed metadata
├── /templates/              # HTML templates for the web UI
├── /chroma/                 # Directory for the persistent ChromaDB database
└── /docs/                   # Documentation files (ARCHITECTURE.md, LLM_AGENT_DOCUMENTATION.md, etc.)
```

## 📚 Additional Documentation

- **`ARCHITECTURE.md`** - Complete system architecture and data flows
- **`LLM_AGENT_DOCUMENTATION.md`** - How the LLM/Agent works, prompts, and validation
- **`ENV_SETUP.md`** - Detailed environment variable configuration
- **`PERFORMANCE_OPTIMIZATIONS.md`** - Feed tracking and performance improvements
- **`FEED_TRACKING_IMPLEMENTATION.md`** - Feed metadata tracking implementation details
- **`QUICK_START.md`** - Quick reference guide
- **`CONFIG_PRIORITY.md`** - Configuration priority and security guidelines

## 📄 License

This project is licensed under the GNU GPL License.

## 🤝 Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your changes. For major changes, please open an issue first to discuss what you would like to change.

## Suggest RSS Feeds

If you have suggestions for additional RSS feeds to include in the news aggregation, please open an issue. The feeds should be well tested against `trafilatura` after the RSS reveals the URL to the news story (note we fetch the feed then the story and store it in ChromaDB).
