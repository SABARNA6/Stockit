"""
=====================================================================
  db/supabase_logger.py
  Fast Supabase logging for all pipeline layers
  Replaces slow Google Sheets + Apps Script doPost approach
  
  Render env vars needed:
    SUPABASE_URL = https://xxx.supabase.co
    SUPABASE_KEY = your anon or service_role key
=====================================================================
"""

import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv() 

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
def _get_headers():
    key = os.environ.get("SUPABASE_KEY")
    return {
        "apikey":        key,
        "Authorization": f"Bearer {key}",
        "Content-Type":  "application/json",
        "Prefer":        "return=minimal",   # faster — don't return inserted rows
    }

def _url(table: str) -> str:
    base = os.environ.get("SUPABASE_URL", "").rstrip("/")
    return f"{base}/rest/v1/{table}"


def _insert(table: str, rows: list) -> bool:
    """Insert rows into a Supabase table. Returns True if successful."""
    if not rows:
        return True
    try:
        response = requests.post(
            _url(table),
            headers=_get_headers(),
            json=rows,
            timeout=10
        )
        if response.status_code in (200, 201):
            print(f"[Supabase] ✅ {table} — {len(rows)} rows inserted")
            return True
        else:
            print(f"[Supabase] ❌ {table} — HTTP {response.status_code}: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"[Supabase] ❌ {table} — Exception: {e}")
        return False


# ─────────────────────────────────────────────
#  RSS POOL — save new articles
# ─────────────────────────────────────────────
def save_articles(articles: list) -> int:
    """
    Save new articles to rss_pool.
    Skips duplicates via UNIQUE constraint on link.
    Returns count of successfully inserted articles.
    """
    if not articles:
        return 0

    rows = [{
        "title":          str(a.get("title", ""))[:500],
        "link":           str(a.get("link",  ""))[:1000],
        "summary":        str(a.get("summary", ""))[:2000],
        "published_date": str(a.get("publish_date", "") or a.get("published_date", "")),
        "source":         str(a.get("source", "")),
        "rss_id":         a.get("rss_id") or None,
    } for a in articles if a.get("link")]

    if not rows:
        return 0

    try:
        # upsert — skip duplicates on link
        response = requests.post(
            _url("rss_pool"),
            headers={**_get_headers(), "Prefer": "resolution=ignore-duplicates,return=minimal"},
            json=rows,
            timeout=15
        )
        if response.status_code in (200, 201):
            print(f"[Supabase] ✅ rss_pool — {len(rows)} articles saved")
            return len(rows)
        else:
            print(f"[Supabase] ❌ rss_pool — {response.status_code}: {response.text[:200]}")
            return 0
    except Exception as e:
        print(f"[Supabase] ❌ rss_pool — {e}")
        return 0


# ─────────────────────────────────────────────
#  NSE STOCKS — save/refresh stock list
# ─────────────────────────────────────────────
def save_nse_stocks(stocks: list) -> int:
    """Upsert NSE stocks — updates existing, inserts new."""
    if not stocks:
        return 0

    rows = []
    for s in stocks:
        ticker = str(s.get("Symbol", s.get("ticker", ""))).strip().upper()
        if not ticker:
            continue
        rows.append({
            "ticker":       ticker,
            "company_name": str(s.get("Company Name", s.get("company_name", ""))).strip(),
            "industry":     str(s.get("Industry",     s.get("industry", ""))).strip(),
            "series":       str(s.get("Series",       s.get("series", ""))).strip(),
            "isin":         str(s.get("ISIN Code",    s.get("isin", ""))).strip(),
        })

    if not rows:
        return 0

    try:
        response = requests.post(
            _url("nse_stocks"),
            headers={**_get_headers(),
                     "Prefer": "resolution=merge-duplicates,return=minimal"},
            json=rows,
            timeout=15
        )
        if response.status_code in (200, 201):
            print(f"[Supabase] ✅ nse_stocks — {len(rows)} stocks upserted")
            return len(rows)
        else:
            print(f"[Supabase] ❌ nse_stocks — {response.status_code}: {response.text[:200]}")
            return 0
    except Exception as e:
        print(f"[Supabase] ❌ nse_stocks — {e}")
        return 0


# ─────────────────────────────────────────────
#  POOL LOGS — RSS fetch history
# ─────────────────────────────────────────────
def log_pool(rss_id, source, status, new_items, skipped, total_pool, message=""):
    _insert("pool_logs", [{
        "rss_id":     rss_id,
        "source":     source,
        "status":     status,
        "new_items":  new_items,
        "skipped":    skipped,
        "total_pool": total_pool,
        "message":    str(message)[:500],
    }])


# ─────────────────────────────────────────────
#  L1 LOGS — NLP results
# ─────────────────────────────────────────────
def log_l1(profiles: list):
    if not profiles:
        return
    rows = [{
        "news_id":        p.get("id"),
        "title":          str(p.get("title", ""))[:300],
        "tickers_found":  ", ".join(e["ticker"] for e in p.get("entities", [])) or "—",
        "event_type":     p.get("event", {}).get("event_type", ""),
        "themes":         ", ".join(p.get("event", {}).get("themes", [])),
        "sentiment":      p.get("sentiment", {}).get("label", ""),
        "urgency_score":  p.get("sentiment", {}).get("urgency_score", 0),
        "relevance_score":p.get("relevance_score", 0),
        "source":         p.get("source", ""),
    } for p in profiles]
    _insert("l1_logs", rows)


# ─────────────────────────────────────────────
#  L2 LOGS — Impact propagation
# ─────────────────────────────────────────────
def log_l2(profiles: list):
    if not profiles:
        return
    rows = []
    for p in profiles:
        for e in p.get("affected_entities", []):
            rows.append({
                "news_id":    p.get("id"),
                "news_title": str(p.get("title", ""))[:300],
                "ticker":     e.get("ticker", ""),
                "company":    e.get("name", ""),
                "industry":   e.get("industry", ""),
                "impact_type":e.get("impact_type", ""),
                "direction":  e.get("direction", ""),
                "confidence": e.get("confidence", 0),
                "reason":     str(e.get("reason", ""))[:500],
                "sentiment":  e.get("sentiment", ""),
            })
    if rows:
        _insert("l2_logs", rows)


# ─────────────────────────────────────────────
#  L3 LOGS — Price predictions
# ─────────────────────────────────────────────
def log_l3(profiles: list):
    if not profiles:
        return
    rows = []
    for p in profiles:
        for e in p.get("affected_entities", []):
            pred = e.get("prediction", {})
            if not pred:
                continue
            pc = e.get("price_context", {})
            mr = pred.get("move_range", {})
            rows.append({
                "news_id":           p.get("id"),
                "news_title":        str(p.get("title", ""))[:300],
                "ticker":            e.get("ticker", ""),
                "company":           e.get("name", ""),
                "alert_priority":    pred.get("alert_priority", ""),
                "direction":         pred.get("direction", ""),
                "move_estimate_pct": pred.get("move_estimate_pct"),
                "move_range_low":    mr.get("low"),
                "move_range_high":   mr.get("high"),
                "confidence":        pred.get("confidence"),
                "time_horizon":      pred.get("time_horizon", ""),
                "current_price":     pc.get("current_price"),
                "trend_8d_pct":      pc.get("trend_8d_pct"),
                "volatility":        pc.get("volatility"),
                "reasoning":         str(pred.get("reasoning", ""))[:500],
                "key_risks":         str(pred.get("key_risks", ""))[:300],
            })
    if rows:
        _insert("l3_logs", rows)


# ─────────────────────────────────────────────
#  HEALTH CHECK — verify connection
# ─────────────────────────────────────────────
def check_connection() -> bool:
    try:
        url      = os.environ.get("SUPABASE_URL", "").rstrip("/")
        key      = os.environ.get("SUPABASE_KEY", "")
        if not url or not key:
            print("[Supabase] ❌ SUPABASE_URL or SUPABASE_KEY not set")
            return False
        response = requests.get(
            f"{url}/rest/v1/nse_stocks?select=ticker&limit=1",
            headers=_get_headers(),
            timeout=5
        )
        ok = response.status_code == 200
        print(f"[Supabase] {'✅ Connected' if ok else '❌ Connection failed — ' + str(response.status_code)}")
        return ok
    except Exception as e:
        print(f"[Supabase] ❌ Connection error: {e}")
        return False