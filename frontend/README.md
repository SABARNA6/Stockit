# Stockit Frontend Documentation

This document defines the frontend contract so backend services can return exactly what the UI expects.

## Purpose

The frontend has two data sources:

1. Stock intelligence APIs (market data, signals, recommendations, fundamentals, news, historical).
2. Supabase (authentication + user watchlist/profile).

If backend responses match this document, the UI works without additional mapping.

## Tech Stack

- React 18 + Vite 5
- Styling: plain CSS
- Charts: custom canvas rendering
- Auth + user data: Supabase JS v2

## Local Run

```bash
npm install
npm run dev
```

App default URL: `http://localhost`

## API Base URL Contract

Frontend API calls are built as:

- `window.STOCK_API_BASE + path` if `window.STOCK_API_BASE` exists.
- otherwise `http://localhost:10000/api + path`.

So backend should expose endpoints on:

- `http://localhost:10000/api`

or you should inject `window.STOCK_API_BASE` in `index.html` before app boot.

## Global Response Envelope

All stock API endpoints should return:

```json
{
  "data": {}
}
```

Notes:

- The frontend reads `response.data` for almost all endpoints.
- Search endpoint currently reads top-level response and then `response.data` inside it.
- Keep envelope consistent to avoid runtime edge cases.

## Error Contract

- Non-2xx HTTP status is treated as failure.
- Frontend throws `API <status>: <path>`.
- Return JSON body for debugging when possible:

```json
{
  "error": "Human-readable message",
  "code": "OPTIONAL_MACHINE_CODE"
}
```

## Endpoint Contract

Base: `/api`

### 1) Overview

`GET /stocks/:symbol`

Used in header, top metrics, last updated, watchlist metadata.

```json
{
  "data": {
    "symbol": "TCS",
    "name": "Tata Consultancy Services Ltd",
    "sector": "IT Services",
    "currentPrice": 4123.4,
    "previousClose": 4078.25,
    "marketCap": 15000000000000,
    "peRatio": 30.4,
    "roe": 0.51,
    "dividendYield": 0.014,
    "fiftyTwoWeekLow": 3120,
    "fiftyTwoWeekHigh": 4580,
    "lastUpdated": "2026-03-15T10:45:00Z"
  }
}
```

### 2) Sparkline

`GET /stocks/:symbol/sparkline?points=14`

```json
{
  "data": {
    "closes": [4050.1, 4072.4, 4091.8, 4123.4]
  }
}
```

### 3) Price Chart

`GET /stocks/:symbol/chart?timeframe=3M`

`timeframe` values used by UI: `1W`, `1M`, `3M`, `6M`, `1Y`, `ALL`

```json
{
  "data": {
    "candles": [
      {
        "timestamp": "2026-03-14T09:15:00Z",
        "open": 4100.0,
        "high": 4140.0,
        "low": 4092.5,
        "close": 4123.4
      }
    ]
  }
}
```

### 4) Volume

`GET /stocks/:symbol/volume?timeframe=3M`

Must align with chart timestamps. Frontend aligns by `timestamp`.

```json
{
  "data": {
    "volumes": [{ "timestamp": "2026-03-14T09:15:00Z", "volume": 1234567 }],
    "avgVolume": 1100000
  }
}
```

### 5) Trend Signals

`GET /stocks/:symbol/trends`

```json
{
  "data": {
    "trend": {
      "direction": "bullish",
      "strength": 72
    },
    "volume": {
      "status": "Spike",
      "institutionalActivity": "High"
    },
    "risk": {
      "riskLevel": "Medium",
      "beta": 1.12,
      "atr": 48.6
    }
  }
}
```

Accepted frontend values:

- `trend.direction`: `bullish` or anything else (treated bearish)
- `volume.status`: `Spike`, `High`, or others
- `risk.riskLevel`: `High`, `Medium`, `Low`

### 6) Recommendation

`GET /stocks/:symbol/recommendation`

