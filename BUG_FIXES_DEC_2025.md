# Bug Fixes - December 2, 2025

## Issues Fixed

### 1. ✅ Duplicate Article Processing

**Problem:** Articles were being processed multiple times by the AI agent, even after being removed from news sources.

**Root Cause:** No tracking of which articles had already been analyzed by the AI agent.

**Solution:**
- Created `processed_articles` table in SQLite to track analyzed articles
- Added `is_article_processed()` function to check if article was already analyzed
- Added `mark_article_processed()` function to record processed articles
- Modified `extract_stock_recommendations()` to skip already-processed articles
- Articles are marked as processed even if no valid recommendations are found (to avoid infinite retries)

**Database Schema:**
```sql
CREATE TABLE processed_articles (
    article_url TEXT PRIMARY KEY,
    processed_date TEXT NOT NULL,
    processed_timestamp TEXT NOT NULL,
    recommendation_count INTEGER DEFAULT 0
)
```

**Benefits:**
- Articles are only analyzed once
- Prevents duplicate LLM API calls
- Saves processing time and costs
- Articles from removed feeds won't be re-analyzed

### 2. ✅ Today's Recommendations Showing Blank

**Problem:** Today's recommendations page showing blank, while historical recommendations appear.

**Root Cause:** Timezone mismatch between storage and retrieval:
- Recommendations stored using NY timezone: `datetime.now(ZoneInfo("America/New_York"))`
- Recommendations queried using system timezone: `date.today().isoformat()`

**Example:**
- Article published Dec 2, 11 PM NY time → Stored with date "2025-12-02"
- Query at 12:01 AM UTC (Dec 3) → Queries for "2025-12-03"
- Result: No match, blank page

**Solution:**
- Updated `get_todays_recommendations()` to use NY timezone
- Updated `get_recommendations_sqlite()` when `today_only=True` to use NY timezone
- Updated `get_recommendation_stats()` to use NY timezone for "today" count
- Updated API endpoint `/api/recommendations/today` to use NY timezone
- Updated template date display to use NY timezone

**Files Changed:**
- `db_utils.py`: All date queries now use NY timezone consistently
- `app.py`: API endpoints and template variables use NY timezone

### 3. ✅ Historical Recommendations Cleanup

**Problem:** Historical recommendations accumulating in database, cluttering the UI.

**Solution:**
- Enhanced `cleanup_old_recommendations()` to use NY timezone
- Added `delete_old_recommendations()` for permanent deletion
- Added `/recommendations/cleanup` API endpoint
- Automatic cleanup runs in periodic task (marks inactive after 3 days)
- Manual cleanup available via API

**Usage:**
```bash
# Mark old recommendations as inactive (default: 7 days)
curl -X POST http://localhost:5070/recommendations/cleanup \
  -H "Content-Type: application/json" \
  -d '{"days_old": 7, "permanent": false}'

# Permanently delete old recommendations
curl -X POST http://localhost:5070/recommendations/cleanup \
  -H "Content-Type: application/json" \
  -d '{"days_old": 7, "permanent": true}'
```

## Code Changes Summary

### Database Changes
1. **New Table:** `processed_articles` - Tracks which articles have been analyzed
2. **New Functions:**
   - `is_article_processed(article_url)` - Check if article was processed
   - `mark_article_processed(article_url, date, count)` - Mark article as processed
   - `cleanup_old_processed_articles(days_old)` - Clean up old tracking records
   - `delete_old_recommendations(days_old)` - Permanently delete old recommendations

### Application Changes
1. **Article Processing:**
   - Filters out already-processed articles before LLM analysis
   - Marks articles as processed after analysis (even on errors)
   - Logs skipped article count

2. **Timezone Consistency:**
   - All date queries use NY timezone (`America/New_York`)
   - Consistent date format: `YYYY-MM-DD`
   - Template displays use NY timezone

3. **Cleanup:**
   - Automatic cleanup of processed article records (7 days)
   - Manual cleanup endpoint for recommendations

## Testing

To verify the fixes:

1. **Check Processed Articles:**
   ```sql
   SELECT COUNT(*) FROM processed_articles;
   SELECT * FROM processed_articles ORDER BY processed_timestamp DESC LIMIT 10;
   ```

2. **Check Today's Recommendations:**
   ```sql
   -- Should match NY timezone date
   SELECT COUNT(*) FROM recommendations 
   WHERE date = date('now', 'localtime') AND active = 1;
   ```

3. **Verify No Duplicates:**
   - Run `extract_stock_recommendations` multiple times
   - Check logs for "Skipping X already-processed articles"
   - Verify articles aren't re-analyzed

## Performance Impact

- **Reduced LLM Calls:** Articles analyzed once, not repeatedly
- **Faster Processing:** Skips already-processed articles immediately
- **Database Efficiency:** Indexed lookups for processed articles

## Known Limitations

1. **Article URL Changes:** If an article URL changes, it may be processed again
2. **Manual Reprocessing:** To re-analyze an article, delete its record from `processed_articles`
3. **Timezone Edge Cases:** If system timezone differs significantly from NY, may see 1-day offset at midnight

## Future Improvements

1. **Article Content Hashing:** Track by content hash instead of URL (handles URL changes)
2. **Reprocessing Option:** Allow manual flag to re-analyze specific articles
3. **Processing History:** Track which recommendations came from which article analysis
4. **Batch Reprocessing:** Allow re-analyzing all articles from a specific date range

