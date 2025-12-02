# app.py
# from apscheduler.schedulers.background import BackgroundScheduler
from chromadb.config import Settings
from collections import defaultdict
from datetime import datetime, timedelta, date
from dateutil.parser import parse as parse_date
from dateutil import parser as date_parser
from flask import Flask, jsonify
from flask import render_template_string
from flask import request, render_template
from markupsafe import Markup
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from zoneinfo import ZoneInfo
# SQLite for recommendations
from db_utils import (
    init_recommendations_db, 
    store_recommendations_sqlite, 
    get_recommendations_sqlite,
    get_todays_recommendations,
    get_recommendations_by_date,
    mark_recommendation_inactive_sqlite,
    mark_ticker_recommendations_inactive_sqlite,
    cleanup_old_recommendations,
    get_recommendation_stats
)
import chromadb
import feedparser
import json
import markdown
import numpy as np
import os
import random
import re
import requests
import sys
import threading
import time
import trafilatura
import uuid
import traceback

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("[WARNING] python-dotenv not installed. Install it with: pip install python-dotenv")
    print("[WARNING] Environment variables will not be loaded from .env file")




#today_str = datetime.now().strftime("%Y-%m-%d")
today_str = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")

def get_today_str():
    """Return today's date string in YYYY-MM-DD format using New York timezone."""
    return datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")

today_str = get_today_str()

app = Flask(__name__)

# Setup Chroma (for articles only)
client = chromadb.Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory="./chroma"))
collection = client.get_or_create_collection(name="marketwatch")

# Initialize SQLite database for recommendations
init_recommendations_db()
print("[INIT] SQLite recommendations database initialized")

# Load LLM configuration from environment variables and JSON file (for backward compatibility)
def load_llm_config(path="llm_config.json"):
    """
    Load LLM configuration from environment variables (REQUIRED for API keys) or JSON file (fallback for non-sensitive settings only).
    
    PRIORITY ORDER:
    1. Environment variables (.env file) - ALWAYS used for API keys
    2. JSON file - Only used for provider, endpoint, model (NO API KEYS)
    
    SECURITY: API keys are NEVER read from JSON files. They must be in .env file.
    """
    # Default configuration
    default_config = {
        "provider": "local",
        "endpoint": "http://localhost:1234/v1/chat/completions",
        "api_key": None,
        "model": None
    }
    
    # Try to load from JSON file for backward compatibility (non-sensitive settings only)
    json_config = {}
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                json_config = json.load(f)
            
            # SECURITY WARNING: Check if API key is in JSON file
            if json_config.get("api_key") and json_config.get("api_key") not in [None, "", "YOUR_OPENAI_API_KEY_HERE", "YOUR_CLAUDE_API_KEY_HERE"]:
                print(f"[llm_config] ⚠️  SECURITY WARNING: API key found in {path}!")
                print("[llm_config] ⚠️  API keys should ONLY be stored in .env file, not in JSON files.")
                print("[llm_config] ⚠️  The API key from JSON will be IGNORED. Please move it to .env file.")
        except Exception as e:
            print(f"[llm_config] Failed to load JSON config, using defaults. Error: {e}")
    
    # Load from environment variables (takes precedence, REQUIRED for API keys)
    provider = os.getenv("LLM_PROVIDER", json_config.get("provider", "local"))
    
    config = {
        "provider": provider,
        "api_key": None,  # API keys are ONLY from environment variables
        "endpoint": None,
        "model": None
    }
    
    # Load provider-specific configuration
    # API KEYS: ONLY from environment variables, NEVER from JSON
    if provider == "openai":
        config["api_key"] = os.getenv("OPENAI_API_KEY")  # Only from .env, never from JSON
        config["endpoint"] = os.getenv("OPENAI_ENDPOINT") or json_config.get("endpoint") or "https://api.openai.com/v1/chat/completions"
        config["model"] = os.getenv("OPENAI_MODEL") or json_config.get("model") or "gpt-4"
    elif provider == "claude":
        config["api_key"] = os.getenv("CLAUDE_API_KEY")  # Only from .env, never from JSON
        config["endpoint"] = os.getenv("CLAUDE_ENDPOINT") or json_config.get("endpoint") or "https://api.anthropic.com/v1/messages"
        config["model"] = os.getenv("CLAUDE_MODEL") or json_config.get("model") or "claude-sonnet-4-20250514"
    elif provider == "ollama":
        config["api_key"] = None  # Ollama typically doesn't require API keys
        config["endpoint"] = os.getenv("OLLAMA_ENDPOINT") or json_config.get("endpoint") or "http://localhost:11434/v1/chat/completions"
        config["model"] = os.getenv("OLLAMA_MODEL") or json_config.get("model") or "llama3.2"
    else:  # local
        config["api_key"] = None
        config["endpoint"] = os.getenv("LOCAL_LLM_ENDPOINT") or json_config.get("endpoint") or "http://localhost:1234/v1/chat/completions"
        config["model"] = os.getenv("LOCAL_LLM_MODEL") or json_config.get("model")
    
    # Merge with defaults
    final_config = {**default_config, **config}
    
    return final_config

# Actually load the LLM config
llm_config = load_llm_config()

# Validate configuration
if llm_config["provider"] not in ["local", "openai", "claude", "ollama"]:
    print(f"[llm_config] Invalid provider '{llm_config['provider']}'. Using default 'local'.")
    llm_config["provider"] = "local"

# Log configuration source for clarity
print(f"[llm_config] Configuration loaded:")
print(f"  Provider: {llm_config['provider']} (from {'environment' if os.getenv('LLM_PROVIDER') else 'JSON/default'})")
if llm_config["provider"] in ["openai", "claude"]:
    api_key_source = "environment (.env)" if os.getenv(f"{llm_config['provider'].upper()}_API_KEY") else "NOT SET"
    print(f"  API Key: {'Set' if llm_config['api_key'] else 'Not set'} ({api_key_source})")
    if not llm_config["api_key"]:
        print(f"  ⚠️  WARNING: API key not set for {llm_config['provider']}. Set {llm_config['provider'].upper()}_API_KEY in .env file.")
        print("  ⚠️  The application may fail when making API calls.")
