import sqlite3
import json
import hashlib
import os
from datetime import datetime, timedelta
from config.config import DB_PATH, TTL, MARKET_OPEN, MARKET_CLOSE
import threading
import atexit


def _conn():
    # Ensure the database directory exists inside containers and local runs.
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init():
    """Create tables on first run."""
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                cache_key   TEXT PRIMARY KEY,
                layer       TEXT NOT NULL,
                value       TEXT NOT NULL,
                created_at  TEXT NOT NULL,
                expires_at  TEXT NOT NULL,
                hit_count   INTEGER DEFAULT 0
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS budget (
                key_id      TEXT NOT NULL,
                model       TEXT NOT NULL,
                date        TEXT NOT NULL,
                req_count   INTEGER DEFAULT 0,
                token_count INTEGER DEFAULT 0,
                PRIMARY KEY (key_id, model, date)
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_expires ON cache(expires_at)")


# ─── TTL HELPERS ─────────────────────────────────────────────────────────────

def _is_market_hours():
    now = datetime.now().strftime("%H:%M")
    return MARKET_OPEN <= now <= MARKET_CLOSE


def _ttl_hours(layer: str) -> int:
    hours = TTL[layer]
    if layer == "equity" and _is_market_hours():
        return 1
    return hours


def _expires(layer: str) -> str:
    return (datetime.now() + timedelta(hours=_ttl_hours(layer))).isoformat()


# ─── KEY BUILDERS ─────────────────────────────────────────────────────────────

def article_key(title: str, description: str) -> str:
    text = (title + description).lower().strip()
    return "article:" + hashlib.sha256(text.encode()).hexdigest()[:16]


def sector_key(sector: str) -> str:
    date = datetime.now().strftime("%Y-%m-%d")
    return f"sector:{sector}:{date}"


def equity_key(symbol: str) -> str:
    date = datetime.now().strftime("%Y-%m-%d")
    hour = datetime.now().strftime("%H")
    return f"equity:{symbol}:{date}:{hour}"


def user_key(user_id: str, symbol: str) -> str:
    date = datetime.now().strftime("%Y-%m-%d")
    return f"user:{user_id}:{symbol}:{date}"


# ─── CORE OPERATIONS ─────────────────────────────────────────────────────────

def get(key: str):
    """Return cached value or None if missing/expired."""
    with _conn() as c:
        row = c.execute(
            "SELECT value FROM cache WHERE cache_key=? AND expires_at>?",
            (key, datetime.now().isoformat())
        ).fetchone()
        if row:
            c.execute(
                "UPDATE cache SET hit_count=hit_count+1 WHERE cache_key=?",
                (key,)
            )
            return json.loads(row["value"])
    return None


def set(key: str, layer: str, value: dict):
    """Store value with correct TTL for the layer."""
    with _conn() as c:
        c.execute("""
            INSERT OR REPLACE INTO cache
            (cache_key, layer, value, created_at, expires_at, hit_count)
            VALUES (?, ?, ?, ?, ?, 0)
        """, (
            key,
            layer,
            json.dumps(value),
            datetime.now().isoformat(),
            _expires(layer),
        ))


def delete(key: str):
    """Invalidate a cache entry (breaking news)."""
    with _conn() as c:
        c.execute("DELETE FROM cache WHERE cache_key=?", (key,))


def purge_expired():
    """Delete all expired rows."""
    with _conn() as c:
        deleted = c.execute(
            "DELETE FROM cache WHERE expires_at<?",
            (datetime.now().isoformat(),)
        ).rowcount
    if deleted > 0:
        print(f"[cache] purged {deleted} expired rows")


def start_purge_thread(interval_hours: int = 1):
    """Run `purge_expired` in a background thread every `interval_hours`."""
    _stop_event = threading.Event()

    def run():
        while not _stop_event.is_set():
            purge_expired()
            _stop_event.wait(interval_hours * 3600)

    print(f"[cache] starting background purge thread (runs every {interval_hours}h)")
    t = threading.Thread(target=run, daemon=True)
    t.start()

    def _shutdown():
        _stop_event.set()
        t.join(timeout=5)

    atexit.register(_shutdown)
    return _shutdown


def stats():
    """Print cache hit summary."""
    with _conn() as c:
        rows = c.execute(
            "SELECT layer, COUNT(*) as n, SUM(hit_count) as hits FROM cache GROUP BY layer"
        ).fetchall()
    for r in rows:
        print(f"[cache] layer={r['layer']}  entries={r['n']}  total_hits={r['hits']}")


def snapshot() -> dict:
    """Return structured cache metrics for API responses."""
    with _conn() as c:
        rows = c.execute(
            "SELECT layer, COUNT(*) as n, COALESCE(SUM(hit_count), 0) as hits FROM cache GROUP BY layer"
        ).fetchall()
        totals = c.execute(
            "SELECT COUNT(*) as total_entries, COALESCE(SUM(hit_count), 0) as total_hits FROM cache"
        ).fetchone()

    per_layer = {
        r["layer"]: {
            "entries": int(r["n"] or 0),
            "hits": int(r["hits"] or 0),
        }
        for r in rows
    }
    return {
        "total_entries": int(totals["total_entries"] or 0),
        "total_hits": int(totals["total_hits"] or 0),
        "layers": per_layer,
    }
