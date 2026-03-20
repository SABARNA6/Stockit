# Stockit Complete Technical Flow and Glossary

## 1) Purpose

This document gives a single source of truth for:

- System architecture across frontend, API gateway, equity intelligence, and ML services.
- End-to-end request and data flows.
- Core modules and their responsibilities.
- Definitions of technical terms used in this project.

It is intended for developers, QA, DevOps, and product stakeholders.

---

## 2) System Overview

Stockit is a multi-service platform with:

- A React frontend for UI and user interactions.
- A Flask API Gateway (`server`) on port `10000` that serves stock, ML, portfolio, user, and equity proxy APIs.
- A separate Flask service (`equity_intelligence_v3`) on port `5000` for RSS ingestion and 3-tier equity impact analysis.
- External data/model providers such as Yahoo Finance, NSE, NewsAPI, Groq, and Supabase.

High-level service topology:

1. Frontend calls `/api/*` endpoints.
2. Gateway handles stock/ML/portfolio/user routes directly.
3. Gateway forwards `/api/equity/*` requests to the Equity Intelligence service.
4. Equity Intelligence performs ingestion, caching, LLM scoring, and impact aggregation.
5. Responses flow back to frontend.

---

## 3) Component Map

### Frontend (`frontend`)

- Entry: `src/main.jsx`, `src/App.jsx`
- API client: `src/api/stockApi.js`
- Feature areas:
  - Stock detail modules (price, trends, recommendations, fundamentals, news)
  - Portfolio pages
  - Auth with Supabase

### API Gateway (`server`)

- Entry: `app.py`
- Blueprints:
  - `routes/stock_routes.py` -> `/api/stocks/*`, `/api/company/search`, `/api/ml/*`
  - `routes/equity_routes.py` -> `/api/equity/*` (proxy)
  - `routes/portfolio_routes.py` -> `/api/portfolio/*`, `/api/watchlist/*`
  - `routes/user_routes.py` -> `/api/user/*`

### Equity Intelligence (`equity_intelligence_v3`)

- Entry: `server.py`
- Blueprints:
  - `routes/rss_routes.py` -> RSS trigger/status
  - `routes/analysis_routes.py` -> analyze, limits, equities sync
- Pipeline modules:
  - `ingestion/rss_fetcher.py`
  - `ingestion/news.py`
  - `tiers/tier1.py`
  - `tiers/tier2.py`
  - `tiers/tier3.py`
  - `core/price_impact.py`
  - `core/cache.py`
  - `core/budget.py`
  - `core/router.py`

### Data and Model Sources

- Market data: `yfinance`, NSE connectors
- News data: RSS feeds, NewsAPI
- Database: Supabase tables (`rss_pool`, `equities`, etc.)
- LLM providers: Groq API (tier scoring and analysis)
- Auth/User data: Supabase Auth and profile/watchlist tables

---

## 4) Runtime and Port Flow

Default local runtime:

- Frontend dev server: Vite default (commonly 5173, project may use 3000 depending on setup)
- API Gateway: `http://localhost:10000`
- Equity Intelligence: `http://localhost:5000`

Flow relationship:

- Frontend -> Gateway (`/api/...`)
- Gateway -> Equity Intelligence for `/api/equity/...`
- Equity Intelligence -> Supabase + Groq + NewsAPI + RSS sources

---

## 5) API Flow (End-to-End)

## 5.1 Stock Data Flow

Endpoint family: `/api/stocks/<symbol>...`

1. Frontend calls gateway endpoint through `stockApi.js`.
2. Gateway route in `stock_routes.py` receives request.
3. Route calls helper functions in `helpers/stock_helper.py`.
4. Helper fetches market/fundamental/news/trend data from external services and internal transforms.
5. Gateway returns normalized JSON response with `success` and `data` (except where route uses custom envelope).
6. Frontend renders components (header, chart, fundamentals, news, recommendation panel).

## 5.2 ML Endpoints Flow

Endpoint family: `/api/ml/*`

