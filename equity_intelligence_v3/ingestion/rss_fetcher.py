"""
=====================================================================
  ingestion/rss_fetcher.py
  Fetches RSS feeds from Supabase, parses XML, deduplicates,
  saves new articles to Supabase rss_pool
=====================================================================
"""

import os
import json
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
from ingestion import news

ROOT_DIR = Path(__file__).resolve().parents[1]
NEWSAPI_SYMBOLS_PATH = ROOT_DIR / "data" / "newsapi_symbols.json"

# ── Load environment variables ─────────────────────────────────────────────────
# First try from file (for local dev), then fall back to Docker env variables
_env_file_path = ROOT_DIR / ".env"
if _env_file_path.exists():
    load_dotenv(_env_file_path)
    print(f"[RSS] Loaded .env from {_env_file_path}")
else:
    print(f"[RSS] .env file not found at {_env_file_path}, using Docker environment")

# Validate critical env vars
_supabase_url = os.getenv("SUPABASE_URL", "").strip()
_supabase_key = os.getenv("SUPABASE_KEY", "").strip()
if not _supabase_url or not _supabase_key:
    print(f"[RSS] WARNING: Missing SUPABASE env vars. URL={bool(_supabase_url)}, KEY={bool(_supabase_key)}")

NEWSAPI_URL = "https://newsapi.org/v2/everything"


def _newsapi_key() -> str:
    return os.getenv("NEWSAPI_KEY", "").strip()


def _newsapi_lookback_days() -> int:
    return int(os.getenv("NEWSAPI_LOOKBACK_DAYS", "30"))


def _newsapi_max_stocks() -> int:
    return int(os.getenv("NEWSAPI_MAX_STOCKS", "15"))


def _newsapi_page_size() -> int:
    return int(os.getenv("NEWSAPI_PAGE_SIZE", "8"))


def _newsapi_request_delay_sec() -> float:
    return float(os.getenv("NEWSAPI_REQUEST_DELAY_SEC", "0.6"))


def _newsapi_max_retries() -> int:
    return int(os.getenv("NEWSAPI_MAX_RETRIES", "2"))


def _newsapi_backoff_sec() -> float:
    return float(os.getenv("NEWSAPI_BACKOFF_SEC", "2.0"))

# ─────────────────────────────────────────────
#  SUPABASE CLIENT (singleton)
# ─────────────────────────────────────────────
_client_instance = None

def _client() -> Client:
    """Create or reuse Supabase client singleton."""
    global _client_instance
    if _client_instance is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in .env file")
        _client_instance = create_client(url, key)
    return _client_instance


def _get_headers() -> dict:
    """Get headers for direct REST API calls."""
    key = os.getenv("SUPABASE_KEY", "").strip()
    if not key:
        raise ValueError("SUPABASE_KEY environment variable is not set or empty")
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "apikey": key,
    }


def _url(table: str) -> str:
    """Build Supabase REST API URL."""
    base_url = os.getenv("SUPABASE_URL")
    return f"{base_url}/rest/v1/{table}"


# ─────────────────────────────────────────────
#  LOAD RSS FEEDS FROM SUPABASE
# ─────────────────────────────────────────────
def load_rss_feeds() -> list:
    """Load active RSS feeds from Supabase rss_feeds table."""
    try:
        response = requests.get(
            _url("rss_feeds") + "?is_active=eq.true&select=id,name,url,category",
            headers=_get_headers(),
            timeout=10
        )
        if response.status_code == 200:
            feeds = response.json()
            print(f"[RSS] Loaded {len(feeds)} active feeds from Supabase")
            return feeds
        else:
            print(f"[RSS] ❌ Failed to load feeds: {response.status_code}")
            return []
    except Exception as e:
        print(f"[RSS] ❌ Exception loading feeds: {e}")
        return []


# ─────────────────────────────────────────────
#  LOAD EXISTING LINKS (for deduplication)
# ─────────────────────────────────────────────
def load_existing_links(hours_back: int = 168) -> set:
    """Load recent article links from rss_pool for deduplication.
    
    Only loads links from the last N hours (default 168 = 7 days) to
    avoid unbounded memory growth. Older articles are already pruned
    by prune_old_news so they won't reappear in feeds.
    """
    try:
        from datetime import datetime, timezone, timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours_back)).isoformat()
        
        all_links = set()
        page      = 0
        page_size = 1000
        max_pages = 100

        while page < max_pages:
            response = requests.get(
                _url("rss_pool") + f"?select=link&gte=created_at,{cutoff}&limit={page_size}&offset={page * page_size}",
                headers=_get_headers(),
                timeout=15
            )
            if response.status_code != 200:
                break
            rows = response.json()
            if not rows:
                break
            all_links.update(r["link"] for r in rows)
            if len(rows) < page_size:
                break
            page += 1

        print(f"[RSS] Loaded {len(all_links)} existing links for dedup (last {hours_back}h)")
        return all_links

    except Exception as e:
        print(f"[RSS] Exception loading existing links: {e}")
        return set()


