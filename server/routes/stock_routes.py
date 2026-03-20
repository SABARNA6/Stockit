# routes/stock_routes.py
# Flask Blueprint — all original endpoints + 5 new ML endpoints
#
# NEW ML ENDPOINTS:
#   GET  /api/ml/price/<symbol>?horizon=5
#   GET  /api/ml/strategy/<symbol>
#   POST /api/ml/strategy/custom
#   POST /api/ml/recommend
#   GET  /api/ml/full/<symbol>?horizon=5   ← price + strategy in one call
#

from flask import Blueprint, jsonify, request
from helpers.stock_helper import (
    # ── existing ──────────────────────────────────────────
    get_realtime_stock,
    get_sparkline,
    get_historical_data,
    get_financials,
    get_finacial_metric,
    get_news,
    get_yfinance_news,
    get_stock_trends,
    get_recommendation,
    get_chart_data,
    get_volume_data,
    search_company,
    is_nse_symbol_present,
    # ── new ML helpers ────────────────────────────────────
    get_ml_price_prediction,
    get_ml_strategy,
    get_ml_strategy_from_ohlcv,
    get_ml_recommendations,
)
import os
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

stock_bp = Blueprint("stocks", __name__, url_prefix="/api")


# ── response wrappers ─────────────────────────────────────────────────────────
def ok(data):
    return jsonify({"success": True, "data": data})

def err(msg, status=400):
    return jsonify({"success": False, "message": msg}), status


# ═════════════════════════════════════════════════════════════════════════════
# EXISTING ENDPOINTS  (all unchanged)
# ═════════════════════════════════════════════════════════════════════════════

@stock_bp.get("/stocks/<symbol>")
def stock_overview(symbol):
    if not is_nse_symbol_present(symbol):
        return err("Stock not present in local NSE symbol cache", 404)

    data = get_realtime_stock(symbol.upper())
    if not data:
        return err("Stock not found", 404)
    return ok(data)


@stock_bp.get("/stocks/<symbol>/sparkline")
def stock_sparkline(symbol):
    points = request.args.get("points", 12, type=int)
    return ok(get_sparkline(symbol.upper(), points))


@stock_bp.get("/stocks/<symbol>/chart")
def stock_chart(symbol):
    timeframe = request.args.get("timeframe", "3M")
    return ok(get_chart_data(symbol.upper(), timeframe))


@stock_bp.get("/stocks/<symbol>/volume")
def stock_volume(symbol):
    timeframe = request.args.get("timeframe", "3M")
    return ok(get_volume_data(symbol.upper(), timeframe))


@stock_bp.get("/stocks/<symbol>/trends")
def stock_trends(symbol):
    return ok(get_stock_trends(symbol.upper()))


@stock_bp.get("/stocks/<symbol>/recommendation")
def stock_recommendation(symbol):
    return ok(get_recommendation(symbol.upper()))


@stock_bp.get("/stocks/<symbol>/fundamentals")
def stock_fundamentals(symbol):
    return ok(get_finacial_metric(symbol.upper()))


def _normalize_sheets_news(raw, symbol: str) -> dict:
    if isinstance(raw, dict):
        articles = raw.get("data") or raw.get("news", [])
    elif isinstance(raw, list):
        articles = raw
    else:
        articles = []
    formatted = []
    for a in articles:
        sentiment = (a.get("sentiment") or "Neutral").capitalize()
        formatted.append({
            "title":       a.get("title", ""),
            "summary":     a.get("summary") or a.get("description", ""),
            "source":      a.get("source", ""),
            "publishedAt": a.get("publishedAt") or a.get("published_at") or a.get("pubdate", ""),
            "url":         a.get("url", ""),
            "tags":        a.get("tags") or [sentiment.lower()],
            "sentiment":   sentiment,
            "confidence":  a.get("confidence", 1.0),
            "symbol":      symbol.upper(),
        })
    pos   = sum(1 for a in formatted if a["sentiment"] == "Positive")
    neg   = sum(1 for a in formatted if a["sentiment"] == "Negative")
    neu   = sum(1 for a in formatted if a["sentiment"] == "Neutral")
    total = pos + neu + neg or 1
    return {
        "source": "cache",
        "sentiment": {
            "positive": round(pos / total * 100, 2),
            "neutral":  round(neu / total * 100, 2),
            "negative": round(neg / total * 100, 2),
        },
        "news": formatted,
    }