else:
    print(f"  API Key: Not required for {llm_config['provider']}")

endpoint_source = "environment" if (os.getenv("OPENAI_ENDPOINT") or os.getenv("CLAUDE_ENDPOINT") or os.getenv("OLLAMA_ENDPOINT") or os.getenv("LOCAL_LLM_ENDPOINT")) else "JSON/default"
print(f"  Endpoint: {llm_config['endpoint']} (from {endpoint_source})")

model_source = "environment" if (os.getenv("OPENAI_MODEL") or os.getenv("CLAUDE_MODEL") or os.getenv("OLLAMA_MODEL") or os.getenv("LOCAL_LLM_MODEL")) else "JSON/default"
if llm_config.get("model"):
    print(f"  Model: {llm_config['model']} (from {model_source})")

# Validate provider-specific requirements
if llm_config["provider"] in ["openai", "claude"]:
    if not llm_config["endpoint"]:
        print(f"[llm_config] Endpoint not set for {llm_config['provider']}. Using default.")
elif llm_config["provider"] in ["local", "ollama"]:
    if not llm_config["endpoint"]:
        print(f"[llm_config] Endpoint not set for {llm_config['provider']}. Using default.")
    # Only check endpoint reachability for local/ollama if not in production
    if os.getenv("FLASK_ENV") != "production":
        try:
            # Just check if endpoint is accessible, don't fail if it's not
            response = requests.get(llm_config["endpoint"].replace("/v1/chat/completions", ""), timeout=2)
        except requests.RequestException:
            print(f"[llm_config] WARNING: {llm_config['provider']} endpoint {llm_config['endpoint']} may not be reachable.")
            print("[llm_config] Make sure your LLM server is running.")

# Prepare LLM messages and send them to the endpoint
def prepare_llm_request(messages, temperature=0.7):
    """
    Prepare LLM request based on provider type.
    Supports: openai, claude, ollama, local
    """
    provider = llm_config.get("provider", "local")
    endpoint = llm_config["endpoint"]
    headers = {}
    payload = {
        "messages": messages,
        "temperature": temperature
    }

    if provider == "openai":
        if llm_config.get("api_key"):
            headers["Authorization"] = f"Bearer {llm_config['api_key']}"
        if llm_config.get("model"):
            payload["model"] = llm_config["model"]
    elif provider == "claude":
        if llm_config.get("api_key"):
            headers["x-api-key"] = llm_config["api_key"]
            headers["anthropic-version"] = "2023-06-01"
        if llm_config.get("model"):
            payload["model"] = llm_config["model"]
    elif provider == "ollama":
        # Ollama uses OpenAI-compatible API, no auth needed
        if llm_config.get("model"):
            payload["model"] = llm_config["model"]
    else:  # local provider
        # local provider — only add model if set
        if llm_config.get("model"):
            payload["model"] = llm_config["model"]

    return endpoint, headers, payload


# SentenceTransformer model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Load news sources from JSON file
def load_news_sources(path="news_sources.json"):
    """
    Load news sources from JSON file.
    Returns a tuple of (feed_urls, batch_size, delay_between_batches, delay_between_feeds)
    """
    default_sources = [
        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114"
    ]
    
    if not os.path.exists(path):
        print(f"[news_sources] Config file {path} not found. Using defaults.")
        return default_sources, 5, 2.0, 1.0
    
    try:
        with open(path, "r") as f:
            config = json.load(f)
        
        sources = config.get("sources", default_sources)
        # Remove duplicates while preserving order
        seen = set()
        unique_sources = []
        for url in sources:
            if url not in seen:
                seen.add(url)
                unique_sources.append(url)
        
        batch_size = config.get("batch_size", 5)
        delay_between_batches = config.get("delay_between_batches", 2.0)
        delay_between_feeds = config.get("delay_between_feeds", 1.0)
        
        print(f"[news_sources] Loaded {len(unique_sources)} unique sources from {path}")
        if len(sources) != len(unique_sources):
            print(f"[news_sources] Removed {len(sources) - len(unique_sources)} duplicate sources")
        
        return unique_sources, batch_size, delay_between_batches, delay_between_feeds
    except Exception as e:
        print(f"[news_sources] Error loading config from {path}: {e}")
        return default_sources, 5, 2.0, 1.0

feed_urls, BATCH_SIZE, DELAY_BETWEEN_BATCHES, DELAY_BETWEEN_FEEDS = load_news_sources()

def fetch_full_article(url):
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            return trafilatura.extract(downloaded, include_comments=False, include_tables=False)
    except Exception as e:
        print(f"[fetch_full_article] Error fetching {url}: {e}")
    return None


