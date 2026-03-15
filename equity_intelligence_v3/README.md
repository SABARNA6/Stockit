# Equity Intelligence v3 Documentation

## Overview

Equity Intelligence v3 is a Flask-based stock intelligence service that:

- Ingests news from RSS feeds and NewsAPI into Supabase.
- Runs a 3-tier relevance/impact pipeline plus rule-based price impact aggregation.
- Exposes REST endpoints for RSS operations, stock analysis, API budget visibility, and equity metadata sync.

It supports both:

- API mode (`server.py`) for on-demand analysis and RSS triggering.
- Batch mode (`main.py`) for processing many equities in one run.

## Core Capabilities

1. News ingestion from Supabase-backed RSS feed list (`rss_feeds`) and NewsAPI symbol universe.
2. Deduplication, filtering, and classification of articles by stock relevance.
3. Tiered LLM analysis with cache + key budget control.
4. Rule-based conversion of article impacts into stock move ranges.
5. Local SQLite cache/budget state + Supabase-backed article/equity storage.

## High-Level Architecture

### Ingestion Layer

- `ingestion/rss_fetcher.py`
  - Loads active RSS feeds from Supabase `rss_feeds`.
  - Parses RSS 2.0 + Atom XML.
  - Deduplicates by article link.
  - Optionally enriches with NewsAPI equity articles from `data/newsapi_symbols.json`.
  - Saves to Supabase `rss_pool`.
  - Logs run summaries to `pool_logs`.

- `ingestion/news.py`
  - Reads from `rss_pool` and normalizes article payloads.
  - Applies retention cleanup (`NEWS_RETENTION_DAYS`, default 7 days).

- `ingestion/equity_sync.py`
  - Syncs local `data/equities.json` profiles into Supabase `equities`.
  - Generates missing profiles via `data/generate_equities.py` when needed.

### Analysis Layer

- `tiers/tier1.py` (free/rule-based)
  - Dedup by content hash.
  - Keyword filter by sector + macro + peers + symbol/company match.
  - Classifies article type (company, sector, macro, noise).

- `tiers/tier2.py` (LLM scoring)
  - Scores relevance 0-10 using Groq.
  - Applies threshold (`TIER2_THRESHOLD`, default 6).
  - Caches sector/article score outputs.

- `tiers/tier3.py` (LLM deep impact)
  - Returns `impact`, `direction`, `confidence`, `cause`, `horizon`.
  - Uses model routing based on score/quality threshold.
  - Caches non-company-specific outputs.

- `core/price_impact.py` (rule-based aggregation)
  - Converts tier outputs into per-article move ranges.
  - Aggregates weighted overall move and direction.

### Platform Layer

- `core/cache.py`
  - SQLite-backed cache + budget tables.
  - Layer TTLs (article/sector/equity/user), with shorter equity TTL during market hours.

- `core/budget.py`
  - Tracks per-key, per-model daily requests/tokens.

- `core/router.py`
  - Chooses model/key based on tier + score + remaining budget + RPM checks.

- `config/config.py`
  - API keys, model names, limits, thresholds, TTLs, file paths.

## Runtime Modes

### 1) API server mode

Entrypoint: `server.py`

- Starts Flask app with blueprints:
  - `routes/rss_routes.py` (`/api/rss/*`)
  - `routes/analysis_routes.py` (`/api/*`)

Default: `http://localhost:5000`

### 2) Batch CLI mode

Entrypoint: `main.py`

- Initializes cache/budget tables.
- Prunes old news.
- Fetches recent articles from Supabase.
- Loads equities, syncs missing profiles to Supabase.
- Runs pipeline equity by equity and prints summaries.

## API Reference

Base URL (default): `http://localhost:5000`

### `GET /`

Service health and endpoint index.

### `GET /api/rss/status`

RSS module health.

### `GET|POST /api/rss/trigger`

Triggers RSS + NewsAPI ingestion.

Example response:

```json
{
  "status": "success",
  "feeds_fetched": 10,
  "total_new": 45,
  "total_skipped": 23,
  "saved_to_db": 45,
  "total_pool": 2500,
  "message": "Fetched 10 feeds. New: 45, Skipped: 23",
  "feed_results": []
}
```

### `GET /api/analyze/<symbol>?hours_back=24&prune_news=false`

Runs full analysis pipeline for one symbol.

Query parameters:

- `hours_back` (int, default `24`): how far back to pull articles.
- `prune_news` (bool, default `false`): whether to trigger retention cleanup first.

On success, response includes:

- `cache.result_cache_status`
- `cache.snapshot`
- `analysis` full pipeline result

