# RSS Fetcher Implementation - Quick Start

## What Was Created

✅ **RSS Fetcher Module** (`ingestion/rss_fetcher.py`)

- Fetches RSS feeds from Supabase `rss_feeds` table
- Parses RSS 2.0 and Atom XML formats
- Deduplicates articles by link
- Saves to Supabase `rss_pool` table
- Logs results to `pool_logs` table

✅ **Flask API Routes** (`routes/rss_routes.py`)

- `GET|POST /api/rss/trigger` - Manually trigger RSS fetch
- `GET /api/rss/status` - Check service health

✅ **Flask Server** (`server.py`)

- Runs on `http://localhost:5000`
- Includes blueprint registration and error handling
- Environment-based port & debug settings

✅ **Test Script** (`test_rss_api.py`)

- Verify API is running
- Trigger RSS fetch
- View results

✅ **Documentation** (`RSS_SETUP.md`)

- Complete setup guide
- Database schema
- API usage examples
- Troubleshooting

## Quick Start (5 minutes)

### 1. Install Dependencies

```bash
cd equity_intelligence_v3
pip install -r requirements.txt
```

### 2. Add RSS Feeds to Supabase

Insert into `rss_feeds` table (create table if needed):

```sql
INSERT INTO rss_feeds (id, name, url, category, is_active) VALUES
  (1, 'Reuters', 'https://feeds.reuters.com/...', 'news', true),
  (2, 'Bloomberg', 'https://feeds.bloomberg.com/...', 'market', true);
```

### 3. Start API Server

```bash
python server.py
```

Output: `API running on http://localhost:5000`

### 4. Trigger RSS Fetch

**Option A: cURL**

```bash
curl http://localhost:5000/api/rss/trigger
```

**Option B: Python Script**

```bash
python test_rss_api.py
```

**Option C: Browser**
Navigate to: `http://localhost:5000/api/rss/trigger`

## API Response Example

```json
{
  "status": "success",
  "feeds_fetched": 2,
  "total_new": 12,
  "total_skipped": 5,
  "saved_to_db": 12,
  "total_pool": 2412,
  "message": "Fetched 2 feeds. New: 12, Skipped: 5"
}
```

## Connection to Pipeline

Articles are automatically available to your pipeline:

```python
# main.py
from ingestion.news import fetch_today

articles = fetch_today(hours_back=24)  # Fetch from rss_pool
# Pass to pipeline...
```

## File Structure

```
equity_intelligence_v3/
├── ingestion/
│   ├── rss_fetcher.py     ← NEW: Core RSS fetcher
│   └── news.py            ← Uses rss_pool table
├── routes/
│   ├── __init__.py        ← NEW
│   └── rss_routes.py      ← NEW: API endpoints
├── server.py              ← NEW: Flask app
├── requirements.txt       ← UPDATED: Added Flask, requests
├── RSS_SETUP.md           ← NEW: Full documentation
└── test_rss_api.py        ← NEW: Test script
```

## Environment Variables Required

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
```

## Troubleshooting

**"No feeds found"?** → Add rows to `rss_feeds` table with `is_active=true`

**"Cannot connect"?** → Start server: `python server.py`

**"Articles not saving"?** → Check Supabase credentials in .env

**"HTTP 500"?** → Check server logs for SQL/connection errors

## Next Steps

1. ✅ Add RSS feed URLs to Supabase `rss_feeds` table
2. ✅ Start the API server: `python server.py`
3. ✅ Trigger fetch: `curl http://localhost:5000/api/rss/trigger`
4. ✅ Verify articles in Supabase `rss_pool` table
5. ✅ Run main pipeline to process articles

## Commands Reference

| Task          | Command                                      |
| ------------- | -------------------------------------------- |
| Start API     | `python server.py`                           |
| Test RSS      | `python test_rss_api.py`                     |
| Trigger fetch | `curl http://localhost:5000/api/rss/trigger` |
| Check status  | `curl http://localhost:5000/api/rss/status`  |
| View logs     | Check terminal output                        |

---

You're all set! 🚀 The RSS fetcher is ready to use with manual API triggers.
