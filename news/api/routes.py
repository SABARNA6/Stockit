"""
api/routes.py
Complete Flask backend — no Apps Script needed
Triggered hourly by cron-job.org → /api/run
"""

from flask import Flask, request, jsonify
from datetime import datetime
import sys, os, threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from layers.layer1_content     import build_unified_profile
from layers.layer2_propagation import run_layer2, load_knowledge_graph
from layers.layer3_prediction  import run_layer3
from database.supabase_logger        import (
    check_connection, save_nse_stocks,
    log_l1
)
from api.rss_fetcher import fetch_all_feeds
from pipeline_optimizer import prefilter_articles, deduplicate_articles, get_next_chunk, save_progress, CHUNK_SIZE
from layers.layer4_reasoning import run_layer4

app = Flask(__name__)

_kg_loaded  = False
_nse_stocks = []


# ─────────────────────────────────────────────
#  STARTUP — load stocks from Supabase
# ─────────────────────────────────────────────
def _load_stocks_from_supabase():
    """Load NSE stocks into Layer 2 knowledge graph."""
    global _kg_loaded, _nse_stocks
    try:
        import requests as req
        from database.supabase_logger import _get_headers, _url

        all_stocks = []
        page_size  = 1000
        offset     = 0

        # Paginate — Supabase default limit is 1000
        while True:
            url      = _url("nse_stocks") + f"?select=ticker,company_name,industry&limit={page_size}&offset={offset}"
            response = req.get(url, headers=_get_headers(), timeout=15)

            print(f"[KG] Fetching stocks offset={offset} → HTTP {response.status_code}")

            if response.status_code != 200:
                print(f"[KG] ❌ Failed: {response.text[:200]}")
                break

            batch = response.json()
            if not batch:
                break

            all_stocks.extend(batch)
            if len(batch) < page_size:
                break
            offset += page_size

        if all_stocks:
            normalized = [{
                "Symbol":       s["ticker"],
                "Company Name": s.get("company_name", ""),
                "Industry":     s.get("industry", ""),
            } for s in all_stocks]
            load_knowledge_graph(normalized)
            _kg_loaded  = True
            _nse_stocks = normalized
            print(f"[KG] ✅ Loaded {len(all_stocks)} stocks from Supabase")
        else:
            print("[KG] ⚠️ No stocks found in nse_stocks table")
    except Exception as e:
        import traceback
        print(f"[KG] ❌ Failed: {e}")
        print(traceback.format_exc())


# ─────────────────────────────────────────────
#  PIPELINE RUNNER
# ─────────────────────────────────────────────
def _run_pipeline(articles: list) -> dict:
    """
    Run optimized L1 → L2 → L3 → L4 pipeline.
    Applies: pre-filter, dedup, chunking, batch sizing, L4 skipping
    """
    if not articles:
        return {"layer1_relevant": 0, "layer2_enriched": 0,
                "layer3_predicted": 0, "layer4_reasoned": 0,
                "dropped": 0, "duplicates": 0, "profiles": []}

    original_count = len(articles)

    # ── Strategy 1: Pre-filter non-financial ─
    articles, dropped = prefilter_articles(articles)

    # ── Strategy 2: Deduplicate similar news ─
    articles, dupes   = deduplicate_articles(articles)

    chunk      = articles   # process ALL articles
    start_idx  = 0
    print(f"[Pipeline] {original_count} → {len(articles)} after filter/dedup "
          f"→ processing all {len(chunk)}")

    # ── Layer 1 ──────────────────────────────
    l1_profiles = []
    for article in chunk:
        try:
            profile = build_unified_profile(article)
            if profile["novelty"]["is_duplicate"]:
                continue
            if profile["is_financially_relevant"]:
                l1_profiles.append(profile)
        except Exception as e:
            print(f"[ERROR] L1 failed for {article.get('id')}: {e}")

    l1_profiles.sort(key=lambda x: x["relevance_score"], reverse=True)
    log_l1(l1_profiles)

    # ── Layer 2 ──────────────────────────────
    l2_profiles = run_layer2(l1_profiles)

    # ── Layer 3 ──────────────────────────────
    l3_profiles = run_layer3(l2_profiles)

    # ── Layer 4 (IMMEDIATE + WATCH only) ─────
    l4_profiles = run_layer4(l3_profiles)

    # ── Save progress ─────────────────────────
    save_progress(
        index    = start_idx + len(chunk),
        total    = len(articles),
        relevant = len(l1_profiles),
        status   = "IN PROGRESS" if start_idx + len(chunk) < len(articles) else "COMPLETE"
    )

    return {
        "original":        original_count,
        "after_filter":    len(articles),
        "dropped":         dropped,
        "duplicates":      dupes,
        "chunk_size":      len(chunk),
        "layer1_relevant": len(l1_profiles),
        "layer2_enriched": len(l2_profiles),
        "layer3_predicted":len(l3_profiles),
        "layer4_reasoned": len(l4_profiles),
        "profiles":        l4_profiles,
    }


