# app.py
from apscheduler.schedulers.background import BackgroundScheduler
from chromadb.config import Settings
from collections import defaultdict
from datetime import datetime
from dateutil import parser as date_parser
from flask import Flask, jsonify
from flask import render_template_string
from flask import request, render_template
from markupsafe import Markup
from sentence_transformers import SentenceTransformer
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from zoneinfo import ZoneInfo
import chromadb
import feedparser
import json
import markdown
import numpy as np
import os
import os
import random
import re
import requests
import sys
import threading
import time
import time
import time
import trafilatura
import uuid
import traceback


#today_str = datetime.now().strftime("%Y-%m-%d")
today_str = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")

app = Flask(__name__)

# Setup Chroma
client = chromadb.Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory="./chroma"))
collection = client.get_or_create_collection(name="marketwatch")
recommendations_collection = client.get_or_create_collection(name="stock_recommendations")

def load_llm_config(path="llm_config.json"):
    default_config = {
        "provider": "local",
        "endpoint": "http://localhost:1234/v1/chat/completions",
        "api_key": None
    }
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                user_config = json.load(f)
                return {**default_config, **user_config}
        except Exception as e:
            print(f"[llm_config] Failed to load config, using default. Error: {e}")
    return default_config

llm_config = load_llm_config()
# Check if the LLM config is valid
if llm_config["provider"] not in ["local", "openai", "claude"]:
    print(f"[llm_config] Invalid provider '{llm_config['provider']}' in llm_config.json. Using default 'local'.")
    llm_config["provider"] = "local"
# If using OpenAI or Claude, ensure the endpoint is set correctly
if llm_config["provider"] in ["openai", "claude"]:
    if not llm_config["endpoint"]:
        print("[llm_config] Endpoint is required for OpenAI or Claude. Using default endpoint.")
        llm_config["endpoint"] = "https://api.openai.com/v1/chat/completions" if llm_config["provider"] == "openai" else "https://api.anthropic.com/v1/complete"
    if not llm_config["api_key"]:
        print("[llm_config] API key is required for OpenAI or Claude. Please set it in llm_config.json.")
        sys.exit(1)
# If using local LLM, ensure the endpoint is set correctly
if llm_config["provider"] == "local":
    if not llm_config["endpoint"]:
        print("[llm_config] Endpoint is required for local LLM. Using default endpoint.")
        llm_config["endpoint"] = "http://localhost:1234/v1/chat/completions"
# Ensure the local endpoint is reachable
try:
    response = requests.get(llm_config["endpoint"])
    if response.status_code != 200:
        print(f"[llm_config] Local LLM endpoint {llm_config['endpoint']} is not reachable. Please check your setup.")
        sys.exit(1)
except requests.RequestException as e:
    print(f"[llm_config] Error connecting to local LLM endpoint: {e}")
    sys.exit(1)

# Prepare LLM messages and send them to the endpoint
def prepare_llm_request(messages, temperature=0.7):
    provider = llm_config.get("provider", "local")
    endpoint = llm_config["endpoint"]
    headers = {}
    payload = {
        "messages": messages,
        "temperature": temperature
    }

    if provider in ["openai", "claude"]:
        headers["Authorization"] = f"Bearer {llm_config['api_key']}"
        if llm_config.get("model"):
            payload["model"] = llm_config["model"]
    else:
        # local provider — only add model if set
        if llm_config.get("model"):
            payload["model"] = llm_config["model"]

    return endpoint, headers, payload


# SentenceTransformer model
model = SentenceTransformer('all-MiniLM-L6-v2')

feed_urls = [
    "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
    "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100727362",
    "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=15837362",
    "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=19832390",
    "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=19794221",
    "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147",
    "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=15839135",
    "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100370673",
    "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258",
    "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664",
    "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=19854910",
    "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000113",
    "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000108",
    "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000115",
    "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001054",
    "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=19836768",
    "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000110",
    "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000116",
    "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000739",
    "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=44877279",
    "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=103395579",
    "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147",
    "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258",
    "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664"
    # add more RSS URLs here
]

