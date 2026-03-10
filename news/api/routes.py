"""
api/routes.py
Flask routes — Apps Script → Layer 1 → Layer 2 → Logs to Google Sheets
"""

from flask import Flask, request, jsonify
from datetime import datetime
import sys, os, json, threading ,requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from layers.layer1_content     import build_unified_profile
from layers.layer2_propagation import run_layer2, load_knowledge_graph

app = Flask(__name__)

# ─────────────────────────────────────────────
#  STATE
# ─────────────────────────────────────────────
_spreadsheet = None
_kg_loaded   = False

# ── Sheet tab names ───────────────────────────
SHEET_NSE    = "Nifty50"    # ← your NSE stocks tab name
SHEET_L1     = "L1_Logs"
SHEET_L2     = "L2_Logs"


# ─────────────────────────────────────────────
#  GOOGLE SHEETS CONNECTION
#  Render env vars needed:
#    GOOGLE_CREDS_JSON  = contents of service_account.json
#    SPREADSHEET_ID     = your Google Sheet ID
# ─────────────────────────────────────────────
def _get_spreadsheet():
    global _spreadsheet
    if _spreadsheet:
        return _spreadsheet
    try:
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials

        creds_json = os.environ.get("GOOGLE_CREDS_JSON")
        sheet_id   = os.environ.get("SPREADSHEET_ID")

        if not creds_json or not sheet_id:
            print("[SHEETS] ❌ Missing GOOGLE_CREDS_JSON or SPREADSHEET_ID in env vars")
            return None

        scope  = ["https://spreadsheets.google.com/feeds",
                  "https://www.googleapis.com/auth/drive"]
        creds  = ServiceAccountCredentials.from_json_keyfile_dict(
                     json.loads(creds_json), scope)
        client = gspread.authorize(creds)
        _spreadsheet = client.open_by_key(sheet_id)
        print("[SHEETS] ✅ Connected to Google Spreadsheet")
        return _spreadsheet

    except Exception as e:
        print(f"[SHEETS] ❌ Connection failed: {e}")
        return None


def _get_or_create_tab(name: str, headers: list):
    """Return worksheet by name, creating it with headers if missing."""
    import gspread
    ss = _get_spreadsheet()
    if not ss:
        return None
    try:
        return ss.worksheet(name)
    except gspread.exceptions.WorksheetNotFound:
        ws = ss.add_worksheet(title=name, rows=10000, cols=len(headers))
        ws.append_row(headers)
        # Bold + colour the header row
        ws.format("1:1", {
            "textFormat":      {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
            "backgroundColor": {"red": 0.1, "green": 0.45, "blue": 0.9}
        })
        print(f"[SHEETS] ✅ Created new tab: '{name}'")
        return ws


# ─────────────────────────────────────────────
#  LOAD NSE STOCKS → Layer 2 Knowledge Graph
# ─────────────────────────────────────────────
def _load_nse_stocks():
    global _kg_loaded
    if _kg_loaded:
        return
    ss = _get_spreadsheet()
    if not ss:
        print("[KG] ❌ Cannot load NSE stocks — no sheet connection")
        return
    try:
        ws     = ss.worksheet(SHEET_NSE)
        stocks = ws.get_all_records()
        load_knowledge_graph(stocks)
        _kg_loaded = True
    except Exception as e:
        print(f"[KG] ❌ Failed to load NSE stocks from '{SHEET_NSE}': {e}")


# ─────────────────────────────────────────────
#  LOG LAYER 1  →  L1_Logs sheet
#  One row per financially relevant article
# ─────────────────────────────────────────────

APPSCRIPT_WEBHOOK = os.environ.get("APPSCRIPT_WEBHOOK_URL")

def _post_to_appscript(payload: dict):
    """Send log data back to Apps Script doPost."""
    if not APPSCRIPT_WEBHOOK:
        print("[LOG] ❌ APPSCRIPT_WEBHOOK_URL not set in env vars")
        return
    try:
        r = requests.post(
            APPSCRIPT_WEBHOOK,
            json=payload,
            timeout=30,
            # Apps Script requires redirects to be followed
            allow_redirects=True
        )
        print(f"[LOG] ✅ Apps Script responded: {r.status_code}")
    except Exception as e:
        print(f"[LOG] ❌ Failed to post to Apps Script: {e}")


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
#  POST /api/ingest
#  Called by Apps Script after every RSS fetch
# ─────────────────────────────────────────────
@app.route("/api/ingest", methods=["POST"])
def ingest():
    # Load NSE knowledge graph once on first request
    _load_nse_stocks()

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

    # ── Log L1 in background thread (non-blocking) ──
    threading.Thread(target=_log_l1, args=(l1_profiles,), daemon=True).start()

    # ── Layer 2 : Gemini impact propagation ──
    l2_profiles = run_layer2(l1_profiles)

    # ── Log L2 in background thread (non-blocking) ──
    threading.Thread(target=_log_l2, args=(l2_profiles,), daemon=True).start()

    print(f"[INGEST] {datetime.now().strftime('%H:%M:%S')} | "
          f"In: {len(articles)} | L1: {len(l1_profiles)} | L2: {len(l2_profiles)}")

    return jsonify({
        "status":          "ok",
        "received":        len(articles),
        "layer1_relevant": len(l1_profiles),
        "layer2_enriched": len(l2_profiles),
        "profiles":        l2_profiles      # → Layer 3 next
    })


# ─────────────────────────────────────────────
#  GET /api/health
# ─────────────────────────────────────────────
@app.route("/api/health", methods=["GET"])
def health():
    ss_ok = _get_spreadsheet() is not None
    return jsonify({
        "status":       "running",
        "timestamp":    datetime.now().isoformat(),
        "sheets_ok":    ss_ok,
        "kg_loaded":    _kg_loaded,
        "layers": {
            "layer1": "active",
            "layer2": "active (Gemini)",
            "layer3": "coming soon",
            "layer4": "coming soon"
        }
    })

@app.route("/api/load-stocks", methods=["POST"])
def load_stocks():
    body   = request.get_json(force=True)
    stocks = body.get("stocks", [])
    if not stocks:
        return jsonify({"error": "No stocks received"}), 400
    load_knowledge_graph(stocks)
    return jsonify({
        "status": "ok",
        "loaded": len(stocks)
    })
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"🚀 Flask API on http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", debug=False, port=port)