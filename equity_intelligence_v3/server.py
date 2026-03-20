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
from core import cache
from routes.rss_routes import rss_bp
from routes.analysis_routes import analysis_bp

load_dotenv()

# Initialize cache database on startup
cache.init()

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
    """Minimal health check response."""
    return jsonify({
        "service": "Equity Intelligence v3",
        "status": "running"
    }), 200


# ─────────────────────────────────────────────
#  ERROR HANDLERS
# ─────────────────────────────────────────────
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def server_error(error):
    return jsonify({"error": "Internal server error"}), 500


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
