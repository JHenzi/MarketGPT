"""
SQLite database utilities for stock recommendations.
Provides date-based querying for "today's recommendations" functionality.
"""

import sqlite3
import json
from datetime import datetime, date, timedelta
from collections import defaultdict
from typing import List, Dict, Optional, Any

try:
    from dateutil import parser as date_parser
except ImportError:
    date_parser = None

DB_FILE = "recommendations.sqlite"

def get_db_connection() -> sqlite3.Connection:
    """Get SQLite database connection with row factory."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_recommendations_db():
    """Initialize the recommendations database with proper schema and indexes."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recommendations (
        id TEXT PRIMARY KEY,
        company TEXT NOT NULL,
        ticker TEXT NOT NULL,
        recommendation TEXT NOT NULL,
        reason TEXT,
        confidence TEXT,
        article_title TEXT,
        article_url TEXT,
        date TEXT NOT NULL,
        timestamp TEXT,
        active INTEGER DEFAULT 1,
        embedding_json TEXT
    )
    """)
    
    # Create indexes for efficient querying
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ticker ON recommendations (ticker)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_recommendation ON recommendations (recommendation)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_date ON recommendations (date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_active ON recommendations (active)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ticker_date ON recommendations (ticker, date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_active_date ON recommendations (active, date)")
    
    # Create feed_metadata table for performance optimizations
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS feed_metadata (
        feed_url TEXT PRIMARY KEY,
        last_check_time TEXT NOT NULL,
        last_article_date TEXT,
        etag TEXT,
        last_modified TEXT,
        update_frequency_hours REAL,
        total_articles_processed INTEGER DEFAULT 0,
        last_successful_check TEXT,
        consecutive_failures INTEGER DEFAULT 0
    )
    """)
    
    # Create processed_articles table to track which articles have been analyzed by AI
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS processed_articles (
        article_url TEXT PRIMARY KEY,
        processed_date TEXT NOT NULL,
        processed_timestamp TEXT NOT NULL,
        recommendation_count INTEGER DEFAULT 0
    )
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_feed_last_check ON feed_metadata (last_check_time)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_processed_date ON processed_articles (processed_date)")
    
    conn.commit()
    conn.close()

