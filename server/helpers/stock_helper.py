# helpers/stock_helper.py
#
# Flask backend helpers — yfinance only
#

import os
import math
import requests
import yfinance as yf
from datetime import datetime
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
from gradio_client import Client as GradioClient


_finbert_client = None


load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

NEWS_API_KEY      = os.getenv("NEWS_API_KEY")
GOOGLE_SHEETS_URL = os.getenv("GOOGLE_SHEETS_URL")
CACHE_TTL_HOURS   = 24

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _ticker_sym(symbol: str) -> str:
    s = symbol.strip().upper()
    return s if s.endswith(".NS") or s.endswith(".BO") else f"{s}.NS"


def _safe_float(val, default=None):
    try:
        v = float(val)
        return None if (math.isnan(v) or math.isinf(v)) else v
    except (TypeError, ValueError):
        return default


def _safe_int(val, default=None):
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


# ─────────────────────────────────────────────────────────────────────────────
# REALTIME OVERVIEW
# ─────────────────────────────────────────────────────────────────────────────

def get_realtime_stock(symbol: str) -> dict:
    try:
        ticker = yf.Ticker(_ticker_sym(symbol))
        info   = ticker.info

        current    = _safe_float(info.get("currentPrice"))
        prev       = _safe_float(info.get("previousClose")) or current
        change     = round(current - prev, 2) if current is not None and prev is not None else None
        change_pct = round((change / prev) * 100, 2) if change is not None and prev else None

        upper_circuit = round(prev * 1.15, 2) if prev else None
        lower_circuit = round(prev * 0.85, 2) if prev else None

        vwap = None
        try:
            history = ticker.history(period="1mo")
            if len(history) > 0:
                tp   = (history["High"] + history["Low"] + history["Close"]) / 3
                vwap = _safe_float(round((tp * history["Volume"]).sum() / history["Volume"].sum(), 2))
        except Exception:
            pass

        return {
            "symbol":           symbol.upper(),
            "name":             info.get("longName") or info.get("shortName") or symbol.upper(),
            "exchange":         info.get("exchange"),
            "sector":           info.get("sector"),
            "industry":         info.get("industry"),
            "currentPrice":     current,
            "previousClose":    prev,
            "open":             _safe_float(info.get("open")),
            "dayHigh":          _safe_float(info.get("dayHigh")),
            "dayLow":           _safe_float(info.get("dayLow")),
            "change":           change,
            "changePercent":    change_pct,
            "volume":           _safe_int(info.get("volume")),
            "avgVolume":        _safe_int(info.get("averageVolume")),
            "marketCap":        _safe_float(info.get("marketCap")),
            "fiftyTwoWeekHigh": _safe_float(info.get("fiftyTwoWeekHigh")),
            "fiftyTwoWeekLow":  _safe_float(info.get("fiftyTwoWeekLow")),
            "peRatio":          _safe_float(info.get("trailingPE")),
            "eps":              _safe_float(info.get("trailingEps")),
            "dividendYield":    _safe_float(info.get("dividendYield")),
            "roe":              _safe_float(info.get("returnOnEquity")),
            "vwap":             vwap,
            "upperCircuit":     upper_circuit,
            "lowerCircuit":     lower_circuit,
            "lastUpdated":      datetime.utcnow().isoformat(),
        }

    except Exception as e:
        print(f"[get_realtime_stock] {symbol}: {e}")
        return {}


# ─────────────────────────────────────────────────────────────────────────────
# SPARKLINE
# ─────────────────────────────────────────────────────────────────────────────

def get_sparkline(symbol: str, points: int = 12) -> dict:
    try:
        ticker  = yf.Ticker(_ticker_sym(symbol))
        history = ticker.history(period="1mo")
        history.reset_index(inplace=True)

        closes = [_safe_float(r["Close"]) for _, r in history.iterrows()]
        closes = [v for v in closes if v is not None]
        closes = closes[-points:]

        first = closes[0] if closes else 0
        last  = closes[-1] if closes else 0
        trend = "up" if last >= first else "down"

        return {
            "prices": closes,
            "trend":  trend,
            "min":    round(min(closes), 2) if closes else None,
            "max":    round(max(closes), 2) if closes else None,
        }
    except Exception as e:
        print(f"[get_sparkline] {symbol}: {e}")
        return {"prices": [], "trend": "neutral", "min": None, "max": None}