def fetch_full_article(url):
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            return trafilatura.extract(downloaded, include_comments=False, include_tables=False)
    except Exception as e:
        print(f"[fetch_full_article] Error fetching {url}: {e}")
    return None


def fetch_rss_multiple(feed_urls):
    all_entries = []
    for url in feed_urls:
        parsed_feed = feedparser.parse(url)
        entries = parsed_feed.entries
        print(f"[fetch_rss_multiple] Fetched {len(entries)} entries from {url}")
        all_entries.extend(entries)
    return all_entries


def embed_text(texts):
    return model.encode(texts).tolist()

def fetch_and_store(feed_urls, delay_between=1.0):
    print("[fetch_and_store] Starting fetch...")

    entries = fetch_rss_multiple(feed_urls)
    total = len(entries)
    added = 0

    print(f"[fetch_and_store] Total {total} entries fetched from all RSS feeds.")

    for i, entry in enumerate(entries, 1):
        title = entry.get("title", "")
        summary = entry.get("summary", "")
        link = entry.get("link", "")
        if not link:
            print(f"[{i}/{total}] Skipping entry with missing link.")
            continue  # skip malformed entry
        published = entry.get("published") or entry.get("pubDate") or ""
        published_date = ""

        if published:
            try:
                parsed = date_parser.parse(published)
                published_date = parsed.strftime("%Y-%m-%d")
            except Exception as e:
                print(f"[{i}/{total}] Failed to parse published date: {published}")

        # Skip if already in DB
        existing = collection.get(where={"link": link})
        if existing["ids"]:
            print(f"[{i}/{total}] Skipping already stored link: {link}")
            continue

        print(f"[{i}/{total}] Fetching full article from: {link}")
        # Fetch full article
        full_article = fetch_full_article(link)
        if full_article and len(full_article) > 200:
            text = f"{title}. {full_article}"
            print(f"[{i}/{total}] Using full article content (length={len(full_article)})")
        else:
            text = f"{title}. {summary}"
            print(f"[{i}/{total}] Using summary content (length={len(summary)})")

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
        print(f"[{i}/{total}] Added document id={doc_id} to collection.")

        # Delay to throttle
        time.sleep(delay_between + random.uniform(0, 0.5))  # jitter helps mimic natural behavior

    print(f"[fetch_and_store] Inserted {added} new entries into the database.")



