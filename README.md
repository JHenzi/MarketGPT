# MarketGPT 📈

MarketGPT is a comprehensive financial news analysis platform that automatically fetches, analyzes, and summarizes market news to provide actionable insights. It uses a local Large Language Model (LLM) to power a Retrieval-Augmented Generation (RAG) system, offering features like daily reports, stock recommendations, and a conversational Q&A interface.

## ✨ Features

![Recommendations](/images/recommendations.png)

- **Automated News Aggregation**: Fetches the latest news from multiple financial RSS feeds (e.g., CNBC).
- **AI-Powered Summarization**: Uses a local LLM to summarize articles and reduce information overload.
- **Vector-Based Semantic Search**: Stores articles in a ChromaDB vector database, allowing users to search for news based on concepts, not just keywords.
- **Daily Market Report**: Automatically categorizes today's news into key market areas (e.g., "Interest Rates," "Sector News," "Global Markets") and generates a daily report.
- **AI Stock Recommendations**: Analyzes news to extract potential BUY/SELL signals for specific stocks, including the reasoning and source article.
- **Interactive Q&A**: A chat interface (`/ask`) that uses a RAG pipeline to answer user questions based on the latest news, complete with source citations.
- **Web Interface**: A clean, user-friendly web UI built with Flask and Tailwind CSS for easy navigation between reports, recommendations, and search.

---

## ⚙️ How It Works

The application follows a multi-step pipeline:

1. **Fetch**: A background process periodically scrapes RSS feeds for new articles.
2. **Scrape & Store**: For each new article, it scrapes the full content, generates a vector embedding using `SentenceTransformers`, and stores the text, metadata, and embedding in a local **ChromaDB** database.
3. ~~**Analyze & Summarize**:~~
   - ~~Another background process identifies articles that haven't been summarized and uses a local LLM to generate a concise summary, which is then saved back to the database.~~
   - ~~A separate process analyzes the day's news to extract and store stock recommendations.~~ This doesn't work.
4. **Generate Report**: The system uses vector search to find the most relevant articles for predefined market categories and compiles them into a markdown report.
5. **Serve**: A **Flask** web server provides the frontend, answering user requests by querying the ChromaDB database and interacting with the LLM for the Q&A feature.

---

## 🚀 Setup and Installation

### Prerequisites

- **Python 3.8+**
- **A local LLM server**: This project is configured to work with an LLM served via an OpenAI-compatible API. A great option is LM Studio.

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

### 3. Configure the LLM Endpoint

The application needs to know the address of your LLM server. This is hardcoded in the source.

1. Start your local LLM server. We're using LM Studio in this example, but you can use any chat completion endpoint like OpenAI, Claude API, or other compatible services. Make sure you are serving a model compatible with chat completions.
2. Note the server URL (e.g., `http://192.168.1.220:1234` for LM Studio, or `https://api.openai.com` for OpenAI).
3. Open `app.py` and `summarize.py` and update the hardcoded `http://192.168.1.220:1234/v1/chat/completions` URL to match your LLM server's address or API endpoint.

This version makes it clear that LM Studio is just one option while keeping the specific example intact for those following along with that setup.

### 4. Run the Application

Start the Flask web server. A background thread will automatically start to fetch news.

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

> The below doesn't work and needs help!

- **`summarize.py`**: Can be run manually to summarize a batch of articles stored in the database.
  ```bash
  python summarize.py
  ```
- **`delete_db.py`**: Deletes the `marketwatch` collection from ChromaDB. Use this if you want to start fresh.
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