# ─────────────────────────────────────────────────────────────────────────────
# HISTORICAL
# ─────────────────────────────────────────────────────────────────────────────

def get_historical_data(symbol: str, period: str = "1mo", page: int = 1, limit: int = 8) -> dict:
    try:
        ticker  = yf.Ticker(_ticker_sym(symbol))
        history = ticker.history(period=period)
        history.reset_index(inplace=True)

        avg_vol    = history["Volume"].mean() if len(history) else 0
        prices     = []
        prev_close = None

        for _, row in history.iterrows():
            dv  = row["Date"]
            ds  = dv.strftime("%Y-%m-%d") if hasattr(dv, "strftime") else str(dv)
            cl  = _safe_float(row["Close"])
            vol = _safe_int(row["Volume"])
            chg = round(((cl - prev_close) / prev_close) * 100, 2) if prev_close and cl else 0

            prices.append({
                "date":          ds,
                "open":          _safe_float(row["Open"]),
                "high":          _safe_float(row["High"]),
                "low":           _safe_float(row["Low"]),
                "close":         cl,
                "volume":        vol,
                "changePercent": chg,
                "highVolume":    bool(vol and avg_vol and vol > avg_vol * 1.5),
            })
            prev_close = cl

        prices.reverse()

        total       = len(prices)
        total_pages = max(1, math.ceil(total / limit))
        start       = (page - 1) * limit
        paginated   = prices[start: start + limit]

        return {
            "prices": paginated,
            "pagination": {
                "currentPage": page,
                "totalPages":  total_pages,
                "totalItems":  total,
                "limit":       limit,
            },
        }
    except Exception as e:
        print(f"[get_historical_data] {symbol}: {e}")
        return {
            "prices": [],
            "pagination": {"currentPage": 1, "totalPages": 0, "totalItems": 0, "limit": limit},
        }


# ─────────────────────────────────────────────────────────────────────────────
# FINANCIAL FUNDAMENTALS
# ─────────────────────────────────────────────────────────────────────────────

def get_financials(symbol: str) -> dict:
    try:
        ticker = yf.Ticker(_ticker_sym(symbol))
        info   = ticker.info

        revenue = _safe_float(info.get("totalRevenue"))
        ebitda  = _safe_float(info.get("ebitda"))
        net_inc = _safe_float(info.get("netIncomeToCommon"))

        return {
            "revenue":           revenue,
            "netProfit":         net_inc,
            "ebitda":            ebitda,
            "ebitdaMargin":      round((ebitda / revenue) * 100, 2) if ebitda and revenue else None,
            "profitMargin":      round((net_inc / revenue) * 100, 2) if net_inc and revenue else None,
            "debtToEquity":      _safe_float(info.get("debtToEquity")),
            "currentRatio":      _safe_float(info.get("currentRatio")),
            "quickRatio":        _safe_float(info.get("quickRatio")),
            "roe":               _safe_float(info.get("returnOnEquity")),
            "roa":               _safe_float(info.get("returnOnAssets")),
            "eps":               _safe_float(info.get("trailingEps")),
            "forwardEps":        _safe_float(info.get("forwardEps")),
            "peRatio":           _safe_float(info.get("trailingPE")),
            "forwardPE":         _safe_float(info.get("forwardPE")),
            "pbRatio":           _safe_float(info.get("priceToBook")),
            "psRatio":           _safe_float(info.get("priceToSalesTrailing12Months")),
            "dividendYield":     _safe_float(info.get("dividendYield")),
            "payoutRatio":       _safe_float(info.get("payoutRatio")),
            "bookValue":         _safe_float(info.get("bookValue")),
            "freeCashflow":      _safe_float(info.get("freeCashflow")),
            "operatingCashflow": _safe_float(info.get("operatingCashflow")),
            "grossMargins":      _safe_float(info.get("grossMargins")),
            "operatingMargins":  _safe_float(info.get("operatingMargins")),
        }

    except Exception as e:
        print(f"[get_financials] {symbol}: {e}")
        return {}


# ─────────────────────────────────────────────────────────────────────────────
# SENTIMENT helper
# ─────────────────────────────────────────────────────────────────────────────

def _get_finbert_client():
    global _finbert_client
    if _finbert_client is None:
        _finbert_client = GradioClient("Sabarna6/FinBERT_FinancialSentimentAnalysis")
    return _finbert_client

