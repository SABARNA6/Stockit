"""
api/routes.py
Flask routes for News Impact Pipeline
Apps Script POSTs to /api/ingest → Layer 1 processes → returns profiles
"""

from flask import Flask, request, jsonify
from datetime import datetime
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from layers.layer1_content import build_unified_profile

app = Flask(__name__)


# ─────────────────────────────────────────────
#  POST /api/ingest
#  Called by Apps Script after every RSS fetch
#  Body: { "articles": [ {id, title, link, ...}, ... ] }
# ─────────────────────────────────────────────
@app.route("/api/ingest", methods=["POST"])
def ingest():
    body = request.get_json(force=True)

    if not body or "articles" not in body:
        return jsonify({"error": "Expected JSON with 'articles' key"}), 400

    articles = body["articles"]
    if not isinstance(articles, list) or len(articles) == 0:
        return jsonify({"status": "ok", "message": "No articles to process", "count": 0})

    profiles   = []
    irrelevant = []

    for article in articles:
        try:
            profile = build_unified_profile(article)

            # Skip duplicates caught by novelty check
            if profile["novelty"]["is_duplicate"]:
                continue

            if profile["is_financially_relevant"]:
                profiles.append(profile)
            else:
                irrelevant.append(profile["id"])

        except Exception as e:
            print(f"[ERROR] Failed to process article {article.get('id')}: {e}")
            continue

    # Sort by relevance score — most important first
    profiles.sort(key=lambda x: x["relevance_score"], reverse=True)

    print(f"[INGEST] {datetime.now()} | Received: {len(articles)} | "
          f"Relevant: {len(profiles)} | Irrelevant: {len(irrelevant)}")

    return jsonify({
        "status":    "ok",
        "received":  len(articles),
        "processed": len(profiles),
        "skipped":   len(irrelevant),
        "profiles":  profiles        # Layer 2 will consume this next
    })


# ─────────────────────────────────────────────
#  GET /api/health  —  quick status check
# ─────────────────────────────────────────────
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status":    "running",
        "timestamp": datetime.now().isoformat(),
        "layers":    {"layer1": "active", "layer2": "coming soon",
                      "layer3": "coming soon", "layer4": "coming soon"}
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"🚀 Flask API running on http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", debug=False, port=port)