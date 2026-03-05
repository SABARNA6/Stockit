# app.py  –  Flask entry point for the StockIt API server
#
# Run:
#   cd server
#   python app.py              (debug mode)
#   flask run --port 5000      (production-like)
#

import os
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load .env from server/ directory
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from routes.stock_routes import stock_bp


def create_app() -> Flask:
    app = Flask(__name__, static_folder='./dist', static_url_path='')
    CORS(app)
    @app.route('/')
    def index():
        static_file = os.path.join(app.static_folder, 'index.html')
        if not os.path.exists(static_file):
            return jsonify({"message": "Frontend not built. Run: npm run build"}), 200
        return app.send_static_file('index.html')
    # ── Register blueprints ──────────────────────────────────────────────────
    app.register_blueprint(stock_bp)

    # ── Health check ─────────────────────────────────────────────────────────
    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "service": "stockit-api"})

    # ── Generic error handlers ────────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"success": False, "message": "Endpoint not found"}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"success": False, "message": "Internal server error"}), 500

    return app


app = create_app()

if __name__ == "__main__":
    port  = int(os.getenv("PORT", 10000))
    debug = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    print(f"[stockit] Starting Flask server on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
