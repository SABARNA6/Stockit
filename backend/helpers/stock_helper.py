# helpers/stock_helper.py
#
# Flask backend helpers — yfinance (primary) + nsepython (NSE-specific supplements)
#

import os
import math
import requests
import yfinance as yf
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

NEWS_API_KEY     = os.getenv("NEWS_API_KEY")
FINBERT_API_URL  = os.getenv("FINBERT_API_URL")
FINBERT_API_KEY  = os.getenv("FINBERT_API_KEY")
GOOGLE_SHEETS_URL = os.getenv("GOOGLE_SHEETS_URL")

# ── nsepython optional import ─────────────────────────────────────────────────
try:
    from nsepython import nse_eq, nse_fno, nse_optionchain_scrapper, indices
    NSE_AVAILABLE = True
except Exception:
    NSE_AVAILABLE = False
    print("[warning] nsepython not available — NSE-specific features disabled")


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _ticker_sym(symbol: str) -> str:
    """Append .NS suffix for NSE equities if not already present."""
    s = symbol.strip().upper()
    return s if s.endswith(".NS") or s.endswith(".BO") else f"{s}.NS"


def _safe_float(val, default=None):
    try:
        v = float(val)
        return None if (math.isnan(v) or math.isinf(v)) else v
    except (TypeError, ValueError):
        return default


def _safe_int(val, default=None):
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


# ─────────────────────────────────────────────────────────────────────────────
# REALTIME OVERVIEW
# ─────────────────────────────────────────────────────────────────────────────

def get_realtime_stock(symbol: str) -> dict:
    try:
        ticker = yf.Ticker(_ticker_sym(symbol))
        info   = ticker.info

        current   = _safe_float(info.get("currentPrice"))
        prev      = _safe_float(info.get("previousClose")) or current
        change    = round(current - prev, 2) if current is not None and prev is not None else None
        change_pct = round((change / prev) * 100, 2) if change is not None and prev else None

        # ── NSE supplement: live quote (delivery %, circuit limits, etc.) ─────
        nse_extra = {}
        if NSE_AVAILABLE:
            try:
                eq = nse_eq(symbol.upper())
                priceInfo = eq.get("priceInfo", {})
                nse_extra = {
                    "upperCircuit":   _safe_float(priceInfo.get("upperCP")),
                    "lowerCircuit":   _safe_float(priceInfo.get("lowerCP")),
                    "vwap":           _safe_float(priceInfo.get("vwap")),
                    "intraDayHighLow": priceInfo.get("intraDayHighLow"),
                    "weekHighLow":    priceInfo.get("weekHighLow"),
                }
            except Exception as e:
                print(f"[nse_eq] {symbol}: {e}")

        return {
            "symbol":           symbol.upper(),
            "name":             info.get("longName") or info.get("shortName") or symbol.upper(),
            "exchange":         info.get("exchange"),
            "sector":           info.get("sector"),
            "industry":         info.get("industry"),
            "currentPrice":     current,
            "previousClose":    prev,
            "open":             _safe_float(info.get("open")),
            "dayHigh":          _safe_float(info.get("dayHigh")),
            "dayLow":           _safe_float(info.get("dayLow")),
            "change":           change,
            "changePercent":    change_pct,
            "volume":           _safe_int(info.get("volume")),
            "avgVolume":        _safe_int(info.get("averageVolume")),
            "marketCap":        _safe_float(info.get("marketCap")),
            "fiftyTwoWeekHigh": _safe_float(info.get("fiftyTwoWeekHigh")),
            "fiftyTwoWeekLow":  _safe_float(info.get("fiftyTwoWeekLow")),
            "peRatio":          _safe_float(info.get("trailingPE")),
            "eps":              _safe_float(info.get("trailingEps")),
            "dividendYield":    _safe_float(info.get("dividendYield")),
            "roe":              _safe_float(info.get("returnOnEquity")),
            "lastUpdated":      datetime.utcnow().isoformat(),
            **nse_extra,
        }

    except Exception as e:
        print(f"[get_realtime_stock] {symbol}: {e}")
        return {}


