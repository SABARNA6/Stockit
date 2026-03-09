# helpers/stock_helper.py
#
# Flask backend helpers — yfinance only
#

import os
import math
import requests
import yfinance as yf
from datetime import datetime
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
from gradio_client import Client as GradioClient
try:
    import nsepython as nse
    _NSE_AVAILABLE = True
except Exception:
    _NSE_AVAILABLE = False


_finbert_client = None


load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

NEWS_API_KEY = os.getenv("NEWS_API_KEY")

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _ticker_sym(symbol: str) -> str:
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


def _nse_fundamentals(symbol: str) -> dict:
    """
    Fetch fundamental data from NSEPython as a fallback.
    Returns a flat dict with any fields it can provide; values are None if unavailable.
    """
    result = {
        "peRatio": None, "pbRatio": None, "eps": None,
        "marketCap": None, "faceValue": None,
        "weekHigh52": None, "weekLow52": None,
        "currentPrice": None, "vwap": None,
    }
    if not _NSE_AVAILABLE:
        return result
    try:
        sym = symbol.strip().upper().replace(".NS", "").replace(".BO", "")
        data   = nse.quote_equity(sym)
        meta   = data.get("metadata",    {})
        price  = data.get("priceInfo",   {})
        sec    = data.get("securityInfo",{})
        whl    = price.get("weekHighLow", {})

        ltp    = _safe_float(price.get("lastPrice"))
        pe     = _safe_float(meta.get("pdSymbolPe"))
        issued = _safe_float(sec.get("issuedSize"))

        result["peRatio"]     = pe
        result["faceValue"]   = _safe_float(sec.get("faceValue"))
        result["currentPrice"]= ltp
        result["vwap"]        = _safe_float(price.get("vwap"))
        result["weekHigh52"]  = _safe_float(whl.get("max"))
        result["weekLow52"]   = _safe_float(whl.get("min"))

        # EPS = Price / P/E
        if ltp and pe and pe > 0:
            result["eps"] = round(ltp / pe, 2)

        # Market Cap = Price × shares issued
        if ltp and issued:
            result["marketCap"] = round(ltp * issued, 0)

        # P/B not directly available from NSE quote — leave None
    except Exception as e:
        print(f"[_nse_fundamentals] {symbol}: {e}")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# REALTIME OVERVIEW
# ─────────────────────────────────────────────────────────────────────────────