def fetch_rss_multiple(feed_urls, batch_size=None, delay_between_batches=None):
    """
    Fetch RSS feeds in batches to avoid overwhelming the system.
    Processes feeds in batches with delays between batches.
    """
    if batch_size is None:
        batch_size = BATCH_SIZE
    if delay_between_batches is None:
        delay_between_batches = DELAY_BETWEEN_BATCHES
    
    all_entries = []
    total_feeds = len(feed_urls)
    
    print(f"[fetch_rss_multiple] Processing {total_feeds} feeds in batches of {batch_size}")
    
    for i in range(0, total_feeds, batch_size):
        batch = feed_urls[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (total_feeds + batch_size - 1) // batch_size
        
        print(f"[fetch_rss_multiple] Processing batch {batch_num}/{total_batches} ({len(batch)} feeds)")
        
        for url in batch:
            try:
                parsed_feed = feedparser.parse(url)
                entries = parsed_feed.entries
                all_entries.extend(entries)
                print(f"[fetch_rss_multiple] Fetched {len(entries)} entries from feed")
            except Exception as e:
                print(f"[fetch_rss_multiple] Error fetching feed {url}: {e}")
                continue
            
            # Small delay between individual feeds
            if delay_between_batches > 0:
                time.sleep(DELAY_BETWEEN_FEEDS + random.uniform(0, 0.3))
        
        # Delay between batches (except for the last batch)
        if i + batch_size < total_feeds and delay_between_batches > 0:
            print(f"[fetch_rss_multiple] Waiting {delay_between_batches}s before next batch...")
            time.sleep(delay_between_batches)
    
    print(f"[fetch_rss_multiple] Total entries fetched: {len(all_entries)}")
    return all_entries


def embed_text(texts):
    return [emb.tolist() for emb in model.encode(texts)]

def fetch_and_store(feed_urls, delay_between=None):
    """
    Fetch RSS feeds and store articles in batches.
    Processes articles in batches to avoid overwhelming the system.
    """
    if delay_between is None:
        delay_between = DELAY_BETWEEN_FEEDS
    
    print("[fetch_and_store] Starting fetch...")

    entries = fetch_rss_multiple(feed_urls)
    total = len(entries)
    added = 0

    print(f"[fetch_and_store] Total {total} entries fetched from all RSS feeds.")
    print(f"[fetch_and_store] Processing articles in batches of {BATCH_SIZE}")

    # Process articles in batches
    for batch_start in range(0, total, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, total)
        batch_entries = entries[batch_start:batch_end]
        batch_num = (batch_start // BATCH_SIZE) + 1
        total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
        
        print(f"[fetch_and_store] Processing article batch {batch_num}/{total_batches} ({len(batch_entries)} articles)")

        for i, entry in enumerate(batch_entries, 1):
            global_index = batch_start + i
            title = entry.get("title", "")
            summary = entry.get("summary", "")
            link = entry.get("link", "")
            if not link:
                print(f"[{global_index}/{total}] Skipping entry with missing link.")
                continue  # skip malformed entry
            published = entry.get("published") or entry.get("pubDate") or ""
            published_date = ""

            if published:
                try:
                    parsed = date_parser.parse(published)
                    published_date = parsed.strftime("%Y-%m-%d")
                except Exception as e:
                    print(f"[{global_index}/{total}] Failed to parse published date: {published}")

            # Skip if already in DB
            existing = collection.get(where={"link": link})
            if existing["ids"]:
                print(f"[{global_index}/{total}] Skipping already stored link: {link}")
                continue

            print(f"[{global_index}/{total}] Fetching full article from: {link}")
            # Fetch full article
            full_article = fetch_full_article(link)
            if full_article and len(full_article) > 200:
                text = f"{title}. {full_article}"
                print(f"[{global_index}/{total}] Using full article content (length={len(full_article)})")
            else:
                text = f"{title}. {summary}"
                print(f"[{global_index}/{total}] Using summary content (length={len(summary)})")

            embedding = embed_text([text])[0]
            doc_id = str(uuid.uuid4())

            collection.add(
                documents=[text],
                embeddings=[embedding],
                ids=[doc_id],
                metadatas=[{
                    "link": link,
                    "published": published,
                    "published_date": published_date,
                    "title": title,
                    "source": "rss",
                    "length": len(text)
                }]
            )

            added += 1
            print(f"[{global_index}/{total}] Added document id={doc_id} to collection.")

            # Delay to throttle
            time.sleep(delay_between + random.uniform(0, 0.5))  # jitter helps mimic natural behavior
        
        # Delay between batches (except for the last batch)
        if batch_end < total and DELAY_BETWEEN_BATCHES > 0:
            print(f"[fetch_and_store] Waiting {DELAY_BETWEEN_BATCHES}s before next batch...")
            time.sleep(DELAY_BETWEEN_BATCHES)

    print(f"[fetch_and_store] Inserted {added} new entries into the database.")

@app.route("/report")
def view_market_report():
    report_path = "market_report.md"

    if not os.path.exists(report_path):
        return "Report not found.", 404

    with open(report_path, "r", encoding="utf-8") as f:
        report_md = f.read()

    # Get last modified time and format it
    last_modified_ts = os.path.getmtime(report_path)
    last_modified_dt = datetime.fromtimestamp(last_modified_ts)
    last_modified_str = last_modified_dt.strftime("%B %d, %Y %I:%M:%S %p")


    # Optional: summary loading as before...
    summary_md = ""
    summary_path = "market_summary.md"
    if os.path.exists(summary_path):
        with open(summary_path, "r", encoding="utf-8") as f:
            summary_md = f.read()

    report_html = markdown.markdown(
        report_md, extensions=["extra", "toc", "sane_lists"]
    )
    summary_html = markdown.markdown(summary_md, extensions=["extra", "toc", "sane_lists"]) if summary_md else ""

    return render_template(
        "report.html",
        report_html=report_html,
        summary_html=summary_html,
        last_modified=last_modified_str
    )

@app.route("/sources", methods=["GET", "POST"])
def sources():
    results = []
    query = ""
    if request.method == "POST":
        query = request.form["query"]
        embedding = embed_text([query])[0]
        search_results = collection.query(
            query_embeddings=[embedding],
            n_results=15,
            include=["documents", "metadatas"]
        )
        docs = search_results["documents"][0]
        metas = search_results["metadatas"][0]
        print(f"[sources] Found {len(docs)} results for query: {query}")

        for doc, meta in zip(docs, metas):
            results.append({
                "title": meta.get("title", "No title"),
                "link": meta.get("link", "#"),
                "published": meta.get("published", "Unknown date"),
                "snippet": doc[:300] + "..." # Truncate long text
            })
        print(f"[sources] Processed {len(results)} results.")

        # Sort by published date (newest first)
        from datetime import datetime

        # Function to parse date strings
        def parse_date(date_str):
            if date_str == "Unknown date":
                return datetime.min  # Put unknown dates at the end
            try:
                # RFC 2822 format: Wed, 25 Jun 2025 15:05:02 GMT
                return datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %Z")
            except ValueError:
                try:
                    # Try other common formats as fallback
                    for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y", "%m/%d/%Y"]:
                        try:
                            return datetime.strptime(date_str, fmt)
                        except ValueError:
                            continue
                    # If none work, try parsing ISO format
                    return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                except:
                    return datetime.min  # Fallback for unparseable dates

        # Sort results by published date descending
        results.sort(key=lambda x: parse_date(x["published"]), reverse=True)

    return render_template("sources.html", query=query, results=results)

@app.route("/ask", methods=["GET", "POST"])
def ask():
    if request.method == "POST":
        user_input = request.form.get("question", "").strip()
        if not user_input:
            return render_template("chat.html", error="Please enter a question.")

        # Embed user input
        embedding = embed_text([user_input])[0]

        # Pull more entries than needed for sorting
        results = collection.query(
            query_embeddings=[embedding],
            n_results=25,  # Pull extra so we can sort by date
            include=["documents", "metadatas"]
        )

        docs = results["documents"][0]
        metas = results["metadatas"][0]

        # Pair up and sort by parsed publish date descending
        combined = []
        for doc, meta in zip(docs, metas):
            published_str = meta.get("published_date")
            try:
                published_dt = date_parser.parse(published_str) if published_str else datetime.min
            except Exception:
                published_dt = datetime.min
            combined.append((published_dt, doc, meta))

        # Sort by date and select top 5
        top_articles = sorted(combined, key=lambda x: x[0], reverse=True)[:5]
        docs = [x[1] for x in top_articles]
        metas = [x[2] for x in top_articles]

        today_str = datetime.utcnow().strftime("%Y-%m-%d")

        # Format context
        context_items = []
        for doc, meta in zip(docs, metas):
            title = meta.get("title", "No title")
            link = meta.get("link", "#")
            published = meta.get("published_date") or "Unknown"
            context_items.append(f"[{title}]({link}) (Published: {published}): {doc}")
        context = "\n\n---\n\n".join(context_items)

        # Prepare LLM prompt
        messages = [
            {
                "role": "system",
                "content": f"""You are MarketGPT, an expert financial news assistant.
Always consider the publish date of news sources when generating responses.
Today is {today_str}. If a source is old, do not base predictions on it.
Be concise, professional, and current.
Don't make up information or provide opinions.
If you don't know the answer, say "I don't know" instead of guessing."""
            },
            {
                "role": "user",
                "content": f"""Here is relevant news context (title, URL, publish date, and content):

{context}

Please answer this question:

{user_input}
"""
            }
        ]

        # Call the LLM endpoint
        endpoint, headers, payload = prepare_llm_request(messages, temperature=0.7)
        response = requests.post(endpoint, headers=headers, json=payload)
        response.raise_for_status()

        # Process the response
        raw_answer = response.json()["choices"][0]["message"]["content"]
        #cleaned_answer = re.sub(r"<think>.*?</think>", "", raw_answer, flags=re.DOTALL | re.IGNORECASE)
        # Strip everything before and including a closing </think> tag
        cleaned_answer = re.sub(r"^.*?</\s*think\s*>", "", raw_answer, flags=re.DOTALL | re.IGNORECASE).strip()

        rendered_answer = Markup(markdown.markdown(cleaned_answer))

        reveal_reason_text = "\n\n---\n\n".join([
            f"{meta.get('title', 'No title')} ({meta.get('link', '#')}) - Published: {meta.get('published_date', 'Unknown')}\n\n{doc}"
            for doc, meta in zip(docs, metas)
        ])

        return render_template("chat.html", question=user_input, answer=rendered_answer, context=reveal_reason_text)

    return render_template("chat.html", question="", answer="", context="")



# Your categories and example phrases (copy from previous message)
CATEGORIES = {
    "Monetary Policy & Inflation": [  # Renamed for clarity
        "Federal Reserve policy changes", # More specific than "decision"
        "Consumer Price Index (CPI) data release", # More specific
        "Central bank inflation targets", # Changed focus
        "Impact of interest rate adjustments on economy", # More specific scenario
        "FOMC meeting announcements and outlook" # Added specific event
    ],
    "Stock Market Indices": [ # Renamed for clarity
        "S&P 500 daily closing values and analysis",
        "Nasdaq Composite technology stock trends", # More specific index name
        "Dow Jones Industrial Average key movers",
        "Broad market index volatility (VIX)", # Added different aspect
        "Exchange Traded Fund (ETF) net asset value changes"
    ],
    "Specific Industry & Sector Performance": [ # Renamed for clarity
        "Oil and gas sector profit reports", # More specific
        "Semiconductor industry supply chain news", # More specific tech
        "Pharmaceutical company drug trial results", # More specific healthcare
        "Banking sector capital requirements updates", # More specific finance
        "Manufacturing output and PMI data" # More specific industrial
    ],
    "Fixed Income & Debt Markets": [ # Renamed for clarity
        "US Treasury yield curve inversions and steepening", # More specific
        "High-yield corporate bond market spreads", # More specific
        "Sovereign debt credit rating changes", # Added different aspect
        "Municipal bond issuance and demand", # Added different aspect
        "Federal government debt ceiling negotiations" # Added specific event
    ],
    "Innovation & Corporate Growth Events": [ # Renamed for clarity
        "Unicorn company IPO filings and valuations", # More specific
        "Breakthroughs in generative AI applications", # More specific
        "Electric vehicle (EV) battery technology advancements", # More specific
        "Biotechnology patent approvals for new treatments", # More specific
        "Company expansion into new international markets" # Changed focus from just earnings
    ],
    "Corporate Challenges & Market Weakness": [ # Renamed for clarity
        "Legacy retail chain store closures", # More specific
        "Major corporation workforce reduction plans", # More specific
        "Quarterly earnings misses and revenue warnings", # More specific
        "Chapter 11 bankruptcy filings by notable companies", # More specific
        "Commercial real estate vacancy rate increases" # More specific
    ],
    "International Trade & Global Economics": [ # Renamed for clarity
        "China's GDP growth rate forecasts", # More specific
        "European Central Bank (ECB) interest rate decisions", # More specific
        "Japan's Nikkei index performance and outlook", # More specific
        "Impact of international trade tariffs on specific goods", # More specific
        "Currency exchange rate fluctuations in G20 economies" # More specific
    ],
}

def generate_market_report(collection, model, top_k=10, output_path="market_report.md", today_str=today_str):
    """
    Generate market report by first fetching all today's articles, then classifying them
    using sentence transformers similarity scoring.
    """
    # report_lines = ["# MarketGPT Daily Report\n"]
    report_lines = [""]
    try:
        # First, try to get all articles for today without any vector search
        # This avoids the hnswlib KeyError issue
        if today_str:
            try:
                # Attempt to fetch with date filter
                all_results = collection.get(
                    where={"published_date": today_str},
                    include=["documents", "metadatas"]
                )
            except Exception as e:
                print(f"[WARNING] Date filtering failed: {e}")
                print("Falling back to fetching all articles...")
                # Fallback: get all articles if date filtering fails
                all_results = collection.get(include=["documents", "metadatas"])
        else:
            # Get all articles if no date specified
            all_results = collection.get(include=["documents", "metadatas"])
        print(f"[generate_market_report] Fetched {len(all_results['documents'])} articles from collection.")
        if not all_results["documents"]:
            print("[WARNING] No articles found in database")
            report_lines.append("_No articles found in database._\n")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(report_lines))
            return
        # Combine documents and metadata
        articles = list(zip(all_results["documents"], all_results["metadatas"]))
        print(f"[INFO] Found {len(articles)} total articles")
        if not articles:
            report_lines.append("_No articles found for today._\n")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(report_lines))
            return
        # Filter by date if we couldn't do it in the query
        if today_str:
            pre_filter_count = len(articles)
            articles = [(doc, meta) for doc, meta in articles 
                        if meta.get("published_date") == today_str]
            print(f"[INFO] Filtered articles by published_date = {today_str}. {len(articles)} of {pre_filter_count} matched.")

        if not articles:
            report_lines.append("_No matching articles found for today._\n")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(report_lines))
            return

        # Pre-compute embeddings for all category phrases
        category_embeddings = {}
        all_phrases = []
        phrase_to_category = {}

        for category, phrases in CATEGORIES.items():
            for phrase in phrases:
                all_phrases.append(phrase)
                phrase_to_category[phrase] = category

        print("[INFO] Computing category embeddings...")
        phrase_embeddings = model.encode(all_phrases)

        for i, phrase in enumerate(all_phrases):
            category = phrase_to_category[phrase]
            if category not in category_embeddings:
                category_embeddings[category] = []
            category_embeddings[category].append(phrase_embeddings[i])

        # Average embeddings for each category
        for category in category_embeddings:
            category_embeddings[category] = np.mean(category_embeddings[category], axis=0)
        print(f"[INFO] Computed embeddings for {len(category_embeddings)} categories")
        # Compute embeddings for all articles
        print("[INFO] Computing article embeddings...")
        article_texts = [doc for doc, _ in articles]
        article_embeddings = model.encode(article_texts)
        print(f"[INFO] Computed embeddings for {len(article_embeddings)} articles")
        # Classify articles into categories
        categorized_articles = defaultdict(list)
        seen_links = set()
        print("[INFO] Initializing categorized articles...")
        print("[INFO] Classifying articles...")
        for i, (doc, meta) in enumerate(articles):
            link = meta.get("link", "")
            if link in seen_links:
                continue
            # print(f"[{i+1}/{len(articles)}] Classifying article: {meta.get('title', 'No title')} ({link})")
            # Find best matching category
            best_category = None
            best_similarity = -1
            # Reshape article embedding for cosine similarity
            article_embedding = article_embeddings[i].reshape(1, -1)
            # Compare with each category embedding
            for category, cat_embedding in category_embeddings.items():
                similarity = cosine_similarity(
                    article_embedding, 
                    cat_embedding.reshape(1, -1)
                )[0][0]
                # print(f"[{i+1}/{len(articles)}] Similarity with category '{category}': {similarity:.3f}")
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_category = category
            # If no category matched, skip this article
            # Only include if similarity is above a threshold (adjust as needed)
            if best_similarity > 0.3:  # Adjust threshold as needed
                categorized_articles[best_category].append((doc, meta, best_similarity))
                seen_links.add(link)
        print(f"[INFO] Classified articles into {len(categorized_articles)} categories")
        # Generate report
        for category in CATEGORIES.keys():
            articles_for_category = categorized_articles.get(category, [])
            if not articles_for_category:
            # Sort by similarity score (descending)
                articles_for_category.sort(key=lambda x: x[2], reverse=True)
            # If no articles matched this category, skip it
            # Limit to top_k articles
            articles_for_category = articles_for_category[:top_k]
            print(f"[INFO] Found {len(articles_for_category)} articles for category '{category}'")
            if not articles_for_category:
                report_lines.append(f"## {category}\n_No matching articles found for today._\n---\n")
                continue
            # Add category header
            report_lines.append(f"## {category}\n")
            for i, (doc, meta, similarity) in enumerate(articles_for_category, 1):
                title = meta.get("title", "No title")
                link = meta.get("link", "#")
                published = meta.get("published", "Unknown date")
                # Optionally include similarity score for debugging
                # report_lines.append(f"{i}. [{title}]({link}) (similarity: {similarity:.3f})  \nPublished: {published}\n")
                report_lines.append(f"{i}. [{title}]({link})\n")
            report_lines.append("\n---\n")

        # Save the final markdown report
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))
        # Print success message
        print(f"[generate_market_report] Report saved to {output_path}")

    except Exception as e:
        print(f"[ERROR] Failed to generate report: {e}")
        report_lines.append(f"_Error generating report: {e}_\n")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))