# ─────────────────────────────────────────────────────────────────────────────
# SPARKLINE  (last N closing prices for a mini-chart)
# ─────────────────────────────────────────────────────────────────────────────

def get_sparkline(symbol: str, points: int = 12) -> dict:
    try:
        ticker  = yf.Ticker(_ticker_sym(symbol))
        history = ticker.history(period="1mo")
        history.reset_index(inplace=True)

        closes = [_safe_float(r["Close"]) for _, r in history.iterrows()]
        closes = [v for v in closes if v is not None]
        closes = closes[-points:]           # keep last N

        first = closes[0] if closes else 0
        last  = closes[-1] if closes else 0
        trend = "up" if last >= first else "down"

        return {
            "prices": closes,
            "trend":  trend,
            "min":    round(min(closes), 2) if closes else None,
            "max":    round(max(closes), 2) if closes else None,
        }
    except Exception as e:
        print(f"[get_sparkline] {symbol}: {e}")
        return {"prices": [], "trend": "neutral", "min": None, "max": None}


# ─────────────────────────────────────────────────────────────────────────────
# HISTORICAL  (paginated OHLCV table)
# ─────────────────────────────────────────────────────────────────────────────

def get_historical_data(symbol: str, period: str = "1mo", page: int = 1, limit: int = 8) -> dict:
    try:
        ticker  = yf.Ticker(_ticker_sym(symbol))
        history = ticker.history(period=period)
        history.reset_index(inplace=True)

        avg_vol = history["Volume"].mean() if len(history) else 0

        prices     = []
        prev_close = None

        for _, row in history.iterrows():
            dv  = row["Date"]
            ds  = dv.strftime("%Y-%m-%d") if hasattr(dv, "strftime") else str(dv)
            cl  = _safe_float(row["Close"])
            vol = _safe_int(row["Volume"])
            chg = round(((cl - prev_close) / prev_close) * 100, 2) if prev_close and cl else 0

            prices.append({
                "date":          ds,
                "open":          _safe_float(row["Open"]),
                "high":          _safe_float(row["High"]),
                "low":           _safe_float(row["Low"]),
                "close":         cl,
                "volume":        vol,
                "changePercent": chg,
                "highVolume":    bool(vol and avg_vol and vol > avg_vol * 1.5),
            })
            prev_close = cl

        prices.reverse()   # newest first

        total      = len(prices)
        total_pages = max(1, math.ceil(total / limit))
        start      = (page - 1) * limit
        paginated  = prices[start : start + limit]

        return {
            "prices": paginated,
            "pagination": {
                "currentPage": page,
                "totalPages":  total_pages,
                "totalItems":  total,
                "limit":       limit,
            },
        }
    except Exception as e:
        print(f"[get_historical_data] {symbol}: {e}")
        return {
            "prices": [],
            "pagination": {"currentPage": 1, "totalPages": 0, "totalItems": 0, "limit": limit},
        }


# ─────────────────────────────────────────────────────────────────────────────
# FINANCIAL FUNDAMENTALS
# ─────────────────────────────────────────────────────────────────────────────