@stock_bp.get("/stocks/<symbol>/news")
def stock_news(symbol):
    import re
    # Normalize: TCS.NS and TCS → same news (strip exchange suffix)
    symbol_clean = re.sub(r"\.(NS|BO|L|TO|AX|HK)$", "", symbol.upper())
    refresh = str(request.args.get("refresh", "0")).lower() in ("1", "true", "yes")

    google_sheet = os.getenv("GOOGLE_SHEETS_URL")
    if google_sheet and not refresh:
        url      = f"{google_sheet}?symbol={symbol_clean}"
        response = requests.get(url)
        if response.ok:
            print("Cache Hit")
            cached_payload = _normalize_sheets_news(response.json(), symbol_clean)
            if cached_payload.get("news"):
                return ok(cached_payload)
            print("Cache empty, falling back to yfinance")
            yf_payload = get_yfinance_news(symbol_clean, limit=10)
            if yf_payload.get("news"):
                return ok(yf_payload)
    print("cache Miss")
    live_payload = get_news(symbol.upper(), get_realtime_stock)
    if live_payload.get("news"):
        return ok(live_payload)

    print("Live news empty, falling back to yfinance")
    return ok(get_yfinance_news(symbol_clean, limit=10))


@stock_bp.get("/stocks/<symbol>/historical")
def stock_historical(symbol):
    period = request.args.get("period", "1mo")
    page   = request.args.get("page",   1, type=int)
    limit  = request.args.get("limit",  8, type=int)
    data   = get_historical_data(symbol.upper(), period, page, limit)
    return jsonify({
        "success": True,
        "symbol":  symbol.upper(),
        "period":  period,
        "data":    data,
    })


@stock_bp.get("/company/search")
def company_search():
    query = request.args.get("q", "").strip() or request.args.get("symbol", "").strip()
    limit = request.args.get("limit", 10, type=int)
    if not query:
        return err("q or symbol query param is required")
    result = search_company(query, limit=limit)
    if "error" in result:
        return err(result["error"], 400)
    return jsonify(result)