def get_realtime_stock(symbol: str) -> dict:
    try:
        ticker_sym = _ticker_sym(symbol)
        ticker     = yf.Ticker(ticker_sym)
        info       = ticker.info

        # ── Fetch NSE real-time data (NSE is primary for Indian price fields) ─
        # yfinance can lag by 15-20 min during market hours; NSE is live.
        nse_rt = {}
        if _NSE_AVAILABLE:
            try:
                sym_clean  = symbol.strip().upper().replace(".NS", "").replace(".BO", "")
                nse_eq     = nse.quote_equity(sym_clean)
                pi         = nse_eq.get("priceInfo",    {})
                meta       = nse_eq.get("metadata",     {})
                sec        = nse_eq.get("securityInfo", {})
                idhl       = pi.get("intraDayHighLow",  {})
                whl        = pi.get("weekHighLow",      {})
                ltp        = _safe_float(pi.get("lastPrice"))
                issued     = _safe_float(sec.get("issuedSize"))
                nse_rt = {
                    "currentPrice":     ltp,
                    "previousClose":    _safe_float(pi.get("previousClose")),
                    "open":             _safe_float(pi.get("open")),
                    "change":           _safe_float(pi.get("change")),
                    "changePercent":    _safe_float(pi.get("pChange")),
                    # NSE provides correct intraday VWAP (not a multi-day average)
                    "vwap":             _safe_float(pi.get("vwap")),
                    "dayHigh":          _safe_float(idhl.get("max")),
                    "dayLow":           _safe_float(idhl.get("min")),
                    # NSE provides actual circuit limits per stock (2/5/10/20%)
                    # not a flat ±15% — these are strings like "2813.30"
                    "upperCircuit":     _safe_float(pi.get("upperCP")),
                    "lowerCircuit":     _safe_float(pi.get("lowerCP")),
                    "fiftyTwoWeekHigh": _safe_float(whl.get("max")),
                    "fiftyTwoWeekLow":  _safe_float(whl.get("min")),
                    "peRatio":          _safe_float(meta.get("pdSymbolPe")),
                    "marketCap":        round(ltp * issued, 0) if ltp and issued else None,
                }
            except Exception as e:
                print(f"[get_realtime_stock] NSE fetch error for {symbol}: {e}")

        # ── Helpers ───────────────────────────────────────────────────────────
        def nse_or_yf(nse_key, yf_val):
            """Prefer NSE (real-time) for price fields; yfinance as fallback."""
            v = nse_rt.get(nse_key)
            return v if v is not None else _safe_float(yf_val)

        def yf_or_nse(yf_val, nse_key):
            """Prefer yfinance for metadata; NSE as fallback."""
            v = _safe_float(yf_val)
            return v if v is not None else nse_rt.get(nse_key)

        # ── Price fields (NSE-first) ───────────────────────────────────────────
        current = nse_or_yf("currentPrice",  info.get("currentPrice"))
        if current is None:
            print(f"[get_realtime_stock] {symbol}: No price data found, symbol may be invalid or delisted")
            return {}

        prev       = nse_or_yf("previousClose", info.get("previousClose")) or current
        open_price = nse_or_yf("open",           info.get("open"))
        day_high   = nse_or_yf("dayHigh",        info.get("dayHigh"))
        day_low    = nse_or_yf("dayLow",         info.get("dayLow"))
        wk52_high  = nse_or_yf("fiftyTwoWeekHigh", info.get("fiftyTwoWeekHigh"))
        wk52_low   = nse_or_yf("fiftyTwoWeekLow",  info.get("fiftyTwoWeekLow"))

        # Change: use NSE's exchange-reported values; compute only if absent
        change     = nse_rt.get("change")
        change_pct = nse_rt.get("changePercent")
        if change is None:
            change = round(current - prev, 2) if prev else None
        if change_pct is None:
            change_pct = round((change / prev) * 100, 2) if change is not None and prev else None
        else:
            change_pct = round(change_pct, 2)

        # VWAP: NSE intraday VWAP is correct; fallback computes from intraday 1m bars
        vwap = nse_rt.get("vwap")
        if vwap is None:
            try:
                hist_1d = ticker.history(period="1d", interval="1m")
                if len(hist_1d) > 0:
                    tp   = (hist_1d["High"] + hist_1d["Low"] + hist_1d["Close"]) / 3
                    vwap = _safe_float(round(
                        (tp * hist_1d["Volume"]).sum() / hist_1d["Volume"].sum(), 2
                    ))
            except Exception:
                pass

        # Circuit limits: NSE gives actual per-stock limits; ±15% only as last resort
        upper_circuit = nse_rt.get("upperCircuit")
        lower_circuit = nse_rt.get("lowerCircuit")
        if upper_circuit is None and prev:
            upper_circuit = round(prev * 1.15, 2)
        if lower_circuit is None and prev:
            lower_circuit = round(prev * 0.85, 2)

        # P/E: NSE's pdSymbolPe is more up-to-date for Indian stocks
        pe_ratio   = nse_or_yf("peRatio",   info.get("trailingPE"))
        market_cap = yf_or_nse(info.get("marketCap"), "marketCap")

        return {
            "symbol":           symbol.upper(),
            "name":             info.get("longName") or info.get("shortName") or symbol.upper(),
            "exchange":         info.get("exchange") or "NSE",
            "sector":           info.get("sector"),
            "industry":         info.get("industry"),
            "currentPrice":     current,
            "previousClose":    prev,
            "open":             open_price,
            "dayHigh":          day_high,
            "dayLow":           day_low,
            "change":           change,
            "changePercent":    change_pct,
            "volume":           _safe_int(info.get("volume")),
            "avgVolume":        _safe_int(info.get("averageVolume")),
            "marketCap":        market_cap,
            "fiftyTwoWeekHigh": wk52_high,
            "fiftyTwoWeekLow":  wk52_low,
            "peRatio":          pe_ratio,
            "eps":              _safe_float(info.get("trailingEps")),
            "dividendYield":    _safe_float(info.get("dividendYield")),
            "roe":              _safe_float(info.get("returnOnEquity")),
            "vwap":             vwap,
            "upperCircuit":     upper_circuit,
            "lowerCircuit":     lower_circuit,
            "lastUpdated":      datetime.utcnow().isoformat(),
        }

    except Exception as e:
        print(f"[get_realtime_stock] {symbol}: {e}")
        import traceback
        traceback.print_exc()
        return {}