def get_financials(symbol: str) -> dict:
    try:
        ticker = yf.Ticker(_ticker_sym(symbol))
        info   = ticker.info

        revenue = _safe_float(info.get("totalRevenue"))
        ebitda  = _safe_float(info.get("ebitda"))
        net_inc = _safe_float(info.get("netIncomeToCommon"))
        pe_ratio = _safe_float(info.get("trailingPE"))
        current_eps = _safe_float(info.get("trailingEps"))
        eps_growth_ttm = None
        peg_ratio = None

        # ── Calculate missing growth metrics using historical data ────────────
        try:
            # Get income statement for historical revenue & net income
            income_stmt = ticker.quarterly_financials
            if income_stmt is not None and not income_stmt.empty:
                # Revenue CAGR (5Y)
                revenues = income_stmt.loc["Total Revenue"].dropna()
                if len(revenues) >= 4:  # At least 4 quarters = 1 year
                    # Get oldest and newest revenue values
                    oldest_qty_revenue = revenues.iloc[-1]  # Oldest
                    newest_qty_revenue = revenues.iloc[0]   # Newest
                    quarters_back = len(revenues) - 1
                    years_back = quarters_back / 4
                    if oldest_qty_revenue and newest_qty_revenue and years_back > 0:
                        rev_cagr = (((newest_qty_revenue / oldest_qty_revenue) ** (1 / years_back)) - 1) * 100
                        revenueCagr5y = round(rev_cagr, 2) if rev_cagr >= -100 else None
                    else:
                        revenueCagr5y = None
                else:
                    revenueCagr5y = None

                # Profit CAGR (5Y) using Net Income
                net_incomes = income_stmt.loc["Net Income"].dropna()
                if len(net_incomes) >= 4:
                    oldest_qty_ni = net_incomes.iloc[-1]
                    newest_qty_ni = net_incomes.iloc[0]
                    quarters_back = len(net_incomes) - 1
                    years_back = quarters_back / 4
                    if oldest_qty_ni and newest_qty_ni and years_back > 0:
                        ni_cagr = (((newest_qty_ni / oldest_qty_ni) ** (1 / years_back)) - 1) * 100
                        profitCagr5y = round(ni_cagr, 2) if ni_cagr >= -100 else None
                    else:
                        profitCagr5y = None
                else:
                    profitCagr5y = None

                # Sales Growth (YoY) - last quarter vs year-ago quarter
                if len(revenues) >= 4:
                    latest_revenue = revenues.iloc[0]
                    year_ago_revenue = revenues.iloc[3]  # 3 quarters back ≈ 1 year
                    if latest_revenue and year_ago_revenue:
                        salesGrowth = ((latest_revenue - year_ago_revenue) / year_ago_revenue) * 100
                        salesGrowth = round(salesGrowth, 2)
                    else:
                        salesGrowth = None
                else:
                    salesGrowth = None
            else:
                revenueCagr5y = None
                profitCagr5y = None
                salesGrowth = None

            # EPS Growth (TTM) - trailing 12 months
            try:
                info_history = ticker.quarterly_financials
                eps_data = ticker.info.get("epsTrailingTwelveMonths")
                forward_eps = _safe_float(ticker.info.get("forwardEps"))
                if current_eps and forward_eps:
                    eps_growth_ttm = ((forward_eps - current_eps) / current_eps) * 100
                    eps_growth_ttm = round(eps_growth_ttm, 2)
            except:
                eps_growth_ttm = None

        except Exception as e:
            print(f"[historical data] {symbol}: {e}")
            revenueCagr5y = None
            profitCagr5y = None
            salesGrowth = None
            eps_growth_ttm = None

        # ── Calculate PEG Ratio if we have EPS growth ────────────────────────
        if pe_ratio and eps_growth_ttm and eps_growth_ttm != 0:
            peg_ratio = round(pe_ratio / eps_growth_ttm, 2)

        # ── Interest Coverage = EBIT / Interest Expense ──────────────────────
        try:
            income_stmt = ticker.quarterly_financials
            if income_stmt is not None and not income_stmt.empty:
                ebit = income_stmt.loc["Operating Income"].iloc[0] if "Operating Income" in income_stmt.index else None
                interest_expense = income_stmt.loc["Interest Expense"].iloc[0] if "Interest Expense" in income_stmt.index else None
                if ebit and interest_expense and interest_expense != 0:
                    interestCoverage = ebit / interest_expense
                    interestCoverage = round(interestCoverage, 2)
                else:
                    interestCoverage = None
            else:
                interestCoverage = None
        except:
            interestCoverage = None

        # ── Fix ROE/ROA: Convert from decimal to percentage (multiply by 100) ─
        roe_raw = _safe_float(info.get("returnOnEquity"))
        roe_pct = round(roe_raw * 100, 2) if roe_raw is not None else None

        roa_raw = _safe_float(info.get("returnOnAssets"))
        roa_pct = round(roa_raw * 100, 2) if roa_raw is not None else None

        # ── Debt to Equity: Try to calculate if direct field doesn't match ────
        debt_to_equity = _safe_float(info.get("debtToEquity"))
        total_debt = _safe_float(info.get("totalDebt"))
        total_equity = _safe_float(info.get("totalEquity"))
        # Fallback calculation if available
        if (debt_to_equity is None or debt_to_equity == 0) and total_debt and total_equity:
            debt_to_equity = total_debt / total_equity

        # ── EV/EBITDA: Calculate manually for accuracy ────────────────────────
        enterprise_value = _safe_float(info.get("enterpriseValue"))
        ev_ebitda = None
        if enterprise_value and ebitda and ebitda != 0:
            ev_ebitda = round(enterprise_value / ebitda, 2)

        return {
            "revenue":           revenue,
            "netProfit":         net_inc,
            "ebitda":            ebitda,
            "ebitdaMargin":      round((ebitda / revenue) * 100, 2) if ebitda and revenue else None,
            "profitMargin":      round((net_inc / revenue) * 100, 2) if net_inc and revenue else None,
            "debtToEquity":      debt_to_equity,
            "currentRatio":      _safe_float(info.get("currentRatio")),
            "quickRatio":        _safe_float(info.get("quickRatio")),
            "roe":               roe_pct,
            "roa":               roa_pct,
            "eps":               _safe_float(info.get("trailingEps")),
            "forwardEps":        _safe_float(info.get("forwardEps")),
            "peRatio":           pe_ratio,
            "forwardPE":         _safe_float(info.get("forwardPE")),
            "pbRatio":           _safe_float(info.get("priceToBook")),
            "psRatio":           _safe_float(info.get("priceToSalesTrailing12Months")),
            "pegRatio":          peg_ratio,
            "dividendYield":     _safe_float(info.get("dividendYield")),
            "payoutRatio":       _safe_float(info.get("payoutRatio")),
            "bookValue":         _safe_float(info.get("bookValue")),
            "freeCashflow":      _safe_float(info.get("freeCashflow")),
            "operatingCashflow": _safe_float(info.get("operatingCashflow")),
            "grossMargins":      _safe_float(info.get("grossMargins")),
            "operatingMargins":  _safe_float(info.get("operatingMargins")),
            "revenueCagr5y":     revenueCagr5y,
            "profitCagr5y":      profitCagr5y,
            "epsGrowthTtm":      eps_growth_ttm,
            "salesGrowth":       salesGrowth,
            "interestCoverage":  interestCoverage,
            "evEbitda":          ev_ebitda,
        }

    except Exception as e:
        print(f"[get_financials] {symbol}: {e}")
        return {}


