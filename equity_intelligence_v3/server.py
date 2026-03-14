"""
=====================================================================
  server.py
  Flask API server for equity intelligence v3
  Manually trigger RSS feeds and manage pipeline
=====================================================================
"""

import os
from flask import Flask, jsonify
from dotenv import load_dotenv
from routes.rss_routes import rss_bp
from routes.analysis_routes import analysis_bp

load_dotenv()

# ─────────────────────────────────────────────
#  INITIALIZE FLASK APP
# ─────────────────────────────────────────────
app = Flask(__name__)

# Register blueprints
app.register_blueprint(rss_bp)
app.register_blueprint(analysis_bp)


# ─────────────────────────────────────────────
#  ROOT ENDPOINT
# ─────────────────────────────────────────────
@app.route("/", methods=["GET"])
def home():
    """Health check and API documentation."""
    return jsonify({
        "service": "Equity Intelligence v3",
        "version": "1.0",
        "status": "running",
        "endpoints": {
            "health": "GET /",
            "rss": {
                "trigger_fetch": "GET|POST /api/rss/trigger",
                "status": "GET /api/rss/status",
            },
            "analysis": {
                "stock_analysis": "GET /api/analyze/<symbol>?hours_back=24",
                "api_limits": "GET /api/limits",
                "equities_sync": "GET|POST /api/equities/sync",
            }
        },
        "documentation": "See /api/rss/status, /api/analyze/<symbol>, /api/limits, /api/equities/sync"
    }), 200


# ─────────────────────────────────────────────
#  ERROR HANDLERS
# ─────────────────────────────────────────────
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def server_error(error):
    return jsonify({"error": "Internal server error", "message": str(error)}), 500


# ─────────────────────────────────────────────
#  RUN SERVER
# ─────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("DEBUG", "False").lower() == "true"
    
    print(f"[server] Starting Equity Intelligence v3 API")
    print(f"[server] API running on http://localhost:{port}")
    print(f"[server] RSS trigger: GET/POST http://localhost:{port}/api/rss/trigger")
    
    app.run(host="0.0.0.0", port=port, debug=debug)
