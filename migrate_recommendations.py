#!/usr/bin/env python3
"""
Migration script to move stock recommendations from Chroma to SQLite.
This enables better date-based querying for "today's recommendations" functionality.
"""

import sqlite3
import json
import os
from datetime import datetime
import chromadb
from chromadb.config import Settings

# Database setup
DB_FILE = "recommendations.sqlite"

def init_sqlite_db():
    """Initialize SQLite database with recommendations table."""
    conn = sqlite3.connect(DB_FILE)
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
    
    conn.commit()
    conn.close()
    print(f"[MIGRATE] SQLite database initialized: {DB_FILE}")

def migrate_from_chroma():
    """Migrate all recommendations from Chroma to SQLite."""
    try:
        # Connect to Chroma
        client = chromadb.Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory="./chroma"))
        recommendations_collection = client.get_or_create_collection(name="stock_recommendations")
        
        # Get all recommendations from Chroma
        print("[MIGRATE] Fetching recommendations from Chroma...")
        results = recommendations_collection.get(include=["documents", "metadatas", "embeddings"])
        
        if not results["ids"]:
            print("[MIGRATE] No recommendations found in Chroma")
            return 0
        
        print(f"[MIGRATE] Found {len(results['ids'])} recommendations in Chroma")
        
        # Connect to SQLite
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        migrated_count = 0
        for i, (rec_id, metadata, embedding) in enumerate(zip(results["ids"], results["metadatas"], results["embeddings"])):
            try:
                # Convert embedding to JSON string for storage
                embedding_json = json.dumps(embedding) if embedding else None
                
                cursor.execute("""
                INSERT OR REPLACE INTO recommendations
                (id, company, ticker, recommendation, reason, confidence, 
                 article_title, article_url, date, timestamp, active, embedding_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    rec_id,
                    metadata.get("company", ""),
                    metadata.get("ticker", ""),
                    metadata.get("recommendation", ""),
                    metadata.get("reason", ""),
                    metadata.get("confidence", ""),
                    metadata.get("article_title", ""),
                    metadata.get("article_url", ""),
                    metadata.get("date", ""),
                    metadata.get("timestamp", datetime.now().isoformat()),
                    1 if metadata.get("active", True) else 0,
                    embedding_json
                ))
                migrated_count += 1
                
                if (i + 1) % 10 == 0:
                    print(f"[MIGRATE] Processed {i + 1}/{len(results['ids'])} recommendations...")
                    
            except Exception as e:
                print(f"[MIGRATE] Error migrating recommendation {rec_id}: {e}")
                continue
        
        conn.commit()
        conn.close()
        
        print(f"[MIGRATE] Successfully migrated {migrated_count} recommendations to SQLite")
        return migrated_count
        
    except Exception as e:
        print(f"[MIGRATE] Error during migration: {e}")
        return 0

def verify_migration():
    """Verify the migration was successful."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Get basic stats
    cursor.execute("SELECT COUNT(*) FROM recommendations")
    total_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM recommendations WHERE active = 1")
    active_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT ticker) FROM recommendations WHERE active = 1")
    unique_tickers = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT date) FROM recommendations WHERE active = 1")
    unique_dates = cursor.fetchone()[0]
    
    # Get most recent recommendations
    cursor.execute("""
    SELECT ticker, recommendation, date, timestamp 
    FROM recommendations 
    WHERE active = 1 
    ORDER BY date DESC, timestamp DESC 
    LIMIT 5
    """)
    recent_recs = cursor.fetchall()
    
    conn.close()
    
    print(f"\n[VERIFY] Migration verification:")
    print(f"  Total recommendations: {total_count}")
    print(f"  Active recommendations: {active_count}")
    print(f"  Unique tickers: {unique_tickers}")
    print(f"  Unique dates: {unique_dates}")
    
    if recent_recs:
        print(f"\n  Most recent recommendations:")
        for ticker, rec_type, date, timestamp in recent_recs:
            print(f"    {ticker}: {rec_type} on {date}")
    
    return total_count

if __name__ == "__main__":
    print("Starting recommendation migration from Chroma to SQLite...")
    
    # Initialize SQLite database
    init_sqlite_db()
    
    # Migrate data
    migrated = migrate_from_chroma()
    
    if migrated > 0:
        # Verify migration
        verify_migration()
        print(f"\n[SUCCESS] Migration completed! {migrated} recommendations migrated to {DB_FILE}")
    else:
        print("\n[WARNING] No recommendations were migrated.")
    
    print(f"\nTo use the new SQLite database, update your Flask app to use: {DB_FILE}")