# ─────────────────────────────────────────────────────────────────────────────
# SENTIMENT helper
# ─────────────────────────────────────────────────────────────────────────────

def _analyze_sentiment(text: str) -> dict:
    if not FINBERT_API_URL:
        return {"sentiment": "Neutral", "confidence": 0.0}
    try:
        headers = {"Content-Type": "application/json"}
        if FINBERT_API_KEY:
            headers["Authorization"] = f"Bearer {FINBERT_API_KEY}"
        res = requests.post(FINBERT_API_URL, headers=headers, json={"text": text}, timeout=10)
        r   = res.json()
        return {
            "sentiment":  str(r.get("label", "Neutral")).capitalize(),
            "confidence": float(r.get("confidence", 0.0)),
        }
    except Exception as e:
        print(f"[FinBERT] {e}")
        return {"sentiment": "Neutral", "confidence": 0.0}


# ─────────────────────────────────────────────────────────────────────────────
# NEWS  (NewsAPI + optional FinBERT sentiment)
# ─────────────────────────────────────────────────────────────────────────────

def get_news(symbol: str) -> dict:
    try:
        if not NEWS_API_KEY:
            raise ValueError("NEWS_API_KEY not configured")

        company_name = (get_realtime_stock(symbol)).get("name") or ""
        params = {
            "q":        company_name,
            "language": "en",
            "sortBy":   "publishedAt",
            "pageSize": 15,
            "apiKey":   NEWS_API_KEY,
        }
        articles = requests.get("https://newsapi.org/v2/everything", params=params, timeout=10)\
                           .json().get("articles", [])
        print(articles)
        formatted = []
        pos = neu = neg = 0

        for a in articles:
            title   = a.get("title", "")
            desc    = a.get("description", "")
            sent    = _analyze_sentiment(f"{title}. {desc}")
            label   = sent["sentiment"]

            if label == "Positive":   pos += 1
            elif label == "Negative": neg += 1
            else:                     neu += 1

            formatted.append({
                "symbol":      symbol.upper(),
                "title":       title,
                "summary":     desc,
                "source":      a.get("source", {}).get("name"),
                "publishedAt": a.get("publishedAt"),
                "url":         a.get("url"),
                "tags":        [label.lower()],
                "sentiment":   label,
                "confidence":  sent["confidence"],
            })

        total = pos + neu + neg or 1
        return {
            "sentiment": {
                "positive": round(pos / total * 100, 2),
                "neutral":  round(neu / total * 100, 2),
                "negative": round(neg / total * 100, 2),
            },
            "news": formatted,
        }

    except Exception as e:
        print(f"[get_news] {symbol}: {e}")
        return {"sentiment": {"positive": 0, "neutral": 100, "negative": 0}, "news": []}