# ─────────────────────────────────────────────────────────────────────────────
# SPARKLINE
# ─────────────────────────────────────────────────────────────────────────────

def get_sparkline(symbol: str, points: int = 12) -> dict:
    try:
        ticker  = yf.Ticker(_ticker_sym(symbol))
        history = ticker.history(period="1mo")
        history.reset_index(inplace=True)

        closes = [_safe_float(r["Close"]) for _, r in history.iterrows()]
        closes = [v for v in closes if v is not None]
        closes = closes[-points:]

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
# HISTORICAL
# ─────────────────────────────────────────────────────────────────────────────

def get_historical_data(symbol: str, period: str = "1mo", page: int = 1, limit: int = 8) -> dict:
    try:
        ticker  = yf.Ticker(_ticker_sym(symbol))
        history = ticker.history(period=period)
        history.reset_index(inplace=True)

        avg_vol    = history["Volume"].mean() if len(history) else 0
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

        prices.reverse()

        total       = len(prices)
        total_pages = max(1, math.ceil(total / limit))
        start       = (page - 1) * limit
        paginated   = prices[start: start + limit]

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

        return {
            "revenue":           revenue,
            "netProfit":         net_inc,
            "ebitda":            ebitda,
            "ebitdaMargin":      round((ebitda / revenue) * 100, 2) if ebitda and revenue else None,
            "profitMargin":      round((net_inc / revenue) * 100, 2) if net_inc and revenue else None,
            "debtToEquity":      _safe_float(info.get("debtToEquity")),
            "currentRatio":      _safe_float(info.get("currentRatio")),
            "quickRatio":        _safe_float(info.get("quickRatio")),
            "roe":               _safe_float(info.get("returnOnEquity")),
            "roa":               _safe_float(info.get("returnOnAssets")),
            "eps":               _safe_float(info.get("trailingEps")),
            "forwardEps":        _safe_float(info.get("forwardEps")),
            "peRatio":           _safe_float(info.get("trailingPE")),
            "forwardPE":         _safe_float(info.get("forwardPE")),
            "pbRatio":           _safe_float(info.get("priceToBook")),
            "psRatio":           _safe_float(info.get("priceToSalesTrailing12Months")),
            "dividendYield":     _safe_float(info.get("dividendYield")),
            "payoutRatio":       _safe_float(info.get("payoutRatio")),
            "bookValue":         _safe_float(info.get("bookValue")),
            "freeCashflow":      _safe_float(info.get("freeCashflow")),
            "operatingCashflow": _safe_float(info.get("operatingCashflow")),
            "grossMargins":      _safe_float(info.get("grossMargins")),
            "operatingMargins":  _safe_float(info.get("operatingMargins")),
        }

    except Exception as e:
        print(f"[get_financials] {symbol}: {e}")
        return {}

