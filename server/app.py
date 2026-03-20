# app.py  —  Unified Flask gateway
# Runs on port 10000 (what the React frontend expects)
# Registers all blueprints:
#   /api/stocks/*          → stock_routes   (yfinance + HF models)
#   /api/ml/*              → inside stock_routes
#   /api/equity/*          → equity_routes  (Equity Intelligence v3 proxy)
#   /api/portfolio/*       → portfolio_routes (Supabase portfolio/watchlist)
#   /api/user/*            → user_routes    (Supabase profile)

from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

# Allow React dev server + deployed frontend origins from env.
_cors_origins = {
    "http://localhost:3000",
    "http://localhost:5173",
}

frontend_url = os.getenv("FRONTEND_URL", "").strip()
if frontend_url:
    _cors_origins.add(frontend_url)

for origin in os.getenv("CORS_ORIGINS", "").split(","):
    origin = origin.strip()
    if origin:
        _cors_origins.add(origin)

CORS(app, resources={r"/api/*": {"origins": sorted(_cors_origins)}})

# ── Register blueprints ───────────────────────────────────────────────────────
from routes.stock_routes     import stock_bp
from routes.equity_routes    import equity_bp
from routes.portfolio_routes import portfolio_bp
from routes.user_routes      import user_bp

app.register_blueprint(stock_bp)       # /api/stocks/* and /api/ml/*
app.register_blueprint(equity_bp)      # /api/equity/*
app.register_blueprint(portfolio_bp)   # /api/portfolio/* and /api/watchlist/*
app.register_blueprint(user_bp)        # /api/user/*


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/")
def health():
    # Keep health output minimal to avoid exposing internal API surface.
    return jsonify({
        "status": "ok",
        "service": "Stockit API Gateway"
    })


if __name__ == "__main__":
    port  = int(os.getenv("PORT", 10000))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    print(f"Starting Stockit Gateway on port {port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
