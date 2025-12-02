# Performance Optimization Opportunities

## Current Performance Issues

### 1. **Redundant Feed Fetching**
- **Problem:** On startup, all RSS feeds are fetched regardless of when they were last checked
- **Impact:** Wastes network bandwidth and processing time
- **Example:** If a feed was checked 5 minutes ago, we fetch it again unnecessarily

### 2. **No Feed-Level Tracking**
- **Problem:** System doesn't track when each feed was last checked
- **Impact:** Can't skip recently-checked feeds
- **Example:** Feed A checked 1 minute ago, Feed B checked 2 hours ago - both get fetched

### 3. **Article-Level Duplicate Checking Only**
- **Problem:** We check if articles exist in DB, but we fetch the entire RSS feed first
- **Impact:** Network requests for feeds that may have no new articles
- **Example:** Fetch 50 articles from a feed, find all 50 already in DB

### 4. **No RSS Feed Metadata Utilization**
- **Problem:** RSS feeds provide ETags and Last-Modified headers we're not using
- **Impact:** Missing opportunity for conditional requests (304 Not Modified)
- **Example:** Feed hasn't changed, but we download it anyway

## Proposed Optimizations

### 1. Feed-Level Last Check Tracking ✅

**Implementation:**
- Store last check time per feed URL in SQLite
- Skip feeds checked within the fetch interval
- Only fetch feeds that haven't been checked recently

**Benefits:**
- Reduces network requests by 50-80% on subsequent runs
- Faster startup times
- Less server load on feed providers

**Example:**
```python
# Feed checked 10 minutes ago, fetch interval is 30 minutes
# Skip this feed, check again in 20 minutes
```

### 2. RSS Feed Metadata (ETags/Last-Modified) ✅

**Implementation:**
- Store ETag and Last-Modified per feed
- Send conditional requests (If-None-Match, If-Modified-Since)
- Use 304 Not Modified responses to skip unchanged feeds

**Benefits:**
- Eliminates unnecessary feed downloads
- Respects server resources
- Faster feed checking

**Example:**
```python
# Feed returns 304 Not Modified
# Skip processing, update last check time only
```

### 3. Feed Update Frequency Tracking ✅

**Implementation:**
- Track how often each feed actually updates
- Adjust check frequency per feed
- Fast-updating feeds checked more often

**Benefits:**
- Prioritize feeds that update frequently
- Reduce checks on slow-updating feeds
- Better resource allocation

**Example:**
```python
# TechCrunch updates hourly - check every 30 min
# HBR updates daily - check every 6 hours
```

### 4. Article Date-Based Filtering ✅

**Implementation:**
- Track last article date per feed
- Only process articles newer than last processed date
- Skip old articles without DB lookup

**Benefits:**
- Faster article processing
- Less database queries
- Focus on new content

**Example:**
```python
# Last article from this feed: 2025-12-02 10:00
# Only process articles published after 10:00
```

### 5. Incremental Feed Processing ✅

**Implementation:**
- Process feeds in priority order (most recently updated first)
- Stop early if time/limit reached
- Resume from where we left off

**Benefits:**
- Better startup performance
- Prioritizes fresh content
- Handles large feed lists efficiently

## Performance Impact Estimates

### Current Performance
- **Startup:** Fetches all 16 feeds (~2-5 minutes)
- **Network Requests:** ~16 RSS feeds + ~50-100 articles
- **Database Queries:** ~50-100 article existence checks
- **Processing Time:** ~5-10 minutes for full cycle

### With Optimizations
- **Startup:** Fetches only feeds needing updates (~30 seconds - 2 minutes)
- **Network Requests:** ~3-5 RSS feeds + ~10-20 new articles
- **Database Queries:** ~10-20 article existence checks
- **Processing Time:** ~1-3 minutes for incremental cycle

**Estimated Improvement:** 60-80% reduction in processing time

## Implementation Strategy

### Phase 1: Feed Tracking Database
1. Create `feed_metadata` table in SQLite
2. Track: feed_url, last_check_time, last_article_date, etag, last_modified
3. Update on each feed check

### Phase 2: Conditional Requests
1. Store ETags and Last-Modified headers
2. Send conditional requests
3. Handle 304 responses

### Phase 3: Smart Feed Selection
1. Filter feeds by last check time
2. Prioritize feeds by update frequency
3. Skip feeds checked within interval

### Phase 4: Article Date Filtering
1. Track last article date per feed
2. Filter articles by date before processing
3. Reduce database lookups

## Database Schema

```sql
CREATE TABLE feed_metadata (
    feed_url TEXT PRIMARY KEY,
    last_check_time TEXT NOT NULL,
    last_article_date TEXT,
    etag TEXT,
    last_modified TEXT,
    update_frequency_hours REAL,
    total_articles_processed INTEGER DEFAULT 0,
    last_successful_check TEXT
);
```

## Configuration Options

Add to `news_sources.json`:
```json
{
  "feed_check_interval_minutes": 30,
  "skip_recently_checked": true,
  "use_conditional_requests": true,
  "max_feeds_per_cycle": 10
}
```

## Benefits Summary

1. **Faster Startup:** 60-80% reduction in initial processing time
2. **Reduced Network Load:** Fewer RSS feed requests
3. **Better Resource Usage:** Focus on feeds that actually update
4. **Respectful Scraping:** Uses HTTP conditional requests properly
5. **Scalability:** Can handle more feeds without linear performance degradation