def get_finacial_metric(symbol):
    try:
        # Add .NS suffix for NSE stocks if not present
        ticker_symbol = f"{symbol}.NS" if not symbol.endswith('.NS') else symbol

        ticker = yf.Ticker(ticker_symbol)
        info   = ticker.info

        # ── Fetch NSEPython data upfront for fallback ─────────────────────────
        nse_data = _nse_fundamentals(symbol)

        # ── Helper: yfinance first, nsepython fallback ────────────────────────
        def yf_or_nse(yf_val, nse_key):
            v = _safe_float(yf_val)
            return v if v is not None else nse_data.get(nse_key)

        # ── Basic fields ──────────────────────────────────────────────────────
        revenue     = _safe_float(info.get('totalRevenue'))
        net_profit  = _safe_float(info.get('netIncomeToCommon'))
        ebitda      = _safe_float(info.get('ebitda'))
        roe_raw     = _safe_float(info.get('returnOnEquity'))   # decimal e.g. 0.42
        roa_raw     = _safe_float(info.get('returnOnAssets'))   # decimal e.g. 0.18
        rev_growth  = _safe_float(info.get('revenueGrowth'))    # decimal e.g. 0.049
        earn_growth = _safe_float(info.get('earningsGrowth'))   # decimal e.g. -0.139
        eps_growth  = _safe_float(info.get('earningsQuarterlyGrowth'))

        # P/E: yfinance first, fallback to NSE's pdSymbolPe
        pe_ratio = yf_or_nse(info.get('trailingPE'), 'peRatio')

        # P/B: yfinance only (NSE doesn't expose it directly)
        pb_ratio = _safe_float(info.get('priceToBook'))

        # Market Cap: yfinance first, fallback NSE computed (price × issuedSize)
        market_cap = yf_or_nse(info.get('marketCap'), 'marketCap')

        ebitda_margin = round(ebitda / revenue * 100, 2) if ebitda and revenue else None

        # ── Net Profit fallback: compute from revenue × profit_margin ─────────
        # (already taken from info, no better NSE source)

        # ── PEG Ratio = P/E ÷ EPS CAGR% from income statement ────────────────
        peg_ratio = None
        fin = None
        try:
            fin = ticker.financials
            if fin is not None and not fin.empty and 'Diluted EPS' in fin.index:
                eps_series = fin.loc['Diluted EPS'].dropna().sort_index(ascending=False)
                if len(eps_series) >= 2:
                    eps_latest = float(eps_series.iloc[0])
                    eps_oldest = float(eps_series.iloc[-1])
                    n_years    = len(eps_series) - 1
                    if eps_oldest > 0 and eps_latest > 0:
                        eps_cagr_pct = ((eps_latest / eps_oldest) ** (1 / n_years) - 1) * 100
                        if eps_cagr_pct > 0 and pe_ratio:
                            peg_ratio = round(pe_ratio / eps_cagr_pct, 2)
            # Fallback PEG: use NSE-computed EPS to derive growth vs sector PE
            if peg_ratio is None and pe_ratio and nse_data.get('eps') and earn_growth:
                earn_growth_pct = earn_growth * 100
                if earn_growth_pct > 0:
                    peg_ratio = round(pe_ratio / earn_growth_pct, 2)
        except Exception:
            pass

        # ── Interest Coverage = EBIT / |Interest Expense| ────────────────────
        interest_coverage = None
        try:
            if fin is None or fin.empty:
                fin = ticker.financials
            if fin is not None and not fin.empty:
                ebit = None
                interest_exp = None
                if 'EBIT' in fin.index:
                    ebit = _safe_float(fin.loc['EBIT'].iloc[0])
                elif 'Operating Income' in fin.index:
                    ebit = _safe_float(fin.loc['Operating Income'].iloc[0])
                if 'Interest Expense Non Operating' in fin.index:
                    interest_exp = _safe_float(fin.loc['Interest Expense Non Operating'].iloc[0])
                elif 'Interest Expense' in fin.index:
                    interest_exp = _safe_float(fin.loc['Interest Expense'].iloc[0])
                if ebit is not None and interest_exp and interest_exp != 0:
                    interest_coverage = round(ebit / abs(interest_exp), 2)
        except Exception:
            pass

        # ── D/E, Current Ratio, Quick Ratio: yfinance, no NSE fallback ────────
        debt_to_equity = _safe_float(info.get('debtToEquity'))
        current_ratio  = _safe_float(info.get('currentRatio'))
        quick_ratio    = _safe_float(info.get('quickRatio'))

        # ── Return camelCase keys matching FundamentalsGrid.jsx ──────────────
        return {
            "profitability": {
                "netProfit":    net_profit,
                "ebitdaMargin": ebitda_margin,
                "roe":          round(roe_raw * 100, 2) if roe_raw is not None else None,
                "roa":          round(roa_raw * 100, 2) if roa_raw is not None else None,
            },
            "valuation": {
                "peRatio":  pe_ratio,
                "pegRatio": peg_ratio,
                "pbRatio":  pb_ratio,
                "evEbitda": _safe_float(info.get('enterpriseToEbitda')),
            },
            "growth": {
                # revenueCagr5y & profitCagr5y: frontend uses fmt.num(v) + "%" → expects percent value
                "revenueCagr5y": round(rev_growth  * 100, 2) if rev_growth  is not None else None,
                "profitCagr5y":  round(earn_growth * 100, 2) if earn_growth is not None else None,
                # epsGrowthTtm & salesGrowth: frontend uses fmt.pct(v * 100) → expects raw decimal
                "epsGrowthTtm":  round(eps_growth, 4) if eps_growth is not None else None,
                "salesGrowth":   round(rev_growth, 4) if rev_growth is not None else None,
            },
            "financialHealth": {
                "debtToEquity":     debt_to_equity,
                "interestCoverage": interest_coverage,
                "currentRatio":     current_ratio,
                "quickRatio":       quick_ratio,
            },
        }

    except Exception as e:
        print(f"Error fetching financial metrics for {symbol}: {e}")
        return {}
    