```json
{
  "data": {
    "recommendation": "buy",
    "confidence": 78,
    "timeHorizon": "3-6 months",
    "technicalScore": 68,
    "fundamentalScore": 81,
    "entryPlan": {
      "accumulationZone": { "min": 3980, "max": 4060 },
      "breakoutAbove": 4180,
      "stopLoss": 3890,
      "riskRewardRatio": 2.4,
      "positionSize": 12
    },
    "reasoning": {
      "technical": ["Momentum improving"],
      "fundamental": ["Strong cash flow"],
      "sentiment": ["Coverage mixed"],
      "risks": ["Valuation near upper band"]
    }
  }
}
```

Accepted recommendation values:

- `buy`, `sell`, `hold`

### 7) Fundamentals

`GET /stocks/:symbol/fundamentals`

Frontend supports nested or flat payload.

Preferred nested format:

```json
{
  "data": {
    "profitability": {
      "netProfit": 25600000000,
      "ebitdaMargin": 24.2,
      "roe": 22.1,
      "roa": 9.6
    },
    "valuation": {
      "peRatio": 30.4,
      "pegRatio": 1.9,
      "pbRatio": 12.1,
      "evEbitda": 18.4
    },
    "growth": {
      "revenueCagr5y": 14.8,
      "profitCagr5y": 13.2,
      "epsGrowthTtm": 0.11,
      "salesGrowth": 0.09
    },
    "financialHealth": {
      "debtToEquity": 0.18,
      "interestCoverage": 24.3,
      "currentRatio": 1.7,
      "quickRatio": 1.5
    }
  }
}
```

### 8) News and Sentiment

`GET /stocks/:symbol/news`

```json
{
  "data": {
    "sentiment": {
      "positive": 54,
      "neutral": 31,
      "negative": 15
    },
    "news": [
      {
        "title": "Company wins large enterprise deal",
        "summary": "Multi-year transformation contract announced...",
        "source": "Business Daily",
        "publishedAt": "2026-03-15T09:20:00Z",
        "url": "https://example.com/article",
        "tags": ["positive", "high-impact"],
        "highImpact": true
      }
    ]
  }
}
```

Filter logic in UI uses `tags` containing one of:

- `positive`, `negative`, `neutral`

### 9) Historical Prices

`GET /stocks/:symbol/historical?period=1mo&page=1&limit=8`

`period` values used by UI: `1mo`, `3mo`, `6mo`, `1y`

```json
{
  "data": {
    "prices": [
      {
        "date": "2026-03-14",
        "open": 4100.0,
        "high": 4140.0,
        "low": 4092.5,
        "close": 4123.4,
        "volume": 1234567,
        "changePercent": 1.11,
        "highVolume": true
      }
    ],
    "pagination": {
      "totalPages": 12
    }
  }
}
```

Required fields:

- `prices` array
- `pagination.totalPages` (if missing or `<=1`, pagination UI hides)

### 10) Symbol Search

`GET /company/search?symbol=TC`

Expected shape (note: frontend currently uses `response.data` directly):

```json
{
  "data": [
    {
      "symbol": "TCS",
      "title": "Tata Consultancy Services Ltd",
      "name": "Tata Consultancy Services Ltd",
      "sentiment": "positive"
    }
  ]
}
```

## Supabase Requirements (Non-stock API)

The frontend uses Supabase directly for auth and watchlist. Backend does not need to proxy these unless you want centralized APIs.

Required tables used in frontend:

1. `profiles`
2. `watchlist`

Minimum columns:

### `profiles`

- `id` (uuid, matches auth user id)
- `full_name` (text)
- `avatar_url` (text, nullable)

### `watchlist`

- `id` (primary key)
- `user_id` (uuid)
- `symbol` (text)
- `name` (text)
- `sector` (text)
- `price` (numeric)
- `target_price` (numeric, nullable)
- `note` (text, nullable)

Recommended unique constraint:

- `(user_id, symbol)`

## Portfolio Module (Detailed)

This section documents the Portfolio area used in `PortfolioPage1` and the files under `src/components/portfolio`.

### Current Data Source Model

Portfolio features currently use Supabase directly from frontend, not the `/api` backend:

1. `portfolio` table: user holdings
2. `watchlist` table: user watchlist
3. `profiles` table: user display profile

