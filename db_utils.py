"""
SQLite database utilities for stock recommendations.
Provides date-based querying for "today's recommendations" functionality.
"""

import sqlite3
import json
from datetime import datetime, date
from collections import defaultdict
from typing import List, Dict, Optional, Any

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
        today_str = date.today().isoformat()
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
    """Get all active recommendations for today."""
    return get_recommendations_sqlite(today_only=True, active_only=True)

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
    
    # Today's recommendations
    today_str = date.today().isoformat()
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
    
    cutoff_date = (date.today() - timedelta(days=days_old)).isoformat()
    
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