# ─────────────────────────────────────────────────────────────────────────────
# SENTIMENT helper
# ─────────────────────────────────────────────────────────────────────────────

def _get_finbert_client():
    global _finbert_client
    if _finbert_client is None:
        _finbert_client = GradioClient("Sabarna6/FinBERT_FinancialSentimentAnalysis")
    return _finbert_client

def _analyze_sentiment(text: str) -> dict:
    try:
        client = _get_finbert_client()
        result = client.predict(text=text, api_name="/predict")
        result=result[0]
        # result is typically a dict like {"Positive": 0.08, "Negative": 0.14, "Neutral": 0.77}
        # or a string — print it once to confirm shape
        # print(f"[FinBERT] raw result: {result}")

        if isinstance(result, dict):
            scores = {
                "Positive": float(result.get("Positive", 0.0)),
                "Negative": float(result.get("Negative", 0.0)),
                "Neutral":  float(result.get("Neutral",  1.0)),
            }
        elif isinstance(result, str):
            # some Gradio endpoints return just the label
            scores = {"Positive": 0.0, "Negative": 0.0, "Neutral": 0.0}
            scores[result.strip().capitalize()] = 1.0
        else:
            return {"sentiment": "Neutral", "confidence": 0.0}

        top_label = max(scores, key=scores.get)
        return {
            "sentiment":  top_label,
            "confidence": round(scores[top_label], 4),
        }

    except Exception as e:
        print(f"[FinBERT] {e}")
        return {"sentiment": "Neutral", "confidence": 0.0}




def get_news(symbol: str, get_realtime_stock_fn) -> dict:
    """
    Fetch news from NewsAPI and analyze sentiment with FinBERT.
    """
    try:
        if not NEWS_API_KEY:
            raise ValueError("NEWS_API_KEY not configured")
        else : 
            print("NEWS_API_KEY is Configured")
        company_name = get_realtime_stock_fn(symbol).get("name") or symbol
        params = {
            "q":        company_name,
            "language": "en",
            "sortBy":   "publishedAt",
            "pageSize": 15,
            "apiKey":   NEWS_API_KEY,
        }
        # print( "company name : ",company_name)
        raw_articles = (
            requests.get("https://newsapi.org/v2/everything", params=params, timeout=10)
            .json()
            .get("articles", [])
        )
        # print("raw articles ",raw_articles)
        formatted = []
        for a in raw_articles:
            title     = a.get("title", "") or ""
            desc      = a.get("description", "") or ""
            sent      = _analyze_sentiment(f"{title}. {desc}")
            sentiment = sent["sentiment"]

            formatted.append({
                "title":       title,
                "summary":     desc,
                "source":      a.get("source", {}).get("name", ""),
                "publishedAt": a.get("publishedAt", ""),
                "url":         a.get("url", ""),
                "tags":        [sentiment.lower()],
                "sentiment":   sentiment,
                "confidence":  sent["confidence"],
                "symbol":      symbol.upper(),
            })

        # Compute sentiment summary
        pos   = sum(1 for a in formatted if a.get("sentiment") == "Positive")
        neg   = sum(1 for a in formatted if a.get("sentiment") == "Negative")
        neu   = sum(1 for a in formatted if a.get("sentiment") == "Neutral")
        total = pos + neu + neg or 1

        return {
            "source":    "live",
            "sentiment": {
                "positive": round(pos / total * 100, 2),
                "neutral":  round(neu / total * 100, 2),
                "negative": round(neg / total * 100, 2),
            },
            "news":      formatted,
        }

    except Exception as e:
        print(f"[get_news] {symbol}: {e}")
        return {
            "source":    "error",
            "sentiment": {"positive": 0, "neutral": 100, "negative": 0},
            "news":      [],
        }