# Alternative simpler approach if the above is still too complex
def generate_market_report_simple(collection, model, top_k=10, output_path="market_report.md", today_str=None):
    """
    Simplified approach using keyword matching + embedding similarity
    """
    report_lines = ["# MarketGPT Daily Report\n"]
    print("[generate_market_report_simple] Starting simple report generation...")
    try:
        # Get all articles (avoid vector search entirely)
        all_results = collection.get(include=["documents", "metadatas"])
        print(f"[generate_market_report_simple] Fetched {len(all_results['documents'])} articles from collection.")    
        if not all_results["documents"]:
            report_lines.append("_No articles found in database._\n")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(report_lines))
            return
        # Combine documents and metadata
        articles = list(zip(all_results["documents"], all_results["metadatas"]))
        print(f"[generate_market_report_simple] Found {len(articles)} total articles")
        # Filter by date if specified
        if today_str:
            articles = [(doc, meta) for doc, meta in articles 
                if meta.get("published_date") == today_str]

        if not articles:
            report_lines.append("_No articles found for today._\n")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(report_lines))
            return

        seen_links = set()

        for category, phrases in CATEGORIES.items():
            category_articles = []
            print(f"[generate_market_report_simple] Processing category: {category} with {len(phrases)} phrases")
            # Simple keyword-based filtering first
            for doc, meta in articles:
                link = meta.get("link", "")
                if link in seen_links:
                    continue

                # Check if any phrase keywords appear in the document
                doc_lower = doc.lower()
                if any(any(word.lower() in doc_lower for word in phrase.split()) 
                        for phrase in phrases):
                    category_articles.append((doc, meta))
                    seen_links.add(link)

                    if len(category_articles) >= top_k:
                        break

            if not category_articles:
                report_lines.append(f"## {category}\n_No matching articles found for today._\n---\n")
                continue
            # Sort by published date (newest first)
            report_lines.append(f"## {category}\n")
            for i, (doc, meta) in enumerate(category_articles, 1):
                title = meta.get("title", "No title")
                link = meta.get("link", "#")
                published = meta.get("published", "Unknown date")
                report_lines.append(f"{i}. [{title}]({link})  \nPublished: {published}\n")
            report_lines.append("\n---\n")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))

        print(f"[generate_market_report_simple] Report saved to {output_path}")

    except Exception as e:
        print(f"[ERROR] Failed to generate simple report: {e}")
        report_lines.append(f"_Error generating report: {e}_\n")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))


