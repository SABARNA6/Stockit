"""
api/routes.py
Flask routes — Apps Script → Layer 1 → Layer 2 → Logs to Google Sheets via doPost
"""

from flask import Flask, request, jsonify
from datetime import datetime
import sys, os, json, threading, requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from layers.layer1_content     import build_unified_profile
from layers.layer2_propagation import run_layer2, load_knowledge_graph

app = Flask(__name__)

# ─────────────────────────────────────────────
#  STATE
# ─────────────────────────────────────────────
_kg_loaded  = False
_nse_stocks = []


# ─────────────────────────────────────────────
#  APPSCRIPT WEBHOOK
#  Read inside function — not at module load time
#  so Render env vars are always available
# ─────────────────────────────────────────────
def _get_webhook():
    return os.environ.get("APPSCRIPT_WEBHOOK_URL")


def _post_to_appscript(payload: dict):
    webhook = _get_webhook()   # ← read fresh every time
    if not webhook:
        print("[LOG] ❌ APPSCRIPT_WEBHOOK_URL not set in Render env vars")
        return
    try:
        r = requests.post(webhook, json=payload, timeout=30, allow_redirects=True)
        print(f"[LOG] ✅ Apps Script responded: {r.status_code}")
    except Exception as e:
        print(f"[LOG] ❌ Failed to post to Apps Script: {e}")


# ─────────────────────────────────────────────
#  LOG LAYER 1  →  L1_Logs sheet via doPost
# ─────────────────────────────────────────────
def _log_l1(profiles: list):
    if not profiles:
        return
    ts   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = [
        [
            ts,
            p.get("id", ""),
            p.get("title", "")[:100],
            ", ".join(e["ticker"] for e in p.get("entities", [])) or "—",
            p.get("event", {}).get("event_type", ""),
            p.get("sentiment", {}).get("label", ""),
            p.get("sentiment", {}).get("urgency_score", 0),
            p.get("relevance_score", 0),
            p.get("source", ""),
        ]
        for p in profiles
    ]
    threading.Thread(
        target=_post_to_appscript,
        args=({"type": "l1_logs", "rows": rows},),
        daemon=True
    ).start()


# ─────────────────────────────────────────────
#  LOG LAYER 2  →  L2_Logs sheet via doPost
# ─────────────────────────────────────────────
def _log_l2(profiles: list):
    if not profiles:
        return
    ts   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = []
    for p in profiles:
        for e in p.get("affected_entities", []):
            rows.append([
                ts,
                p.get("id", ""),
                p.get("title", "")[:100],
                e.get("ticker", ""),
                e.get("name", ""),
                e.get("industry", ""),
                e.get("impact_type", ""),
                e.get("direction", ""),
                e.get("confidence", 0),
                e.get("reason", "")[:150],
                e.get("sentiment", ""),
            ])
    if rows:
        threading.Thread(
            target=_post_to_appscript,
            args=({"type": "l2_logs", "rows": rows},),
            daemon=True
        ).start()


# ─────────────────────────────────────────────
#  POST /api/load-stocks
#  Called by Apps Script syncStocksToFlask()
# ─────────────────────────────────────────────
@app.route("/api/load-stocks", methods=["POST"])
def load_stocks():
    global _kg_loaded, _nse_stocks        # ← Bug 2 fix
    body   = request.get_json(force=True)
    stocks = body.get("stocks", [])
    if not stocks:
        return jsonify({"error": "No stocks received"}), 400

    load_knowledge_graph(stocks)
    _kg_loaded  = True                    # ← Bug 2 fix
    _nse_stocks = stocks
    print(f"[KG] ✅ Loaded {len(stocks)} stocks via /api/load-stocks")
    return jsonify({"status": "ok", "loaded": len(stocks)})


# ─────────────────────────────────────────────
#  POST /api/ingest
#  Called by Apps Script after every RSS fetch
# ─────────────────────────────────────────────
@app.route("/api/ingest", methods=["POST"])
def ingest():
    body = request.get_json(force=True)
    if not body or "articles" not in body:
        return jsonify({"error": "Expected JSON with 'articles' key"}), 400

    articles = body.get("articles", [])
    if not articles:
        return jsonify({"status": "ok", "message": "No articles received", "count": 0})

    # ── Layer 1 : NLP ────────────────────────
    l1_profiles = []
    for article in articles:
        try:
            profile = build_unified_profile(article)
            if profile["novelty"]["is_duplicate"]:
                continue
            if profile["is_financially_relevant"]:
                l1_profiles.append(profile)
        except Exception as e:
            print(f"[ERROR] Layer1 failed for article {article.get('id')}: {e}")

    l1_profiles.sort(key=lambda x: x["relevance_score"], reverse=True)

    # ── Log L1 (background, non-blocking) ────
    _log_l1(l1_profiles)

    # ── Layer 2 : Gemini ─────────────────────
    l2_profiles = run_layer2(l1_profiles)

    # ── Log L2 (background, non-blocking) ────
    _log_l2(l2_profiles)

    print(f"[INGEST] {datetime.now().strftime('%H:%M:%S')} | "
          f"In: {len(articles)} | L1: {len(l1_profiles)} | L2: {len(l2_profiles)}")

    return jsonify({
        "status":          "ok",
        "received":        len(articles),
        "layer1_relevant": len(l1_profiles),
        "layer2_enriched": len(l2_profiles),
        "profiles":        l2_profiles
    })


# ─────────────────────────────────────────────
#  GET /api/health
# ─────────────────────────────────────────────
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status":       "running",
        "timestamp":    datetime.now().isoformat(),
        "kg_loaded":    _kg_loaded,
        "kg_stocks":    len(_nse_stocks),
        "webhook_set":  bool(_get_webhook()),   # ← shows if webhook is configured
        "gemini_set":   bool(os.environ.get("GEMINI_API_KEY")),
        "layers": {
            "layer1": "active",
            "layer2": "active (Gemini)",
            "layer3": "coming soon",
            "layer4": "coming soon"
        }
    })