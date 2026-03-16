# routes/equity_routes.py
#
# Proxies Equity Intelligence v3 (runs on localhost:5000)
# into this gateway under /api/equity/*
#
# Equity Intelligence endpoints exposed:
#   GET  /api/equity/analyze/<symbol>?hours_back=24
#   GET  /api/equity/limits
#   POST /api/equity/trigger
#   GET  /api/equity/status

from flask import Blueprint, jsonify, request
import requests as http
import os

equity_bp = Blueprint("equity", __name__, url_prefix="/api/equity")

# Equity Intelligence v3 base URL (runs on port 5000 by default)
EI_BASE = os.getenv("EQUITY_INTELLIGENCE_URL", "http://localhost:5000")

TIMEOUT = 30  # seconds — LLM analysis can be slow


def ok(data):
    return jsonify({"success": True, "data": data})

def err(msg, status=400):
    return jsonify({"success": False, "message": msg}), status


def _proxy_get(path: str, params: dict = None):
    """Forward a GET request to Equity Intelligence and return its response."""
    try:
        resp = http.get(f"{EI_BASE}{path}", params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        return jsonify(resp.json()), resp.status_code
    except http.exceptions.ConnectionError:
        return err("Equity Intelligence service is not running. "
                   "Start it with: python server.py (port 5000)", 503)
    except http.exceptions.Timeout:
        return err("Equity Intelligence timed out — LLM analysis is taking too long.", 504)
    except http.exceptions.HTTPError as e:
        return err(f"Equity Intelligence error: {str(e)}", 502)
    except Exception as e:
        return err(str(e), 500)


def _proxy_post(path: str, body: dict = None):
    """Forward a POST request to Equity Intelligence."""
    try:
        resp = http.post(f"{EI_BASE}{path}", json=body or {}, timeout=TIMEOUT)
        resp.raise_for_status()
        return jsonify(resp.json()), resp.status_code
    except http.exceptions.ConnectionError:
        return err("Equity Intelligence service is not running. "
                   "Start it with: python server.py (port 5000)", 503)
    except Exception as e:
        return err(str(e), 500)


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/equity/analyze/<symbol>?hours_back=24&prune_news=false
#
# Full LLM pipeline for one symbol.
# Response from Equity Intelligence:
# {
#   "symbol": "TCS",
#   "sentiment_score": 7.4,
#   "overall_direction": "BULLISH",
#   "price_impact": {
#     "overall_move_low": 0.5,
#     "overall_move_high": 1.8,
#     "overall_move_range": "+0.5% to +1.8%",
#     "overall_direction": "BULLISH",
#     "signals": {"bullish": 3, "bearish": 1, "neutral": 2}
#   },
#   "results": [...]
# }
# ─────────────────────────────────────────────────────────────────────────────
@equity_bp.get("/analyze/<symbol>")
def equity_analyze(symbol):
    hours_back  = request.args.get("hours_back",  24,    type=int)
    prune_news  = request.args.get("prune_news",  "false")
    return _proxy_get(
        f"/api/analyze/{symbol.upper()}",
        params={"hours_back": hours_back, "prune_news": prune_news},
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/equity/limits
# Returns Groq key/model budget + NewsAPI status + cache snapshot.
# ─────────────────────────────────────────────────────────────────────────────
@equity_bp.get("/limits")
def equity_limits():
    return _proxy_get("/api/limits")


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/equity/trigger
# Triggers RSS + NewsAPI ingestion into Supabase rss_pool.
# ─────────────────────────────────────────────────────────────────────────────
@equity_bp.post("/trigger")
def equity_trigger():
    return _proxy_post("/api/rss/trigger")


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/equity/status
# RSS module health check.
# ─────────────────────────────────────────────────────────────────────────────
@equity_bp.get("/status")
def equity_status():
    return _proxy_get("/api/rss/status")
