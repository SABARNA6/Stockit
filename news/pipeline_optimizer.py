"""
=====================================================================
  pipeline_optimizer.py
  Reduces tokens + requests before articles hit LLM layers

  Strategies:
  1. L1 pre-filter   — drop irrelevant articles early
  2. Deduplication   — cluster similar headlines, keep one
  3. Chunked processing — limit per run, track progress
=====================================================================
"""

import re
import os
import requests
from datetime import datetime


# ─────────────────────────────────────────────
#  STRATEGY 1 — L1 PRE-FILTER
#  Drop articles that won't yield useful signals
# ─────────────────────────────────────────────

# Categories that rarely have Indian stock impact
NON_FINANCIAL_SOURCES = {
    "espn", "espn india", "sportstar", "khel now",
    "bollywood hungama", "pinkvilla", "koimoi",
    "india today entertainment", "variety", "rolling stone",
    "billboard", "hollywood reporter", "tmz",
    "the health site", "native planet", "conde nast traveler",
    "matador network", "make magazine", "lifehacker",
    "hackaday", "wpbeginner", "css-tricks", "sitepoint",
    "a list apart", "smashing magazine",
}

FINANCIAL_KEYWORDS = {
    # Companies / markets
    "nse", "bse", "sensex", "nifty", "sebi", "rbi", "ipo",
    "stock", "share", "equity", "market", "invest",
    # Events
    "earnings", "results", "profit", "revenue", "quarterly",
    "merger", "acquisition", "dividend", "buyback",
    "bankruptcy", "default", "debt", "rating",
    # Macro
    "inflation", "gdp", "rate", "repo", "fiscal", "budget",
    "crude", "oil", "rupee", "dollar", "forex",
    # Indian companies (common mentions)
    "reliance", "tata", "infosys", "hdfc", "icici", "sbi",
    "wipro", "adani", "bajaj", "mahindra", "ongc", "ntpc",
}


def prefilter_articles(articles: list) -> tuple[list, int]:
    """
    Filter articles before L1 processing.
    Returns (kept_articles, dropped_count)
    """
    kept    = []
    dropped = 0

    for a in articles:
        source = str(a.get("source", "")).lower().strip()
        title  = str(a.get("title",  "")).lower()
        summary= str(a.get("summary","")).lower()
        text   = title + " " + summary

        # Drop non-financial sources entirely
        if source in NON_FINANCIAL_SOURCES:
            dropped += 1
            continue

        # Must contain at least one financial keyword
        if not any(kw in text for kw in FINANCIAL_KEYWORDS):
            dropped += 1
            continue

        kept.append(a)

    print(f"[Filter] {len(articles)} articles → {len(kept)} kept, {dropped} dropped")
    return kept, dropped


# ─────────────────────────────────────────────
#  STRATEGY 2 — DEDUPLICATION
#  Cluster similar headlines, keep highest quality
# ─────────────────────────────────────────────

def _normalize(text: str) -> str:
    """Normalize text for comparison."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    # Remove common filler words
    stopwords = {'the','a','an','in','on','at','to','for','of','and','or',
                 'is','are','was','were','has','have','had','will','be',
                 'by','with','from','says','said','report','reports'}
    words = [w for w in text.split() if w not in stopwords]
    return ' '.join(words)


def _similarity(a: str, b: str) -> float:
    """Simple word overlap similarity (0-1)."""
    words_a = set(_normalize(a).split())
    words_b = set(_normalize(b).split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union        = words_a | words_b
    return len(intersection) / len(union)


def deduplicate_articles(articles: list, threshold: float = 0.6) -> tuple[list, int]:
    """
    Remove duplicate/similar articles.
    Keeps the one with the longest summary (most content).
    Returns (unique_articles, removed_count)
    """
    if not articles:
        return [], 0

    unique  = []
    removed = 0

    for article in articles:
        title   = article.get("title", "")
        is_dupe = False

        for kept in unique:
            sim = _similarity(title, kept.get("title", ""))
            if sim >= threshold:
                # Keep the one with more content
                if len(article.get("summary","")) > len(kept.get("summary","")):
                    unique.remove(kept)
                    unique.append(article)
                is_dupe = True
                removed += 1
                break

        if not is_dupe:
            unique.append(article)

    print(f"[Dedup] {len(articles)} articles → {len(unique)} unique, {removed} duplicates removed")
    return unique, removed


# ─────────────────────────────────────────────
#  STRATEGY 5 — CHUNKED PROCESSING
#  Track progress in Supabase, process N per run
# ─────────────────────────────────────────────

CHUNK_SIZE = 50   # articles per run (tune based on API limits)


def get_progress() -> dict:
    """Read current pipeline progress from Supabase."""
    try:
        from database.supabase_logger import _get_headers, _url
        r = requests.get(
            _url("pipeline_progress") + "?select=*&limit=1&order=id.desc",
            headers=_get_headers(),
            timeout=10
        )
        if r.status_code == 200 and r.json():
            return r.json()[0]
    except Exception as e:
        print(f"[Progress] ⚠️ Failed to read: {e}")
    return {"last_processed_index": 0, "status": "NOT STARTED"}


def save_progress(index: int, total: int, relevant: int, status: str):
    """Update pipeline progress in Supabase."""
    try:
        from database.supabase_logger import _get_headers, _url
        requests.patch(
            _url("pipeline_progress") + "?id=eq.1",
            headers={**_get_headers(), "Prefer": "return=minimal"},
            json={
                "last_processed_index": index,
                "total_articles":       total,
                "total_relevant":       relevant,
                "status":               status,
                "last_run":             datetime.now().isoformat(),
            },
            timeout=10
        )
    except Exception as e:
        print(f"[Progress] ⚠️ Failed to save: {e}")


def get_next_chunk(articles: list) -> tuple[list, int]:
    """
    Get the next CHUNK_SIZE articles to process.
    Returns (chunk, start_index)
    """
    progress    = get_progress()
    start_index = progress.get("last_processed_index", 0)

    # If we've processed everything, restart from 0
    if start_index >= len(articles):
        print(f"[Progress] All {len(articles)} articles processed — resetting")
        start_index = 0

    chunk = articles[start_index: start_index + CHUNK_SIZE]
    print(f"[Progress] Chunk: articles {start_index}→{start_index + len(chunk)} "
          f"of {len(articles)} total")
    return chunk, start_index