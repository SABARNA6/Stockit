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
import re
import time
import threading

equity_bp = Blueprint("equity", __name__, url_prefix="/api/equity")

# Equity Intelligence v3 base URL (runs on port 5000 by default)
EI_BASE = os.getenv("EQUITY_INTELLIGENCE_URL", "http://localhost:5000")

TIMEOUT = int(os.getenv("EQUITY_PROXY_TIMEOUT", "120"))  # LLM analysis can be slow

_REQUIRE_API_KEY = os.getenv("EQUITY_REQUIRE_API_KEY", "false").lower() == "true"
_EQUITY_API_KEY = os.getenv("EQUITY_API_KEY", "")

_ANALYZE_RATE_LIMIT = int(os.getenv("EQUITY_ANALYZE_RATE_LIMIT", "3"))
_ANALYZE_RATE_WINDOW_SEC = int(os.getenv("EQUITY_ANALYZE_RATE_WINDOW_SEC", "60"))
_MAX_CONCURRENT_ANALYZE = int(os.getenv("EQUITY_ANALYZE_MAX_CONCURRENT", "2"))
_INFLIGHT_TTL_SEC = int(os.getenv("EQUITY_ANALYZE_INFLIGHT_TTL_SEC", "300"))
_ANALYZE_RESULT_CACHE_TTL_SEC = int(os.getenv("EQUITY_ANALYZE_RESULT_CACHE_TTL_SEC", "240"))
_ANALYZE_WAIT_FOR_INFLIGHT_SEC = int(os.getenv("EQUITY_ANALYZE_WAIT_FOR_INFLIGHT_SEC", "95"))

_rate_hits: dict[str, list[float]] = {}
_inflight: dict[str, float] = {}
_inflight_events: dict[str, threading.Event] = {}
_analyze_result_cache: dict[str, tuple[float, dict, int]] = {}
_guard_lock = threading.Lock()


def ok(data):
    return jsonify({"success": True, "data": data})

def err(msg, status=400):
    return jsonify({"success": False, "message": msg}), status


def _client_id() -> str:
    fwd = request.headers.get("X-Forwarded-For", "").strip()
    if fwd:
        return fwd.split(",")[0].strip()
    return request.remote_addr or "unknown"


def _require_equity_api_key():
    if not _REQUIRE_API_KEY:
        return None
    incoming = request.headers.get("X-Equity-Key", "")
    if not _EQUITY_API_KEY or incoming != _EQUITY_API_KEY:
        return err("Unauthorized equity endpoint", 401)
    return None


def _check_rate_limit(scope: str, client: str, limit: int, window_sec: int):
    now = time.time()
    key = f"{scope}:{client}"
    with _guard_lock:
        hits = [ts for ts in _rate_hits.get(key, []) if now - ts < window_sec]
        if len(hits) >= limit:
            retry_after = max(1, int(window_sec - (now - hits[0])))
            return (
                jsonify({
                    "success": False,
                    "message": "Rate limit exceeded for equity analyze",
                    "retryAfterSec": retry_after,
                }),
                429,
            )
        hits.append(now)
        _rate_hits[key] = hits
    return None


def _start_inflight(job_key: str):
    now = time.time()
    with _guard_lock:
        stale = [k for k, ts in _inflight.items() if now - ts > _INFLIGHT_TTL_SEC]
        for k in stale:
            _inflight.pop(k, None)
            evt = _inflight_events.pop(k, None)
            if evt is not None:
                evt.set()

        if job_key in _inflight:
            return {"mode": "join", "event": _inflight_events.get(job_key)}

        if len(_inflight) >= _MAX_CONCURRENT_ANALYZE:
            return {
                "mode": "reject",
                "response": (
                    jsonify({
                        "success": False,
                        "message": "Analysis capacity busy, please retry shortly",
                        "maxConcurrent": _MAX_CONCURRENT_ANALYZE,
                    }),
                    429,
                ),
            }

        _inflight[job_key] = now
        _inflight_events[job_key] = threading.Event()
    return {"mode": "owner", "event": _inflight_events.get(job_key)}


def _end_inflight(job_key: str):
    evt = None
    with _guard_lock:
        _inflight.pop(job_key, None)
        evt = _inflight_events.pop(job_key, None)
    if evt is not None:
        evt.set()


def _cache_get_analyze(job_key: str):
    now = time.time()
    with _guard_lock:
        stale = [k for k, (ts, _, _) in _analyze_result_cache.items() if now - ts > _ANALYZE_RESULT_CACHE_TTL_SEC]
        for k in stale:
            _analyze_result_cache.pop(k, None)

        hit = _analyze_result_cache.get(job_key)
        if hit is None:
            return None
        _, payload, status = hit
        return payload, status


