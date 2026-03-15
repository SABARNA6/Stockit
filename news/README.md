# News Intelligence Service Documentation

## 1. Overview

This service ingests RSS news, filters and enriches it through a 4-layer pipeline, logs outputs to Supabase, and exposes REST endpoints for pipeline execution and stock-level signal retrieval.

Primary goals:

- Fetch and deduplicate RSS news continuously.
- Detect financially relevant articles for Indian equities.
- Map article impact to NSE tickers.
- Predict short-term directional impact with confidence and alert priority.
- Serve aggregated stock signals via API.

Core app entrypoint is the Flask app in `api/routes.py` (also used by Gunicorn in Docker).

## 2. High-Level Architecture

Flow:

1. RSS fetch (`api/rss_fetcher.py`)
2. Pre-filter + dedup (`pipeline_optimizer.py`)
3. Layer 1: content understanding (`layers/layer1_content.py`)
4. Layer 2: impact propagation (`layers/layer2_propagation.py`)
5. Layer 3: price prediction (`layers/layer3_prediction.py`)
6. Layer 4: reasoning and validation (`layers/layer4_reasoning.py`)
7. Persist logs and outputs to Supabase (`database/supabase_logger.py`)
8. Serve API responses (`api/routes.py`)

Data persistence is done through Supabase REST API (no ORM).

## 3. Project Structure

- `api/routes.py`: Flask routes and orchestration.
- `api/rss_fetcher.py`: RSS source loading, XML parsing, dedup by link, Supabase insert.
- `layers/layer1_content.py`: Rule-based entity/event/sentiment extraction.
- `layers/layer2_propagation.py`: LLM-based ticker impact expansion.
- `layers/layer3_prediction.py`: LLM + historical price context predictions.
- `layers/layer4_reasoning.py`: LLM reasoning refinement and final priority.
- `layers/llm_client.py`: OpenRouter-first, Gemini-fallback LLM client.
- `pipeline_optimizer.py`: early filter, dedup, chunk/progress helpers.
- `database/schema.sql`: required Supabase tables and indexes.
- `database/seed_rss.sql`: seed feeds.
- `data/import_rss_feeds.py`: CSV-to-Supabase feed uploader.
- `Dockerfile`: production container build.

Notes:

- `run.py` currently exists but is empty.
- `config.py` currently exists but is empty.
- Runtime behavior is defined in `api/routes.py` and layer modules.

## 4. External Dependencies

From `requirements.txt`:

- Flask
- Gunicorn
- vaderSentiment
- pandas
- gspread + oauth2client (legacy/optional CSV/Sheets workflows)
- requests
- python-dateutil

Docker image also installs spaCy small model (`en_core_web_sm`), though current active Layer 1 logic is primarily rule/VADER-based.

## 5. Environment Variables

Minimum required variables:

- `SUPABASE_URL`: Supabase project URL (example: `https://xxx.supabase.co`)
- `SUPABASE_KEY`: Supabase API key used for REST calls
- `OPENROUTER_API_KEY`: primary LLM provider key
- `GEMINI_API_KEY`: fallback LLM provider key
- `PORT`: optional, default 10000

Use `.env.example` as a template.

## 6. Database Setup (Supabase)

Run these in order:

1. Execute `database/schema.sql` in Supabase SQL Editor.
2. Execute `database/seed_rss.sql` to seed default feeds.

Tables used by the service:

- `rss_feeds`: configured RSS sources
- `rss_pool`: raw fetched article store (dedup by unique `link`)
- `pool_logs`: RSS execution logs
- `nse_stocks`: stock universe for propagation
- `l1_logs`: layer1 output log
- `l2_logs`: layer2 output log
- `l3_logs`: layer3 output log
- `l4_logs`: layer4 output log
- `pipeline_progress`: run progress metadata

Key constraints/index behavior:

- `rss_feeds.url` is unique.
- `rss_pool.link` is unique.
- Most log tables have indexes on `ticker`, `news_id`, and `created_at` where relevant.

## 7. Local Run

### 7.1 Python setup

