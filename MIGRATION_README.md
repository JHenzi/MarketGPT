# SQLite Migration for Stock Recommendations

This document describes the migration from Chroma to SQLite for stock recommendations and the new date-based functionality.

## Overview

The stock recommendations have been migrated from ChromaDB to SQLite to enable better date-based querying and improved performance for "today's recommendations" functionality.

## Migration Summary

- **Total Recommendations Migrated**: 452
- **Unique Tickers**: 350
- **Date Range**: 2025-07-03 to present
- **Database File**: `recommendations.sqlite`

## New Features

### 1. Date-Based Querying

You can now efficiently query recommendations by specific dates:

```python
from db_utils import get_todays_recommendations, get_recommendations_by_date

# Get today's recommendations
today_recs = get_todays_recommendations()

# Get recommendations for a specific date
historical_recs = get_recommendations_by_date("2025-07-03")
```

### 2. Enhanced Flask Routes

#### Web Interface
- `/recommendations` - View all recommendations (existing)
- `/recommendations?today=true` - View only today's recommendations
- `/recommendations?date=2025-07-03` - View recommendations for a specific date
- `/recommendations?type=BUY&today=true` - Combined filtering

#### API Endpoints
- `GET /api/recommendations/today` - JSON API for today's recommendations
- `GET /api/recommendations/date/2025-07-03` - JSON API for specific date

### 3. Improved Performance

SQLite indexes have been created on:
- `ticker` - Fast ticker-based lookups
- `date` - Fast date-based queries
- `recommendation` - Fast filtering by BUY/SELL/HOLD
- `active` - Fast filtering of active recommendations
- Combined indexes for common query patterns

## Database Schema

```sql
CREATE TABLE recommendations (
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
);
```

## Usage Examples

### Python API

```python
from db_utils import *

# Initialize database (done automatically in app.py)
init_recommendations_db()

# Store new recommendations
new_recs = [
    {
        "company": "Apple Inc",
        "ticker": "AAPL", 
        "recommendation": "BUY",
        "reason": "Strong earnings",
        "confidence": "HIGH",
        "article_title": "Apple Beats Q3 Estimates",
        "article_url": "https://example.com/apple-news"
    }
]
store_recommendations_sqlite(new_recs, "2025-10-17")

# Query recommendations
today_recs = get_todays_recommendations()
aapl_recs = get_recommendations_sqlite(ticker="AAPL")
buy_recs = get_recommendations_sqlite(recommendation_type="BUY")

# Get statistics
stats = get_recommendation_stats()
print(f"Today's recommendations: {stats['today']}")
```

### Flask Web Interface

```bash
# View today's recommendations
curl "http://localhost:5020/recommendations?today=true"

# View recommendations for a specific date
curl "http://localhost:5020/recommendations?date=2025-07-03"

# API endpoint for today's recommendations
curl "http://localhost:5020/api/recommendations/today"

# API endpoint for specific date
curl "http://localhost:5020/api/recommendations/date/2025-07-03"
```

## Migration Process

1. **Run Migration Script**:
   ```bash
   python migrate_recommendations.py
   ```

2. **Verify Migration**:
   ```bash
   python test_migration.py
   ```

3. **Update Application**: The main app.py has been updated to use SQLite instead of Chroma for recommendations.

## Benefits

### Before (Chroma)
- Vector similarity search required for all queries
- No efficient date-based filtering
- Complex filtering logic in application code
- Slower queries for simple lookups

### After (SQLite)
- Direct SQL queries with indexes
- Native date filtering with `WHERE date = ?`
- Simple and fast ticker/recommendation type filtering
- Better performance for "today's recommendations"
- Easier to backup and manage

## Backward Compatibility

- All existing functionality is preserved
- The `/recommendations` route works exactly as before
- New query parameters are optional
- ChromaDB is still used for article storage and similarity search

## Files Changed

- `migrate_recommendations.py` - Migration script
- `db_utils.py` - SQLite database utilities
- `app.py` - Updated to use SQLite for recommendations
- `test_migration.py` - Comprehensive test suite

## Testing

Run the test suite to verify everything works:

```bash
python test_migration.py
```

Expected output shows successful migration of 452 recommendations with all functionality working correctly.

## Maintenance

### Cleanup Old Recommendations
```python
from db_utils import cleanup_old_recommendations

# Mark recommendations older than 7 days as inactive
cleanup_old_recommendations(days_old=7)
```

### Database Statistics
```python
from db_utils import get_recommendation_stats

stats = get_recommendation_stats()
# Returns: total, active, today, unique_tickers, buy_count, sell_count
```

This migration provides a solid foundation for date-based recommendation queries while maintaining all existing functionality.