@app.route("/")
def home():
    return render_template("index.html")

def extract_stock_recommendations(collection, model, today_str):
    """
    Read today's news and extract buy/sell recommendations for stocks
    """
    print(f"[extract_stock_recommendations] Analyzing news for {today_str}")

    # Get all today's articles
    today_articles = collection.get(
        where={"published_date": today_str},
        include=["documents", "metadatas"]
    )

    if not today_articles["documents"]:
        print("[extract_stock_recommendations] No articles found for today")
        return

    docs = today_articles["documents"]
    metas = today_articles["metadatas"]

    # Batch process articles to avoid too many API calls
    batch_size = 5
    all_recommendations = []

    for i in range(0, len(docs), batch_size):
        batch_docs = docs[i:i+batch_size]
        batch_metas = metas[i:i+batch_size]

        # Prepare context for LLM
        context_items = []
        for doc, meta in zip(batch_docs, batch_metas):
            title = meta.get("title", "No title")
            link = meta.get("link", "#")
            context_items.append(f"Title: {title}\nURL: {link}\nContent: {doc[:1000]}")

        context = "\n\n---\n\n".join(context_items)

        # Prepare LLM prompt for stock analysis
        messages = [
            {
                "role": "system",
                "content": """You are a financial analyst. Analyze news articles and identify any stock buy/sell signals. Be careful to not make up ticker symbols or to suggest buy/sell recommendations on things that are not stocks, bonds, mutual funds, or ETFs. If you are unsure, do not provide a suggestion.

Look for:
- Company earnings beats/misses
- Analyst upgrades/downgrades
- New product launches or innovations
- Regulatory approvals/rejections
- Management changes
- Market share gains/losses
- Financial guidance changes

Respond ONLY with a JSON array of recommendations. Each recommendation should have:
{
  "company": "Company Name",
  "ticker": "STOCK_SYMBOL",
  "recommendation": "BUY" or "SELL",
  "reason": "Brief reason for recommendation",
  "confidence": "HIGH", "MEDIUM", or "LOW",
  "article_title": "Article title",
  "article_url": "Article URL"
}

If no clear recommendations, return empty array [].
DO NOT include any text outside the JSON array. Especially do not include any markdown or HTML formatting like backticks. Do not explain your reasoning or provide any additional commentary. Just return the JSON array."""
            },
            {
                "role": "user", 
                "content": f"Analyze these news articles for stock recommendations:\n\n{context}"
            }
        ]

        try:
            # Call your local LLM
            # response = requests.post(
            #     "http://192.168.1.220:1234/v1/chat/completions",
            #     json={
            #         "messages": messages,
            #         "temperature": 0.3,
            #     }
            # )
            endpoint, headers, payload = prepare_llm_request(messages, temperature=0.7)
            response = requests.post(endpoint, headers=headers, json=payload)


            raw_response = response.json()["choices"][0]["message"]["content"]
            # Clean up the response
            # Remove any <think> tags - first line commented out didn't work for DeepSeek + Qwen 3
            # raw_response = re.sub(r"<think>.*?</think>", "", raw_response, flags=re.DOTALL | re.IGNORECASE)
            #raw_response = re.sub(r"<\s*think\s*>.*?<\s*/\s*think\s*>", "", raw_response, flags=re.DOTALL | re.IGNORECASE)
            raw_response = re.sub(r"<\s*/?\s*think\s*>", "", raw_response, flags=re.IGNORECASE)
            # Remove any markdown formatting
            raw_response = re.sub(r"```json\s*([\s\S]*?)\s*```", r"\1", raw_response)
            # Clean up any extra whitespace
            raw_response = raw_response.strip()
            # Parse JSON response
            print(f"[extract_stock_recommendations] Raw response: {raw_response}")
            if not raw_response:
                print("[extract_stock_recommendations] No recommendations found in response")
                continue
            try:
                batch_recommendations = json.loads(raw_response)
                if isinstance(batch_recommendations, list):
                    all_recommendations.extend(batch_recommendations)
            except json.JSONDecodeError as e:
                print(f"[extract_stock_recommendations] JSON parse error: {e}")
                print(f"Raw response: {raw_response}")

        except Exception as e:
            print(f"[extract_stock_recommendations] Error processing batch: {e}")

        # Small delay between batches
        time.sleep(2)

    # Store recommendations in ChromaDB
    store_recommendations(all_recommendations, today_str)
    print(f"[extract_stock_recommendations] Processed {len(all_recommendations)} recommendations")