# ─────────────────────────────────────────────
#  GET /api/run  ← triggered by cron-job.org
#  Full pipeline: fetch RSS → L1 → L2 → L3
# ─────────────────────────────────────────────
@app.route("/api/run", methods=["GET", "POST"])
def run_pipeline():
    started_at = datetime.now()
    print(f"\n[RUN] ═══ Pipeline started at {started_at.strftime('%H:%M:%S')} ═══")

    # ── Step 1: Fetch RSS ─────────────────────
    rss_result = fetch_all_feeds()
    if "error" in rss_result:
        return jsonify({"status": "error", "message": rss_result["error"]}), 500

    new_articles = rss_result.get("articles", [])

    if not new_articles:
        return jsonify({
            "status":       "ok",
            "message":      "No new articles found",
            "feeds_fetched": rss_result.get("feeds_fetched", 0),
            "total_new":    0,
        })

    # ── Step 2: Run pipeline ──────────────────
    result = _run_pipeline(new_articles)

    elapsed = (datetime.now() - started_at).seconds
    print(f"[RUN] ═══ Done in {elapsed}s — "
          f"L1:{result['layer1_relevant']} "
          f"L2:{result['layer2_enriched']} "
          f"L3:{result['layer3_predicted']} ═══\n")

    return jsonify({
        "status":           "ok",
        "elapsed_seconds":  elapsed,
        "feeds_fetched":    rss_result.get("feeds_fetched", 0),
        "articles_fetched": rss_result.get("total_new", 0),
        "layer1_relevant":  result["layer1_relevant"],
        "layer2_enriched":  result["layer2_enriched"],
        "layer3_predicted": result["layer3_predicted"],
        "feed_results":     rss_result.get("feed_results", []),
    })


# ─────────────────────────────────────────────
#  POST /api/ingest  ← manual article push
#  (kept for Apps Script compatibility)
# ─────────────────────────────────────────────
@app.route("/api/ingest", methods=["POST"])
def ingest():
    body = request.get_json(force=True)
    if not body or "articles" not in body:
        return jsonify({"error": "Expected JSON with 'articles' key"}), 400

    articles = body.get("articles", [])
    result   = _run_pipeline(articles)

    return jsonify({
        "status":           "ok",
        "received":         len(articles),
        **result
    })


# ─────────────────────────────────────────────
#  POST /api/load-stocks  ← called by Apps Script
# ─────────────────────────────────────────────
@app.route("/api/load-stocks", methods=["POST"])
def load_stocks():
    global _kg_loaded, _nse_stocks
    body   = request.get_json(force=True)
    stocks = body.get("stocks", [])
    if not stocks:
        return jsonify({"error": "No stocks received"}), 400

    load_knowledge_graph(stocks)
    _kg_loaded  = True
    _nse_stocks = stocks
    threading.Thread(target=save_nse_stocks, args=(stocks,), daemon=True).start()
    print(f"[KG] ✅ Loaded {len(stocks)} stocks via /api/load-stocks")
    return jsonify({"status": "ok", "loaded": len(stocks)})


# ─────────────────────────────────────────────
#  POST /api/add-feed  ← add RSS feed to Supabase
# ─────────────────────────────────────────────
@app.route("/api/add-feed", methods=["POST"])
def add_feed():
    import requests as req
    from database.supabase_logger import _get_headers, _url
    body = request.get_json(force=True)
    name = body.get("name", "")
    url  = body.get("url",  "")
    if not name or not url:
        return jsonify({"error": "name and url required"}), 400

    response = req.post(
        _url("rss_feeds"),
        headers=_get_headers(),
        json={
            "name":      name,
            "url":       url,
            "category":  body.get("category", "news"),
            "country":   body.get("country", "IN"),
            "is_active": True,
        },
        timeout=10
    )
    if response.status_code in (200, 201):
        return jsonify({"status": "ok", "message": f"Feed '{name}' added"})
    return jsonify({"error": response.text}), 400


# ─────────────────────────────────────────────
#  GET /api/health
# ─────────────────────────────────────────────
@app.route("/api/health", methods=["GET"])
def health():
    sb_ok = check_connection()
    return jsonify({
        "status":         "running",
        "timestamp":      datetime.now().isoformat(),
        "supabase_ok":    sb_ok,
        "kg_loaded":      _kg_loaded,
        "kg_stocks":      len(_nse_stocks),
        "openrouter_set": bool(os.environ.get("OPENROUTER_API_KEY")),
        "gemini_set":     bool(os.environ.get("GEMINI_API_KEY")),
        "layers": {
            "layer1": "active",
            "layer2": "active (OpenRouter + Gemini fallback)",
            "layer3": "active (OpenRouter + Price API)",
            "layer4": "coming soon"
        }
    })


