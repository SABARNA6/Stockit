# Server README (Generated)

## 1. Functionality
`/server` provides the core REST API for Stockit, including:
- Real-time quote + fundamentals (`/api/stocks/<symbol>`).
- Sparkline/chart/volume/historical endpoints.
- Trend signal and recommendation logic.
- News + sentiment with NewsAPI + FinBERT.
- ML endpoints for predictions and portfolio recommendations.

## 2. Why this is calculated
- `trends` was designed to distill key technical indicators quickly for UX.
- `recommendation` provides actionable plan (entry zone, stop loss, R/R) using a simple ruleset.
- `news` provides sentiment composition for news-driven bias.
- ML endpoints encapsulate experimental/AI models (price + strategy + portfolio suggestions).

## 3. Formula details
### get_stock_trends
- Moving averages (MA20, MA50) for direction:
  - `bullish` if current > MA20 and current > MA50
  - `bearish` if current < MA20 and current < MA50, else `neutral`
- `strength` = min(abs(current - MA20)/MA20 * 1000, 100)
- Volume ratio = volume / avg_volume:
  - `Spike` ≥ 2.5, `High` ≥1.2, `Low` <0.8, else `Normal`
- `deliveryPercent` = clamp(50 + (ratio-1)*20 + consistency*20, 35, 85).
- ATR calculation (14-day):
  - TR = max(high-low, abs(high-close_prev), abs(low-close_prev))
  - ATR = avg(TR)
- risk level:
  - `High` if beta >1.3 or ATR% >3
  - `Low` if beta <0.8 and ATR% <1.5
  - else `Medium`

### get_recommendation
- `upside` = (targetMeanPrice - current)/current*100
- `confidence` bands: >20 → 80; >10 → 70; >0 → 60; >-10 → 50; else 40
- tech_score = clamp(100 - (pe/30*100), 30, 95)
- fund_score = clamp(50 + upside, 30, 95)
- entry zone: stop_loss = 0.92*current, breakout = 1.05*current, accumulation 0.96—1.02*current
- risk-reward = (target-current)/(current-stop_loss)

### get_finacial_metric
- EBITDA margin = ebitda/revenue
- ROE/ROA normalized to %
- PEG from EPS CAGR and PE when available.

### get_news
- Queries NewsAPI by company name plus fallback to stripped symbol.
- FinBERT sentiment per article by `Sabarna6/FinBERT_FinancialSentimentAnalysis`.
- Aggregate % sentiment across batch.

## 4. Endpoints
- `/` frontend proxy
- `/health`
- `/api/stocks/<symbol>`
- `/api/stocks/<symbol>/sparkline` etc.
- `/api/ml/price/<symbol>?horizon=5`
- `/api/ml/strategy/<symbol>`, `/api/ml/strategy/custom`
- `/api/ml/recommend` + `/api/ml/full/<symbol>`

## 5. Setup
```bash
cd server
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# fill keys: NEWS_API_KEY, GOOGLE_SHEETS_URL optional
python app.py
```