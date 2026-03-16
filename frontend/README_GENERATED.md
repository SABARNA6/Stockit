# Frontend README (Generated)

## 1. Functionality
`/frontend` is a React + Vite UI layer for the Stockit platform:
- Stock search and symbol autocomplete.
- Price charts, sparklines, volume, trend signals.
- Fundamental metric panels and historical data tables.
- News feed with sentiment tags and filters.
- Portfolio dashboard with allocation, holdings, watchlist.

## 2. Why this is calculated
- UI needs aligned shapes across endpoints to avoid transformations in client.
- Trend/recommendation/navigations provide immediate buy/sell context to users.
- All values are expected to be computed in backend to keep frontend lightweight.

## 3. Data contract and formulas
- All endpoints return JSON envelope with `data`.
- `trends`: expects `trend.direction`, `trend.strength`, `volume.status`, `risk.riskLevel`.
- `recommendation`: `buy|sell|hold` + `confidence`, `entryPlan`, `riskRewardRatio`.
- `news`: `positive/neutral/negative` counts + normalized news row objects.

### Endpoints consumed
- `/api/stocks/:symbol`
- `/api/stocks/:symbol/sparkline?points=N`
- `/api/stocks/:symbol/chart?timeframe=1W|1M|3M|6M|1Y|ALL`
- `/api/stocks/:symbol/volume?timeframe=...`
- `/api/stocks/:symbol/trends`
- `/api/stocks/:symbol/recommendation`
- `/api/stocks/:symbol/fundamentals`
- `/api/stocks/:symbol/news`
- `/api/stocks/:symbol/historical?period=1mo|3mo|6mo|1y&page=X&limit=Y`
- `/api/company/search?symbol=`

## 4. Run
```bash
cd frontend
npm install
npm run dev
```
Default app URL: http://localhost:3000

## 5. Deployment with backend (same machine)
- Backend should be on `http://localhost:10000/api` or use `window.STOCK_API_BASE`.
- `docker-compose` can run all at once from root.