# ─────────────────────────────────────────────
#  STARTUP — lazy load on first request
#  Avoids env var timing issues on Render
# ─────────────────────────────────────────────
@app.before_request
def startup():
    global _kg_loaded
    # Skip heavy startup for lightweight endpoints
    if request.path in ("/api/health",) or request.path.startswith("/api/stock"):
        return
    if not _kg_loaded:
        check_connection()
        _load_stocks_from_supabase()




# ─────────────────────────────────────────────
#  GET /api/stock/<ticker>
#  Returns latest news + predictions for a stock
# ─────────────────────────────────────────────
@app.route("/api/stock/<ticker>", methods=["GET"])
def get_stock(ticker: str):
    import requests as req
    from database.supabase_logger import _get_headers, _url

    ticker  = ticker.upper().strip()
    hours   = int(request.args.get("hours", 24))
    limit   = int(request.args.get("limit", 20))
    since   = (datetime.now() - __import__('datetime').timedelta(hours=hours)).isoformat()

    def _fetch(table, extra_select="*"):
        r = req.get(
            _url(table) +
            f"?ticker=eq.{ticker}"
            f"&created_at=gte.{since}"
            f"&order=created_at.desc"
            f"&limit={limit}"
            f"&select={extra_select}",
            headers=_get_headers(), timeout=10
        )
        return r.json() if r.status_code == 200 else []

    # ── Try l4_logs first, fall back to l3_logs ──
    l4_rows = _fetch("l4_logs")
    l3_rows = _fetch("l3_logs") if not l4_rows else []
    l2_rows = _fetch("l2_logs", "news_id,news_title,impact_type,direction,confidence,reason,created_at")

    signal_rows = l4_rows or l3_rows
    data_source = "l4_logs" if l4_rows else ("l3_logs" if l3_rows else None)

    if not signal_rows:
        # Widen search to 7 days automatically
        since7 = (datetime.now() - __import__('datetime').timedelta(hours=168)).isoformat()
        def _fetch7(table, extra_select="*"):
            r = req.get(
                _url(table) +
                f"?ticker=eq.{ticker}"
                f"&created_at=gte.{since7}"
                f"&order=created_at.desc"
                f"&limit={limit}"
                f"&select={extra_select}",
                headers=_get_headers(), timeout=10
            )
            return r.json() if r.status_code == 200 else []

        l4_rows     = _fetch7("l4_logs")
        l3_rows     = _fetch7("l3_logs") if not l4_rows else []
        signal_rows = l4_rows or l3_rows
        data_source = "l4_logs(7d)" if l4_rows else ("l3_logs(7d)" if l3_rows else None)
        hours       = 168  # update for response

    if not signal_rows:
        return jsonify({
            "ticker":      ticker,
            "hours":       hours,
            "data_source": None,
            "message":     f"No data found for {ticker} — pipeline may not have processed relevant news yet",
            "signals":     []
        })

    l2_map = {str(r["news_id"]): r for r in l2_rows}

    merged = []
    for row in signal_rows:
        news_id = str(row.get("news_id", ""))
        l2      = l2_map.get(news_id, {})
        merged.append({
            "news_id":           row.get("news_id"),
            "news_title":        row.get("news_title"),
            "created_at":        row.get("created_at"),
            "impact_type":       l2.get("impact_type",  row.get("impact_type", "")),
            "impact_reason":     l2.get("reason", ""),
            "alert_priority":    row.get("alert_priority"),
            "direction":         row.get("direction"),
            "move_estimate_pct": row.get("move_estimate_pct"),
            "move_range":        {"low": row.get("move_range_low"), "high": row.get("move_range_high")},
            "confidence":        row.get("confidence"),
            "time_horizon":      row.get("time_horizon"),
            "current_price":     row.get("current_price"),
            "trend_8d_pct":      row.get("trend_8d_pct"),
            "volatility":        row.get("volatility"),
            "reasoning":         row.get("reasoning", row.get("l4_rationale", "")),
            "key_risks":         row.get("key_risks", ""),
            "l4_rationale":      row.get("l4_rationale", ""),
            "l4_flag":           row.get("l4_flag", ""),
            "reasoning_summary": row.get("reasoning_summary", ""),
        })

    immediate = [r for r in merged if r["alert_priority"] == "IMMEDIATE"]
    watch     = [r for r in merged if r["alert_priority"] == "WATCH"]
    bullish   = [r for r in merged if r["direction"] == "UP"]
    bearish   = [r for r in merged if r["direction"] == "DOWN"]

    return jsonify({
        "ticker":      ticker,
        "hours":       hours,
        "data_source": data_source,
        "summary": {
            "total_signals":   len(merged),
            "immediate":       len(immediate),
            "watch":           len(watch),
            "bullish_signals": len(bullish),
            "bearish_signals": len(bearish),
            "avg_confidence":  round(sum(r["confidence"] or 0 for r in merged) / len(merged), 2) if merged else 0,
        },
        "signals": merged
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", debug=False, port=port)