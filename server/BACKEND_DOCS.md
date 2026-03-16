# StockIt — Backend Documentation

**Stack:** Python · Flask · yfinance · NSEPython · NewsAPI · FinBERT (Gradio/HuggingFace)

---

## Table of Contents

1. [Project Structure](#1-project-structure)
2. [Environment Variables](#2-environment-variables)
3. [Running the Server](#3-running-the-server)
4. [Application Entry Point — `app.py`](#4-application-entry-point--apppy)
5. [API Routes — `routes/stock_routes.py`](#5-api-routes--routesstock_routespy)
   - [Response Envelope](#response-envelope)
   - [Route Reference Table](#route-reference-table)
   - [Route Details](#route-details)
6. [Helper Functions — `helpers/stock_helper.py`](#6-helper-functions--helpersstock_helperpy)
   - [Data Sources & Priority](#data-sources--priority)
   - [Internal Utility Functions](#internal-utility-functions)
   - [Public Helper Functions](#public-helper-functions)
7. [Data Flow Diagram](#7-data-flow-diagram)
8. [Dependencies](#8-dependencies)
9. [Error Handling](#9-error-handling)

---

## 1. Project Structure

```
server/
├── app.py                  # Flask application factory & entry point
├── requirements.txt        # Python dependencies
├── .env                    # Secret keys (not committed)
├── .env.example            # Template for .env
├── test.py                 # Manual test scripts
├── test_data.py            # Sample test data
├── routes/
│   └── stock_routes.py     # All API endpoint definitions (Blueprint)
└── helpers/
    └── stock_helper.py     # All data-fetching & computation logic
```

---

## 2. Environment Variables

Copy `.env.example` to `.env` and fill in the values:

| Variable            | Required            | Description                                                                                                                                  |
| ------------------- | ------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `NEWS_API_KEY`      | Yes (for live news) | API key from [newsapi.org](https://newsapi.org) — used to fetch news articles                                                                |
| `FINBERT_API_URL`   | No                  | Not actively used; FinBERT is accessed via the Gradio HuggingFace Hub client                                                                 |
| `FINBERT_API_KEY`   | No                  | Reserved for future authenticated FinBERT access                                                                                             |
| `GOOGLE_SHEETS_URL` | No                  | URL of a Google Sheets REST endpoint used as a **news cache**. When set, news requests hit this cache first before calling NewsAPI + FinBERT |
| `PORT`              | No                  | HTTP port to listen on. Defaults to `10000` at runtime (production), can be set to `5000` locally                                            |
| `FLASK_DEBUG`       | No                  | Set to `"true"` to enable Flask debug/reloader. Defaults to `"true"`                                                                         |

---

## 3. Running the Server

```bash
cd server

# Development (debug mode on)
python app.py

# Or using Flask CLI
flask run --port 5000
```

The server binds to `0.0.0.0` so it's reachable from the network (or Docker). Port is read from `PORT` env var, defaulting to `10000`.

---

## 4. Application Entry Point — `app.py`

The `create_app()` factory function:

1. **Loads `.env`** from the `server/` directory using `python-dotenv`.
2. **Creates the Flask app**, setting `./dist` as the static folder (serves the built React frontend).
3. **Enables CORS** globally via `flask-cors` so the React dev server on a different port can call the API.
4. **Registers the `stock_bp` Blueprint** with the `/api` prefix (all data endpoints).
5. **Defines three built-in routes:**

| Route         | Description                                                                                           |
| ------------- | ----------------------------------------------------------------------------------------------------- |
| `GET /`       | Serves `dist/index.html` (built frontend). Returns a JSON hint if the frontend hasn't been built yet. |
| `GET /health` | Health-check endpoint. Returns `{"status": "ok", "service": "stockit-api"}`.                          |
| `404` handler | Returns `{"success": false, "message": "Endpoint not found"}` for unknown routes.                     |
| `500` handler | Returns `{"success": false, "message": "Internal server error"}` for unhandled exceptions.            |

---

## 5. API Routes — `routes/stock_routes.py`

All routes live under the **`/api`** prefix (Flask Blueprint `url_prefix="/api"`).

### Response Envelope

Every data response is wrapped in a consistent envelope using two helper functions:

```json
// Success
{ "success": true, "data": { ... } }

// Error
{ "success": false, "message": "error description" }
```

The `ok(data)` helper wraps success payloads; `err(msg, status)` wraps error payloads.

> **Exception:** `/api/stocks/<symbol>/historical` returns a slightly extended envelope with `symbol` and `period` fields directly on the top-level object.

---

### Route Reference Table

| Method | Endpoint                              | Query Params                 | Description                            |
| ------ | ------------------------------------- | ---------------------------- | -------------------------------------- |
| `GET`  | `/api/stocks/<symbol>`                | —                            | Real-time stock overview               |
| `GET`  | `/api/stocks/<symbol>/sparkline`      | `points` (int, default `12`) | Last N closing prices for a mini chart |
| `GET`  | `/api/stocks/<symbol>/chart`          | `timeframe` (default `3M`)   | OHLC candlestick data                  |
| `GET`  | `/api/stocks/<symbol>/volume`         | `timeframe` (default `3M`)   | Daily volume bars                      |
| `GET`  | `/api/stocks/<symbol>/trends`         | —                            | Trend direction, volume status, risk   |
| `GET`  | `/api/stocks/<symbol>/recommendation` | —                            | Buy/sell recommendation + entry plan   |
| `GET`  | `/api/stocks/<symbol>/fundamentals`   | —                            | Structured financial metrics           |
| `GET`  | `/api/stocks/<symbol>/news`           | —                            | News articles + sentiment analysis     |
| `GET`  | `/api/stocks/<symbol>/historical`     | `period`, `page`, `limit`    | Paginated OHLCV history                |
| `GET`  | `/api/company/search`                 | `symbol` (required)          | Company lookup on NSE & BSE            |

> **Symbol format:** Pass just the ticker, e.g., `RELIANCE`, `TCS`, `INFY`. The backend appends `.NS` automatically for NSE data.

---

### Route Details

#### `GET /api/stocks/<symbol>`

Returns a real-time snapshot of the stock.

**Sample Response `data` object:**

```json
{
  "symbol": "RELIANCE",
  "name": "Reliance Industries Limited",
  "exchange": "NSE",
  "sector": "Energy",
  "industry": "Oil & Gas Integrated",
  "currentPrice": 2950.1,
  "previousClose": 2930.0,
  "open": 2935.0,
  "dayHigh": 2975.0,
  "dayLow": 2920.0,
  "change": 20.1,
  "changePercent": 0.69,
  "volume": 5234100,
  "avgVolume": 4800000,
  "marketCap": 1993600000000,
  "fiftyTwoWeekHigh": 3217.0,
  "fiftyTwoWeekLow": 2220.3,
  "peRatio": 24.5,
  "eps": 120.14,
  "dividendYield": 0.003,
  "roe": 0.095,
  "vwap": 2947.8,
  "upperCircuit": 3369.5,
  "lowerCircuit": 2490.5,
  "lastUpdated": "2026-03-10T09:31:00"
}
```

Returns `404` with `{ "success": false, "message": "Stock not found" }` if the symbol is invalid or delisted.

---

#### `GET /api/stocks/<symbol>/sparkline?points=12`

Returns the last `points` daily closing prices for rendering a small trend line.

**Sample Response `data` object:**

```json
{
  "prices": [2810.0, 2835.5, 2860.0, 2890.0, 2920.5, 2950.1],
  "trend": "up",
  "min": 2810.0,
  "max": 2950.1
}
```

- `trend`: `"up"` if last price ≥ first price, otherwise `"down"`.

---

#### `GET /api/stocks/<symbol>/chart?timeframe=3M`

Returns OHLC candlestick data for the selected timeframe.

**Supported `timeframe` values:**

| Value | Maps to yfinance period |
| ----- | ----------------------- |
| `1W`  | `5d`                    |
| `1M`  | `1mo`                   |
| `3M`  | `3mo` (default)         |
| `6M`  | `6mo`                   |
| `1Y`  | `1y`                    |
| `ALL` | `max`                   |

**Sample Response `data` object:**

```json
{
  "candles": [
    {
      "timestamp": "2026-01-02",
      "open": 2820.0,
      "high": 2855.0,
      "low": 2810.0,
      "close": 2840.0
    },
    {
      "timestamp": "2026-01-03",
      "open": 2840.0,
      "high": 2875.0,
      "low": 2830.0,
      "close": 2860.0
    }
  ]
}
```

Only candles with all four valid OHLC values are included.

---

#### `GET /api/stocks/<symbol>/volume?timeframe=3M`

Returns daily volume bars alongside the period average volume.

**Sample Response `data` object:**

```json
{
  "volumes": [
    { "timestamp": "2026-01-02", "volume": 6100000, "aboveAvg": true },
    { "timestamp": "2026-01-03", "volume": 3900000, "aboveAvg": false }
  ],
  "avgVolume": 4800000
}
```

- `aboveAvg`: `true` if that day's volume exceeded the period average.
- Missing/zero-volume days are excluded.

---

#### `GET /api/stocks/<symbol>/trends`

Returns trend signals computed from 3 months of price/volume history.

**Sample Response `data` object:**

```json
{
  "trend": {
    "direction": "bullish",
    "strength": 72.5
  },
  "volume": {
    "status": "High",
    "ratio": 1.43,
    "institutionalActivity": "Net Buying",
    "deliveryPercent": 68.4
  },
  "risk": {
    "volatility": "Medium",
    "beta": 1.1,
    "atr": 58.4,
    "riskLevel": "Medium"
  }
}
```

**How each field is computed:**

| Field                          | Logic                                                                                                       |
| ------------------------------ | ----------------------------------------------------------------------------------------------------------- |
| `trend.direction`              | `"bullish"` if current price > 20-day MA AND > 50-day MA. `"bearish"` if below both. `"neutral"` otherwise. |
| `trend.strength`               | How far (%) price is from its 20-day MA, scaled × 10, capped at 100.                                        |
| `volume.status`                | `"Spike"` if vol ≥ 2.5× avg; `"High"` if ≥ 1.2×; `"Low"` if < 0.8×; `"Normal"` otherwise.                   |
| `volume.ratio`                 | Today's volume ÷ average volume.                                                                            |
| `volume.institutionalActivity` | `"Net Buying"` if ratio > 1, else `"Net Selling"`.                                                          |
| `volume.deliveryPercent`       | Proxy estimate (50–85%) based on volume ratio and volume consistency (std dev).                             |
| `risk.atr`                     | 14-day Average True Range using the actual formula: TR = max(H-L, \|H-prevC\|, \|L-prevC\|).                |
| `risk.volatility`              | `"High"` if beta > 1.2; `"Low"` if beta < 0.8; `"Medium"` otherwise.                                        |
| `risk.riskLevel`               | `"High"` if beta > 1.3 or ATR% > 3; `"Low"` if beta < 0.8 and ATR% < 1.5; `"Medium"` otherwise.             |

---

#### `GET /api/stocks/<symbol>/recommendation`

Returns an analyst-backed buy/sell recommendation with a full entry plan.

**Sample Response `data` object:**

```json
{
  "recommendation": "buy",
  "confidence": 70,
  "timeHorizon": "Medium Term",
  "targetPrice": 3200.0,
  "upside": 8.47,
  "technicalScore": 73,
  "fundamentalScore": 58,
  "analystRecs": {
    "strongBuy": 5,
    "buy": 12,
    "hold": 8,
    "sell": 2,
    "strongSell": 0
  },
  "entryPlan": {
    "accumulationZone": { "min": 2832.1, "max": 3009.1 },
    "breakoutAbove": 3097.61,
    "stopLoss": 2714.09,
    "riskRewardRatio": 2.09,
    "positionSize": 10
  },
  "reasoning": {
    "technical": ["Price near support", "RSI in normal range"],
    "fundamental": ["Revenue growth positive", "Healthy balance sheet"],
    "sentiment": ["Analyst consensus: Buy"],
    "risks": ["Market volatility", "Sector headwinds"]
  }
}
```

**`recommendation` values:** `"strongbuy"` | `"buy"` | `"hold"` | `"sell"` | `"strongsell"`

**Computed fields:**

| Field              | Logic                                                                    |
| ------------------ | ------------------------------------------------------------------------ |
| `confidence`       | 80 if upside > 20%; 70 if > 10%; 60 if > 0%; 50 if > -10%; 40 otherwise. |
| `technicalScore`   | `100 - (P/E / 30 × 100)`, clamped to [30, 95].                           |
| `fundamentalScore` | `50 + upside%`, clamped to [30, 95].                                     |
| `stopLoss`         | `currentPrice × 0.92` (8% below current).                                |
| `breakoutAbove`    | `currentPrice × 1.05` (5% above current).                                |
| `riskRewardRatio`  | `(target - current) / (current - stopLoss)`.                             |

---

#### `GET /api/stocks/<symbol>/fundamentals`

Returns financial metrics grouped into four categories used by `FundamentalsGrid.jsx`.

**Sample Response `data` object:**

```json
{
  "profitability": {
    "netProfit": 45000000000,
    "ebitdaMargin": 18.5,
    "roe": 9.5,
    "roa": 5.2
  },
  "valuation": {
    "peRatio": 24.5,
    "pegRatio": 1.2,
    "pbRatio": 2.3,
    "evEbitda": 14.8
  },
  "growth": {
    "revenueCagr5y": 4.9,
    "profitCagr5y": -13.9,
    "epsGrowthTtm": -0.139,
    "salesGrowth": 0.049
  },
  "financialHealth": {
    "debtToEquity": 42.5,
    "interestCoverage": 8.3,
    "currentRatio": 1.2,
    "quickRatio": 0.9
  }
}
```

> **Note on units:** `revenueCagr5y` and `profitCagr5y` are percentage values (e.g., `4.9` = 4.9%). `epsGrowthTtm` and `salesGrowth` are raw decimal values (e.g., `0.049` = 4.9%) — the frontend handles formatting differently for each.

**How `pegRatio` is computed:**

1. Tries to compute EPS CAGR from the income statement (`ticker.financials` — Diluted EPS row).
2. Falls back to `P/E ÷ earningsGrowth%` if income statement data is unavailable.

**How `interestCoverage` is computed:**
`EBIT / |Interest Expense|` from `ticker.financials`.

---

#### `GET /api/stocks/<symbol>/news`

Returns up to 15 news articles with per-article AI sentiment analysis.

**Cache-first behaviour:**

1. If `GOOGLE_SHEETS_URL` is configured → fetches news from the Google Sheets REST endpoint using `?symbol=SYMBOL`. The response is normalised into the standard shape (`_normalize_sheets_news`).
2. If no cache URL or the cache request fails → calls **NewsAPI** for articles and runs each article through **FinBERT** for sentiment.

**Sample Response `data` object:**

```json
{
  "source": "live",
  "sentiment": {
    "positive": 46.67,
    "neutral": 33.33,
    "negative": 20.0
  },
  "news": [
    {
      "title": "Reliance reports record quarterly profit",
      "summary": "Reliance Industries posted...",
      "source": "Economic Times",
      "publishedAt": "2026-03-09T14:30:00Z",
      "url": "https://...",
      "tags": ["positive"],
      "sentiment": "Positive",
      "confidence": 0.9231,
      "symbol": "RELIANCE"
    }
  ]
}
```

- `source`: `"live"` (NewsAPI + FinBERT), `"cache"` (Google Sheets), or `"error"`.
- `sentiment.positive/neutral/negative`: Percentage breakdown across all articles.
- `confidence`: FinBERT's score for the top-predicted sentiment class (0–1).

---

#### `GET /api/stocks/<symbol>/historical?period=1mo&page=1&limit=8`

Returns paginated OHLCV data sorted newest-first.

**Query Parameters:**

| Param    | Default | Description                                                                      |
| -------- | ------- | -------------------------------------------------------------------------------- |
| `period` | `1mo`   | yfinance period string: `1d`, `5d`, `1mo`, `3mo`, `6mo`, `1y`, `2y`, `5y`, `max` |
| `page`   | `1`     | Page number (1-based)                                                            |
| `limit`  | `8`     | Items per page                                                                   |

**Response envelope** (note: extended format, not the standard `{success, data}` wrapper):

```json
{
  "success": true,
  "symbol": "RELIANCE",
  "period": "1mo",
  "data": {
    "prices": [
      {
        "date": "2026-03-10",
        "open": 2935.0,
        "high": 2975.0,
        "low": 2920.0,
        "close": 2950.1,
        "volume": 5234100,
        "changePercent": 0.69,
        "highVolume": true
      }
    ],
    "pagination": {
      "currentPage": 1,
      "totalPages": 3,
      "totalItems": 22,
      "limit": 8
    }
  }
}
```

- `changePercent`: Change from previous trading day's close.
- `highVolume`: `true` if volume > 1.5× the period average volume.

---

#### `GET /api/company/search?symbol=RELIANCE`

Looks up a company on both **NSE** and **BSE** simultaneously.

**Query Parameters:**

| Param    | Required | Description                            |
| -------- | -------- | -------------------------------------- |
| `symbol` | Yes      | Company ticker without exchange suffix |

**Sample Response:**

```json
{
  "data": [
    {
      "symbol": "RELIANCE",
      "name": "Reliance Industries Limited",
      "exchange": "NSE",
      "sector": "Energy",
      "industry": "Oil & Gas Integrated"
    },
    {
      "symbol": "RELIANCE",
      "name": "Reliance Industries Limited",
      "exchange": "BSE",
      "sector": "Energy",
      "industry": "Oil & Gas Integrated"
    }
  ]
}
```

Returns both NSE and BSE entries if the stock is listed on both exchanges. Returns an empty `data` array if the symbol isn't found on either.

---

## 6. Helper Functions — `helpers/stock_helper.py`

### Data Sources & Priority

The backend uses **three live data sources** and one cache layer:

| Source                               | Used For                                            | Priority                                                        |
| ------------------------------------ | --------------------------------------------------- | --------------------------------------------------------------- |
| **NSEPython** (`nsepython`)          | Live prices, circuit limits, VWAP, P/E, market cap  | **Primary** for all real-time price fields                      |
| **yfinance**                         | Historical data, fundamentals, financials, metadata | **Primary** for all non-price fields; fallback for price fields |
| **NewsAPI**                          | News article headlines & descriptions               | Live source for news                                            |
| **FinBERT** (via Gradio HuggingFace) | Per-article NLP sentiment classification            | Called for each news article                                    |
| **Google Sheets**                    | Pre-analyzed news cache                             | Checked before NewsAPI to reduce API usage                      |

> yfinance can lag 15–20 minutes during NSE market hours, which is why NSEPython is preferred for all price-related fields.

---

### Internal Utility Functions

#### `_ticker_sym(symbol: str) → str`

Converts a bare stock symbol to the yfinance NSE format.

- `"RELIANCE"` → `"RELIANCE.NS"`
- `"RELIANCE.NS"` → `"RELIANCE.NS"` (idempotent)
- `.BO` suffixes are also preserved as-is.

#### `_safe_float(val, default=None) → float | None`

Safely converts any value to a float. Returns `None` for `None`, `NaN`, `Infinity`, or unconvertible values.

#### `_safe_int(val, default=None) → int | None`

Safely converts any value to an integer. Returns `None` for `None` or unconvertible values.

#### `_nse_fundamentals(symbol: str) → dict`

Fetches fundamental data from NSEPython as a fallback source when yfinance doesn't have a value.

Returns a flat dict with keys: `peRatio`, `pbRatio`, `eps`, `marketCap`, `faceValue`, `weekHigh52`, `weekLow52`, `currentPrice`, `vwap`.

- **EPS** is computed as `Price / P/E` ratio when not directly available.
- **Market Cap** is computed as `Price × shares issued`.
- P/B ratio is **not available** from NSE and is always `None` here.

#### `_get_finbert_client() → GradioClient`

Lazily initializes a singleton Gradio client connected to the `Sabarna6/FinBERT_FinancialSentimentAnalysis` HuggingFace Space. The client is cached in the module-level `_finbert_client` variable.

#### `_analyze_sentiment(text: str) → dict`

Sends text to FinBERT and returns:

```python
{ "sentiment": "Positive" | "Negative" | "Neutral", "confidence": float }
```

Returns `{"sentiment": "Neutral", "confidence": 0.0}` on any error.

---

### Public Helper Functions

#### `get_realtime_stock(symbol: str) → dict`

The most complex function in the codebase. Performs a **two-source merge**:

1. Fetches live data from NSEPython (real-time during market hours).
2. Fetches metadata from yfinance.
3. Merges them using two resolution strategies:
   - `nse_or_yf(key, yf_val)`: Prefer NSE for **price fields** (currentPrice, VWAP, circuits, etc.)
   - `yf_or_nse(yf_val, key)`: Prefer yfinance for **metadata fields** (marketCap, P/E as secondary)

**VWAP fallback:** If NSE VWAP is unavailable, computes it from 1-minute intraday bars:

```
VWAP = Σ(TypicalPrice × Volume) / ΣVolume
     where TypicalPrice = (High + Low + Close) / 3
```

**Circuit limits fallback:** If NSE doesn't provide per-stock circuit limits, uses ±15% of previous close as an approximation.

Returns `{}` (empty dict) if no price data is found (invalid/delisted symbol).

---

#### `get_sparkline(symbol: str, points: int = 12) → dict`

Fetches 1 month of daily history and returns the last `points` closing prices.

---

#### `get_historical_data(symbol: str, period: str, page: int, limit: int) → dict`

Fetches OHLCV for the given yfinance `period`, computes daily change % and high-volume flags, reverses to newest-first, then paginates.

---

#### `get_financials(symbol: str) → dict`

Returns raw financial statement data from yfinance `ticker.info`. A lower-level version of `get_finacial_metric` — returns a flat dict with ~20 fields. _(Note: this function is imported in `stock_routes.py` but not mapped to a dedicated route; it may be used internally or reserved for future use.)_

---

#### `get_finacial_metric(symbol: str) → dict`

The structured version of financials. Performs additional computations:

1. Fetches `ticker.info` from yfinance.
2. Fetches `_nse_fundamentals()` as a fallback for P/E, market cap.
3. Computes **PEG Ratio** from income statement EPS CAGR or earnings growth.
4. Computes **Interest Coverage** from the income statement (EBIT / |Interest Expense|).
5. Converts decimal values (0.42) to percentage values (42%) for `roe` and `roa`.
6. Returns data in four nested groups: `profitability`, `valuation`, `growth`, `financialHealth`.

---

#### `get_news(symbol: str, get_realtime_stock_fn) → dict`

1. Resolves the company's full name from `get_realtime_stock_fn` (used as the NewsAPI search query — company names return better results than tickers).
2. Fetches up to 15 articles from `https://newsapi.org/v2/everything`.
3. Runs **each article** through `_analyze_sentiment(title + description)`.
4. Computes sentiment percentages across all articles.

The `get_realtime_stock_fn` is passed in (dependency injection) to avoid a circular import.

---

#### `get_stock_trends(symbol: str) → dict`

Fetches 3 months of daily OHLCV and computes:

- **Trend direction**: Price vs 20-day and 50-day Simple Moving Average.
- **Trend strength**: Distance from 20-day MA as a 0–100 score.
- **Volume status**: Ratio of today's volume to 3-month average.
- **Delivery %**: Proxy estimate from volume ratio + volume consistency.
- **ATR (14-day)**: True Range formula over last 14 trading days.
- **Risk level**: Combined beta + ATR% threshold classification.

---

#### `get_recommendation(symbol: str) → dict`

Reads `ticker.info` from yfinance and:

- Maps `recommendationKey` (e.g., `"strong_buy"`) to the frontend's format (`"strongbuy"`).
- Computes `upside` as `(targetMeanPrice - currentPrice) / currentPrice × 100`.
- Derives `confidence`, `technicalScore`, `fundamentalScore` from upside and P/E.
- Reads analyst count breakdown from `ticker.recommendations` (the latest row).
- Generates a fixed entry plan (stop-loss, breakout level, accumulation zone, risk:reward ratio).

---

#### `get_chart_data(symbol: str, timeframe: str) → dict`

Maps the frontend's `timeframe` string (e.g., `"3M"`) to a yfinance period (e.g., `"3mo"`) using `_PERIOD_MAP` and returns OHLC candles.

---

#### `get_volume_data(symbol: str, timeframe: str) → dict`

Same timeframe mapping as `get_chart_data`. Returns daily volumes with an `aboveAvg` flag computed against the period average.

---

#### `search_company(symbol: str) → dict`

Tries `SYMBOL.NS` and `SYMBOL.BO` via yfinance. For each, if `longName` or `shortName` is found in `ticker.info`, it adds an entry to the results list. Returns both exchanges if the stock is dual-listed.

---

## 7. Data Flow Diagram

```
Browser / React Frontend
         │
         │  HTTP GET /api/...
         ▼
┌─────────────────────────────────┐
│         Flask  app.py           │
│   (CORS, Blueprint registration)│
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│    routes/stock_routes.py       │
│  (URL parsing, validation,      │
│   ok/err envelope, caching)     │
└──────────────┬──────────────────┘
               │ calls helper functions
               ▼
┌─────────────────────────────────────────────────────┐
│              helpers/stock_helper.py                │
│                                                     │
│  ┌───────────┐  ┌──────────────┐  ┌─────────────┐  │
│  │ NSEPython │  │   yfinance   │  │   NewsAPI   │  │
│  │ (live NSE)│  │ (yf.Ticker)  │  │  /v2/every- │  │
│  │ prices,   │  │  history,    │  │  thing      │  │
│  │ circuits  │  │  info, recs  │  └──────┬──────┘  │
│  └─────┬─────┘  └──────┬───────┘         │         │
│        │               │                 ▼         │
│        └───────┬────────┘         ┌─────────────┐  │
│                │                  │   FinBERT   │  │
│                ▼                  │  (Gradio/   │  │
│         Merge & compute           │  HuggingFace│  │
│                │                  └──────┬──────┘  │
│                └──────────────────────────┘         │
└─────────────────────────────────────────────────────┘
               │
               │  JSON response
               ▼
         Frontend
```

---

## 8. Dependencies

From `requirements.txt`:

| Package         | Version  | Purpose                                          |
| --------------- | -------- | ------------------------------------------------ |
| `flask`         | ≥ 3.0.0  | Web framework                                    |
| `flask-cors`    | ≥ 4.0.0  | Cross-Origin Resource Sharing                    |
| `python-dotenv` | ≥ 1.0.0  | Loading `.env` environment variables             |
| `yfinance`      | ≥ 0.2.38 | Stock market data (Yahoo Finance)                |
| `nsepython`     | ≥ 2.8    | Real-time NSE India data                         |
| `requests`      | ≥ 2.31.0 | HTTP client for NewsAPI and Google Sheets        |
| `gradio_client` | latest   | Calling FinBERT on HuggingFace Spaces            |
| `websockets`    | ≥ 12.0   | Required by `gradio_client` for Gradio streaming |

> `nsepython` is imported with a try/except guard. If it fails to import (e.g., on a non-Indian network or if not installed), the server still starts and falls back to yfinance-only data.

---

## 9. Error Handling

**At the application level:**

- `404` and `500` Flask error handlers return JSON responses (not HTML).

**At the route level:**

- `stock_overview` returns `404` if `get_realtime_stock` returns an empty dict.
- `company_search` returns `400` if `symbol` query param is missing or if the helper returns an error key.
- All other routes return whatever the helper function returns; if that is an empty/fallback dict, the frontend receives `{ "success": true, "data": {...empty...} }`.

**At the helper level:**

- Every helper function is wrapped in a `try/except Exception as e` block.
- On failure, helpers print a log message with `[function_name] symbol: error` and return a safe fallback value (empty dict, empty list, or a neutral defaults object).
- `_safe_float` and `_safe_int` silently return `None` on conversion failure, preventing crashes from missing yfinance fields.

---

_Documentation generated for StockIt backend — March 2026._