# ─────────────────────────────────────────────
#  PARSE RSS XML
# ─────────────────────────────────────────────
def _parse_rss(xml_text: str) -> list:
    """Parse RSS/Atom XML and return list of items."""
    items = []
    try:
        root = ET.fromstring(xml_text)
        ns   = {"atom": "http://www.w3.org/2005/Atom"}

        # ── RSS 2.0 ──────────────────────────────
        for item in root.findall(".//item"):
            title   = item.findtext("title",       "").strip()
            link    = item.findtext("link",         "").strip()
            summary = item.findtext("description", "").strip()
            pubdate = item.findtext("pubDate",      "").strip()

            # Clean HTML from summary
            if "<" in summary:
                import re
                summary = re.sub(r"<[^>]+>", "", summary).strip()

            if link:
                items.append({
                    "title":   title[:500],
                    "link":    link[:1000],
                    "summary": summary[:2000],
                    "pubDate": pubdate,
                })

        # ── Atom feed ────────────────────────────
        if not items:
            for entry in root.findall(".//atom:entry", ns):
                title   = entry.findtext("atom:title",   "", ns).strip()
                summary = entry.findtext("atom:summary", "", ns).strip()
                pubdate = entry.findtext("atom:updated", "", ns).strip()
                link    = ""
                link_el = entry.find("atom:link", ns)
                if link_el is not None:
                    link = link_el.get("href", "").strip()

                if link:
                    items.append({
                        "title":   title[:500],
                        "link":    link[:1000],
                        "summary": summary[:2000],
                        "pubDate": pubdate,
                    })

    except ET.ParseError as e:
        print(f"[RSS] ❌ XML parse error: {e}")

    return items


# ─────────────────────────────────────────────
#  FETCH ONE FEED
# ─────────────────────────────────────────────
def _fetch_feed(feed: dict, existing_links: set) -> tuple[list, int]:
    """
    Fetch and parse one RSS feed.
    Returns (new_articles, skipped_count)
    """
    url        = feed["url"]
    source     = feed["name"]
    rss_id     = feed["id"]
    new_articles = []
    skipped    = 0

    try:
        headers = {"User-Agent": "Mozilla/5.0 NewsBot/1.0"}
        response = requests.get(
            url,
            timeout=15,
            headers=headers,
            allow_redirects=True
        )

        # Some sources return 426 (Upgrade Required) for plain HTTP URLs.
        if response.status_code == 426 and url.startswith("http://"):
            upgraded_url = "https://" + url[len("http://") :]
            print(f"[RSS] ⚠️  {source} — HTTP 426, retrying with HTTPS URL")
            response = requests.get(
                upgraded_url,
                timeout=15,
                headers=headers,
                allow_redirects=True
            )

        if response.status_code != 200:
            print(f"[RSS] ❌ {source} — HTTP {response.status_code} {response.text[:160]}")
            return [], 0

        items = _parse_rss(response.text)

        for item in items:
            link = item["link"].strip()
            if not link:
                continue
            if link in existing_links:
                skipped += 1
                continue

            existing_links.add(link)  # mark as seen
            new_articles.append({
                "title":          item["title"],
                "link":           link,
                "summary":        item["summary"],
                "published_date": item["pubDate"],
                "source":         source,
                "rss_id":         rss_id,
            })

        print(f"[RSS] {source} — {len(new_articles)} new, {skipped} skipped")

    except requests.Timeout:
        print(f"[RSS] ❌ {source} — Timeout")
    except Exception as e:
        print(f"[RSS] ❌ {source} — {e}")

    return new_articles, skipped


def load_nse_stocks(limit: int | None = None) -> list[dict]:
    """
    Load the curated NewsAPI stock universe from JSON.
    Handles missing nullable fields by normalizing to empty strings.
    """
    if limit is None:
        limit = _newsapi_max_stocks()

    try:
        with open(NEWSAPI_SYMBOLS_PATH, encoding="utf-8") as f:
            rows = json.load(f)

        stocks = []
        for row in rows[:limit]:
            ticker = (row.get("symbol") or row.get("ticker") or "").strip().upper()
            if not ticker:
                continue
            stocks.append({
                "ticker": ticker,
                "company_name": (row.get("company_name") or "").strip(),
                "industry": (row.get("industry") or "").strip(),
                "series": (row.get("series") or "").strip(),
                "isin_code": (row.get("isin_code") or row.get("isin") or "").strip(),
            })

        print(f"[NewsAPI] Loaded {len(stocks)} stocks from newsapi_symbols.json")
        return stocks
    except Exception as e:
        print(f"[NewsAPI] ❌ Exception loading newsapi_symbols.json: {e}")
        return []


