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

# Allow React dev server (localhost:3000) + any deployed frontend origin
CORS(app, resources={r"/api/*": {"origins": [
    "http://localhost:3000",
    "http://localhost:5173",
    os.getenv("FRONTEND_URL", ""),
]}})

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
    return jsonify({
        "status":  "ok",
        "service": "Stockit API Gateway",
        "port":    10000,
        "endpoints": [
            "GET  /api/stocks/<symbol>",
            "GET  /api/stocks/<symbol>/sparkline",
            "GET  /api/stocks/<symbol>/chart",
            "GET  /api/stocks/<symbol>/volume",
            "GET  /api/stocks/<symbol>/trends",
            "GET  /api/stocks/<symbol>/recommendation",
            "GET  /api/stocks/<symbol>/fundamentals",
            "GET  /api/stocks/<symbol>/news",
            "GET  /api/stocks/<symbol>/historical",
            "GET  /api/company/search",
            "GET  /api/ml/price/<symbol>",
            "GET  /api/ml/strategy/<symbol>",
            "POST /api/ml/strategy/custom",
            "POST /api/ml/recommend",
            "GET  /api/ml/full/<symbol>",
            "GET  /api/equity/analyze/<symbol>",
            "GET  /api/equity/limits",
            "POST /api/equity/trigger",
            "GET  /api/portfolio",
            "POST /api/portfolio",
            "DELETE /api/portfolio/<id>",
            "GET  /api/watchlist",
            "POST /api/watchlist",
            "DELETE /api/watchlist/<id>",
            "GET  /api/user/profile",
            "PUT  /api/user/profile",
        ]
    })


if __name__ == "__main__":
    port  = int(os.getenv("PORT", 10000))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    print(f"Starting Stockit Gateway on port {port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
