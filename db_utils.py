import sqlite3
import json
import os
from datetime import datetime

DB_FILE = "market_insights.sqlite"

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database and creates the stock_recommendations table if it doesn't exist."""
    if os.path.exists(DB_FILE):
        print(f"[DB] Database {DB_FILE} already exists.")
    else:
        print(f"[DB] Creating database {DB_FILE}...")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stock_recommendations (
        id TEXT PRIMARY KEY,
        company TEXT,
        ticker TEXT,
        recommendation TEXT,
        reason TEXT,
        confidence TEXT,
        article_title TEXT,
        article_url TEXT,
        date TEXT,
        timestamp TEXT,
        active INTEGER DEFAULT 1,
        embedding BLOB
    )
    """)

    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ticker ON stock_recommendations (ticker)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_recommendation ON stock_recommendations (recommendation)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_date ON stock_recommendations (date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_active ON stock_recommendations (active)")

    conn.commit()
    conn.close()
    print("[DB] stock_recommendations table initialized with indexes.")

def store_recommendation_sqlite(rec_data, embedding_list):
    """
    Stores a single stock recommendation in the SQLite database.
    'rec_data' is a dictionary containing all recommendation fields.
    'embedding_list' is the list of floats representing the embedding.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    rec_id = f"{rec_data['ticker']}_{rec_data['date']}_{rec_data['recommendation']}"

    # Convert embedding list to bytes (JSON string then UTF-8 bytes)
    embedding_blob = json.dumps(embedding_list).encode('utf-8')

    try:
        cursor.execute("""
        INSERT OR REPLACE INTO stock_recommendations
        (id, company, ticker, recommendation, reason, confidence, article_title, article_url, date, timestamp, active, embedding)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rec_id,
            rec_data['company'],
            rec_data['ticker'],
            rec_data['recommendation'],
            rec_data['reason'],
            rec_data['confidence'],
            rec_data['article_title'],
            rec_data['article_url'],
            rec_data['date'],
            rec_data.get('timestamp', datetime.now().isoformat()), # Default to now if not provided
            rec_data.get('active', 1), # Default to active if not provided
            embedding_blob
        ))
        conn.commit()
        print(f"[DB] Stored recommendation ID: {rec_id}")
        return True
    except sqlite3.Error as e:
        print(f"[DB] Error storing recommendation ID {rec_id}: {e}")
        return False
    finally:
        conn.close()

def get_recommendations_sqlite(ticker=None, recommendation_type=None, active_only=True):
    """
    Retrieves stock recommendations from SQLite, with optional filters.
    Embeddings are retrieved as JSON strings and need to be parsed.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM stock_recommendations"
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

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY timestamp DESC" # Most recent first

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    recommendations = []
    for row in rows:
        rec = dict(row)
        # Deserialize embedding from BLOB (UTF-8 bytes to JSON string, then parse)
        if rec['embedding']:
            rec['embedding'] = json.loads(rec['embedding'].decode('utf-8'))
        recommendations.append(rec)

    return recommendations

def mark_recommendation_inactive_sqlite(rec_id):
    """Marks a specific recommendation as inactive by its ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE stock_recommendations SET active = 0 WHERE id = ?", (rec_id,))
        conn.commit()
        if cursor.rowcount > 0:
            print(f"[DB] Marked recommendation ID {rec_id} as inactive.")
            return True
        else:
            print(f"[DB] No recommendation found with ID {rec_id} to mark inactive.")
            return False
    except sqlite3.Error as e:
        print(f"[DB] Error marking recommendation ID {rec_id} inactive: {e}")
        return False
    finally:
        conn.close()

def mark_all_ticker_recommendations_inactive_sqlite(ticker):
    """Marks all recommendations for a given ticker as inactive."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE stock_recommendations SET active = 0 WHERE ticker = ?", (ticker,))
        conn.commit()
        print(f"[DB] Marked all recommendations for ticker {ticker} as inactive. Rows affected: {cursor.rowcount}")
        return True
    except sqlite3.Error as e:
        print(f"[DB] Error marking recommendations for ticker {ticker} inactive: {e}")
        return False
    finally:
        conn.close()

