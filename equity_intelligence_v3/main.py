import json
import os
from config.config import EQUITIES_PATH

from core import cache
from core import budget
from core import pipeline
from ingestion import news
from ingestion import equity_sync


def load_equities() -> list[dict]:
    with open(EQUITIES_PATH) as f:
        return json.load(f)


def print_results(result: dict):
    print(f"\n{'═'*70}")
    print(f"  EQUITY    : {result.get('symbol')}")
    print(f"  DIRECTION : {result.get('overall_direction')}")
    print(f"  SENTIMENT : {result.get('sentiment_score')} / 10")
    print(f"  ARTICLES  : {result.get('articles_analyzed')} analyzed")
    print(f"  STATUS    : {result.get('cache_status')}")
    print(f"{'─'*70}")

    for r in result.get("results", []):
        print(f"\n  TITLE     : {r.get('title', 'N/A')}")
        print(f"  IMPACT    : {r.get('impact','?')}  |  "
              f"DIRECTION: {r.get('direction','?')}  |  "
              f"CONFIDENCE: {r.get('confidence','?')}  |  "
              f"HORIZON: {r.get('horizon','?')}")
        print(f"  CAUSE     : {r.get('cause', 'N/A')}")
        print(f"  {'·'*66}")
    print()


def main():
    # ── setup ────────────────────────────────────────────────────────
    os.makedirs("db",   exist_ok=True)
    os.makedirs("data", exist_ok=True)
    cache.init()
    cache.purge_expired()

    # Keep only the latest one week of news in rss_pool.
    news.prune_old_news(days=7)

    # ── fetch articles from Supabase ─────────────────────────────────
    total_available = news.count_today(hours_back=24)
    print(f"\n[main] {total_available} articles available in Supabase today")

    articles = news.fetch_today(hours_back=24)

    if not articles:
        print("[main] No articles fetched. Check Supabase connection or rss_pool data.")
        return

    # ── load equities ────────────────────────────────────────────────
    equities = load_equities()
    print(f"[main] {len(equities)} equities | {len(articles)} articles")

    # ── sync equities to Supabase (generate missing profiles) ────────
    equity_sync.sync(EQUITIES_PATH)

    budget.summary()

    # ── sort: NIFTY50 first to warm sector cache ──────────────────────
    equities.sort(key=lambda e: (e.get("priority", 99), e["symbol"]))

    # ── run pipeline for each equity ──────────────────────────────────
    all_results = []
    for equity in equities:
        try:
            result = pipeline.run(articles, equity)
            all_results.append(result)
            print_results(result)
        except RuntimeError as e:
            print(f"\n[main] STOPPING: {e}")
            break
        except Exception as e:
            print(f"[main] ERROR on {equity['symbol']}: {e}")
            continue

    # ── final summary ─────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"[main] Completed {len(all_results)} equities")
    budget.summary()
    cache.stats()


if __name__ == "__main__":
    main()