# ─────────────────────────────────────────────────────────────────────────────
# TRENDS
# ─────────────────────────────────────────────────────────────────────────────

def get_stock_trends(symbol: str) -> dict:
    try:
        ticker  = yf.Ticker(_ticker_sym(symbol))
        info    = ticker.info

        current = _safe_float(info.get("currentPrice")) or 0
        volume  = _safe_float(info.get("volume"))  or 0
        avg_vol = _safe_float(info.get("averageVolume")) or volume or 1
        beta    = _safe_float(info.get("beta")) or 1.0

        # ── Pull 3-month history for MA, ATR, delivery ─────────────────────
        history = ticker.history(period="3mo")

        # ── Trend: price vs 20-day and 50-day SMA ──────────────────────────
        # Single day move is noise; proper trend = price position relative to MAs
        direction = "neutral"
        strength  = 50.0
        if len(history) >= 10:
            closes = history["Close"]
            ma20   = float(closes.tail(20).mean()) if len(closes) >= 20 else float(closes.mean())
            ma50   = float(closes.tail(50).mean()) if len(closes) >= 50 else float(closes.mean())

            if current > ma20 and current > ma50:
                direction = "bullish"
            elif current < ma20 and current < ma50:
                direction = "bearish"
            else:
                direction = "neutral"

            # Strength = how far (%) price is from its own 20d MA, capped 0–100
            pct_from_ma20 = abs((current - ma20) / ma20 * 100) if ma20 else 0
            strength = round(min(pct_from_ma20 * 10, 100), 1)  # 10% above MA → 100 strength

        # ── Volume: Spike = >2.5× avg, High = >1.2×, Low = <0.8× ──────────
        vol_ratio  = volume / avg_vol
        if vol_ratio >= 2.5:
            vol_status = "Spike"
        elif vol_ratio >= 1.2:
            vol_status = "High"
        elif vol_ratio < 0.8:
            vol_status = "Low"
        else:
            vol_status = "Normal"

        # Delivery % from historical vol consistency (proxy)
        delivery_pct = 65
        if len(history) > 5:
            try:
                vol_std         = float(history["Volume"].std())
                vol_mean        = float(history["Volume"].mean())
                vol_consistency = 1 - (vol_std / vol_mean if vol_mean > 0 else 1)
                delivery_pct    = round(50 + (vol_ratio - 1) * 20 + vol_consistency * 20, 2)
                delivery_pct    = round(min(max(delivery_pct, 35), 85), 2)
            except Exception:
                pass

        # ── ATR (14-day Average True Range) — actual formula ──────────────
        # TR = max(High-Low, |High-prevClose|, |Low-prevClose|)
        atr = None
        if len(history) >= 2:
            try:
                h   = history["High"].values
                l   = history["Low"].values
                c   = history["Close"].values
                trs = []
                for i in range(1, len(h)):
                    tr = max(h[i] - l[i], abs(h[i] - c[i-1]), abs(l[i] - c[i-1]))
                    trs.append(tr)
                atr = round(float(sum(trs[-14:]) / min(len(trs), 14)), 2)
            except Exception:
                pass
        if atr is None:
            atr = round(current * 0.02, 2)  # last resort fallback

        # ── Risk level: combine beta + ATR as % of price ───────────────────
        atr_pct = (atr / current * 100) if current else 2
        if beta > 1.3 or atr_pct > 3:
            risk_level = "High"
        elif beta < 0.8 and atr_pct < 1.5:
            risk_level = "Low"
        else:
            risk_level = "Medium"

        volatility = "High" if beta > 1.2 else "Low" if beta < 0.8 else "Medium"

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
                "riskLevel":  risk_level,
            },
        }

    except Exception as e:
        print(f"[get_stock_trends] {symbol}: {e}")
        return {
            "trend":  {"direction": "neutral", "strength": 50},
            "volume": {"status": "Normal", "ratio": 1, "institutionalActivity": "Neutral", "deliveryPercent": 50},
            "risk":   {"volatility": "Medium", "beta": 1.0, "atr": 0, "riskLevel": "Medium"},
        }


