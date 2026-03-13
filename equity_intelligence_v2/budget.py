import sqlite3
from datetime import datetime
from config import DB_PATH, LIMITS


def _conn():
    return sqlite3.connect(DB_PATH)


def _today():
    return datetime.now().strftime("%Y-%m-%d")


# ─── READ ─────────────────────────────────────────────────────────────────────

def used(key_id: str, model: str) -> dict:
    """Return {req_count, token_count} used today for this key+model."""
    with _conn() as c:
        row = c.execute(
            "SELECT req_count, token_count FROM budget WHERE key_id=? AND model=? AND date=?",
            (key_id, model, _today())
        ).fetchone()
    if row:
        return {"reqs": row[0], "tokens": row[1]}
    return {"reqs": 0, "tokens": 0}


def remaining(key_id: str, model: str) -> dict:
    """Return remaining requests and tokens for today."""
    limits = LIMITS[model]
    u = used(key_id, model)
    return {
        "reqs":   limits["rpd"] - u["reqs"],
        "tokens": limits["tpd"] - u["tokens"],
    }


def can_afford(key_id: str, model: str, est_tokens: int) -> bool:
    """Check if this key has budget for one more call."""
    r = remaining(key_id, model)
    return r["reqs"] >= 1 and r["tokens"] >= est_tokens


# ─── WRITE ────────────────────────────────────────────────────────────────────

def record(key_id: str, model: str, tokens_used: int):
    """Record one API call after it completes."""
    with _conn() as c:
        c.execute("""
            INSERT INTO budget (key_id, model, date, req_count, token_count)
            VALUES (?, ?, ?, 1, ?)
            ON CONFLICT(key_id, model, date)
            DO UPDATE SET
                req_count   = req_count   + 1,
                token_count = token_count + ?
        """, (key_id, model, _today(), tokens_used, tokens_used))


# ─── SUMMARY ─────────────────────────────────────────────────────────────────

def summary():
    """Print today's usage for all keys."""
    with _conn() as c:
        rows = c.execute(
            "SELECT key_id, model, req_count, token_count FROM budget WHERE date=?",
            (_today(),)
        ).fetchall()
    print("\n[budget] Usage today:")
    print(f"  {'key':<8} {'model':<30} {'reqs':>6} {'tokens':>10}")
    print("  " + "-" * 58)
    for r in rows:
        model   = r[1]
        limits  = LIMITS.get(model, {})
        rpd     = limits.get("rpd", "?")
        tpd     = limits.get("tpd", "?")
        print(f"  {r[0]:<8} {model:<30} {r[2]:>6}/{rpd:<6} {r[3]:>10}/{tpd}")