# ═════════════════════════════════════════════════════════════════════════════
# NEW ML ENDPOINTS
# ═════════════════════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────────────────────────
# GET /api/ml/price/<symbol>?horizon=5
#
# Price prediction — P10 / P50 / P90 for N days ahead.
#
# Response:
# {
#   "success": true,
#   "data": {
#     "ticker": "RELIANCE",
#     "current_close": 2910.5,
#     "predicted_next_close_p50": 2945.2,
#     "predicted_change_pct": 1.2,
#     "horizon_days": 5,
#     "forecast": [
#       {"date": "2026-03-16", "p10": 2880.0, "p50": 2945.2, "p90": 3010.5},
#       ...
#     ]
#   }
# }
# ─────────────────────────────────────────────────────────────────────────────
@stock_bp.get("/ml/price/<symbol>")
def ml_price(symbol):
    horizon = request.args.get("horizon", 5, type=int)
    horizon = max(1, min(horizon, 14))
    result  = get_ml_price_prediction(symbol.upper(), horizon)
    if "error" in result:
        return err(result["error"], 500)
    return ok(result)


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/ml/strategy/<symbol>
#
# Buy / Hold / Sell signal with stop-loss and take-profit.
# Fetches live data from Yahoo Finance automatically.
#
# Response:
# {
#   "success": true,
#   "data": {
#     "ticker": "RELIANCE",
#     "action": "buy",
#     "confidence": 0.82,
#     "class_probabilities": {"buy": 0.82, "hold": 0.12, "sell": 0.06},
#     "suggested_position_size_pct": 0.085,
#     "risk_plan": {
#       "current_close": 2910.5,
#       "stop_loss": 2878.2,
#       "take_profit": 2952.8,
#       "atr_used": 21.5
#     }
#   }
# }
# ─────────────────────────────────────────────────────────────────────────────
@stock_bp.get("/ml/strategy/<symbol>")
def ml_strategy(symbol):
    result = get_ml_strategy(symbol.upper())
    if "error" in result:
        return err(result["error"], 500)
    return ok(result)


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/ml/strategy/custom
#
# Strategy signal using your own OHLCV candle data.
# Body: { "ticker": "AAPL", "ohlcv": [{date,open,high,low,close,volume}, ...] }
# Minimum 30 candles required; 50+ recommended.
# ─────────────────────────────────────────────────────────────────────────────
@stock_bp.post("/ml/strategy/custom")
def ml_strategy_custom():
    body = request.get_json(silent=True)
    if not body:
        return err("Request body must be JSON")

    ticker = body.get("ticker", "CUSTOM").upper()
    ohlcv  = body.get("ohlcv", [])

    if not isinstance(ohlcv, list) or len(ohlcv) < 30:
        return err("ohlcv must be an array with at least 30 candles")

    required = {"date", "open", "high", "low", "close", "volume"}
    if ohlcv and not required.issubset(ohlcv[0].keys()):
        missing = required - set(ohlcv[0].keys())
        return err(f"Missing fields in ohlcv: {', '.join(missing)}")

    result = get_ml_strategy_from_ohlcv(ticker, ohlcv)
    if "error" in result:
        return err(result["error"], 500)
    return ok(result)


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/ml/recommend
#
# Portfolio-aware stock recommendations + 60-day backtest.
#
# Body:
# {
#   "portfolio": [
#     {"ticker": "RELIANCE", "market_value": 50000},
#     {"ticker": "TCS.NS",   "market_value": 30000}
#   ],
#   "extra_candidates": "NFLX,ADBE",   (optional)
#   "risk_profile": "Medium",           (Low | Medium | High)
#   "top_k": 5,
#   "run_backtest": true
# }
#
# Response:
# {
#   "success": true,
#   "data": {
#     "recommendations": [
#       {"rank":1, "ticker":"INFY.NS", "score":0.021,
#        "predicted_return":0.048, "target_weight":0.42,
#        "latest_close":1580.5}
#     ],
#     "backtest_summary": {
#       "INFY.NS": {"hit_rate_pct":61.5, "alpha_pct":1.7, "verdict":"Outperformed"}
#     },
#     "portfolio_weights": {"RELIANCE": 0.625, "TCS.NS": 0.375},
#     "auto_suggested": ["WIPRO.NS", "HCLTECH.NS", ...]
#   }
# }
# ─────────────────────────────────────────────────────────────────────────────
@stock_bp.post("/ml/recommend")
def ml_recommend():
    body = request.get_json(silent=True)
    if not body:
        return err("Request body must be JSON")

    portfolio = body.get("portfolio", [])
    if not isinstance(portfolio, list) or not portfolio:
        return err("portfolio must be a non-empty array of {ticker, market_value}")

    for item in portfolio:
        if "ticker" not in item or "market_value" not in item:
            return err("Each portfolio item needs 'ticker' and 'market_value'")

    risk_profile     = body.get("risk_profile", "Medium")
    extra_candidates = body.get("extra_candidates", "")
    top_k            = max(1, min(int(body.get("top_k", 5)), 10))
    run_backtest     = bool(body.get("run_backtest", True))

    if risk_profile not in ("Low", "Medium", "High"):
        return err("risk_profile must be Low, Medium, or High")

    result = get_ml_recommendations(
        portfolio=portfolio,
        extra_candidates=extra_candidates,
        risk_profile=risk_profile,
        top_k=top_k,
        run_backtest=run_backtest,
    )

    if "error" in result:
        return err(result["error"], 500)
    return ok(result)


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/ml/full/<symbol>?horizon=5
#
# Price prediction + Strategy signal in ONE API call.
# Use this on stock detail pages to avoid two separate requests.
#
# Response:
# {
#   "success": true,
#   "data": {
#     "ticker": "RELIANCE",
#     "price": { ...price prediction... },
#     "strategy": { ...buy/hold/sell signal... }
#   }
# }
# ─────────────────────────────────────────────────────────────────────────────
@stock_bp.get("/ml/full/<symbol>")
def ml_full(symbol):
    horizon  = max(1, min(request.args.get("horizon", 5, type=int), 14))
    symbol   = symbol.upper()
    price    = get_ml_price_prediction(symbol, horizon)
    strategy = get_ml_strategy(symbol)
    return ok({
        "ticker":   symbol,
        "price":    price,
        "strategy": strategy,
    })