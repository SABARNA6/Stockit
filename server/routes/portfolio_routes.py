# routes/portfolio_routes.py
#
# Portfolio + Watchlist REST endpoints.
# Uses user's own JWT token to query Supabase — no service_role needed.
# Supabase RLS enforces user isolation automatically.

from flask import Blueprint, jsonify, request
from helpers.supabase_helper import get_client_for_user, get_user_from_token
from helpers.stock_helper import search_company

portfolio_bp = Blueprint("portfolio", __name__, url_prefix="/api")


def ok(data):
    return jsonify({"success": True, "data": data})

def err(msg, status=400):
    return jsonify({"success": False, "message": msg}), status


def _normalize_symbol(symbol: str) -> str:
    s = str(symbol or "").strip().upper()
    if not s:
        return ""
    if ":" in s:
        s = s.split(":")[-1]
    s = s.replace(" ", "")
    for suffix in (".NS", ".BO"):
        if s.endswith(suffix):
            s = s[: -len(suffix)]
            break
    return s


def _get_token(req) -> tuple[str | None, object]:
    """Extract Bearer token from Authorization header."""
    auth = req.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None, err("Missing Authorization header", 401)
    token = auth.split(" ", 1)[1].strip()
    if not token:
        return None, err("Empty token", 401)

    # Validate token has correct structure + not expired
    user = get_user_from_token(token)
    if not user:
        return None, err("Invalid or expired token", 401)

    return token, None


# ══════════════════════════════════════════════════════════════════════════════
# PORTFOLIO
# ══════════════════════════════════════════════════════════════════════════════

@portfolio_bp.get("/portfolio")
def list_portfolio():
    """GET /api/portfolio — list holdings for authenticated user."""
    token, error = _get_token(request)
    if error:
        return error

    try:
        sb   = get_client_for_user(token)
        resp = sb.table("portfolio").select("*").order("created_at", desc=True).execute()
        return ok(resp.data or [])
    except Exception as e:
        print(f"[list_portfolio] {e}")
        return err(str(e), 500)


@portfolio_bp.post("/portfolio")
def add_portfolio():
    """
    POST /api/portfolio — add one or many holdings.

    Body (single):   { "symbol": "TCS", "qty": 50, "avg_cost": 3450 }
    Body (bulk):     [ { "symbol": "TCS", "qty": 50, "avg_cost": 3450 }, ... ]
    """
    token, error = _get_token(request)
    if error:
        return error

    user = get_user_from_token(token)
    body = request.get_json(silent=True)
    if not body:
        return err("Request body must be JSON")

    rows = body if isinstance(body, list) else [body]

    validated = []
    symbol_exists_cache = {}
    for row in rows:
        symbol = _normalize_symbol(row.get("symbol", ""))
        if not symbol:
            return err("Each holding requires a 'symbol'")

        if symbol not in symbol_exists_cache:
            lookup = search_company(symbol)
            symbol_exists_cache[symbol] = bool(lookup.get("data"))
        if not symbol_exists_cache[symbol]:
            return err(f"Invalid equity symbol: {symbol}. Use valid tickers like TCS or RELIANCE.")

        try:
            qty      = float(row.get("qty"))
            avg_cost = float(row.get("avg_cost"))
        except (TypeError, ValueError):
            return err(f"Invalid qty or avg_cost for {symbol}")

        if qty <= 0 or avg_cost <= 0:
            return err(f"qty and avg_cost must be greater than 0 for {symbol}")

        validated.append({
            "user_id":  user["id"],
            "symbol":   symbol,
            "qty":      qty,
            "avg_cost": avg_cost,
        })

    try:
        sb   = get_client_for_user(token)
        resp = sb.table("portfolio").insert(validated).execute()
        return ok(resp.data)
    except Exception as e:
        print(f"[add_portfolio] {e}")
        return err(str(e), 500)


@portfolio_bp.delete("/portfolio/<holding_id>")
def delete_portfolio(holding_id):
    """DELETE /api/portfolio/<id> — remove a holding."""
    token, error = _get_token(request)
    if error:
        return error

    try:
        sb = get_client_for_user(token)
        sb.table("portfolio").delete().eq("id", holding_id).execute()
        return ok({"deleted": holding_id})
    except Exception as e:
        print(f"[delete_portfolio] {e}")
        return err(str(e), 500)


# ══════════════════════════════════════════════════════════════════════════════
# WATCHLIST
# ══════════════════════════════════════════════════════════════════════════════

@portfolio_bp.get("/watchlist")
def list_watchlist():
    """GET /api/watchlist — list watchlist for authenticated user."""
    token, error = _get_token(request)
    if error:
        return error

    try:
        sb   = get_client_for_user(token)
        resp = sb.table("watchlist").select("*").order("created_at", desc=True).execute()
        return ok(resp.data or [])
    except Exception as e:
        print(f"[list_watchlist] {e}")
        return err(str(e), 500)


@portfolio_bp.post("/watchlist")
def add_watchlist():
    """
    POST /api/watchlist — add a stock to watchlist.

    Body: { "symbol": "INFY", "name": "Infosys", "sector": "IT",
            "price": 1900, "target_price": 2100, "note": "..." }
    """
    token, error = _get_token(request)
    if error:
        return error

    user = get_user_from_token(token)
    body = request.get_json(silent=True)
    if not body:
        return err("Request body must be JSON")

    symbol = str(body.get("symbol", "")).strip().upper()
    if not symbol:
        return err("'symbol' is required")

    row = {
        "user_id":      user["id"],
        "symbol":       symbol,
        "name":         body.get("name",         symbol),
        "sector":       body.get("sector",        ""),
        "price":        body.get("price",         None),
        "target_price": body.get("target_price",  None),
        "note":         body.get("note",          ""),
    }

    try:
        sb   = get_client_for_user(token)
        resp = sb.table("watchlist").insert(row).execute()
        return ok(resp.data[0] if resp.data else row)
    except Exception as e:
        msg = str(e)
        if "unique" in msg.lower() or "duplicate" in msg.lower():
            return err(f"{symbol} is already in your watchlist", 409)
        print(f"[add_watchlist] {e}")
        return err(msg, 500)


@portfolio_bp.delete("/watchlist/<item_id>")
def delete_watchlist(item_id):
    """DELETE /api/watchlist/<id> — remove a watchlist item."""
    token, error = _get_token(request)
    if error:
        return error

    try:
        sb = get_client_for_user(token)
        sb.table("watchlist").delete().eq("id", item_id).execute()
        return ok({"deleted": item_id})
    except Exception as e:
        print(f"[delete_watchlist] {e}")
        return err(str(e), 500)