```bash
cd news
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 7.2 Start service (Flask dev)

```bash
python api/routes.py
```

Default bind: `0.0.0.0:10000`

### 7.3 Start service (Gunicorn, production style)

```bash
gunicorn --bind 0.0.0.0:10000 --workers 1 --timeout 300 "api.routes:app"
```

## 8. Docker Run

Build:

```bash
docker build -t stockit-news ./news
```

Run:

```bash
docker run --rm -p 10000:10000 --env-file ./news/.env stockit-news
```

The container command starts Gunicorn with `api.routes:app`.

## 9. API Reference

Base URL examples below assume local run:

- `http://localhost:10000`

### 9.1 Health

`GET /api/health`

Returns service status, Supabase connectivity, KG load state, API key presence, and layer status metadata.

Example:

```json
{
  "status": "running",
  "supabase_ok": true,
  "kg_loaded": true,
  "kg_stocks": 1900,
  "openrouter_set": true,
  "gemini_set": true,
  "layers": {
    "layer1": "active",
    "layer2": "active (OpenRouter + Gemini fallback)",
    "layer3": "active (OpenRouter + Price API)",
    "layer4": "coming soon"
  }
}
```

### 9.2 Run Full Pipeline

`GET /api/run` or `POST /api/run`

Behavior:

1. Fetch active feeds from `rss_feeds`.
2. Parse and dedup links against `rss_pool`.
3. Run L1 -> L2 -> L3 -> L4 for new articles.
4. Return execution summary.

Success example:

```json
{
  "status": "ok",
  "elapsed_seconds": 27,
  "feeds_fetched": 10,
  "articles_fetched": 42,
  "layer1_relevant": 15,
  "layer2_enriched": 15,
  "layer3_predicted": 12,
  "feed_results": []
}
```

No-new-data example:

```json
{
  "status": "ok",
  "message": "No new articles found",
  "feeds_fetched": 10,
  "total_new": 0
}
```

### 9.3 Manual Ingest

`POST /api/ingest`

Body:

```json
{
  "articles": [
    {
      "id": 123,
      "title": "Sample headline",
      "summary": "Sample summary",
      "link": "https://example.com/news/123",
      "source": "Example Source",
      "publish_date": "2026-03-15T10:00:00Z"
    }
  ]
}
```

Returns processing counts and profiles summary from the same pipeline runner.

### 9.4 Load Stock Universe

`POST /api/load-stocks`

Body:

```json
{
  "stocks": [
    {
      "Symbol": "TCS",
      "Company Name": "Tata Consultancy Services",
      "Industry": "IT Services"
    }
  ]
}
```

Loads in-memory knowledge graph and asynchronously persists to `nse_stocks`.

### 9.5 Add RSS Feed

`POST /api/add-feed`

Body:

```json
{
  "name": "My Feed",
  "url": "https://example.com/rss.xml",
  "category": "news",
  "country": "IN"
}
```

Adds a feed row into `rss_feeds`.

### 9.6 Get Stock Signals

`GET /api/stock/<ticker>?hours=24&limit=20`

Behavior:

- Reads latest ticker signals from `l4_logs`; if unavailable, falls back to `l3_logs`.
- Enriches with impact context from `l2_logs`.
- If no rows in requested window, automatically widens search to 7 days.

Response includes:

- `summary` (total, immediate/watch, bullish/bearish, average confidence)
- `signals` list with movement, confidence, horizon, rationale, risks

## 10. Pipeline Details

### 10.1 RSS Layer

In `api/rss_fetcher.py`:

- Loads active feeds from Supabase.
- Loads existing links from `rss_pool` with pagination.
- Parses RSS 2.0 and Atom.
- Cleans HTML from summaries.
- Deduplicates by article link.
- Inserts to `rss_pool` with duplicate-ignore preference.
- Logs run summary in `pool_logs`.

### 10.2 Optimizer Stage

In `pipeline_optimizer.py`:

- `prefilter_articles`: removes clearly non-financial content by source and keyword checks.
- `deduplicate_articles`: title similarity clustering (word-overlap heuristic).
- `save_progress` and chunk helpers: support incremental operation (current run path processes all filtered articles).

