"""
api/routes.py
Flask — Apps Script → L1 → L2 → L3 → Logs via Apps Script doPost
"""

from flask import Flask, request, jsonify
from datetime import datetime
import sys, os, json, threading, requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from layers.layer1_content     import build_unified_profile
from layers.layer2_propagation import run_layer2, load_knowledge_graph
from layers.layer3_prediction  import run_layer3

app = Flask(__name__)

_kg_loaded  = False
_nse_stocks = []


def _get_webhook():
    return os.environ.get("APPSCRIPT_WEBHOOK_URL")


def _post_to_appscript(payload: dict):
    webhook = _get_webhook()
    if not webhook:
        print("[LOG] ❌ APPSCRIPT_WEBHOOK_URL not set")
        return
    try:
        r = requests.post(webhook, json=payload, timeout=30, allow_redirects=True)
        print(f"[LOG] ✅ Apps Script responded: {r.status_code}")
    except Exception as e:
        print(f"[LOG] ❌ Failed to post to Apps Script: {e}")


def _log_l1(profiles: list):
    if not profiles:
        return
    ts   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = [[
        ts,
        p.get("id", ""),
        p.get("title", "")[:100],
        ", ".join(e["ticker"] for e in p.get("entities", [])) or "—",
        p.get("event", {}).get("event_type", ""),
        p.get("sentiment", {}).get("label", ""),
        p.get("sentiment", {}).get("urgency_score", 0),
        p.get("relevance_score", 0),
        p.get("source", ""),
    ] for p in profiles]
    threading.Thread(target=_post_to_appscript,
                     args=({"type": "l1_logs", "rows": rows},), daemon=True).start()


def _log_l2(profiles: list):
    if not profiles:
        return
    ts, rows = datetime.now().strftime("%Y-%m-%d %H:%M:%S"), []
    for p in profiles:
        for e in p.get("affected_entities", []):
            rows.append([ts, p.get("id",""), p.get("title","")[:100],
                         e.get("ticker",""), e.get("name",""), e.get("industry",""),
                         e.get("impact_type",""), e.get("direction",""),
                         e.get("confidence",0), e.get("reason","")[:150], e.get("sentiment","")])
    if rows:
        threading.Thread(target=_post_to_appscript,
                         args=({"type": "l2_logs", "rows": rows},), daemon=True).start()


def _log_l3(profiles: list):
    """Log Layer 3 predictions — one row per stock prediction."""
    if not profiles:
        return
    ts, rows = datetime.now().strftime("%Y-%m-%d %H:%M:%S"), []
    for p in profiles:
        for e in p.get("affected_entities", []):
            pred = e.get("prediction", {})
            if not pred:
                continue
            pc = e.get("price_context", {})
            rows.append([
                ts,
                p.get("id", ""),
                p.get("title", "")[:100],
                e.get("ticker", ""),
                e.get("name", ""),
                pred.get("alert_priority", ""),
                pred.get("direction", ""),
                pred.get("move_estimate_pct", ""),
                f"{pred.get('move_range', {}).get('low','')} to {pred.get('move_range', {}).get('high','')}",
                pred.get("confidence", ""),
                pred.get("time_horizon", ""),
                pc.get("current_price", ""),
                pc.get("trend_8d_pct", ""),
                pc.get("volatility", ""),
                pred.get("reasoning", "")[:200],
                pred.get("key_risks", "")[:150],
            ])
    if rows:
        threading.Thread(target=_post_to_appscript,
                         args=({"type": "l3_logs", "rows": rows},), daemon=True).start()


# ─────────────────────────────────────────────
#  POST /api/load-stocks
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
    print(f"[KG] ✅ Loaded {len(stocks)} stocks")
    return jsonify({"status": "ok", "loaded": len(stocks)})


# ─────────────────────────────────────────────
#  POST /api/ingest
# ─────────────────────────────────────────────
@app.route("/api/ingest", methods=["POST"])
def ingest():
    body = request.get_json(force=True)
    if not body or "articles" not in body:
        return jsonify({"error": "Expected JSON with 'articles' key"}), 400

    articles = body.get("articles", [])
    if not articles:
        return jsonify({"status": "ok", "message": "No articles received", "count": 0})

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
    _log_l1(l1_profiles)

    # ── Layer 2 ──────────────────────────────
    l2_profiles = run_layer2(l1_profiles)
    _log_l2(l2_profiles)

    # ── Layer 3 ──────────────────────────────
    l3_profiles = run_layer3(l2_profiles)
    _log_l3(l3_profiles)

    print(f"[INGEST] {datetime.now().strftime('%H:%M:%S')} | "
          f"In:{len(articles)} L1:{len(l1_profiles)} "
          f"L2:{len(l2_profiles)} L3:{len(l3_profiles)}")

    return jsonify({
        "status":          "ok",
        "received":        len(articles),
        "layer1_relevant": len(l1_profiles),
        "layer2_enriched": len(l2_profiles),
        "layer3_predicted": len(l3_profiles),
        "profiles":        l3_profiles
    })


# ─────────────────────────────────────────────
#  GET /api/health
# ─────────────────────────────────────────────
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status":      "running",
        "timestamp":   datetime.now().isoformat(),
        "kg_loaded":   _kg_loaded,
        "kg_stocks":   len(_nse_stocks),
        "webhook_set": bool(_get_webhook()),
        "gemini_set":  bool(os.environ.get("GEMINI_API_KEY")),
        "layers": {
            "layer1": "active",
            "layer2": "active (Gemini)",
            "layer3": "active (Gemini + Price API)",
            "layer4": "coming soon"
        }
    })