### `GET /api/limits`

Returns:

- Groq key/model usage (requests/tokens used + remaining) from local budget DB.
- NewsAPI best-effort live status probe + rate-limit headers when available.
- Cache snapshot summary.

### `GET|POST /api/equities/sync`

Syncs local `equities.json` into Supabase `equities` table.

## Output Schema (Analysis)

Top-level fields from `core/pipeline.py`:

- `symbol`
- `timestamp`
- `cache_status` (`fresh` or `hit`)
- `elapsed_sec`
- `articles_input`
- `articles_analyzed`
- `sentiment_score` (0-10 weighted)
- `overall_direction` (`BULLISH`, `BEARISH`, `NEUTRAL`)
- `price_impact`
- `results`

`price_impact` contains:

- `overall_move_low`
- `overall_move_high`
- `overall_move_range` (text)
- `overall_direction`
- `signals` (`bullish`, `bearish`, `neutral` counts)

Each item in `results` includes tier outputs + derived move range fields.

## Environment Variables

Required:

- `SUPABASE_URL`
- `SUPABASE_KEY`
- `GROQ_KEY_A`
- `GROQ_KEY_B`

Optional/feature flags:

- `PORT` (default `5000`)
- `DEBUG` (`true`/`false`)
- `NEWS_RETENTION_DAYS` (default `7`)
- `NEWSAPI_KEY` (or `NEWS_API_KEY` alias)
- `NEWSAPI_LOOKBACK_DAYS` (default `30`)
- `NEWSAPI_MAX_STOCKS` (default `15`)
- `NEWSAPI_PAGE_SIZE` (default `8`)
- `NEWSAPI_REQUEST_DELAY_SEC` (default `0.6`)
- `NEWSAPI_MAX_RETRIES` (default `2`)
- `NEWSAPI_BACKOFF_SEC` (default `2.0`)

## Dependencies

From `requirements.txt`:

- `groq`
- `httpx`
- `python-dotenv`
- `supabase`
- `flask`
- `requests`
- `yfinance`
- `nse`

## Data Files

- `data/equities.json`: curated equity profiles used by pipeline.
- `data/keywords.json`: sector/macro keyword map for Tier 1.
- `data/newsapi_symbols.json`: stock universe used for NewsAPI queries.

## Setup and Run

### 1. Install

```bash
cd equity_intelligence_v3
pip install -r requirements.txt
```

### 2. Configure `.env`

Set required keys and Supabase URL.

### 3. Start API server

```bash
python server.py
```

### 4. Trigger ingestion

```bash
curl http://localhost:5000/api/rss/trigger
```

### 5. Analyze a stock

```bash
curl "http://localhost:5000/api/analyze/NGLFINE?hours_back=24"
```

### 6. Check budgets/limits

```bash
curl http://localhost:5000/api/limits
```

## Supabase Tables Used

Ingestion and logging:

- `rss_feeds`
- `rss_pool`
- `pool_logs`

Equity metadata:

- `equities`

Note: Ensure RLS/policies allow required read/write actions for the key used by this service.

## Caching and Budget Behavior

- Equity-level results are cached by symbol + date + hour.
- Sector/article level caches reduce repeated LLM calls.
- Budget limits are enforced per key/model using local SQLite (`db/cache.db`).
- Router falls back across keys/models when budget allows.

## Known Operational Notes

1. `EndPoints.txt`, `QUICKSTART.md`, and `RSS_SETUP.md` provide quick/manual references; this README is the consolidated technical document.
2. During market hours, equity cache TTL is reduced for fresher analysis.
3. Tier 3 has parser fallbacks; malformed LLM JSON degrades gracefully to low-confidence neutral outputs.
4. If no relevant articles pass thresholds, analysis returns an error-style payload with status details.

## Troubleshooting

### No articles analyzed

- Verify `rss_pool` has fresh rows.
- Increase `hours_back` in `/api/analyze/<symbol>`.
- Run `/api/rss/trigger` first.

### RSS trigger returns no feeds

- Ensure `rss_feeds` has active rows (`is_active=true`).

### Supabase auth errors

- Verify `SUPABASE_URL` and `SUPABASE_KEY` values.
- Confirm table permissions/RLS for service operations.

### LLM budget exhausted

- Check `/api/limits` for per-model remaining requests/tokens.
- Wait for daily reset or adjust workload.

### Symbol not found

- `/api/analyze/<symbol>` attempts dynamic generation via `generate_equity`.
- If generation fails, add profile manually to `data/equities.json` and re-run sync.
