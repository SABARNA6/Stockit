"""
=====================================================================
  ingestion/rss_fetcher.py
  Fetches RSS feeds from Supabase, parses XML, deduplicates,
  saves new articles to Supabase rss_pool
=====================================================================
"""

import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client, Client
from ingestion import news

load_dotenv()

# ─────────────────────────────────────────────
#  SUPABASE CLIENT
# ─────────────────────────────────────────────
def _client() -> Client:
    """Create Supabase client."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in .env file")
    return create_client(url, key)


def _get_headers() -> dict:
    """Get headers for direct REST API calls."""
    key = os.getenv("SUPABASE_KEY")
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
def load_existing_links() -> set:
    """Load all existing article links from rss_pool for deduplication."""
    try:
        # Supabase pagination — load all links
        all_links = set()
        page      = 0
        page_size = 1000

        while True:
            response = requests.get(
                _url("rss_pool") + f"?select=link&limit={page_size}&offset={page * page_size}",
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

        print(f"[RSS] Loaded {len(all_links)} existing links for dedup")
        return all_links

    except Exception as e:
        print(f"[RSS] ❌ Exception loading existing links: {e}")
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
        response = requests.get(
            url,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0 NewsBot/1.0"},
            allow_redirects=True
        )
        if response.status_code != 200:
            print(f"[RSS] ❌ {source} — HTTP {response.status_code}")
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


# ─────────────────────────────────────────────
#  SAVE ARTICLES TO SUPABASE
# ─────────────────────────────────────────────
def _save_new_articles(articles: list) -> int:
    """Save new articles to rss_pool. Returns count saved."""
    if not articles:
        return 0
    try:
        response = requests.post(
            _url("rss_pool"),
            headers={**_get_headers(),
                     "Prefer": "resolution=ignore-duplicates,return=minimal"},
            json=articles,
            timeout=20
        )
        if response.status_code in (200, 201):
            print(f"[RSS] ✅ Saved {len(articles)} articles to rss_pool")
            return len(articles)
        else:
            print(f"[RSS] ❌ Save failed: {response.status_code} {response.text[:200]}")
            return 0
    except Exception as e:
        print(f"[RSS] ❌ Save exception: {e}")
        return 0


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
            "triggered_at": datetime.utcnow().isoformat(),
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
        return {
            "status": "error",
            "message": "No active feeds found in Supabase rss_feeds table",
            "feeds_fetched": 0,
            "total_new": 0,
            "total_skipped": 0,
        }

    existing_links = load_existing_links()

    all_new_articles = []
    feed_results     = []

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
