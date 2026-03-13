# RSS Fetcher Setup & Usage Guide

## Overview

The equity_intelligence_v3 now includes an **RSS Reader & News Ingestion System** that can be triggered manually via API.

## Filing Structure

```
equity_intelligence_v3/
├── ingestion/
│   ├── __init__.py
│   ├── news.py           # Fetches from rss_pool table
│   └── rss_fetcher.py    # NEW: Fetches RSS feeds and populates rss_pool
├── routes/
│   ├── __init__.py
│   └── rss_routes.py     # NEW: Flask routes for RSS API
├── server.py             # NEW: Flask API server
└── requirements.txt      # Updated with Flask & requests
```

## Features

✅ **Fetch RSS Feeds** - Retrieves active feeds from `rss_feeds` table
✅ **Deduplication** - Skips articles already in `rss_pool`
✅ **XML Parsing** - Supports both RSS 2.0 and Atom feeds
✅ **HTML Cleanup** - Removes HTML tags from summaries
✅ **Logging** - Records fetch results to `pool_logs` table
✅ **API Trigger** - Manual control via GET/POST request

## Database Requirements

You need the following Supabase tables:

### 1. `rss_feeds` table

```sql
CREATE TABLE rss_feeds (
  id INT PRIMARY KEY,
  name TEXT NOT NULL,
  url TEXT NOT NULL,
  category TEXT,
  is_active BOOLEAN DEFAULT true
);
```

### 2. `rss_pool` table (should already exist)

```sql
CREATE TABLE rss_pool (
  id INT PRIMARY KEY,
  title TEXT,
  link TEXT UNIQUE,
  summary TEXT,
  published_date TEXT,
  source TEXT,
  rss_id INT,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### 3. `pool_logs` table

```sql
CREATE TABLE pool_logs (
  id INT PRIMARY KEY,
  rss_id INT,
  source TEXT,
  status TEXT,
  new_items INT,
  skipped INT,
  total_pool INT,
  message TEXT,
  triggered_at TIMESTAMP DEFAULT NOW()
);
```

## Setup

### 1. Install Dependencies

```bash
cd equity_intelligence_v3
pip install -r requirements.txt
```

### 2. Configure .env

Make sure your `.env` file has:

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
GROQ_KEY_A=your-groq-key
GROQ_KEY_B=your-groq-key
```

### 3. Add RSS Feeds to Database

Insert feed URLs into the `rss_feeds` table:

```sql
INSERT INTO rss_feeds (id, name, url, category, is_active) VALUES
  (1, 'Reuters Finance', 'https://feeds.reuters.com/finance/...', 'news', true),
  (2, 'Bloomberg Markets', 'https://feeds.bloomberg.com/...', 'markets', true),
  (3, 'CNBC Investing', 'https://feeds.cnbc.com/id/...', 'investing', true);
```

## Usage

### Start the API Server

```bash
python server.py
```

This starts Flask on `http://localhost:5000`

### Manual RSS Trigger

#### Option 1: Using cURL

```bash
# GET request
curl http://localhost:5000/api/rss/trigger

# POST request
curl -X POST http://localhost:5000/api/rss/trigger
```

#### Option 2: Using Python

```python
import requests
response = requests.get("http://localhost:5000/api/rss/trigger")
print(response.json())
```

#### Option 3: Using JavaScript/Fetch

```javascript
fetch("http://localhost:5000/api/rss/trigger")
  .then((res) => res.json())
  .then((data) => console.log(data));
```

#### Option 4: Using HTTPie

```bash
http GET localhost:5000/api/rss/trigger
```

### API Response

**Success (200):**

```json
{
  "status": "success",
  "feeds_fetched": 10,
  "total_new": 45,
  "total_skipped": 23,
  "saved_to_db": 45,
  "total_pool": 2500,
  "message": "Fetched 10 feeds. New: 45, Skipped: 23",
  "feed_results": [
    {
      "source": "Reuters Finance",
      "new": 5,
      "skipped": 2
    },
    {
      "source": "Bloomberg Markets",
      "new": 8,
      "skipped": 3
    }
  ]
}
```

**Error (500):**

```json
{
  "status": "error",
  "message": "RSS fetch failed: [error details]"
}
```

### Check Service Status

```bash
curl http://localhost:5000/api/rss/status
```

Response:

```json
{
  "status": "ok",
  "service": "equity_intelligence_v3 RSS Fetcher",
  "endpoints": {
    "trigger": "GET|POST /api/rss/trigger",
    "status": "GET /api/rss/status"
  }
}
```

## Integration with Pipeline

The RSS fetcher feeds articles into the existing pipeline:

1. **RSS Fetcher** (`ingestion/rss_fetcher.py`) → Saves to `rss_pool`
2. **News Reader** (`ingestion/news.py`) → Fetches from `rss_pool`
3. **Pipeline** (`core/pipeline.py`) → Processes articles through tiers

To use in main.py:

```python
from ingestion.news import fetch_today

# Fetch articles from rss_pool (auto-populated by RSS fetcher)
articles = fetch_today(hours_back=24)
# Process with pipeline...
```

## Scheduling (Optional)

### Using APScheduler

```python
from apscheduler.schedulers.background import BackgroundScheduler
from ingestion.rss_fetcher import fetch_all_feeds

scheduler = BackgroundScheduler()
scheduler.add_job(fetch_all_feeds, 'interval', minutes=30)
scheduler.start()
```

### Using Cron (Linux/Mac)

```bash
# Fetch RSS every 30 minutes
*/30 * * * * curl http://localhost:5000/api/rss/trigger
```

### Using Windows Task Scheduler

1. Create a batch file `fetch_rss.bat`:
   ```batch
   curl http://localhost:5000/api/rss/trigger
   ```
2. Schedule it to run every 30 minutes

## Troubleshooting

**No feeds returned?**

- Check that `rss_feeds` table has `is_active = true` entries
- Verify SUPABASE_URL and SUPABASE_KEY in .env

**Duplicate articles?**

- The system checks `link` field for uniqueness
- Ensure feed URLs are valid and return unique links

**Timeout errors?**

- Some feeds may be slow. Timeout is set to 15 seconds per feed
- Edit `_fetch_feed()` function to adjust timeout

**Supabase 401 Unauthorized?**

- Check SUPABASE_KEY is the anon key, not service role key
- Verify Row Level Security (RLS) policies allow inserts

## API Endpoints Summary

| Method   | Endpoint           | Purpose                                 |
| -------- | ------------------ | --------------------------------------- |
| GET/POST | `/api/rss/trigger` | Manually fetch and ingest all RSS feeds |
| GET      | `/api/rss/status`  | Check RSS service health                |
| GET      | `/`                | Health check & API documentation        |

---

**Ready!** Your RSS fetcher is configured and ready to fetch news articles on demand. 🚀