Also important:

- Live price (`ltp`) in portfolio pages is currently mocked in frontend (`mockLTP`) and not fetched from backend.
- AI Picks and Portfolio News pages are currently mock-data driven in frontend (`AI_SUGGESTIONS`, `PERSONALIZED_NEWS`).

### Portfolio Page Data Fetch

On entering portfolio mode, frontend executes in parallel:

1. `select * from portfolio where user_id = :userId order by created_at desc`
2. `select * from watchlist where user_id = :userId order by created_at desc`

Frontend then computes per holding:

- `ltp`
- `currentValue = qty * ltp`

### Required Supabase Tables for Portfolio Module

#### `portfolio`

Minimum columns used:

- `id` (primary key)
- `user_id` (uuid)
- `symbol` (text)
- `qty` (numeric)
- `avg_cost` (numeric)
- `created_at` (timestamp, for ordering)

Insert payload used by Add Holding:

```json
{
  "user_id": "<uuid>",
  "symbol": "TCS",
  "qty": 50,
  "avg_cost": 3450
}
```

Mutations used:

- Insert many: `insert(data[])`
- Delete one: `delete where id = :id`

#### `watchlist`

Minimum columns used:

- `id` (primary key)
- `user_id` (uuid)
- `symbol` (text)
- `name` (text)
- `sector` (text)
- `price` (numeric, nullable)
- `target_price` (numeric, nullable)
- `note` (text, nullable)
- `created_at` (timestamp, for ordering)

Insert payload used:

```json
{
  "user_id": "<uuid>",
  "symbol": "INFY",
  "name": "Infosys Ltd",
  "sector": "IT",
  "price": 1900,
  "target_price": 1900,
  "note": "Optional"
}
```

Mutations used:

- Insert one: `insert({...}).select().single()`
- Delete one: `delete where id = :id`

Note about field usage:

- Portfolio watchlist UI currently displays target comparison using `price`.
- Stock page watchlist add flow writes both `price` (current price) and `target_price` (user target).
- To avoid mismatches, keep both fields populated until frontend unifies this behavior.

#### `profiles`

Minimum columns used:

- `id` (uuid, equals auth user id)
- `full_name` (text)
- `avatar_url` (text, nullable)

### Add Holding Input Rules

Manual mode accepts rows with:

- `symbol` (string, converted to uppercase)
- `qty` (numeric)
- `avg_cost` (numeric)

CSV mode expected header and format:

```csv
Symbol,Qty,Avg Cost
TCS,50,3450
HCLTECH,30,1620
```

Rows with invalid numeric values are ignored client-side.

### Portfolio Backendization (If You Move It to API)

If you later want backend-owned portfolio APIs (instead of direct Supabase in frontend), mirror these contracts:

1. `GET /portfolio` -> list holdings for authenticated user
2. `POST /portfolio` -> create one or many holdings
3. `DELETE /portfolio/:id` -> remove holding
4. `GET /watchlist` -> list watchlist items
5. `POST /watchlist` -> add watchlist item
6. `DELETE /watchlist/:id` -> remove watchlist item

Suggested response envelope remains:

```json
{
  "data": {}
}
```

### Security / RLS Expectations

For Supabase tables used directly by frontend, enforce per-user isolation:

1. A user can read only rows where `user_id = auth.uid()`.
2. A user can insert rows only with `user_id = auth.uid()`.
3. A user can delete/update only own rows.

Without correct RLS, portfolio and watchlist pages can expose cross-user data.

## Backend Implementation Checklist

1. Expose all endpoints listed above under `/api`.
2. Return `{ "data": ... }` envelope for success.
3. Keep field names exactly as documented (camelCase).
4. Support all timeframe/period values consumed by UI.
5. Return 4xx/5xx on failures with JSON error payload.
6. Ensure chart and volume timestamps are comparable for alignment.
7. Ensure null-safe behavior (frontend tolerates nulls but better to return complete objects).

## Notes

- Currency display is INR-oriented in UI (`en-IN`, `₹`).
- This frontend is informational only and not financial advice.