def store_recommendations(recommendations, date_str):
    """
    Store stock recommendations in SQLite database.
    """
    if not recommendations:
        return
    
    try:
        store_recommendations_sqlite(recommendations, date_str)
        print(f"[store_recommendations] Stored {len(recommendations)} recommendations for {date_str}")
    except Exception as e:
        print(f"[store_recommendations] Error storing recommendations: {e}")
        traceback.print_exc()


def get_stock_recommendations(ticker=None, recommendation_type=None, days_back=7, today_only=True):
    """
    Retrieve stock recommendations from SQLite with optional filtering
    """
    try:
        return get_recommendations_sqlite(
            ticker=ticker,
            recommendation_type=recommendation_type,
            today_only=today_only,
            active_only=True
        )
    except Exception as e:
        print(f"[get_stock_recommendations] Error: {e}")
        return {}

def get_related_articles_for_stock(ticker, days_back=7):
    """
    Get recent articles mentioning a specific stock
    """
    # Search for articles mentioning the ticker
    search_query = f"{ticker} stock shares"
    embedding = embed_text([search_query])[0]

    results = collection.query(
        query_embeddings=[embedding],
        n_results=20,
        include=["documents", "metadatas"]
    )

    # Filter results that actually mention the ticker
    relevant_articles = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        if ticker.upper() in doc.upper() or ticker.lower() in meta.get("title", "").lower():
            relevant_articles.append({
                "title": meta.get("title", "No title"),
                "link": meta.get("link", "#"),
                "published_date": meta.get("published_date", "Unknown"),
                "snippet": doc[:300] + "..."
            })

    return relevant_articles

