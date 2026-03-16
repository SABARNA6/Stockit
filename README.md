# Stockit Centralized README

## 🧾 Project Overview
Stockit is an AI-powered stock analytics platform for traders, investors, and quant researchers. It combines live market data, fundamental metrics, ML-based strategy recommendations, and NLP-driven news sentiment from multiple submodules.

Live deployment: http://35.200.248.46

### Who should use this project
- Retail traders seeking data-driven trend signals.
- Fundamental investors requiring valuation ratios + ESG-style signals.
- Quant/ML engineers exploring model integration in production.
- Teams that need a complete **frontend + backend + data pipeline** stack for equity analysis.

## 📦 Repository Structure
- `/server`: Flask API + model integration endpoints (core runtime for analytics + news sentiment)
- `/equity_intelligence_v3`: News ingestion + tiered intelligence pipeline + impact estimation.
- `/frontend`: React/Vite UI, Supabase auth + portfolio dashboards.
- root `README.md`: full installation and feature snapshot (already provided).

---

## ✅ How to use this project
1. `git clone` the repo.
2. Choose staging mode:
   - `cd server`, install Python dependencies, set `.env` and run `python app.py`.
   - `cd equity_intelligence_v3`, install requirements, set `.env` for Supabase/NewsAPI/GROQ and run `python server.py`.
   - `cd frontend`, run `npm install && npm run dev`.
3. Open UI at `http://localhost:3000`, backend at `http://localhost:10000/api`.
4. For live site, use `http://35.200.248.46`.

---

## 🧩 Submodule quick links

### `/server`
Core endpoints:
- `/api/stocks/<symbol>` (snapshot + fundamentals)
- `/api/stocks/<symbol>/trends` (technical risk/trend)
- `/api/stocks/<symbol>/news` (NewsAPI+FinBERT)
- `/api/stocks/<symbol>/recommendation` (rule-based trade plan)
- `/api/ml/*` (price forecast and strategy/recommendations via Gradio models)

### `/equity_intelligence_v3`
Pipeline:
- Ingest RSS + NewsAPI into Supabase
- Tier 1 static processing (dedup, keyword, class)
- Tier 2 relevance scoring (Groq 0-10)
- Tier 3 impact/depth (Groq categories + cause/horizon)
- Price impact rules (mapping to move ranges and weighted summary)

### `/frontend`
React-based dashboard with:
- Symbol search + watchlist
- Chart/sparkline/volume/trend/recommendations
- Portfolio pages, allocation visuals, news feed
- API contract matching `/server` endpoints

---

## 📘 What each README contains
- Functionality summary
- What is calculated and why
- Formula / scoring logic

See these files:
- `equity_intelligence_v3/README_GENERATED.md`
- `server/README_GENERATED.md`
- `frontend/README_GENERATED.md`
