import os
import hashlib
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
NEWS_RETENTION_DAYS = int(os.getenv("NEWS_RETENTION_DAYS", "7"))

# ─── SUPABASE CLIENT ──────────────────────────────────────────────────────────

def _client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in .env file")
    return create_client(url, key)


def _parse_datetime(value: str | None) -> datetime | None:
    """Best-effort parser for ISO8601 and RSS-style dates."""
    if not value:
        return None

    text = value.strip()
    if not text:
        return None

    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        pass

    try:
        return parsedate_to_datetime(text)
    except (TypeError, ValueError, IndexError):
        return None


def _to_utc_naive(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.astimezone().replace(tzinfo=None)
    return value


def prune_old_news(days: int = NEWS_RETENTION_DAYS) -> int:
    """
    Delete rows older than `days` from rss_pool based on published_date.
    Falls back to created_at when published_date is missing/unparseable.
    Returns number of deleted rows (best effort).
    """
    cutoff = datetime.utcnow() - timedelta(days=days)
    try:
        client = _client()
        response = (
            client.table("rss_pool")
            .select("id, published_date, created_at")
            .execute()
        )
        rows = response.data or []

        old_ids = []
        for row in rows:
            published_at = _to_utc_naive(_parse_datetime(row.get("published_date")))
            created_at = _to_utc_naive(_parse_datetime(row.get("created_at")))
            effective_date = published_at or created_at
            if effective_date and effective_date < cutoff:
                old_ids.append(row["id"])

        deleted = 0
        for start in range(0, len(old_ids), 500):
            batch_ids = old_ids[start:start + 500]
            delete_response = (
                client.table("rss_pool")
                .delete()
                .in_("id", batch_ids)
                .execute()
            )
            deleted += len(delete_response.data or [])

        print(f"[news] retention cleanup: removed {deleted} rows older than {days} days")
        return deleted
    except Exception as e:
        print(f"[news] retention cleanup failed: {e}")
        return 0


# ─── FETCH ────────────────────────────────────────────────────────────────────

def fetch_today(hours_back: int = 24) -> list[dict]:
    """
    Fetch articles from rss_pool created in the last `hours_back` hours.
    Maps Supabase columns → pipeline article format.

    rss_pool columns used:
      id, title, link, summary, published_date, source, created_at
    """
    since = (datetime.utcnow() - timedelta(hours=hours_back)).isoformat()

    client = _client()

    response = (
        client.table("rss_pool")
        .select("id, title, link, summary, published_date, source, created_at")
        .gte("created_at", since)
        .order("created_at", desc=True)
        .execute()
    )

    rows = response.data or []
    print(f"[news] fetched {len(rows)} articles from Supabase (last {hours_back}hr)")

    articles = []
    for row in rows:
        title       = (row.get("title") or "").strip()
        description = (row.get("summary") or "").strip()

        if not title:
            continue  # skip empty titles

        # build consistent hash (same logic as tier1.py dedup)
        text = (title + description).lower()
        h    = hashlib.sha256(text.encode()).hexdigest()[:16]

        articles.append({
            "hash":           h,
            "title":          title,
            "description":    description,
            "link":           row.get("link", ""),
            "source":         row.get("source", ""),
            "published_date": row.get("published_date", ""),
            "created_at":     row.get("created_at", ""),
            "supabase_id":    row.get("id"),
        })

    print(f"[news] {len(articles)} valid articles after cleaning")
    return articles


def fetch_by_source(source: str, hours_back: int = 24) -> list[dict]:
    """Fetch articles from a specific source only."""
    since = (datetime.utcnow() - timedelta(hours=hours_back)).isoformat()

    client = _client()

    response = (
        client.table("rss_pool")
        .select("id, title, link, summary, published_date, source, created_at")
        .eq("source", source)
        .gte("created_at", since)
        .order("created_at", desc=True)
        .execute()
    )

    rows = response.data or []
    print(f"[news] fetched {len(rows)} articles from source='{source}'")
    return rows


def fetch_latest(limit: int = 100) -> list[dict]:
    """Fetch the most recent N articles regardless of time."""
    client = _client()

    response = (
        client.table("rss_pool")
        .select("id, title, link, summary, published_date, source, created_at")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    rows = response.data or []
    print(f"[news] fetched latest {len(rows)} articles")
    return rows


def count_today(hours_back: int = 24) -> int:
    """Quick count of articles available — useful before starting pipeline."""
    since = (datetime.utcnow() - timedelta(hours=hours_back)).isoformat()
    client = _client()

    response = (
        client.table("rss_pool")
        .select("id", count="exact")
        .gte("created_at", since)
        .execute()
    )
    return response.count or 0