# Add this route to your Flask app
@app.route("/recommendations")
def view_recommendations():
    """
    Display stock buy/sell recommendations - defaults to today's recommendations
    """
    rec_type = request.args.get("type")  # "BUY" or "SELL"
    ticker = request.args.get("ticker")
    date_filter = request.args.get("date")  # YYYY-MM-DD format
    today_only = request.args.get("today", "true").lower() == "true"  # Default to true
    show_all = request.args.get("all", "false").lower() == "true"  # Explicit all parameter

    if show_all:
        # Show all recommendations when explicitly requested
        recommendations = get_stock_recommendations(
            ticker=ticker,
            recommendation_type=rec_type,
            today_only=False
        )
        today_only = False
    elif date_filter:
        # Show recommendations for specific date
        recommendations = get_recommendations_by_date(date_filter)
        today_only = False
        # Apply additional filters if needed
        if rec_type or ticker:
            filtered_recs = {}
            for t, recs in recommendations.items():
                if ticker and t != ticker:
                    continue
                filtered_recommendations = []
                for rec in recs:
                    if rec_type and rec["recommendation"] != rec_type:
                        continue
                    filtered_recommendations.append(rec)
                if filtered_recommendations:
                    filtered_recs[t] = filtered_recommendations
            recommendations = filtered_recs
    else:
        # Default: show today's recommendations
        recommendations = get_todays_recommendations()
        today_only = True
        # Apply additional filters if needed
        if rec_type or ticker:
            filtered_recs = {}
            for t, recs in recommendations.items():
                if ticker and t != ticker:
                    continue
                filtered_recommendations = []
                for rec in recs:
                    if rec_type and rec["recommendation"] != rec_type:
                        continue
                    filtered_recommendations.append(rec)
                if filtered_recommendations:
                    filtered_recs[t] = filtered_recommendations
            recommendations = filtered_recs

    # Get related articles for each recommended stock
    stock_data = {}
    for ticker_key, recs in recommendations.items():
        related_articles = get_related_articles_for_stock(ticker_key)
        stock_data[ticker_key] = {
            "recommendations": recs,
            "related_articles": related_articles[:5]  # Limit to 5 most relevant
        }

    # Get recommendation statistics for the template
    stats = get_recommendation_stats()

    return render_template("recommendations.html",
                            stock_data=stock_data,
                            filter_type=rec_type,
                            filter_ticker=ticker,
                            filter_date=date_filter,
                            today_only=today_only,
                            today_date=datetime.now().strftime("%B %d, %Y"),
                            stats=stats
                            )