def _newsapi_query(stock: dict) -> str:
    """Build a plain NewsAPI query: company name (fallback: ticker)."""
    ticker = stock["ticker"]
    company = stock.get("company_name", "")

    if company:
        return company
    return ticker


def _normalize_newsapi_article(article: dict, stock: dict) -> dict | None:
    """
    Convert NewsAPI payload to rss_pool row format.
    Returns None when essential fields are missing.
    """
    title = (article.get("title") or "").strip()
    summary = (article.get("description") or article.get("content") or "").strip()
    link = (article.get("url") or "").strip()
    published = (article.get("publishedAt") or "").strip()

    # Missing values handling: keep only records with minimum required fields.
    if not title or not link:
        return None

    source_obj = article.get("source") or {}
    source_name = (source_obj.get("name") or "NewsAPI").strip()
    ticker = stock.get("ticker", "")

    return {
        "title": f"[{ticker}] {title}"[:500],
        "link": link[:1000],
        "summary": (summary or f"News article related to {ticker}")[:2000],
        "published_date": published,
        "source": source_name[:120],
        "rss_id": None,
    }


def fetch_newsapi_equity_articles(existing_links: set) -> tuple[list, int, int]:
    """
    Fetch equity news from NewsAPI for symbols in newsapi_symbols.json.
    Filters to last NEWSAPI_LOOKBACK_DAYS days.
    Returns (new_articles, skipped_duplicates, failed_stocks).
    """
    newsapi_key = _newsapi_key()
    if not newsapi_key:
        print("[NewsAPI] Skipped: NEWSAPI_KEY not configured")
        return [], 0, 0

    stocks = load_nse_stocks()
    if not stocks:
        return [], 0, 0

    new_articles: list[dict] = []
    skipped = 0
    failed = 0

    request_delay = _newsapi_request_delay_sec()
    max_retries = _newsapi_max_retries()
    base_backoff = _newsapi_backoff_sec()

    for stock in stocks:
        params = {
            "q": _newsapi_query(stock),
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": _newsapi_page_size(),
            "apiKey": newsapi_key,
        }
        try:
            response = None
            for attempt in range(max_retries + 1):
                response = requests.get(NEWSAPI_URL, params=params, timeout=20)

                if response.status_code != 429:
                    break

                retry_after_header = response.headers.get("Retry-After", "").strip()
                if retry_after_header.isdigit():
                    wait_sec = float(retry_after_header)
                else:
                    wait_sec = base_backoff * (2 ** attempt)

                if attempt < max_retries:
                    print(
                        f"[NewsAPI] ⚠️  {stock['ticker']} — HTTP 429, "
                        f"retrying in {wait_sec:.1f}s (attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(wait_sec)

            if response is None or response.status_code != 200:
                failed += 1
                code = response.status_code if response is not None else "NO_RESPONSE"
                details = ""
                if response is not None:
                    details = f" {response.text[:160]}"
                print(f"[NewsAPI] ❌ {stock['ticker']} — HTTP {code}{details}")
                time.sleep(request_delay)
                continue

            payload = response.json() or {}
            rows = payload.get("articles") or []
            stock_new = 0

            for row in rows:
                normalized = _normalize_newsapi_article(row, stock)
                if not normalized:
                    continue

                link = normalized["link"]
                if link in existing_links:
                    skipped += 1
                    continue

                existing_links.add(link)
                new_articles.append(normalized)
                stock_new += 1

            print(f"[NewsAPI] {stock['ticker']} — {stock_new} new")
            time.sleep(request_delay)
        except Exception as e:
            failed += 1
            print(f"[NewsAPI] ❌ {stock['ticker']} — {e}")
            time.sleep(request_delay)

    print(
        f"[NewsAPI] Done — {len(new_articles)} new, {skipped} skipped, "
        f"{failed} stock queries failed"
    )
    return new_articles, skipped, failed


# ─────────────────────────────────────────────
#  SAVE ARTICLES TO SUPABASE
# ─────────────────────────────────────────────
def _save_new_articles(articles: list) -> int:
    """Save new articles to rss_pool in batches. Returns count saved."""
    if not articles:
        return 0
    
    # ✅ Explicitly set created_at for each article (timezone-aware UTC)
    now_utc = datetime.now(timezone.utc).isoformat()
    for article in articles:
        if "created_at" not in article:
            article["created_at"] = now_utc
    
    total_saved = 0
    batch_size = 50  # Smaller batches reduce conflict likelihood
    
    for i in range(0, len(articles), batch_size):
        batch = articles[i:i + batch_size]
        try:
            response = requests.post(
                _url("rss_pool"),
                headers={**_get_headers(),
                         "Prefer": "return=minimal"},
                json=batch,
                timeout=20
            )
            
            # 409 means conflicts exist - that's OK, some were saved
            if response.status_code in (200, 201):
                total_saved += len(batch)
                print(f"[RSS] ✅ Saved batch {i//batch_size + 1}: {len(batch)} articles")
            elif response.status_code == 409:
                # Partial save on conflict - count what was saved
                total_saved += len(batch)
                print(f"[RSS] ⚠️  Batch {i//batch_size + 1} had conflicts, partial save: {len(batch)} attempted")
            else:
                print(f"[RSS] ❌ Batch {i//batch_size + 1} save failed: {response.status_code}")
        except Exception as e:
            print(f"[RSS] ❌ Batch {i//batch_size + 1} exception: {e}")
    
    print(f"[RSS] ✅ Total saved to rss_pool: {total_saved} articles")
    return total_saved


# ─────────────────────────────────────────────
#  LOG TO DATABASE
# ─────────────────────────────────────────────
def _log_to_pool_logs(result: dict):
    """Log fetch results to pool_logs table."""
    try:
        client = _client()
        log_entry = {
            "rss_id": None,
            "source": "ALL FEEDS",
            "status": "SUCCESS",
            "new_items": result.get("total_new", 0),
            "skipped": result.get("total_skipped", 0),
            "total_pool": result.get("total_pool", 0),
            "message": result.get("message", ""),
            "created_at": datetime.utcnow().isoformat(),
        }
        client.table("pool_logs").insert(log_entry).execute()
        print(f"[RSS] ✅ Logged to pool_logs")
    except Exception as e:
        print(f"[RSS] ⚠️  Could not log to pool_logs: {e}")


# ─────────────────────────────────────────────
#  MAIN RUNNER
# ─────────────────────────────────────────────
def fetch_all_feeds() -> dict:
    """
    Fetch all active RSS feeds, deduplicate, save to Supabase.
    Returns summary dict.
    """
    print(f"\n[RSS] ═══ Starting RSS fetch at {datetime.utcnow().strftime('%H:%M:%S')} ═══")

    # Keep rss_pool lean before dedup and fetch.
    news.prune_old_news(days=7)

    feeds = load_rss_feeds()
    if not feeds:
        print("[RSS] No active RSS feeds found in rss_feeds table; continuing with NewsAPI only")

    existing_links = load_existing_links()

    all_new_articles = []
    feed_results     = []

    # ── Fetch equity news from NewsAPI first (last 30 days) ────────
    newsapi_articles, newsapi_skipped, newsapi_failed = fetch_newsapi_equity_articles(existing_links)
    if newsapi_articles or newsapi_skipped or newsapi_failed:
        all_new_articles.extend(newsapi_articles)
        feed_results.append({
            "source": "NewsAPI (newsapi_symbols.json)",
            "new": len(newsapi_articles),
            "skipped": newsapi_skipped,
            "failed_stocks": newsapi_failed,
        })

    # ── Then fetch classic RSS feeds ────────────────────────────────
    for feed in feeds:
        new_articles, skipped = _fetch_feed(feed, existing_links)
        all_new_articles.extend(new_articles)
        feed_results.append({
            "source":   feed["name"],
            "new":      len(new_articles),
            "skipped":  skipped,
        })

    # ── Save all new articles to Supabase ────
    saved = _save_new_articles(all_new_articles)

    # Enforce one-week retention after inserts too.
    news.prune_old_news(days=7)

    # ── Calculate totals ─────────────────────
    total_new = sum(r["new"] for r in feed_results)
    total_skip = sum(r["skipped"] for r in feed_results)
    total_pool = len(existing_links) + saved

    # ── Log to pool_logs ─────────────────────
    result = {
        "status": "success",
        "feeds_fetched": len(feeds),
        "total_new": total_new,
        "total_skipped": total_skip,
        "saved_to_db": saved,
        "total_pool": total_pool,
        "message": f"Fetched {len(feeds)} feeds. New: {total_new}, Skipped: {total_skip}",
        "feed_results": feed_results,
    }

    _log_to_pool_logs(result)

    print(f"[RSS] ═══ Done — {total_new} new articles from {len(feeds)} feeds ═══\n")
    return result
