from datetime import datetime
from core import cache
from core import price_impact
from tiers import tier1
from tiers import tier2
from tiers import tier3


def _has_bad_cached_causes(result: dict) -> bool:
    rows = result.get("results") or []
    for row in rows:
        cause = (row.get("cause") or "").lower()
        if "parse error" in cause or "check logs" in cause:
            return True
    return False


def _sentiment_score(results: list[dict]) -> float:
    """Weighted sentiment score 0-10."""
    if not results:
        return 5.0
    weight = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    total_w, total_s = 0, 0
    for r in results:
        w = weight.get(r.get("impact", "LOW"), 1)
        d = r.get("direction", "NEUTRAL")
        s = 7 if d == "BULLISH" else 3 if d == "BEARISH" else 5
        total_w += w
        total_s += w * s
    return round(total_s / total_w, 1) if total_w else 5.0


def _overall_direction(score: float) -> str:
    if score >= 6.0:
        return "BULLISH"
    if score <= 4.0:
        return "BEARISH"
    return "NEUTRAL"


def run(articles: list[dict], equity: dict) -> dict:
    """
    Full pipeline for one equity.
    Returns structured analysis result.
    """
    symbol = equity["symbol"]
    print(f"\n{'='*60}")
    print(f"[pipeline] Starting: {symbol}")
    print(f"{'='*60}")

    # check equity-level cache first
    eq_key = cache.equity_key(symbol)
    cached = cache.get(eq_key)
    if cached:
        if _has_bad_cached_causes(cached):
            print(f"[pipeline] CACHE BYPASS for {symbol} — stale fallback causes detected")
        else:
            print(f"[pipeline] CACHE HIT for {symbol} — returning cached result")
            cached["cache_status"] = "hit"
            return cached

    start = datetime.now()

    # ── Tier 1: free filter ──────────────────────────────────────────
    t1_results = tier1.run(articles, equity)
    if not t1_results:
        print(f"[pipeline] No articles survived Tier 1 for {symbol}")
        return {"symbol": symbol, "error": "no relevant articles", "results": []}

    # ── Tier 2: relevance scoring ────────────────────────────────────
    t2_results = tier2.run(t1_results, equity)
    if not t2_results:
        print(f"[pipeline] No articles passed Tier 2 threshold for {symbol}")
        return {"symbol": symbol, "error": "no articles above threshold", "results": []}

    # ── Tier 3: deep analysis ────────────────────────────────────────
    t3_results = tier3.run(t2_results, equity)

    # ── Price impact estimation (rule-based, no beta) ───────────────
    t3_results, impact_summary = price_impact.apply(t3_results)

    # ── Build output ─────────────────────────────────────────────────
    sentiment = _sentiment_score(t3_results)
    elapsed   = round((datetime.now() - start).total_seconds(), 1)

    output = {
        "symbol":            symbol,
        "timestamp":         datetime.now().isoformat(),
        "cache_status":      "fresh",
        "elapsed_sec":       elapsed,
        "articles_input":    len(articles),
        "articles_analyzed": len(t3_results),
        "sentiment_score":   sentiment,
        "overall_direction": _overall_direction(sentiment),
        "price_impact":      impact_summary,
        "results":           t3_results,
    }

    # store in equity cache (shared across all users for TTL window)
    cache.set(eq_key, "equity", output)

    print(f"[pipeline] {symbol} done in {elapsed}s | "
          f"sentiment={sentiment} | direction={output['overall_direction']}")
    return output