@app.route("/api/recommendations/today")
def api_todays_recommendations():
    """
    API endpoint to get today's recommendations as JSON
    """
    try:
        recommendations = get_todays_recommendations()
        stats = get_recommendation_stats()
        
        return jsonify({
            "status": "success",
            "date": date.today().isoformat(),
            "stats": stats,
            "recommendations": recommendations
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route("/api/recommendations/date/<date_str>")
def api_recommendations_by_date(date_str):
    """
    API endpoint to get recommendations for a specific date as JSON
    """
    try:
        # Validate date format
        datetime.strptime(date_str, "%Y-%m-%d")
        
        recommendations = get_recommendations_by_date(date_str)
        
        return jsonify({
            "status": "success",
            "date": date_str,
            "recommendations": recommendations
        }), 200
    except ValueError:
        return jsonify({
            "status": "error",
            "message": "Invalid date format. Use YYYY-MM-DD"
        }), 400
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route("/recommendations/delete", methods=["POST"])
def delete_recommendation():
    data = request.get_json()
    ticker = data.get("ticker")
    rec_id_part = data.get("rec_id")  # e.g., "BUY_2023-10-27"

    if not ticker:
        return jsonify({"status": "error", "message": "Ticker not provided"}), 400

    try:
        if rec_id_part:
            parts = rec_id_part.split('_')
            if len(parts) == 2:
                recommendation_type = parts[0]
                date_str = parts[1]
                sqlite_id = f"{ticker}_{date_str}_{recommendation_type}"

                print(f"[delete_recommendation] Attempting to mark ID as inactive: {sqlite_id}")
                success = mark_recommendation_inactive_sqlite(sqlite_id)
                
                if success:
                    return jsonify({
                        "status": "success",
                        "message": f"Recommendation for {ticker} ({recommendation_type} on {date_str}) marked inactive"
                    }), 200
                else:
                    return jsonify({"status": "info", "message": "Recommendation not found."}), 404

        # No rec_id_part — mark all recommendations for the ticker as inactive
        print(f"[delete_recommendation] No rec_id_part provided. Marking all for ticker {ticker} as inactive.")
        affected = mark_ticker_recommendations_inactive_sqlite(ticker)
        
        if affected > 0:
            return jsonify({"status": "success", "message": f"All {affected} recommendations for {ticker} marked as inactive"}), 200
        else:
            return jsonify({"status": "info", "message": f"No active recommendations found for {ticker}."}), 200

    except Exception as e:
        print(f"[delete_recommendation] Error marking recommendation inactive for {ticker}: {e}")
        return jsonify({"status": "error", "message": f"Error updating {ticker}: {str(e)}"}), 500

def mark_old_recommendations_inactive(days_old=3):
    """Mark old recommendations as inactive using SQLite."""
    try:
        affected = cleanup_old_recommendations(days_old)
        print(f"[cleanup] Marked {affected} old recommendations as inactive.")
        return affected
    except Exception as e:
        print(f"[cleanup] Error during cleanup: {e}")
        return 0

def summarize_market_report(input_path="market_report.md", output_path="market_summary.md"):
    """
    Reads the full market report and summarizes it using the configured LLM.
    """
    # Step 1: Read report from disk
    if not os.path.exists(input_path):
        print(f"[ERROR] File not found: {input_path}")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        report_content = f.read()

    # Step 2: Prepare LLM prompt/messages
    messages = [
    {
        "role": "system",
        "content": (
            "You are an expert market strategist who generates insights for professional traders and fund managers. "
            "Your job is to analyze market news and extract useful, actionable patterns based on real companies, sectors, or commodities. "
            "Never invent ticker symbols, and do not provide recommendations on things that cannot be traded (like 'Congress')."
        )
    },
    {
        "role": "user",
        "content": (
            "Analyze the following market report and provide a concise summary in 6–10 bullet points. "
            "Focus on sector movement, key stock or commodity events, and macroeconomic factors driving behavior. "
            "Extract meaningful relationships between events (e.g. 'food stocks down due to rising oil prices'). "
            "Avoid vague or generic commentary. Only refer to real, investable sectors, commodities, or companies. "
            "Do not include financial advice, disclaimers, or language like 'as an AI'."
            "\n\n"
            f"{report_content}"
        )
    }
]


    # Step 3: Prepare and send the request to the LLM
    endpoint, headers, payload = prepare_llm_request(messages)
    try:
        response = requests.post(endpoint, json=payload, headers=headers)
        response.raise_for_status()
        summary = response.json()["choices"][0]["message"]["content"]
        #summary = re.sub(r"<\s*think\s*>.*?<\s*/\s*think\s*>", "", summary, flags=re.DOTALL | re.IGNORECASE)
        #summary = re.sub(r"<\s*/?\s*think\s*>", "", summary, flags=re.IGNORECASE)
        # Strip everything before and including a closing </think> tag
        summary = re.sub(r"^.*?</\s*think\s*>", "", summary, flags=re.DOTALL | re.IGNORECASE).strip()

    except Exception as e:
        print(f"[ERROR] Failed to get summary from LLM: {e}")
        return

    # Step 4: Write output
    with open(output_path, "w", encoding="utf-8") as f:
        # f.write("# MarketGPT Summary\n\n")
        f.write(summary.strip())

    print(f"[✅] Market summary saved to {output_path}")


def periodic_fetch_and_report():
    while True:
        try:
            print("[periodic] Starting periodic task...")

            try:
                print("[periodic] Fetching articles...")
                fetch_and_store(feed_urls)
                print("[periodic] Fetch done.")
            except Exception as e:
                print(f"[periodic] Error during fetch_and_store: {e}")
                traceback.print_exc()
                time.sleep(300)  # Wait 5 minutes before next run
                continue

            try:
                print("[periodic] Generating report...")
                generate_market_report(collection, model)
                print("[periodic] Report generated.")
            except Exception as e:
                print(f"[periodic] Error during generate_market_report: {e}")
                traceback.print_exc()
            try:
                print("[periodic] Summarizing report...")
                summarize_market_report()
                print("[periodic] Report summarized.")
            except Exception as e:
                print(f"[periodic] Error during summarize_market_report: {e}")
                traceback.print_exc()
            try:
                print("[periodic] Extracting stock recommendations...")
                extract_stock_recommendations(collection, model, today_str)
                print("[periodic] Recommendations extracted.")
            except Exception as e:
                print(f"[periodic] Error during extract_stock_recommendations: {e}")
                traceback.print_exc()
            # Turn this back on to clean up old recommendations every X days on the repeating cycle
            try:
                print("[periodic] Cleaning up old recommendations...")
                mark_old_recommendations_inactive(days_old=3)
                print("[periodic] Old recommendations cleaned up.")
            except Exception as e:
                print(f"[periodic] Error during cleanup: {e}")
                traceback.print_exc()
            print("[periodic] Sleeping for 15 minutes...")
            time.sleep(15 * 60)  # 15 minutes
        except KeyboardInterrupt:
            print("[periodic] Periodic task interrupted by user.")
            break

        except Exception as e:
            print(f"[periodic] Unexpected top-level error: {e}")
            traceback.print_exc()
            print("[periodic] Waiting 5 minutes before retrying...")
            time.sleep(300)

if __name__ == "__main__":
    # Start background thread before Flask server
    thread = threading.Thread(target=periodic_fetch_and_report, daemon=True)
    thread.start()

    # Get port from environment variable, fallback to 5070
    port = int(os.getenv("PORT", "5070"))
    debug_mode = os.getenv("FLASK_ENV") != "production"
    
    print(f"[app] Starting Flask server on port {port} (debug={debug_mode})")
    app.run(port=port, debug=debug_mode, host="0.0.0.0")