def _cache_set_analyze(job_key: str, payload: dict, status: int):
    with _guard_lock:
        _analyze_result_cache[job_key] = (time.time(), payload, status)


def _proxy_get(path: str, params: dict = None):
    """Forward a GET request to Equity Intelligence and return its response."""
    payload, status = _proxy_get_payload(path, params=params)
    return jsonify(payload), status


def _proxy_get_payload(path: str, params: dict = None):
    """Forward GET request and return JSON payload + status without Flask response wrapper."""
    try:
        resp = http.get(f"{EI_BASE}{path}", params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        try:
            body = resp.json()
        except ValueError:
            body = {"raw": resp.text}
        return body, resp.status_code
    except http.exceptions.ConnectionError:
        return {"success": False, "message": "Equity Intelligence service unavailable"}, 503
    except http.exceptions.Timeout:
        return {"success": False, "message": "Equity Intelligence request timed out"}, 504
    except http.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else 502
        try:
            upstream_body = e.response.json() if e.response is not None else {}
        except ValueError:
            upstream_body = {"raw": (e.response.text if e.response is not None else "")}

        message = "Upstream Equity Intelligence error"
        if isinstance(upstream_body, dict):
            message = (
                upstream_body.get("message")
                or upstream_body.get("error")
                or upstream_body.get("status")
                or message
            )

        return {
            "success": False,
            "message": message,
            "upstream": {
                "status": status,
                "path": path,
                "body": upstream_body,
            },
        }, status
    except Exception:
        return {"success": False, "message": "Unexpected proxy error"}, 500


def _proxy_post(path: str, body: dict = None):
    """Forward a POST request to Equity Intelligence."""
    try:
        resp = http.post(f"{EI_BASE}{path}", json=body or {}, timeout=TIMEOUT)
        resp.raise_for_status()
        return jsonify(resp.json()), resp.status_code
    except http.exceptions.ConnectionError:
        return err("Equity Intelligence service unavailable", 503)
    except http.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else 502
        try:
            upstream_body = e.response.json() if e.response is not None else {}
        except ValueError:
            upstream_body = {"raw": (e.response.text if e.response is not None else "")}

        message = "Upstream Equity Intelligence error"
        if isinstance(upstream_body, dict):
            message = (
                upstream_body.get("message")
                or upstream_body.get("error")
                or upstream_body.get("status")
                or message
            )

        return jsonify({
            "success": False,
            "message": message,
            "upstream": {
                "status": status,
                "path": path,
                "body": upstream_body,
            },
        }), status
    except Exception:
        return err("Unexpected proxy error", 500)


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
    auth_error = _require_equity_api_key()
    if auth_error:
        return auth_error

    normalized_symbol = str(symbol or "").strip().upper()
    if not re.fullmatch(r"[A-Z0-9]{1,15}", normalized_symbol):
        return err("Invalid symbol format", 400)

    hours_back = request.args.get("hours_back", 24, type=int)
    prune_news = request.args.get("prune_news", "false")
    hours_back = max(1, min(int(hours_back or 24), 24))

    client = _client_id()
    limited = _check_rate_limit(
        scope="equity_analyze",
        client=client,
        limit=_ANALYZE_RATE_LIMIT,
        window_sec=_ANALYZE_RATE_WINDOW_SEC,
    )
    if limited:
        return limited

    job_key = f"{normalized_symbol}:{hours_back}:{str(prune_news).lower()}"

    cached = _cache_get_analyze(job_key)
    if cached:
        payload, status = cached
        return jsonify(payload), status

    inflight = _start_inflight(job_key)
    if inflight.get("mode") == "reject":
        return inflight["response"]

    if inflight.get("mode") == "join":
        evt = inflight.get("event")
        if evt is not None:
            evt.wait(_ANALYZE_WAIT_FOR_INFLIGHT_SEC)
        cached_after_wait = _cache_get_analyze(job_key)
        if cached_after_wait:
            payload, status = cached_after_wait
            return jsonify(payload), status

        return (
            jsonify({
                "success": False,
                "message": "Analysis in progress, retry shortly",
                "jobKey": job_key,
                "retryAfterSec": 3,
            }),
            202,
        )

    try:
        payload, status = _proxy_get_payload(
            f"/api/analyze/{normalized_symbol}",
            params={"hours_back": hours_back, "prune_news": prune_news},
        )
        if status < 500:
            _cache_set_analyze(job_key, payload, status)
        return jsonify(payload), status
    finally:
        _end_inflight(job_key)


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
    auth_error = _require_equity_api_key()
    if auth_error:
        return auth_error
    return _proxy_post("/api/rss/trigger")


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/equity/status
# RSS module health check.
# ─────────────────────────────────────────────────────────────────────────────
@equity_bp.get("/status")
def equity_status():
    return _proxy_get("/api/rss/status")