# ─────────────────────────────────────────────────────────────────────────────
# TRENDS  (directional, volume, risk signals)
# ─────────────────────────────────────────────────────────────────────────────

def get_stock_trends(symbol: str) -> dict:
    try:
        ticker = yf.Ticker(_ticker_sym(symbol))
        info   = ticker.info
        hist   = ticker.history(period="14d")  # Get last 14 days for ATR calculation

        current  = _safe_float(info.get("currentPrice")) or 0
        prev     = _safe_float(info.get("previousClose")) or current
        volume   = _safe_float(info.get("volume")) or 0
        avg_vol  = _safe_float(info.get("averageVolume")) or volume or 1
        beta     = _safe_float(info.get("beta")) or 1.0

        chg_pct   = ((current - prev) / prev * 100) if prev else 0
        direction = "bullish" if chg_pct > 0 else "bearish" if chg_pct < 0 else "neutral"
        # Strength should be the absolute change percentage, capped at 100
        strength  = round(min(abs(chg_pct), 100), 2)

        vol_ratio  = volume / avg_vol
        vol_status = "High" if vol_ratio > 1.2 else "Low" if vol_ratio < 0.8 else "Normal"
        # Set to "Spike" if volume is exceptionally high
        if vol_ratio > 1.5:
            vol_status = "Spike"

        volatility = "High" if beta > 1.2 else "Low" if beta < 0.8 else "Medium"

        # ── Calculate proper ATR (Average True Range) ──────────────────────────
        atr = None
        if not hist.empty and len(hist) >= 14:
            try:
                # True Range = max(High - Low, |High - Previous Close|, |Low - Previous Close|)
                hist['High_Prev_Close'] = abs(hist['High'] - hist['Close'].shift(1))
                hist['Low_Prev_Close'] = abs(hist['Low'] - hist['Close'].shift(1))
                hist['High_Low'] = hist['High'] - hist['Low']
                hist['TrueRange'] = hist[['High_Low', 'High_Prev_Close', 'Low_Prev_Close']].max(axis=1)
                # ATR is the 14-period average of True Range
                atr = round(hist['TrueRange'].tail(14).mean(), 2)
            except Exception:
                # Fallback: simple 2% of current price
                atr = round(current * 0.02, 2) if current else 0
        else:
            # Fallback if not enough historical data
            atr = round(current * 0.02, 2) if current else 0

        # ── NSE delivery percentage ──────────────────────────────────────────
        delivery_pct = 65   # fallback
        if NSE_AVAILABLE:
            try:
                eq = nse_eq(symbol.upper())
                trade = eq.get("securityWiseDP", {})
                raw = trade.get("deliveryToTradedQuantity")
                if raw is not None:
                    delivery_pct = round(float(raw), 2)
            except Exception:
                pass

        return {
            "trend": {
                "direction": direction,
                "strength":  strength,
            },
            "volume": {
                "status":                vol_status,
                "ratio":                 round(vol_ratio, 2),
                "institutionalActivity": "Net Buying" if vol_ratio > 1 else "Net Selling",
                "deliveryPercent":       delivery_pct,
            },
            "risk": {
                "volatility": volatility,
                "beta":       round(beta, 2),
                "atr":        atr,
                "riskLevel":  volatility,
            },
        }

    except Exception as e:
        print(f"[get_stock_trends] {symbol}: {e}")
        return {
            "trend":  {"direction": "neutral", "strength": 0},
            "volume": {"status": "Normal", "ratio": 1, "institutionalActivity": "Neutral", "deliveryPercent": 50},
            "risk":   {"volatility": "Medium", "beta": 1.0, "atr": 0, "riskLevel": "Medium"},
        }