def get_recommendation_by_id_sqlite(rec_id):
    """Retrieves a single recommendation by its ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM stock_recommendations WHERE id = ?", (rec_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        rec = dict(row)
        if rec['embedding']:
            rec['embedding'] = json.loads(rec['embedding'].decode('utf-8'))
        return rec
    return None

if __name__ == '__main__':
    # Example Usage & Basic Test
    print("Running basic DB tests...")
    init_db()

    # Test data
    sample_rec_1 = {
        "company": "TestCorp", "ticker": "TCORP", "recommendation": "BUY",
        "reason": "Strong earnings", "confidence": "HIGH",
        "article_title": "TCORP Beats Estimates", "article_url": "http://example.com/tcorp_news",
        "date": "2023-10-27", "timestamp": datetime.now().isoformat(), "active": 1
    }
    sample_embedding_1 = [0.1] * 384 # Assuming 384 is embedding dimension

    sample_rec_2 = {
        "company": "AnotherCo", "ticker": "ANCO", "recommendation": "SELL",
        "reason": "Weak guidance", "confidence": "MEDIUM",
        "article_title": "ANCO Lowers Outlook", "article_url": "http://example.com/anco_news",
        "date": "2023-10-28", "timestamp": datetime.now().isoformat(), "active": 1
    }
    sample_embedding_2 = [0.2] * 384

    # Store
    store_recommendation_sqlite(sample_rec_1, sample_embedding_1)
    store_recommendation_sqlite(sample_rec_2, sample_embedding_2)

    # Retrieve all
    all_recs = get_recommendations_sqlite(active_only=False)
    print(f"\nAll recommendations ({len(all_recs)}):")
    for r in all_recs:
        print(f"  {r['ticker']} - {r['recommendation']} (Embedding type: {type(r['embedding'])}, Len: {len(r['embedding']) if r['embedding'] else 'N/A'})")

    # Retrieve filtered
    buy_recs = get_recommendations_sqlite(recommendation_type="BUY")
    print(f"\nBUY recommendations ({len(buy_recs)}):")
    for r in buy_recs:
        print(f"  {r['ticker']} - {r['recommendation']}")

    tcorp_recs = get_recommendations_sqlite(ticker="TCORP")
    print(f"\nTCORP recommendations ({len(tcorp_recs)}):")
    for r in tcorp_recs:
        print(f"  {r['ticker']} - {r['recommendation']}")

    # Mark inactive
    rec_id_to_deactivate = f"{sample_rec_1['ticker']}_{sample_rec_1['date']}_{sample_rec_1['recommendation']}"
    mark_recommendation_inactive_sqlite(rec_id_to_deactivate)

    # Retrieve active (TCORP should be gone)
    active_recs = get_recommendations_sqlite(active_only=True)
    print(f"\nActive recommendations after deactivation ({len(active_recs)}):")
    for r in active_recs:
        print(f"  {r['ticker']} - {r['recommendation']}")
        assert r['ticker'] != "TCORP"

    # Retrieve by ID
    retrieved_by_id = get_recommendation_by_id_sqlite(rec_id_to_deactivate)
    print(f"\nRetrieved by ID ({rec_id_to_deactivate}): {retrieved_by_id['ticker'] if retrieved_by_id else 'Not Found'}, Active: {retrieved_by_id['active'] if retrieved_by_id else 'N/A'}")
    assert retrieved_by_id and retrieved_by_id['active'] == 0

    # Mark all ANCO inactive
    mark_all_ticker_recommendations_inactive_sqlite("ANCO")
    anco_recs_after_mass_deactivation = get_recommendations_sqlite(ticker="ANCO", active_only=True)
    print(f"\nActive ANCO recommendations after mass deactivation: {len(anco_recs_after_mass_deactivation)}")
    assert len(anco_recs_after_mass_deactivation) == 0

    print("\nBasic DB tests completed.")
    # Clean up the test DB file
    # os.remove(DB_FILE)
    # print(f"Test database {DB_FILE} removed.")
    print(f"Test database {DB_FILE} retained for inspection. Remove manually if needed.")
