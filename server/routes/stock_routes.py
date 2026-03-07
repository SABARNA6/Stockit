# routes/stock_routes.py
# Flask Blueprint — mirrors every endpoint the React frontend consumes.

from flask import Blueprint, jsonify, request
from helpers.stock_helper import (
    get_realtime_stock,
    get_sparkline,
    get_historical_data,
    get_financials,
    get_news,
    get_stock_trends,
    get_recommendation,
    get_chart_data,
    get_volume_data,
    search_company,
)

stock_bp = Blueprint("stocks", __name__, url_prefix="/api")


# ── tiny wrapper so every response has { success, data } ─────────────────────
def ok(data):
    return jsonify({"success": True, "data": data})


def err(msg, status=400):
    return jsonify({"success": False, "message": msg}), status


# ─────────────────────────────────────────────────────────────────────────────
# /api/stocks/<symbol>
# ─────────────────────────────────────────────────────────────────────────────
@stock_bp.get("/stocks/<symbol>")
def stock_overview(symbol):
    data = get_realtime_stock(symbol.upper())
    if not data:
        return err("Stock not found", 404)
    return ok(data)


# ─────────────────────────────────────────────────────────────────────────────
# /api/stocks/<symbol>/sparkline?points=12
# ─────────────────────────────────────────────────────────────────────────────
@stock_bp.get("/stocks/<symbol>/sparkline")
def stock_sparkline(symbol):
    points = request.args.get("points", 12, type=int)
    return ok(get_sparkline(symbol.upper(), points))


# ─────────────────────────────────────────────────────────────────────────────
# /api/stocks/<symbol>/chart?timeframe=3M
# ─────────────────────────────────────────────────────────────────────────────
@stock_bp.get("/stocks/<symbol>/chart")
def stock_chart(symbol):
    timeframe = request.args.get("timeframe", "3M")
    return ok(get_chart_data(symbol.upper(), timeframe))


# ─────────────────────────────────────────────────────────────────────────────
# /api/stocks/<symbol>/volume?timeframe=3M
# ─────────────────────────────────────────────────────────────────────────────
@stock_bp.get("/stocks/<symbol>/volume")
def stock_volume(symbol):
    timeframe = request.args.get("timeframe", "3M")
    return ok(get_volume_data(symbol.upper(), timeframe))


# ─────────────────────────────────────────────────────────────────────────────
# /api/stocks/<symbol>/trends
# ─────────────────────────────────────────────────────────────────────────────
@stock_bp.get("/stocks/<symbol>/trends")
def stock_trends(symbol):
    return ok(get_stock_trends(symbol.upper()))


# ─────────────────────────────────────────────────────────────────────────────
# /api/stocks/<symbol>/recommendation
# ─────────────────────────────────────────────────────────────────────────────
@stock_bp.get("/stocks/<symbol>/recommendation")
def stock_recommendation(symbol):
    return ok(get_recommendation(symbol.upper()))


# ─────────────────────────────────────────────────────────────────────────────
# /api/stocks/<symbol>/fundamentals
# ─────────────────────────────────────────────────────────────────────────────
@stock_bp.get("/stocks/<symbol>/fundamentals")
def stock_fundamentals(symbol):
    return ok(get_financials(symbol.upper()))


# ─────────────────────────────────────────────────────────────────────────────
# /api/stocks/<symbol>/news   → used by frontend
# ─────────────────────────────────────────────────────────────────────────────
@stock_bp.get("/stocks/<symbol>/news")
def stock_news(symbol):
    return ok(get_news(symbol.upper(), get_realtime_stock))




# ─────────────────────────────────────────────────────────────────────────────
# /api/stocks/<symbol>/historical?period=1mo&page=1&limit=8
# ─────────────────────────────────────────────────────────────────────────────
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


# ─────────────────────────────────────────────────────────────────────────────
# /api/company/search?symbol=RELIANCE
# ─────────────────────────────────────────────────────────────────────────────
@stock_bp.get("/company/search")
def company_search():
    symbol = request.args.get("symbol", "").strip().upper()
    if not symbol:
        return err("symbol query param is required")
    result = search_company(symbol)
    if "error" in result:
        return err(result["error"], 400)
    return jsonify(result)