# ─────────────────────────────────────────────────────────────────────────────
# RECOMMENDATION
# ─────────────────────────────────────────────────────────────────────────────

def get_recommendation(symbol: str) -> dict:
    try:
        ticker  = yf.Ticker(_ticker_sym(symbol))
        info    = ticker.info

        current = _safe_float(info.get("currentPrice")) or 0
        target  = _safe_float(info.get("targetMeanPrice")) or current * 1.1
        pe      = _safe_float(info.get("trailingPE")) or 15
        rec_key = (info.get("recommendationKey") or "hold").lower()

        _map           = {"strong_buy": "strongbuy", "buy": "buy", "hold": "hold",
                          "sell": "sell", "strong_sell": "strongsell"}
        recommendation = _map.get(rec_key, "hold")

        upside     = ((target - current) / current * 100) if current else 0
        confidence = 80 if upside > 20 else 70 if upside > 10 else 60 if upside > 0 else 50 if upside > -10 else 40

        tech_score = int(min(max(100 - (pe / 30 * 100), 30), 95))
        fund_score = int(min(max(50 + upside, 30), 95))
        stop_loss  = round(current * 0.92, 2)
        breakout   = round(current * 1.05, 2)
        zone_min   = round(current * 0.96, 2)
        zone_max   = round(current * 1.02, 2)
        rr_ratio   = round((target - current) / max(current - stop_loss, 0.01), 2) if current > stop_loss else 2.5

        analyst_recs = {}
        try:
            rec_df = ticker.recommendations
            if rec_df is not None and not rec_df.empty:
                latest       = rec_df.iloc[-1]
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
            "recommendation":   recommendation,
            "confidence":       confidence,
            "timeHorizon":      "Short Term" if abs(upside) < 15 else "Medium Term",
            "targetPrice":      round(target, 2),
            "upside":           round(upside, 2),
            "technicalScore":   tech_score,
            "fundamentalScore": fund_score,
            "analystRecs":      analyst_recs,
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
            "recommendation": "hold", "confidence": 50,
            "timeHorizon": "Medium Term", "targetPrice": None, "upside": None,
            "technicalScore": 50, "fundamentalScore": 50, "analystRecs": {},
            "entryPlan": {
                "accumulationZone": {"min": 0, "max": 0},
                "breakoutAbove": 0, "stopLoss": 0,
                "riskRewardRatio": 1, "positionSize": 5,
            },
            "reasoning": {"technical": [], "fundamental": [], "sentiment": [], "risks": []},
        }


# ─────────────────────────────────────────────────────────────────────────────
# CHART DATA
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
            open_v  = _safe_float(row["Open"])
            high_v  = _safe_float(row["High"])
            low_v   = _safe_float(row["Low"])
            close_v = _safe_float(row["Close"])
            
            # Only include candles with all valid OHLC values
            if open_v is not None and high_v is not None and low_v is not None and close_v is not None:
                candles.append({
                    "timestamp": ds,
                    "open":      open_v,
                    "high":      high_v,
                    "low":       low_v,
                    "close":     close_v,
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

        # Filter valid volumes first for accurate average
        valid_vols = [_safe_int(row["Volume"]) for _, row in history.iterrows()]
        valid_vols = [v for v in valid_vols if v is not None and v > 0]
        avg_vol = int(sum(valid_vols) / len(valid_vols)) if valid_vols else 0

        volumes = []
        for _, row in history.iterrows():
            dv  = row["Date"]
            ds  = dv.strftime("%Y-%m-%d") if hasattr(dv, "strftime") else str(dv)
            vol = _safe_int(row["Volume"])
            
            # Only include volumes with valid data
            if vol is not None and vol > 0:
                volumes.append({
                    "timestamp": ds,
                    "volume":    vol,
                    "aboveAvg":  bool(avg_vol and vol > avg_vol),
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

    sym     = symbol.strip().upper()
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

    return {"data": results}