1. Frontend (or client) calls ML endpoint.
2. `stock_routes.py` validates request.
3. ML helper executes prediction/recommendation logic.
4. Gateway wraps and returns result.

Included capabilities:

- Price horizon forecast (`/api/ml/price/<symbol>`)
- Strategy signal (`/api/ml/strategy/<symbol>`)
- Custom OHLCV strategy (`/api/ml/strategy/custom`)
- Portfolio-aware recommendation (`/api/ml/recommend`)
- Combined model response (`/api/ml/full/<symbol>`)

## 5.3 Equity Intelligence Proxy Flow

Endpoint family: `/api/equity/*`

1. Frontend or client calls gateway endpoint.
2. `equity_routes.py` forwards request to Equity Intelligence base URL (`EQUITY_INTELLIGENCE_URL`, default `http://localhost:5000`).
3. Equity Intelligence processes request via `analysis_routes.py` or `rss_routes.py`.
4. Response is proxied back to caller.

Proxy endpoints:

- Analyze symbol -> `/api/equity/analyze/<symbol>`
- Limits/budget -> `/api/equity/limits`
- Trigger ingestion -> `/api/equity/trigger`
- RSS status -> `/api/equity/status`

---

## 6) Equity Intelligence Internal Flow

## 6.1 Ingestion Flow

Trigger: `/api/rss/trigger`

1. Load active feed list from Supabase.
2. Fetch and parse RSS/Atom content.
3. Optional NewsAPI fetch for configured symbols.
4. Deduplicate articles (link/content checks).
5. Store normalized articles in Supabase `rss_pool`.
6. Write ingestion run metadata/logs.

## 6.2 Analysis Flow

Trigger: `/api/analyze/<symbol>?hours_back=24`

1. Validate symbol and load equity metadata.
2. Pull recent articles (`hours_back`) from ingestion layer.
3. Run Tier 1 (keyword and relevance filtering).
4. Run Tier 2 (LLM relevance scoring and thresholding).
5. Run Tier 3 (deep impact extraction: direction/confidence/horizon/cause).
6. Aggregate article impacts via `price_impact.py`.
7. Build final analysis payload with sentiment score and directional summary.
8. Return with cache metadata and runtime details.

## 6.3 Caching and Budget Control

- `core/cache.py`
  - Stores reusable results in SQLite to reduce recomputation and cost.
  - Applies TTL strategy by layer (article, sector, equity, user context).

- `core/budget.py`
  - Tracks daily request/token usage per API key and model.

- `core/router.py`
  - Selects key/model according to remaining capacity and policy.

Result:

- Better latency.
- Controlled LLM spending.
- Reduced rate-limit failures.

---

## 7) Data Contract and Response Patterns

Common patterns in gateway APIs:

- Success envelope: `{ "success": true, "data": ... }`
- Error envelope: `{ "success": false, "message": "..." }`

Frontend client expectations:

- Most calls read `response.data`.
- Some legacy/custom routes include additional top-level fields.
- Symbols should generally be uppercase and exchange suffix handling may vary by endpoint.

---

## 8) Configuration and Environment Variables

## 8.1 Gateway (`server`)

Common variables:

- `PORT` (default 10000)
- `DEBUG`
- `FRONTEND_URL` (CORS allow-list)
- `GOOGLE_SHEETS_URL` (news cache source)
- `EQUITY_INTELLIGENCE_URL` (proxy target, default localhost:5000)

## 8.2 Equity Intelligence (`equity_intelligence_v3`)

Required core variables:

- `SUPABASE_URL`
- `SUPABASE_KEY`
- `GROQ_KEY_A`
- `GROQ_KEY_B`

Optional/common variables:

- `PORT` (default 5000)
- `DEBUG`
- `NEWSAPI_KEY` or `NEWS_API_KEY`
- `NEWS_RETENTION_DAYS`
- `NEWSAPI_LOOKBACK_DAYS`
- `NEWSAPI_MAX_STOCKS`
- `NEWSAPI_PAGE_SIZE`
- `NEWSAPI_REQUEST_DELAY_SEC`
- `NEWSAPI_MAX_RETRIES`
- `NEWSAPI_BACKOFF_SEC`