@app.route("/report")
def view_market_report():
    if not os.path.exists("market_report.md"):
        return "Report not found.", 404

    with open("market_report.md", "r", encoding="utf-8") as f:
        md_content = f.read()

    # Convert markdown to HTML
    html_content = markdown.markdown(
        md_content,
        extensions=["extra", "toc", "sane_lists"]
    )

    return render_template("report.html", report_html=html_content)

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
        user_input = request.form["question"]
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
Cite all sources using [markdown links](http://example.com/markdown-links). 
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

        # Call LLM
        # response = requests.post(
        #     "http://192.168.1.220:1234/v1/chat/completions",
        #     json={
        #         "messages": messages,
        #         "temperature": 0.7,
        #     }
        # )
        endpoint, headers, payload = prepare_llm_request(messages, temperature=0.7)
        response = requests.post(endpoint, headers=headers, json=payload)
        response.raise_for_status()


        raw_answer = response.json()["choices"][0]["message"]["content"]
        cleaned_answer = re.sub(r"<think>.*?</think>", "", raw_answer, flags=re.DOTALL | re.IGNORECASE)
        rendered_answer = Markup(markdown.markdown(cleaned_answer))

        reveal_reason_text = "\n\n---\n\n".join([
            f"{meta.get('title', 'No title')} ({meta.get('link', '#')}) - Published: {meta.get('published_date', 'Unknown')}\n\n{doc}"
            for doc, meta in zip(docs, metas)
        ])

        return render_template("chat.html", question=user_input, answer=rendered_answer, context=reveal_reason_text)

    return render_template("chat.html")


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

def generate_market_report(collection, model: SentenceTransformer, top_k=10, output_path="market_report.md"):
    report_lines = ["# MarketGPT Daily Report\n"]
    seen_article_links = set()  # Track which articles have already been included

    for category, phrases in CATEGORIES.items():
        # Use the first phrase as the representative embedding query
        topic_query = phrases[0]
        embedding = model.encode([topic_query])[0]

        results = collection.query(
            query_embeddings=[embedding.tolist()],
            n_results=top_k * 3,  # Fetch more to allow for filtering/deduplication
            include=["documents", "metadatas"],
            where={"published_date": today_str}
        )

        docs = results["documents"][0]
        metas = results["metadatas"][0]

        articles_for_category = []
        for doc, meta in zip(docs, metas):
            link = meta.get("link")
            if not link or link in seen_article_links:
                continue

            # Optional: apply keyword filter for extra precision
            if not any(keyword.lower() in doc.lower() for keyword in phrases):
                continue

            articles_for_category.append((doc, meta))
            seen_article_links.add(link)

            if len(articles_for_category) >= top_k:
                break

        if not articles_for_category:
            report_lines.append(f"## {category}\n_No matching articles found for today._\n---\n")
            continue

        report_lines.append(f"## {category}\n")
        for i, (doc, meta) in enumerate(articles_for_category, 1):
            title = meta.get("title", "No title")
            link = meta.get("link", "#")
            published = meta.get("published", "Unknown date")
            report_lines.append(f"{i}. [{title}]({link})  \nPublished: {published}\n")
        report_lines.append("\n---\n")

    # Save the final markdown report
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    print(f"[generate_market_report] Report saved to {output_path}")


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
                "content": """You are a financial analyst. Analyze news articles and identify any stock buy/sell signals.

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
            # Remove any <think> tags
            raw_response = re.sub(r"<think>.*?</think>", "", raw_response, flags=re.DOTALL | re.IGNORECASE)
            # Remove any markdown formatting
            raw_response = re.sub(r"```json\s*([\s\S]*?)\s*```", r"\1", raw_response)
            # Clean up any extra whitespace
            raw_response = raw_response.strip()
            # Parse JSON response
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
    Store stock recommendations in ChromaDB
    """
    for rec in recommendations:
        # Create unique ID based on ticker and date
        rec_id = f"{rec['ticker']}_{date_str}_{rec['recommendation']}"

        # Check if already exists - use a simpler approach
        # Query by the unique ID we're about to create
        try:
            existing = recommendations_collection.get(ids=[rec_id])
            if existing["ids"]:
                print(f"[store_recommendations] Recommendation already exists: {rec['ticker']} {rec['recommendation']}")
                continue
        except Exception as e:
            # If ID doesn't exist, that's fine - we'll create it
            pass

        # Create embedding of the recommendation text
        rec_text = f"{rec['company']} {rec['ticker']} {rec['recommendation']} {rec['reason']}"
        embedding = embed_text([rec_text])[0]

        # Store in collection
        try:
            print(f"[store_recommendations] Storing recommendation with ID: {rec_id}")
            recommendations_collection.add(
            documents=[rec_text],
            embeddings=[embedding],
            ids=[rec_id],
            metadatas=[{
                "company": rec["company"],
                "ticker": rec["ticker"],
                "recommendation": rec["recommendation"],
                "reason": rec["reason"],
                "confidence": rec["confidence"],
                "article_title": rec["article_title"],
                "article_url": rec["article_url"],
                "date": date_str,
                "timestamp": datetime.now().isoformat()
            }]
            )
            print(f"[store_recommendations] Stored: {rec['ticker']} - {rec['recommendation']}")
        except Exception as e:
            print(f"[store_recommendations] Error storing recommendation ID={rec_id}: {e}")
            traceback.print_exc()  # This gives you the full context and stack trace


def get_stock_recommendations(ticker=None, recommendation_type=None, days_back=7):
    """
    Retrieve stock recommendations with optional filtering
    """
    try:
        # Get all recommendations first, then filter in Python
        # ChromaDB's where clause is limited, so we'll do post-filtering
        results = recommendations_collection.get(
            include=["documents", "metadatas"]
        )

        # Filter results based on parameters
        filtered_docs = []
        filtered_metas = []
        
        for doc, meta in zip(results["documents"], results["metadatas"]):
            # Apply filters
            if ticker and meta.get("ticker") != ticker:
                continue
            if recommendation_type and meta.get("recommendation") != recommendation_type:
                continue
            
            # You can add date filtering here if needed
            # if days_back and is_older_than(meta.get("date"), days_back):
            #     continue
            
            filtered_docs.append(doc)
            filtered_metas.append(meta)

        # Group by ticker for easier display
        grouped_recs = defaultdict(list)

        for doc, meta in zip(filtered_docs, filtered_metas):
            ticker_key = meta["ticker"]
            grouped_recs[ticker_key].append({
                "company": meta["company"],
                "recommendation": meta["recommendation"],
                "reason": meta["reason"],
                "confidence": meta["confidence"],
                "article_title": meta["article_title"],
                "article_url": meta["article_url"],
                "date": meta["date"],
                "timestamp": meta["timestamp"]
            })

        return dict(grouped_recs)
    
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
    Display stock buy/sell recommendations
    """
    rec_type = request.args.get("type")  # "BUY" or "SELL"
    ticker = request.args.get("ticker")

    recommendations = get_stock_recommendations(
        ticker=ticker,
        recommendation_type=rec_type
    )

    # Get related articles for each recommended stock
    stock_data = {}
    for ticker, recs in recommendations.items():
        related_articles = get_related_articles_for_stock(ticker)
        stock_data[ticker] = {
            "recommendations": recs,
            "related_articles": related_articles[:5]  # Limit to 5 most relevant
        }

    return render_template("recommendations.html",
                            stock_data=stock_data,
                            filter_type=rec_type,
                            filter_ticker=ticker
                            )

@app.route("/recommendations/delete", methods=["POST"])
def delete_recommendation():
    data = request.get_json()
    ticker = data.get("ticker")
    # The rec_id in the HTML is a combination of recommendation type and date,
    # but the actual ID in ChromaDB is ticker_date_recommendation
    # We need to construct the correct ID to delete.
    # However, the `store_recommendations` function creates an id like: f"{rec['ticker']}_{date_str}_{rec['recommendation']}"
    # We need to ensure we can reconstruct this or have enough info.
    # Let's assume for now the client will send enough info to identify the specific document.
    # A simpler approach might be to delete ALL recommendations for a ticker.

    rec_id_part = data.get("rec_id") # This might be like "BUY_2023-10-27"

    if not ticker:
        return jsonify({"status": "error", "message": "Ticker not provided"}), 400

    try:
        # Option 1: Delete all recommendations for a ticker if specific ID is hard to get
        # results = recommendations_collection.get(where={"ticker": ticker})
        # if results["ids"]:
        #     recommendations_collection.delete(ids=results["ids"])
        #     return jsonify({"status": "success", "message": f"Stopped watching {ticker}"}), 200
        # else:
        #     return jsonify({"status": "error", "message": f"No recommendations found for {ticker}"}), 404

        # Option 2: Attempt to delete a specific recommendation if we can form the ID.
        # The button sends `data-rec-id="{{ rec.recommendation }}_{{ rec.date }}"`
        # The ID in DB is `f"{ticker}_{date}_{recommendation}"`
        # So, if rec_id_part is "BUY_2023-11-01", and ticker is "AAPL",
        # the DB ID would be "AAPL_2023-11-01_BUY".
        if rec_id_part:
            parts = rec_id_part.split('_')
            if len(parts) == 2:
                recommendation_type = parts[0]
                date_str = parts[1]
                chroma_id_to_delete = f"{ticker}_{date_str}_{recommendation_type}"

                print(f"[delete_recommendation] Attempting to delete ID: {chroma_id_to_delete}")
                try:
                    recommendations_collection.delete(ids=[chroma_id_to_delete])
                    print(f"[delete_recommendation] Successfully deleted ID: {chroma_id_to_delete}")
                    return jsonify({"status": "success", "message": f"Recommendation for {ticker} ({recommendation_type} on {date_str}) removed"}), 200
                except Exception as e:
                    # This might fail if the ID doesn't exist, which is okay.
                    # Or it could be a more serious error.
                    # ChromaDB's delete doesn't error if ID not found, it just does nothing.
                    # So we might need to check if it existed first if we want to give specific feedback.
                    print(f"[delete_recommendation] Info: Could not delete ID {chroma_id_to_delete} (may not exist or error): {e}")
                    # Fallback: try deleting all for the ticker if specific delete seems to fail or if that's preferred.
                    # For now, let's assume specific delete is what's wanted.
                    # If it didn't delete, it might be because the ID was wrong or it was already gone.
                    # We can refine this if the specific ID is not working as expected.
                    # A robust way is to query first, then delete.
                    existing_rec = recommendations_collection.get(ids=[chroma_id_to_delete])
                    if not existing_rec["ids"]:
                        return jsonify({"status": "info", "message": f"Recommendation for {ticker} ({recommendation_type} on {date_str}) already removed or not found."}), 200


            # If rec_id_part is not in the expected format, or if specific deletion is too complex,
            # fall back to deleting all recommendations for the ticker.
            # This is a safer bet if the ID matching is tricky.
            print(f"[delete_recommendation] rec_id_part '{rec_id_part}' not usable for specific deletion, or specific deletion failed. Checking all for ticker {ticker}.")
            results = recommendations_collection.get(where={"ticker": ticker})
            if results["ids"]:
                recommendations_collection.delete(ids=results["ids"])
                print(f"[delete_recommendation] Deleted ALL recommendations for ticker: {ticker}")
                return jsonify({"status": "success", "message": f"Stopped watching all recommendations for {ticker}"}), 200
            else:
                print(f"[delete_recommendation] No recommendations found for ticker {ticker} to delete.")
                return jsonify({"status": "info", "message": f"No recommendations found for {ticker} to remove."}), 200

        else: # if no rec_id_part, delete all for the ticker
            print(f"[delete_recommendation] No rec_id_part provided. Deleting all for ticker {ticker}.")
            results = recommendations_collection.get(where={"ticker": ticker})
            if results["ids"]:
                recommendations_collection.delete(ids=results["ids"])
                return jsonify({"status": "success", "message": f"Stopped watching all recommendations for {ticker}"}), 200
            else:
                return jsonify({"status": "info", "message": f"No recommendations found for {ticker} to remove."}), 200


    except Exception as e:
        print(f"[delete_recommendation] Error deleting recommendation for {ticker}: {e}")
        return jsonify({"status": "error", "message": f"Error stopping watching {ticker}: {str(e)}"}), 500


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
                print("[periodic] Extracting stock recommendations...")
                extract_stock_recommendations(collection, model, today_str)
                print("[periodic] Recommendations extracted.")
            except Exception as e:
                print(f"[periodic] Error during extract_stock_recommendations: {e}")
                traceback.print_exc()

            print("[periodic] Sleeping for 15 minutes...")
            time.sleep(15 * 60)  # 15 minutes

        except Exception as e:
            print(f"[periodic] Unexpected top-level error: {e}")
            traceback.print_exc()
            print("[periodic] Waiting 5 minutes before retrying...")
            time.sleep(300)

if __name__ == "__main__":
    # Start background thread before Flask server
    thread = threading.Thread(target=periodic_fetch_and_report, daemon=True)
    thread.start()

    app.run(port=5020, debug=True, host="0.0.0.0")