### 10.3 Layer 1 (Rule-Based NLP)

In `layers/layer1_content.py`:

- Rule-based extraction of Indian ticker entities.
- Event classification with keyword buckets.
- VADER sentiment + urgency triggers.
- Novelty scoring with in-memory hash dedup for the current process.
- Produces `relevance_score` and `is_financially_relevant`.

### 10.4 Layer 2 (Impact Propagation)

In `layers/layer2_propagation.py`:

- Uses loaded stock universe and sector index.
- Skips articles already processed in `l2_logs`.
- Batches profiles and asks LLM for affected entities.
- Outputs `impact_type`, direction, confidence, reason.
- Logs each batch immediately into `l2_logs`.

### 10.5 Layer 3 (Prediction)

In `layers/layer3_prediction.py`:

- Skips articles already processed in `l3_logs`.
- Pulls recent historical prices from external API:
  - `http://34.14.196.114/api/stocks/<ticker>/historical?period=1mo&page=1&limit=8`
- Builds price context (trend, volatility, momentum, volume ratio).
- Uses LLM to produce direction, move estimate/range, confidence, priority, rationale.
- Logs per profile into `l3_logs`.

### 10.6 Layer 4 (Reasoning)

In `layers/layer4_reasoning.py`:

- Skips rows already present in `l4_logs`.
- Skips L4 for low-priority profiles where highest L3 priority is `INFO` or `IGNORE`.
- Validates/refines L3 outputs and generates plain-English rationale.
- Writes final reasoning rows to `l4_logs`.

## 11. LLM Routing and Fallback

In `layers/llm_client.py`:

1. Primary call: OpenRouter (`openrouter/free`).
2. Fallback call: Gemini 2.5 Flash Lite.
3. Both paths normalize output to parsed JSON structures.
4. Retry logic for transient failures and rate limits.

## 12. Operational Notes

- Startup stock loading is lazy (`before_request`) and skipped for lightweight routes like `/api/health` and `/api/stock/*`.
- Knowledge graph is loaded either from `nse_stocks` in Supabase or via `/api/load-stocks`.
- Most write paths use minimal-return preferences for speed.
- Service is designed for cron-triggered runs (`/api/run`).

## 13. Cron Trigger Example

A scheduler (for example cron-job.org) can call:

- `GET https://<your-host>/api/run`

Recommended cadence: hourly.

## 14. Quick Validation Checklist

After deployment, validate in order:

1. `GET /api/health` returns `supabase_ok: true`.
2. `GET /api/run` returns `status: ok`.
3. `rss_pool` and `pool_logs` receive new rows.
4. `l1_logs`, `l2_logs`, and `l3_logs` populate after relevant news.
5. `GET /api/stock/TCS` returns non-empty `signals` once pipeline has relevant output.

## 15. Known Gaps / Caveats

- `run.py` and `config.py` are currently empty and not used for runtime.
- Health response text still labels layer4 as "coming soon", while layer4 code path exists and runs for suitable profiles.
- Layer 3 depends on external historical price API reachability.
- LLM output quality and availability depend on provider quotas and response correctness.

## 16. Useful Commands

Run pipeline manually:

```bash
curl -X GET "http://localhost:10000/api/run"
```

Get stock signals:

```bash
curl -X GET "http://localhost:10000/api/stock/TCS?hours=24&limit=20"
```

Add feed:

```bash
curl -X POST "http://localhost:10000/api/add-feed" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"My Feed\",\"url\":\"https://example.com/rss.xml\",\"category\":\"business\",\"country\":\"IN\"}"
```

Manual ingest:

```bash
curl -X POST "http://localhost:10000/api/ingest" \
  -H "Content-Type: application/json" \
  -d "{\"articles\":[{\"id\":1,\"title\":\"Sample\",\"summary\":\"Sample summary\",\"link\":\"https://example.com/1\",\"source\":\"Sample Source\",\"publish_date\":\"2026-03-15T10:00:00Z\"}]}"
```
