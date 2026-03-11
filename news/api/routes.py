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
from db.supabase_logger        import (
    check_connection, save_nse_stocks,
    log_l1, log_l2, log_l3
)
from api.rss_fetcher import fetch_all_feeds

app = Flask(__name__)

_kg_loaded  = False
_nse_stocks = []


# ─────────────────────────────────────────────
#  STARTUP — load stocks from Supabase
# ─────────────────────────────────────────────
def _load_stocks_from_supabase():
    """Load NSE stocks into Layer 2 knowledge graph at startup."""
    global _kg_loaded, _nse_stocks
    try:
        import requests as req
        from db.supabase_logger import _get_headers, _url
        response = req.get(
            _url("nse_stocks") + "?select=ticker,company_name,industry&limit=2000",
            headers=_get_headers(),
            timeout=15
        )
        if response.status_code == 200:
            stocks = response.json()
            if stocks:
                # Normalize to expected format
                normalized = [{
                    "Symbol":       s["ticker"],
                    "Company Name": s["company_name"],
                    "Industry":     s["industry"],
                } for s in stocks]
                load_knowledge_graph(normalized)
                _kg_loaded  = True
                _nse_stocks = normalized
                print(f"[KG] ✅ Loaded {len(stocks)} stocks from Supabase at startup")
            else:
                print("[KG] ⚠️ No stocks in Supabase yet — run /api/load-stocks first")
        else:
            print(f"[KG] ❌ Failed to load stocks: {response.status_code}")
    except Exception as e:
        print(f"[KG] ❌ Startup stock load failed: {e}")


# ─────────────────────────────────────────────
#  PIPELINE RUNNER
# ─────────────────────────────────────────────
def _run_pipeline(articles: list) -> dict:
    """Run L1 → L2 → L3 on a list of articles."""
    if not articles:
        return {"layer1_relevant": 0, "layer2_enriched": 0,
                "layer3_predicted": 0, "profiles": []}

    # ── Layer 1 ──────────────────────────────
    l1_profiles = []
    for article in articles:
        try:
            profile = build_unified_profile(article)
            if profile["novelty"]["is_duplicate"]:
                continue
            if profile["is_financially_relevant"]:
                l1_profiles.append(profile)
        except Exception as e:
            print(f"[ERROR] L1 failed for {article.get('id')}: {e}")

    l1_profiles.sort(key=lambda x: x["relevance_score"], reverse=True)
    threading.Thread(target=log_l1, args=(l1_profiles,), daemon=True).start()

    # ── Layer 2 ──────────────────────────────
    l2_profiles = run_layer2(l1_profiles)
    threading.Thread(target=log_l2, args=(l2_profiles,), daemon=True).start()

    # ── Layer 3 ──────────────────────────────
    l3_profiles = run_layer3(l2_profiles)
    threading.Thread(target=log_l3, args=(l3_profiles,), daemon=True).start()

    return {
        "layer1_relevant":  len(l1_profiles),
        "layer2_enriched":  len(l2_profiles),
        "layer3_predicted": len(l3_profiles),
        "profiles":         l3_profiles,
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
    from db.supabase_logger import _get_headers, _url
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
#  STARTUP
# ─────────────────────────────────────────────
with app.app_context():
    check_connection()
    _load_stocks_from_supabase()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", debug=False, port=port)