def _analyze_sentiment(text: str) -> dict:
    try:
        client = _get_finbert_client()
        result = client.predict(text=text, api_name="/predict")
        result=result[0]
        # result is typically a dict like {"Positive": 0.08, "Negative": 0.14, "Neutral": 0.77}
        # or a string — print it once to confirm shape
        print(f"[FinBERT] raw result: {result}")

        if isinstance(result, dict):
            scores = {
                "Positive": float(result.get("Positive", 0.0)),
                "Negative": float(result.get("Negative", 0.0)),
                "Neutral":  float(result.get("Neutral",  1.0)),
            }
        elif isinstance(result, str):
            # some Gradio endpoints return just the label
            scores = {"Positive": 0.0, "Negative": 0.0, "Neutral": 0.0}
            scores[result.strip().capitalize()] = 1.0
        else:
            return {"sentiment": "Neutral", "confidence": 0.0}

        top_label = max(scores, key=scores.get)
        return {
            "sentiment":  top_label,
            "confidence": round(scores[top_label], 4),
        }

    except Exception as e:
        print(f"[FinBERT] {e}")
        return {"sentiment": "Neutral", "confidence": 0.0}

# ─────────────────────────────────────────────────────────────────────────────
# GOOGLE SHEETS CACHE
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_cached_news(symbol: str) -> list[dict] | None:
    """
    Sheet2 columns (1-indexed):
      1: title  2: confidence  3: sentiment  4: pubdate
      5: summary  6: symbol  7: url  8: source
    """
    if not GOOGLE_SHEETS_URL:
        return None

    try:
        res  = requests.get(GOOGLE_SHEETS_URL, params={"symbol": symbol}, timeout=18)
        body = res.json()
        rows = body.get("data", [])

        if not rows:
            return None

        # ── Freshness check ──────────────────────────────────────────────────
        first_row     = rows[0]
        cached_at_str = first_row.get("pubdate") or first_row.get("publishedAt")

        if cached_at_str:
            cached_at = datetime.fromisoformat(cached_at_str.replace("Z", "+00:00"))
            age       = datetime.now(timezone.utc) - cached_at
            if age > timedelta(hours=CACHE_TTL_HOURS):
                print(f"[Cache] Stale for {symbol} ({age}), refreshing.")
                return None

        # ── Normalize to NewsCard contract ───────────────────────────────────
        normalized = []
        for row in rows:
            sentiment = str(row.get("sentiment", "Neutral")).strip().capitalize()
            pubdate   = row.get("pubdate") or row.get("publishedAt") or ""

            normalized.append({
                "title":       row.get("title", ""),
                "summary":     row.get("summary", ""),
                "source":      row.get("source", ""),        # sheet col 8
                "publishedAt": pubdate,                       # renamed from pubdate
                "url":         row.get("url", ""),           # sheet col 7
                "tags":        [sentiment.lower()],
                "sentiment":   sentiment,
                "confidence":  float(row.get("confidence", 0)),
                "symbol":      row.get("symbol", symbol.upper()),
            })

        print(f"[Cache] HIT for {symbol} ({len(normalized)} articles)")
        return normalized

    except Exception as e:
        print(f"[Cache] Sheets fetch failed: {e}")
        return None


def _compute_sentiment_summary(articles: list[dict]) -> dict:
    pos   = sum(1 for a in articles if a.get("sentiment") == "Positive")
    neg   = sum(1 for a in articles if a.get("sentiment") == "Negative")
    neu   = sum(1 for a in articles if a.get("sentiment") == "Neutral")
    total = pos + neu + neg or 1
    return {
        "positive": round(pos / total * 100, 2),
        "neutral":  round(neu / total * 100, 2),
        "negative": round(neg / total * 100, 2),
    }


# ─────────────────────────────────────────────────────────────────────────────
# NEWS  (cache-first → NewsAPI + FinBERT)
# ─────────────────────────────────────────────────────────────────────────────

