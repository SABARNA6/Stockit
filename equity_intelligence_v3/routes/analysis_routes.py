"""
=====================================================================
  routes/analysis_routes.py
  API endpoints for stock analysis and API key budget/limit checks
=====================================================================
"""

import os
import json
import requests
from flask import Blueprint, jsonify, request

from config.config import EQUITIES_PATH, GROQ_KEYS, LIMITS
from core import pipeline, budget, cache
from ingestion import news, equity_sync
from data.generate_equities import generate_equity

analysis_bp = Blueprint("analysis", __name__, url_prefix="/api")


def _mask_key(key: str | None) -> str:
    if not key:
        return ""
    if len(key) <= 8:
        return "*" * len(key)
    return key[:4] + "..." + key[-4:]


def _load_equities() -> list[dict]:
    with open(EQUITIES_PATH) as f:
        return json.load(f)


def _find_equity(symbol: str) -> dict | None:
    symbol = symbol.upper()
    equities = _load_equities()
    for e in equities:
        if e.get("symbol", "").upper() == symbol:
            return e

    # If missing locally, attempt one-off generation from yfinance rules.
    generated = generate_equity(symbol)
    if not generated:
        return None

    equities.append(generated)
    with open(EQUITIES_PATH, "w") as f:
        json.dump(equities, f, indent=2)
    return generated


@analysis_bp.route("/analyze/<symbol>", methods=["GET"])
def analyze_symbol(symbol: str):
    """
    Analyze one symbol via full pipeline and return cache metadata.

    Query params:
      hours_back   int (default 24)
      prune_news   bool (default false) -> optionally run retention cleanup first
    """
    try:
        symbol = symbol.strip().upper()
        hours_back = int(request.args.get("hours_back", 24))
        prune_news = request.args.get("prune_news", "false").lower() == "true"

        if prune_news:
            news.prune_old_news(days=7)

        equity = _find_equity(symbol)
        if not equity:
            return jsonify({
                "status": "error",
                "message": f"Symbol {symbol} not found in equities and could not be generated",
            }), 404

        articles = news.fetch_today(hours_back=hours_back)
        if not articles:
            return jsonify({
                "status": "error",
                "message": "No articles available for analysis",
                "symbol": symbol,
                "hours_back": hours_back,
                "cache": cache.snapshot(),
            }), 404

        result = pipeline.run(articles, equity)

        return jsonify({
            "status": "success",
            "symbol": symbol,
            "hours_back": hours_back,
            "cache": {
                "result_cache_status": result.get("cache_status", "unknown"),
                "snapshot": cache.snapshot(),
            },
            "analysis": result,
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@analysis_bp.route("/limits", methods=["GET"])
def get_api_limits():
    """
    Return Groq (local budget-tracked) and NewsAPI (live ping) limit status.
    """
    try:
        # Groq limits are tracked in local SQLite budget table.
        groq_status = {}
        for key_id, key_value in GROQ_KEYS.items():
            key_entry = {
                "configured": bool(key_value),
                "masked_key": _mask_key(key_value),
                "models": {},
            }
            for model, model_limits in LIMITS.items():
                used = budget.used(key_id, model)
                remaining = budget.remaining(key_id, model)
                key_entry["models"][model] = {
                    "limits": {
                        "rpm": model_limits.get("rpm"),
                        "rpd": model_limits.get("rpd"),
                        "tpm": model_limits.get("tpm"),
                        "tpd": model_limits.get("tpd"),
                    },
                    "used_today": {
                        "requests": used["reqs"],
                        "tokens": used["tokens"],
                    },
                    "remaining_today": {
                        "requests": remaining["reqs"],
                        "tokens": remaining["tokens"],
                    },
                }
            groq_status[key_id] = key_entry

        # NewsAPI status: best-effort probe + response headers.
        newsapi_key = os.getenv("NEWSAPI_KEY") or os.getenv("NEWS_API_KEY")
        newsapi = {
            "configured": bool(newsapi_key),
            "masked_key": _mask_key(newsapi_key),
            "status_code": None,
            "headers": {},
            "body_status": None,
            "body_message": None,
        }

        if newsapi_key:
            response = requests.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q": "markets",
                    "language": "en",
                    "pageSize": 1,
                    "apiKey": newsapi_key,
                },
                timeout=10,
            )
            payload = response.json() if response.headers.get("Content-Type", "").startswith("application/json") else {}
            newsapi["status_code"] = response.status_code
            newsapi["body_status"] = payload.get("status")
            newsapi["body_message"] = payload.get("message")
            newsapi["headers"] = {
                "x-ratelimit-limit": response.headers.get("X-RateLimit-Limit"),
                "x-ratelimit-remaining": response.headers.get("X-RateLimit-Remaining"),
                "x-ratelimit-reset": response.headers.get("X-RateLimit-Reset"),
            }

        return jsonify({
            "status": "success",
            "groq": groq_status,
            "newsapi": newsapi,
            "cache": cache.snapshot(),
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@analysis_bp.route("/equities/sync", methods=["GET", "POST"])
def sync_equities_to_supabase():
    """
    Sync local equities.json into Supabase `equities` table.

    Behavior:
    - Checks which local symbols are missing in Supabase
    - Generates missing profiles when needed
    - Upserts into Supabase
    """
    try:
        local_equities = _load_equities()
        saved = equity_sync.sync(EQUITIES_PATH)

        return jsonify({
            "status": "success",
            "message": "Equity sync completed",
            "local_equities_count": len(local_equities),
            "saved_to_supabase": saved,
            "equities_path": EQUITIES_PATH,
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
