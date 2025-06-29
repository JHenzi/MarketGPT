# MarketGPT 📈

MarketGPT is a comprehensive financial news analysis platform that automatically fetches, analyzes, and summarizes market news to provide actionable insights. It uses a local Large Language Model (LLM) to power a Retrieval-Augmented Generation (RAG) system, offering features like daily reports, stock recommendations, and a conversational Q&A interface.

## ✨ Features

![Recommendations](/images/recommendations.png)

- **Automated News Aggregation**: Fetches the latest news from multiple financial RSS feeds (e.g., CNBC).
- **AI-Powered Analysis (Configurable LLM)**: The core application (`app.py`) uses a Large Language Model (LLM) for features like Q&A and stock recommendations. This is configurable via an `llm_config.json` file, allowing you to use providers like OpenAI, Anthropic Claude, or a local LLM (e.g., via LM Studio).
- **Vector-Based Semantic Search**: Stores articles in a ChromaDB vector database, allowing users to search for news based on concepts, not just keywords.
- **Daily Market Report**: Automatically categorizes today's news into key market areas (e.g., "Interest Rates," "Sector News," "Global Markets") and generates a daily report.
- **AI Stock Recommendations**: The AI agent analyzes news (via `app.py` and its configured LLM) to extract potential BUY/SELL signals for specific stocks, including the reasoning and source article.
- **Interactive Q&A**: A chat interface (`/ask`) that uses a RAG pipeline (powered by the configured LLM in `app.py`) to answer user questions based on the latest news, complete with source citations.
- **Web Interface**: A clean, user-friendly web UI built with Flask and Tailwind CSS for easy navigation between reports, recommendations, and search.

---

## ⚙️ How It Works

The application follows a multi-step pipeline:

1. **Fetch**: A background process periodically scrapes RSS feeds for new articles.
2. **Scrape & Store**: For each new article, it scrapes the full content, generates a vector embedding using `SentenceTransformers`, and stores the text, metadata, and embedding in a local **ChromaDB** database. The database is automatically created if it doesn't exist. If you encounter issues or want to start fresh with news articles, you can use the `delete_db.py` script (see Helper Scripts). Stock recommendations are stored in a separate ChromaDB collection.
3. **Analyze & Recommend (via `app.py`)**:
   - The main application's background tasks analyze the day's news using the LLM configured in `llm_config.json` to extract and store stock recommendations.
   - The Q&A feature also uses this configured LLM to generate responses.
4. **Generate Report**: The system uses vector search to find the most relevant articles for predefined market categories and compiles them into a markdown report.
5. **Serve**: A **Flask** web server provides the frontend, answering user requests by querying the ChromaDB database and interacting with the LLM (as configured in `llm_config.json`) for the Q&A and recommendation features.

---

## 🚀 Setup and Installation

### Prerequisites

- **Python 3.8+**
- **LLM Access**: Depending on your choice, you'll need:
  - Access to an OpenAI or Anthropic Claude API (and an API key).
  - Or, a local LLM server (e.g., LM Studio, Ollama) that provides an OpenAI-compatible API endpoint.

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

### 3. Configure the LLM for `app.py`

The main application (`app.py`) uses an `llm_config.json` file to connect to your chosen Large Language Model.

1. **Choose a configuration template:** In the root directory, you'll find example configuration files:

   - `llm_config.json.localLLM` (for local models like LM Studio, Ollama)
   - `llm_config.json.openai` (for OpenAI API)
   - `llm_config.json.claude` (for Anthropic Claude API)

2. **Create `llm_config.json`:** Copy your chosen template and rename it to `llm_config.json`. For example:

   ```bash
   # If using a local LLM
   cp llm_config.json.localLLM llm_config.json
   ```

   ```bash
   # If using OpenAI
   cp llm_config.json.openai llm_config.json
   ```

3. **Edit `llm_config.json`:**

   - Open `llm_config.json` in a text editor.
   - **For local LLM:** Update the `endpoint` if your local server uses a different address (e.g., `http://localhost:11434/v1/chat/completions` for Ollama). The `model` field can often be left as `"default"` or set to a specific model name if your server requires it. `api_key` can be `null`.
     ```json
     {
       "provider": "local",
       "endpoint": "http://localhost:1234/v1/chat/completions",
       "model": "default",
       "api_key": null
     }
     ```
   - **For OpenAI:** Replace `"YOUR_OPENAI_API_KEY_HERE"` with your actual OpenAI API key. You can also change the `model` (e.g., `"gpt-4o-mini"`, `"gpt-3.5-turbo"`).
     ```json
     {
       "provider": "openai",
       "endpoint": "https://api.openai.com/v1/chat/completions",
       "model": "gpt-4o-mini",
       "api_key": "YOUR_OPENAI_API_KEY_HERE"
     }
     ```
   - **For Claude:** Replace `"YOUR_CLAUDE_API_KEY_HERE"` with your actual Anthropic API key. Update the `model` if needed (e.g., `"claude-3-sonnet-20240229"`).

     ```json
     {
       "provider": "claude",
       "endpoint": "https://api.anthropic.com/v1/messages",
       "model": "claude-3-opus-20240229",
       "api_key": "YOUR_CLAUDE_API_KEY_HERE"
     }
     ```

     _(Note: The Claude endpoint and model might vary based on API version and chosen model. Refer to Anthropic's documentation.)_

The `app.py` will automatically load this configuration when it starts.

### 4. Run the Application

Start the Flask web server. A background thread will automatically start to fetch news, generate reports, and find recommendations.

```bash
python app.py
```

The application will be available at `http://0.0.0.0:5020`.

The first time you run it, the background process will begin fetching and storing articles. This may take a few minutes. Subsequent reports and recommendations will be generated from this data.

---

## 🛠️ Usage

Navigate to `http://localhost:5020` in your browser.

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
├── app.py                    # Main Flask application, routes, and background jobs
├── summarize.py              # Script for summarizing articles
├── article_scraper.py        # Helper script for fetching article text (used by other modules)
├── delete_db.py              # Utility to clear the database collection
├── requirements.txt          # Python dependencies
├── market_report.md          # The generated daily report
├── /templates/               # HTML templates for the web UI
└── /chroma/                  # Directory for the persistent ChromaDB database
```

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details

## 🤝 Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your changes. For major changes, please open an issue first to discuss what you would like to change.

## Suggest RSS Feeds

If you have suggestions for additional RSS feeds to include in the news aggregation, please open an issue. The feeds should be well tested against `trafilatura` after the RSS reveals the URL to the news story (note we fetch the feed then the story and store it in ChromaDB).