def get_news(symbol: str, get_realtime_stock_fn) -> dict:
    """
    1. Check Google Sheets cache for fresh articles.
    2. On miss/stale → fetch from NewsAPI, run FinBERT on each article.
    3. Return unified response with NewsCard-compatible fields.
    """

    # ── Step 1: Cache check ───────────────────────────────────────────────────
    cached = _fetch_cached_news(symbol)
    if cached:
        return {
            "source":    "cache",
            "sentiment": _compute_sentiment_summary(cached),
            "news":      cached,
        }

    # ── Step 2: Fetch fresh from NewsAPI ─────────────────────────────────────
    try:
        if not NEWS_API_KEY:
            raise ValueError("NEWS_API_KEY not configured")

        company_name = get_realtime_stock_fn(symbol).get("name") or symbol
        params = {
            "q":        company_name,
            "language": "en",
            "sortBy":   "publishedAt",
            "pageSize": 15,
            "apiKey":   NEWS_API_KEY,
        }
        raw_articles = (
            requests.get("https://newsapi.org/v2/everything", params=params, timeout=10)
            .json()
            .get("articles", [])
        )

        # ── Step 3: Run FinBERT + normalize to NewsCard contract ──────────────
        formatted = []
        for a in raw_articles:
            title     = a.get("title", "") or ""
            desc      = a.get("description", "") or ""
            sent      = _analyze_sentiment(f"{title}. {desc}")
            sentiment = sent["sentiment"]

            formatted.append({
                "title":       title,
                "summary":     desc,
                "source":      a.get("source", {}).get("name", ""),
                "publishedAt": a.get("publishedAt", ""),
                "url":         a.get("url", ""),
                "tags":        [sentiment.lower()],
                "sentiment":   sentiment,
                "confidence":  sent["confidence"],
                "symbol":      symbol.upper(),
            })

        return {
            "source":    "live",
            "sentiment": _compute_sentiment_summary(formatted),
            "news":      formatted,
        }

    except Exception as e:
        print(f"[get_news] {symbol}: {e}")
        return {
            "source":    "error",
            "sentiment": {"positive": 0, "neutral": 100, "negative": 0},
            "news":      [],
        }


# ─────────────────────────────────────────────────────────────────────────────
# ANALYZE-FULL  (used by AppScript → Google Sheets cache writer)
# ─────────────────────────────────────────────────────────────────────────────

def get_news_for_cache(symbol: str) -> list[dict]:
    """
    Fetches news via yfinance, runs FinBERT on each article via _analyze_sentiment,
    and returns a list of dicts for the /api/news/analyze-full endpoint.
    AppScript reads this to write to Sheet2 (8 columns).
    """
    try:
        ticker      = yf.Ticker(_ticker_sym(symbol))
        raw_news    = ticker.news or []
    except Exception as e:
        print(f"[get_news_for_cache] yfinance fetch failed for {symbol}: {e}")
        return []

    if not raw_news:
        return []

    formatted = []
    for item in raw_news:
        # yfinance news structure: item has 'content' dict
        content   = item.get("content") or item  # fallback: some versions return flat dict
        title     = str(content.get("title")   or "").strip()
        summary   = str(content.get("summary") or content.get("description") or "").strip()
        pubdate   = str(content.get("pubDate") or content.get("providerPublishTime") or "").strip()
        url       = str(content.get("canonicalUrl", {}).get("url") if isinstance(content.get("canonicalUrl"), dict) else content.get("url") or "").strip()
        source    = str(content.get("provider", {}).get("displayName") if isinstance(content.get("provider"), dict) else content.get("source") or "").strip()

        if not title:
            continue

        sent      = _analyze_sentiment(f"{title}. {summary}")
        sentiment = sent["sentiment"]

        formatted.append({
            # ── AppScript / Sheet2 columns ─────────────────────────────────
            "title":       title,
            "confidence":  sent["confidence"],
            "sentiment":   sentiment,
            "pubdate":     pubdate,          # col 4 — sheet header is pubdate
            "summary":     summary,
            "symbol":      symbol.upper(),
            "url":         url,              # col 7
            "source":      source,           # col 8
            # ── NewsCard contract extras ───────────────────────────────────
            "publishedAt": pubdate,
            "tags":        [sentiment.lower()],
        })

    return formatted


# ─────────────────────────────────────────────────────────────────────────────
# TRENDS
# ─────────────────────────────────────────────────────────────────────────────