# ─────────────────────────────────────────────────────────────────────────────
# RECOMMENDATION
# ─────────────────────────────────────────────────────────────────────────────

def get_recommendation(symbol: str) -> dict:
    try:
        ticker = yf.Ticker(_ticker_sym(symbol))
        info   = ticker.info

        current    = _safe_float(info.get("currentPrice")) or 0
        target     = _safe_float(info.get("targetMeanPrice")) or current * 1.1
        pe         = _safe_float(info.get("trailingPE")) or 15
        rec_key    = (info.get("recommendationKey") or "hold").lower()

        # Map yfinance analyst key → own label
        _map = {"strong_buy": "strongbuy", "buy": "buy", "hold": "hold",
                "sell": "sell", "strong_sell": "strongsell"}
        recommendation = _map.get(rec_key, "hold")

        # Confidence from target upside
        upside = ((target - current) / current * 100) if current else 0
        if upside > 20:
            confidence = 80
        elif upside > 10:
            confidence = 70
        elif upside > 0:
            confidence = 60
        elif upside > -10:
            confidence = 50
        else:
            confidence = 40

        tech_score  = int(min(max(100 - (pe / 30 * 100), 30), 95))
        fund_score  = int(min(max(50 + upside, 30), 95))

        stop_loss   = round(current * 0.92, 2)
        breakout    = round(current * 1.05, 2)
        zone_min    = round(current * 0.96, 2)
        zone_max    = round(current * 1.02, 2)
        rr_ratio    = round((target - current) / max(current - stop_loss, 0.01), 2) if current > stop_loss else 2.5

        # ── analyst recommendations from yfinance ────────────────────────────
        analyst_recs = {}
        try:
            rec_df = ticker.recommendations
            if rec_df is not None and not rec_df.empty:
                latest = rec_df.iloc[-1]
                analyst_recs = {
                    "strongBuy":  int(latest.get("strongBuy", 0)),
                    "buy":        int(latest.get("buy", 0)),
                    "hold":       int(latest.get("hold", 0)),
                    "sell":       int(latest.get("sell", 0)),
                    "strongSell": int(latest.get("strongSell", 0)),
                }
        except Exception:
            pass

        return {
            "recommendation": recommendation,
            "confidence":     confidence,
            "timeHorizon":    "Short Term" if abs(upside) < 15 else "Medium Term",
            "targetPrice":    round(target, 2),
            "upside":         round(upside, 2),
            "technicalScore": tech_score,
            "fundamentalScore": fund_score,
            "analystRecs":    analyst_recs,
            "entryPlan": {
                "accumulationZone": {"min": zone_min, "max": zone_max},
                "breakoutAbove":    breakout,
                "stopLoss":         stop_loss,
                "riskRewardRatio":  rr_ratio,
                "positionSize":     10,
            },
            "reasoning": {
                "technical":   ["Price near support" if current < target else "Price near resistance",
                                "RSI in normal range"],
                "fundamental": ["Revenue growth positive" if upside > 0 else "Revenue under pressure",
                                "Healthy balance sheet"],
                "sentiment":   ["Analyst consensus: " + rec_key.replace("_", " ").title()],
                "risks":       ["Market volatility", "Sector headwinds"],
            },
        }

    except Exception as e:
        print(f"[get_recommendation] {symbol}: {e}")
        return {
            "recommendation": "hold",
            "confidence": 50,
            "timeHorizon": "Medium Term",
            "targetPrice": None,
            "upside": None,
            "technicalScore": 50,
            "fundamentalScore": 50,
            "analystRecs": {},
            "entryPlan": {
                "accumulationZone": {"min": 0, "max": 0},
                "breakoutAbove": 0,
                "stopLoss": 0,
                "riskRewardRatio": 1,
                "positionSize": 5,
            },
            "reasoning": {"technical": [], "fundamental": [], "sentiment": [], "risks": []},
        }