---

## 9) Failure and Recovery Flow

Common failure points:

- External API outage or rate-limit (NewsAPI, market providers, LLM).
- Missing environment variables.
- Equity Intelligence service not running while gateway proxy is called.
- Supabase connectivity issues.

Recovery approach:

1. Check gateway health (`/`).
2. Check equity status (`/api/equity/status`).
3. Check limits (`/api/equity/limits`).
4. Re-trigger ingestion (`/api/equity/trigger`).
5. Validate environment variables and API keys.
6. Confirm ports and service startup order.

---

## 10) Complete Technical Glossary

API Gateway:

- A central backend service that receives client requests and dispatches them to internal modules/services.

Blueprint (Flask):

- A modular route grouping mechanism in Flask to organize endpoints by domain.

CORS:

- Cross-Origin Resource Sharing; browser policy controls allowing frontend and backend on different origins to communicate.

OHLCV:

- Open, High, Low, Close, Volume candle format for historical market data.

Sparkline:

- A compact mini-chart showing recent price movement points.

Timeframe:

- Window of data requested (for example 1W, 1M, 3M, 1Y).

Sentiment Analysis:

- NLP classification of news into positive/neutral/negative polarity.

FinBERT:

- A finance-tuned BERT model used for sentiment understanding in financial text.

Tier 1 / Tier 2 / Tier 3 pipeline:

- Multi-stage filtering and analysis process:
  - Tier 1: rule/keyword relevance filtering.
  - Tier 2: LLM relevance scoring.
  - Tier 3: deep impact reasoning extraction.

Price Impact Aggregation:

- Combining article-level impact signals into an expected move range and direction.

LLM Routing:

- Selecting which model/key to use based on cost, quality, and remaining quota.

Budget Tracking:

- Monitoring request/token usage limits for model providers.

Rate Limit:

- Provider-imposed cap on request frequency or token throughput.

TTL (Time To Live):

- Cache expiry duration after which data is considered stale.

Deduplication:

- Removing duplicate records, often by URL hash/content similarity.

Supabase:

- Backend platform used for database, auth, and managed APIs.

Upsert:

- Insert new row or update existing row if conflict key already exists.

Proxy Route:

- Endpoint that forwards request/response between client and another service.

Envelope Response:

- Standardized JSON wrapper format for API responses.

Risk Profile:

- Investor risk tolerance category (Low/Medium/High) used by recommendation logic.

Backtest:

- Historical simulation to evaluate how a strategy would have performed.

Confidence Score:

- Numeric estimate of model certainty in a prediction or classification.

Horizon:

- Prediction lookahead period, usually in days.

Market Cap:

- Company valuation = current price multiplied by shares outstanding.

P/E Ratio:

- Price-to-earnings ratio, valuation metric based on earnings per share.

ROE:

- Return on Equity, profitability relative to shareholder equity.

ATR:

- Average True Range, volatility measure used in risk/stop-loss planning.

Stop Loss:

- Price threshold used to limit downside risk.

Take Profit:

- Price target used to lock in gains.

Position Size:

- Fraction of portfolio capital allocated to a trade.

---

## 11) Suggested Standard Operating Flow (Developer)

1. Start Equity Intelligence service (port 5000).
2. Start API Gateway service (port 10000).
3. Start Frontend app.
4. Trigger RSS ingestion (optional but recommended before analysis).
5. Call stock and equity endpoints from frontend.
6. Monitor limits and cache status when debugging latency/cost.
7. Validate response envelopes for frontend compatibility.

---

## 12) Future Documentation Improvements

- Add sequence diagrams for each major endpoint family.
- Add table-level Supabase schema reference.
- Add deployment matrix for local, Docker, and production cloud.
- Add explicit SLA/SLO for endpoint latency and uptime.
- Add automated OpenAPI/Swagger generation from Flask routes.