def get_stock_trends(symbol: str) -> dict:
    try:
        ticker  = yf.Ticker(_ticker_sym(symbol))
        info    = ticker.info

        current  = _safe_float(info.get("currentPrice")) or 0
        prev     = _safe_float(info.get("previousClose")) or current
        volume   = _safe_float(info.get("volume")) or 0
        avg_vol  = _safe_float(info.get("averageVolume")) or volume or 1
        beta     = _safe_float(info.get("beta")) or 1.0

        chg_pct   = ((current - prev) / prev * 100) if prev else 0
        direction = "bullish" if chg_pct > 0 else "bearish" if chg_pct < 0 else "neutral"
        strength  = round(min(abs(chg_pct) * 10, 100), 1)

        vol_ratio  = volume / avg_vol
        vol_status = "High" if vol_ratio > 1.2 else "Low" if vol_ratio < 0.8 else "Normal"
        volatility = "High" if beta > 1.2 else "Low" if beta < 0.8 else "Medium"

        delivery_pct = 65
        try:
            history      = ticker.history(period="1mo")
            if len(history) > 5:
                vol_std         = history["Volume"].std()
                vol_mean        = history["Volume"].mean()
                vol_consistency = 1 - (vol_std / vol_mean if vol_mean > 0 else 1)
                delivery_pct    = round(50 + (vol_ratio - 1) * 20 + vol_consistency * 20, 2)
                delivery_pct    = round(min(max(delivery_pct, 35), 85), 2)
        except Exception:
            pass

        return {
            "trend":  {"direction": direction, "strength": strength},
            "volume": {
                "status":                vol_status,
                "ratio":                 round(vol_ratio, 2),
                "institutionalActivity": "Net Buying" if vol_ratio > 1 else "Net Selling",
                "deliveryPercent":       delivery_pct,
            },
            "risk": {
                "volatility": volatility,
                "beta":       round(beta, 2),
                "atr":        round(current * 0.02, 2),
                "riskLevel":  volatility,
            },
        }

    except Exception as e:
        print(f"[get_stock_trends] {symbol}: {e}")
        return {
            "trend":  {"direction": "neutral", "strength": 50},
            "volume": {"status": "Normal", "ratio": 1, "institutionalActivity": "Neutral", "deliveryPercent": 50},
            "risk":   {"volatility": "Medium", "beta": 1.0, "atr": 0, "riskLevel": "Medium"},
        }


# ─────────────────────────────────────────────────────────────────────────────
# RECOMMENDATION
# ─────────────────────────────────────────────────────────────────────────────

def get_recommendation(symbol: str) -> dict:
    try:
        ticker  = yf.Ticker(_ticker_sym(symbol))
        info    = ticker.info

        current = _safe_float(info.get("currentPrice")) or 0
        target  = _safe_float(info.get("targetMeanPrice")) or current * 1.1
        pe      = _safe_float(info.get("trailingPE")) or 15
        rec_key = (info.get("recommendationKey") or "hold").lower()

        _map           = {"strong_buy": "strongbuy", "buy": "buy", "hold": "hold",
                          "sell": "sell", "strong_sell": "strongsell"}
        recommendation = _map.get(rec_key, "hold")

        upside     = ((target - current) / current * 100) if current else 0
        confidence = 80 if upside > 20 else 70 if upside > 10 else 60 if upside > 0 else 50 if upside > -10 else 40

        tech_score = int(min(max(100 - (pe / 30 * 100), 30), 95))
        fund_score = int(min(max(50 + upside, 30), 95))
        stop_loss  = round(current * 0.92, 2)
        breakout   = round(current * 1.05, 2)
        zone_min   = round(current * 0.96, 2)
        zone_max   = round(current * 1.02, 2)
        rr_ratio   = round((target - current) / max(current - stop_loss, 0.01), 2) if current > stop_loss else 2.5

        analyst_recs = {}
        try:
            rec_df = ticker.recommendations
            if rec_df is not None and not rec_df.empty:
                latest       = rec_df.iloc[-1]
                analyst_recs = {
                    "strongBuy":  int(latest.get("strongBuy", 0)),
                    "buy":        int(latest.get("buy", 0)),
                    "hold":       int(latest.get("hold", 0)),
                    "sell":       int(latest.get("sell", 0)),
                    "strongSell": int(latest.get("strongSell", 0)),
                }
        except Exception:
            pass

        return {
            "recommendation":   recommendation,
            "confidence":       confidence,
            "timeHorizon":      "Short Term" if abs(upside) < 15 else "Medium Term",
            "targetPrice":      round(target, 2),
            "upside":           round(upside, 2),
            "technicalScore":   tech_score,
            "fundamentalScore": fund_score,
            "analystRecs":      analyst_recs,
            "entryPlan": {
                "accumulationZone": {"min": zone_min, "max": zone_max},
                "breakoutAbove":    breakout,
                "stopLoss":         stop_loss,
                "riskRewardRatio":  rr_ratio,
                "positionSize":     10,
            },
            "reasoning": {
                "technical":   ["Price near support" if current < target else "Price near resistance",
                                "RSI in normal range"],
                "fundamental": ["Revenue growth positive" if upside > 0 else "Revenue under pressure",
                                "Healthy balance sheet"],
                "sentiment":   ["Analyst consensus: " + rec_key.replace("_", " ").title()],
                "risks":       ["Market volatility", "Sector headwinds"],
            },
        }

    except Exception as e:
        print(f"[get_recommendation] {symbol}: {e}")
        return {
            "recommendation": "hold", "confidence": 50,
            "timeHorizon": "Medium Term", "targetPrice": None, "upside": None,
            "technicalScore": 50, "fundamentalScore": 50, "analystRecs": {},
            "entryPlan": {
                "accumulationZone": {"min": 0, "max": 0},
                "breakoutAbove": 0, "stopLoss": 0,
                "riskRewardRatio": 1, "positionSize": 5,
            },
            "reasoning": {"technical": [], "fundamental": [], "sentiment": [], "risks": []},
        }