def store_recommendations_sqlite(recommendations: List[Dict[str, Any]], date_str: str):
    """Store multiple recommendations in SQLite database."""
    if not recommendations:
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    stored_count = 0
    for rec in recommendations:
        try:
            rec_id = f"{rec['ticker']}_{date_str}_{rec['recommendation']}"
            
            cursor.execute("""
            INSERT OR REPLACE INTO recommendations
            (id, company, ticker, recommendation, reason, confidence,
             article_title, article_url, date, timestamp, active, embedding_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rec_id,
                rec["company"],
                rec["ticker"],
                rec["recommendation"],
                rec["reason"],
                rec["confidence"],
                rec["article_title"],
                rec["article_url"],
                date_str,
                datetime.now().isoformat(),
                1,
                None  # We can add embedding support later if needed
            ))
            stored_count += 1
            
        except Exception as e:
            print(f"[store_recommendations_sqlite] Error storing recommendation {rec.get('ticker', 'unknown')}: {e}")
            continue
    
    conn.commit()
    conn.close()
    print(f"[store_recommendations_sqlite] Stored {stored_count} recommendations for {date_str}")

def get_recommendations_sqlite(
    ticker: Optional[str] = None,
    recommendation_type: Optional[str] = None,
    date_filter: Optional[str] = None,
    active_only: bool = True,
    today_only: bool = False
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Get recommendations from SQLite with various filters.
    Returns grouped recommendations by ticker.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM recommendations"
    conditions = []
    params = []
    
    if active_only:
        conditions.append("active = ?")
        params.append(1)
    
    if ticker:
        conditions.append("ticker = ?")
        params.append(ticker)
    
    if recommendation_type:
        conditions.append("recommendation = ?")
        params.append(recommendation_type)
    
    if today_only:
        # Use NY timezone to match how recommendations are stored
        from zoneinfo import ZoneInfo
        from datetime import datetime
        today_str = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
        conditions.append("date = ?")
        params.append(today_str)
    elif date_filter:
        conditions.append("date = ?")
        params.append(date_filter)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY date DESC, timestamp DESC"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    # Group by ticker
    grouped_recs = defaultdict(list)
    for row in rows:
        ticker_key = row["ticker"]
        grouped_recs[ticker_key].append({
            "company": row["company"],
            "recommendation": row["recommendation"],
            "reason": row["reason"],
            "confidence": row["confidence"],
            "article_title": row["article_title"],
            "article_url": row["article_url"],
            "date": row["date"],
            "timestamp": row["timestamp"],
            "id": row["id"]
        })
    
    return dict(grouped_recs)

def get_todays_recommendations() -> Dict[str, List[Dict[str, Any]]]:
    """Get all active recommendations for today using NY timezone."""
    from zoneinfo import ZoneInfo
    from datetime import datetime
    # Use NY timezone to match how recommendations are stored
    today_str = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
    return get_recommendations_sqlite(today_only=False, date_filter=today_str, active_only=True)

def get_recommendations_by_date(date_str: str) -> Dict[str, List[Dict[str, Any]]]:
    """Get all active recommendations for a specific date."""
    return get_recommendations_sqlite(date_filter=date_str, active_only=True)

def mark_recommendation_inactive_sqlite(rec_id: str) -> bool:
    """Mark a specific recommendation as inactive."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("UPDATE recommendations SET active = 0 WHERE id = ?", (rec_id,))
        conn.commit()
        success = cursor.rowcount > 0
        
        if success:
            print(f"[mark_recommendation_inactive_sqlite] Marked {rec_id} as inactive")
        else:
            print(f"[mark_recommendation_inactive_sqlite] No recommendation found with ID {rec_id}")
        
        return success
    
    except Exception as e:
        print(f"[mark_recommendation_inactive_sqlite] Error: {e}")
        return False
    finally:
        conn.close()

def mark_ticker_recommendations_inactive_sqlite(ticker: str) -> int:
    """Mark all recommendations for a ticker as inactive. Returns number affected."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("UPDATE recommendations SET active = 0 WHERE ticker = ? AND active = 1", (ticker,))
        conn.commit()
        affected = cursor.rowcount
        
        print(f"[mark_ticker_recommendations_inactive_sqlite] Marked {affected} recommendations inactive for {ticker}")
        return affected
    
    except Exception as e:
        print(f"[mark_ticker_recommendations_inactive_sqlite] Error: {e}")
        return 0
    finally:
        conn.close()

def get_recommendation_stats() -> Dict[str, int]:
    """Get basic statistics about recommendations."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    stats = {}
    
    # Total recommendations
    cursor.execute("SELECT COUNT(*) FROM recommendations")
    stats["total"] = cursor.fetchone()[0]
    
    # Active recommendations
    cursor.execute("SELECT COUNT(*) FROM recommendations WHERE active = 1")
    stats["active"] = cursor.fetchone()[0]
    
    # Today's recommendations (using NY timezone to match storage)
    from zoneinfo import ZoneInfo
    from datetime import datetime
    today_str = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
    cursor.execute("SELECT COUNT(*) FROM recommendations WHERE active = 1 AND date = ?", (today_str,))
    stats["today"] = cursor.fetchone()[0]
    
    # Unique tickers
    cursor.execute("SELECT COUNT(DISTINCT ticker) FROM recommendations WHERE active = 1")
    stats["unique_tickers"] = cursor.fetchone()[0]
    
    # BUY vs SELL
    cursor.execute("SELECT COUNT(*) FROM recommendations WHERE active = 1 AND recommendation = 'BUY'")
    stats["buy_count"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM recommendations WHERE active = 1 AND recommendation = 'SELL'")
    stats["sell_count"] = cursor.fetchone()[0]
    
    conn.close()
    return stats

def cleanup_old_recommendations(days_old: int = 7) -> int:
    """Mark old recommendations as inactive. Returns number affected."""
    from datetime import timedelta
    from zoneinfo import ZoneInfo
    from datetime import datetime
    
    # Use NY timezone to match how recommendations are stored
    today = datetime.now(ZoneInfo("America/New_York")).date()
    cutoff_date = (today - timedelta(days=days_old)).isoformat()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
        UPDATE recommendations 
        SET active = 0 
        WHERE date < ? AND active = 1
        """, (cutoff_date,))
        
        conn.commit()
        affected = cursor.rowcount
        
        print(f"[cleanup_old_recommendations] Marked {affected} recommendations inactive (older than {days_old} days)")
        return affected
    
    except Exception as e:
        print(f"[cleanup_old_recommendations] Error: {e}")
        return 0
    finally:
        conn.close()

def delete_old_recommendations(days_old: int = 7) -> int:
    """Permanently delete old recommendations (not just mark inactive). Returns number deleted."""
    from datetime import timedelta
    from zoneinfo import ZoneInfo
    from datetime import datetime
    
    # Use NY timezone to match how recommendations are stored
    today = datetime.now(ZoneInfo("America/New_York")).date()
    cutoff_date = (today - timedelta(days=days_old)).isoformat()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
        DELETE FROM recommendations 
        WHERE date < ?
        """, (cutoff_date,))
        
        conn.commit()
        deleted = cursor.rowcount
        
        print(f"[delete_old_recommendations] Deleted {deleted} recommendations (older than {days_old} days)")
        return deleted
    
    except Exception as e:
        print(f"[delete_old_recommendations] Error: {e}")
        return 0
    finally:
        conn.close()

# Feed metadata functions for performance optimization
def get_feed_metadata(feed_url: str) -> Optional[Dict[str, Any]]:
    """Get metadata for a specific feed."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM feed_metadata WHERE feed_url = ?", (feed_url,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None

def update_feed_metadata(feed_url: str, last_check_time: str, last_article_date: Optional[str] = None,
                        etag: Optional[str] = None, last_modified: Optional[str] = None,
                        articles_processed: int = 0, success: bool = True):
    """Update or create feed metadata."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    existing = get_feed_metadata(feed_url)
    
    if existing:
        # Update existing
        consecutive_failures = 0 if success else existing.get("consecutive_failures", 0) + 1
        total_articles = existing.get("total_articles_processed", 0) + articles_processed
        
        # Calculate update frequency (average hours between checks)
        update_frequency = existing.get("update_frequency_hours")
        if date_parser:
            try:
                last_check = date_parser.parse(existing["last_check_time"])
                current_check = date_parser.parse(last_check_time)
                hours_since = (current_check - last_check).total_seconds() / 3600
                if hours_since > 0:
                    # Exponential moving average
                    old_freq = existing.get("update_frequency_hours") or hours_since
                    update_frequency = (old_freq * 0.7) + (hours_since * 0.3)
            except Exception:
                pass
        
        cursor.execute("""
            UPDATE feed_metadata 
            SET last_check_time = ?,
                last_article_date = COALESCE(?, last_article_date),
                etag = COALESCE(?, etag),
                last_modified = COALESCE(?, last_modified),
                total_articles_processed = ?,
                last_successful_check = CASE WHEN ? = 1 THEN ? ELSE last_successful_check END,
                consecutive_failures = ?,
                update_frequency_hours = COALESCE(?, update_frequency_hours)
            WHERE feed_url = ?
        """, (last_check_time, last_article_date, etag, last_modified, total_articles,
             1 if success else 0, last_check_time, consecutive_failures, update_frequency, feed_url))
    else:
        # Insert new
        cursor.execute("""
            INSERT INTO feed_metadata 
            (feed_url, last_check_time, last_article_date, etag, last_modified, 
             total_articles_processed, last_successful_check, consecutive_failures)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (feed_url, last_check_time, last_article_date, etag, last_modified,
              articles_processed, last_check_time if success else None, 0 if success else 1))
    
    conn.commit()
    conn.close()

def is_article_processed(article_url: str) -> bool:
    """Check if an article has already been processed by the AI agent."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT 1 FROM processed_articles WHERE article_url = ?", (article_url,))
    result = cursor.fetchone()
    conn.close()
    
    return result is not None

def mark_article_processed(article_url: str, processed_date: str, recommendation_count: int = 0):
    """Mark an article as processed by the AI agent."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT OR REPLACE INTO processed_articles 
        (article_url, processed_date, processed_timestamp, recommendation_count)
        VALUES (?, ?, ?, ?)
    """, (article_url, processed_date, datetime.now().isoformat(), recommendation_count))
    
    conn.commit()
    conn.close()