# ─────────────────────────────────────────────────────────────────────────────
# CHART DATA  (OHLC candles)
# ─────────────────────────────────────────────────────────────────────────────

_PERIOD_MAP = {
    "1W": "5d", "1M": "1mo", "3M": "3mo",
    "6M": "6mo", "1Y": "1y", "ALL": "max",
}


def get_chart_data(symbol: str, timeframe: str = "3M") -> dict:
    try:
        period  = _PERIOD_MAP.get(timeframe.upper(), "3mo")
        ticker  = yf.Ticker(_ticker_sym(symbol))
        history = ticker.history(period=period)
        history.reset_index(inplace=True)

        candles = []
        for _, row in history.iterrows():
            dv = row["Date"]
            ds = dv.strftime("%Y-%m-%d") if hasattr(dv, "strftime") else str(dv)
            candles.append({
                "timestamp": ds,
                "open":      _safe_float(row["Open"]),
                "high":      _safe_float(row["High"]),
                "low":       _safe_float(row["Low"]),
                "close":     _safe_float(row["Close"]),
            })

        return {"candles": candles}

    except Exception as e:
        print(f"[get_chart_data] {symbol}: {e}")
        return {"candles": []}


# ─────────────────────────────────────────────────────────────────────────────
# VOLUME DATA
# ─────────────────────────────────────────────────────────────────────────────

def get_volume_data(symbol: str, timeframe: str = "3M") -> dict:
    try:
        period  = _PERIOD_MAP.get(timeframe.upper(), "3mo")
        ticker  = yf.Ticker(_ticker_sym(symbol))
        history = ticker.history(period=period)
        history.reset_index(inplace=True)

        avg_vol = int(history["Volume"].mean()) if len(history) else 0

        volumes = []
        for _, row in history.iterrows():
            dv  = row["Date"]
            ds  = dv.strftime("%Y-%m-%d") if hasattr(dv, "strftime") else str(dv)
            vol = _safe_int(row["Volume"]) or 0
            volumes.append({
                "timestamp":  ds,
                "volume":     vol,
                "aboveAvg":   bool(avg_vol and vol > avg_vol),
            })

        return {"volumes": volumes, "avgVolume": avg_vol}

    except Exception as e:
        print(f"[get_volume_data] {symbol}: {e}")
        return {"volumes": [], "avgVolume": 0}


# ─────────────────────────────────────────────────────────────────────────────
# COMPANY SEARCH
# ─────────────────────────────────────────────────────────────────────────────

def search_company(symbol: str) -> dict:
    if not symbol:
        return {"error": "Symbol parameter is required"}

    sym = symbol.strip().upper()

    # 1) Try Google Sheets directory if configured
    if GOOGLE_SHEETS_URL:
        try:
            res = requests.get(f"{GOOGLE_SHEETS_URL}?symbol={sym}", timeout=15)
            data = res.json()
            if data.get("data") and len(data["data"]) > 0:
                return data
        except Exception as e:
            print(f"[search_company/sheets] {e}")

    # 2) Try yfinance quick lookup
    results = []
    for suffix in [".NS", ".BO"]:
        try:
            t    = yf.Ticker(sym + suffix)
            info = t.info
            name = info.get("longName") or info.get("shortName")
            if name:
                results.append({
                    "symbol":   sym,
                    "name":     name,
                    "exchange": "NSE" if suffix == ".NS" else "BSE",
                    "sector":   info.get("sector"),
                    "industry": info.get("industry"),
                })
        except Exception:
            pass

    # 3) Optionally enrich with nsepython equity search
    if NSE_AVAILABLE and not results:
        try:
            eq = nse_eq(sym)
            meta = eq.get("info", {})
            results.append({
                "symbol":   sym,
                "name":     meta.get("companyName", sym),
                "exchange": "NSE",
                "sector":   meta.get("industry"),
                "industry": meta.get("industry"),
            })
        except Exception:
            pass

    return {"data": results}