# ─────────────────────────────────────────────────────────────────────────────
# CHART DATA
# ─────────────────────────────────────────────────────────────────────────────

_PERIOD_MAP = {
    "1W": "5d", "1M": "1mo", "3M": "3mo",
    "6M": "6mo", "1Y": "1y", "ALL": "max",
}


def get_chart_data(symbol: str, timeframe: str = "3M") -> dict:
    try:
        period  = _PERIOD_MAP.get(timeframe.upper(), "3mo")
        ticker  = yf.Ticker(_ticker_sym(symbol))
        history = ticker.history(period=period)
        history.reset_index(inplace=True)

        candles = []
        for _, row in history.iterrows():
            dv = row["Date"]
            ds = dv.strftime("%Y-%m-%d") if hasattr(dv, "strftime") else str(dv)
            candles.append({
                "timestamp": ds,
                "open":      _safe_float(row["Open"]),
                "high":      _safe_float(row["High"]),
                "low":       _safe_float(row["Low"]),
                "close":     _safe_float(row["Close"]),
            })

        return {"candles": candles}

    except Exception as e:
        print(f"[get_chart_data] {symbol}: {e}")
        return {"candles": []}


# ─────────────────────────────────────────────────────────────────────────────
# VOLUME DATA
# ─────────────────────────────────────────────────────────────────────────────

def get_volume_data(symbol: str, timeframe: str = "3M") -> dict:
    try:
        period  = _PERIOD_MAP.get(timeframe.upper(), "3mo")
        ticker  = yf.Ticker(_ticker_sym(symbol))
        history = ticker.history(period=period)
        history.reset_index(inplace=True)

        avg_vol = int(history["Volume"].mean()) if len(history) else 0

        volumes = []
        for _, row in history.iterrows():
            dv  = row["Date"]
            ds  = dv.strftime("%Y-%m-%d") if hasattr(dv, "strftime") else str(dv)
            vol = _safe_int(row["Volume"]) or 0
            volumes.append({
                "timestamp": ds,
                "volume":    vol,
                "aboveAvg":  bool(avg_vol and vol > avg_vol),
            })

        return {"volumes": volumes, "avgVolume": avg_vol}

    except Exception as e:
        print(f"[get_volume_data] {symbol}: {e}")
        return {"volumes": [], "avgVolume": 0}


# ─────────────────────────────────────────────────────────────────────────────
# COMPANY SEARCH
# ─────────────────────────────────────────────────────────────────────────────

def search_company(symbol: str) -> dict:
    if not symbol:
        return {"error": "Symbol parameter is required"}

    sym     = symbol.strip().upper()
    results = []

    for suffix in [".NS", ".BO"]:
        try:
            t    = yf.Ticker(sym + suffix)
            info = t.info
            name = info.get("longName") or info.get("shortName")
            if name:
                results.append({
                    "symbol":   sym,
                    "name":     name,
                    "exchange": "NSE" if suffix == ".NS" else "BSE",
                    "sector":   info.get("sector"),
                    "industry": info.get("industry"),
                })
        except Exception:
            pass

    return {"data": results}