def cleanup_old_processed_articles(days_old: int = 7):
    """Remove old processed article records to keep database clean."""
    from datetime import timedelta
    cutoff_date = (date.today() - timedelta(days=days_old)).isoformat()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM processed_articles WHERE processed_date < ?", (cutoff_date,))
        conn.commit()
        deleted = cursor.rowcount
        print(f"[cleanup_old_processed_articles] Deleted {deleted} old processed article records")
        return deleted
    except Exception as e:
        print(f"[cleanup_old_processed_articles] Error: {e}")
        return 0
    finally:
        conn.close()

def get_feeds_needing_update(feed_urls: List[str], check_interval_minutes: int) -> List[str]:
    """Return list of feeds that need to be checked (not checked within interval)."""
    if date_parser is None:
        # If dateutil not available, check all feeds
        return feed_urls
    
    cutoff_time = datetime.now() - timedelta(minutes=check_interval_minutes)
    cutoff_str = cutoff_time.isoformat()
    
    # Return feeds that need checking
    feeds_to_check = []
    for feed_url in feed_urls:
        metadata = get_feed_metadata(feed_url)
        if not metadata:
            # New feed, needs checking
            feeds_to_check.append(feed_url)
        else:
            try:
                last_check = date_parser.parse(metadata["last_check_time"])
                if last_check < cutoff_time:
                    feeds_to_check.append(feed_url)
            except Exception:
                # If parsing fails, check it
                feeds_to_check.append(feed_url)
    
    return feeds_to_check

if __name__ == "__main__":
    # Test the database functions
    print("Testing SQLite recommendations database...")
    
    init_recommendations_db()
    
    # Test data
    test_recs = [
        {
            "company": "Apple Inc",
            "ticker": "AAPL",
            "recommendation": "BUY",
            "reason": "Strong iPhone sales",
            "confidence": "HIGH",
            "article_title": "Apple Reports Record Quarter",
            "article_url": "https://example.com/apple-news"
        },
        {
            "company": "Tesla Inc",
            "ticker": "TSLA", 
            "recommendation": "SELL",
            "reason": "Production concerns",
            "confidence": "MEDIUM",
            "article_title": "Tesla Production Slowdown",
            "article_url": "https://example.com/tesla-news"
        }
    ]
    
    today = date.today().isoformat()
    store_recommendations_sqlite(test_recs, today)
    
    # Test retrieval
    all_recs = get_recommendations_sqlite()
    print(f"All recommendations: {len(all_recs)}")
    
    todays_recs = get_todays_recommendations()
    print(f"Today's recommendations: {len(todays_recs)}")
    
    # Test stats
    stats = get_recommendation_stats()
    print(f"Stats: {stats}")
    
    print("Test completed!")