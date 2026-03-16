from __future__ import annotations

import json
import time
import warnings
from datetime import date, timedelta

import gradio as gr
import numpy as np
import pandas as pd
import yfinance as yf
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import train_test_split

warnings.filterwarnings("ignore")


# ══════════════════════════════════════════════════════════
# SANITIZER — orjson (Gradio 6) rejects numpy scalar types
# ══════════════════════════════════════════════════════════
def _sanitize(obj):
    if isinstance(obj, dict):          return {str(k): _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)): return [_sanitize(i) for i in obj]
    if isinstance(obj, np.integer):    return int(obj)
    if isinstance(obj, np.floating):   return float(obj)
    if isinstance(obj, np.bool_):      return bool(obj)
    if isinstance(obj, np.str_):       return str(obj)
    if isinstance(obj, np.ndarray):    return [_sanitize(i) for i in obj.tolist()]
    return obj


# ══════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════
HISTORY_DAYS   = 400
MIN_ROWS       = 60
BACKTEST_DAYS  = 60
FORWARD_DAYS   = 5
MAX_CANDIDATES = 20      # max auto-suggested tickers to fetch & score

RISK_AVERSION  = {"Low": 1.6, "Medium": 1.0, "High": 0.5}
CONC_PENALTY   = 0.8

RF_PARAMS = dict(n_estimators=300, max_depth=5,
                 min_samples_leaf=5, random_state=42, n_jobs=-1)

FEATURE_COLS = ["ret_1d", "ret_5d", "momentum_20d",
                "volatility_20d", "volume_chg_5d", "rsi_14", "sma_ratio"]


# ══════════════════════════════════════════════════════════
# SECTOR PEER MAP  (US + Indian stocks)
# ══════════════════════════════════════════════════════════
SECTOR_PEERS: dict[str, list[str]] = {
    # US Tech
    "AAPL":  ["MSFT", "GOOGL", "META", "AMZN", "NVDA", "QCOM", "ADBE"],
    "MSFT":  ["AAPL", "GOOGL", "META", "AMZN", "NVDA", "CRM",  "ORCL"],
    "GOOGL": ["META", "MSFT",  "AAPL", "AMZN", "SNAP", "TTD",  "PINS"],
    "META":  ["GOOGL","SNAP",  "PINS", "AAPL", "AMZN", "TTD",  "NFLX"],
    "NVDA":  ["AMD",  "INTC",  "QCOM", "AVGO", "TSM",  "ARM",  "MRVL"],
    "TSLA":  ["RIVN", "F",     "GM",   "TM",   "NIO",  "LCID", "STLA"],
    "AMZN":  ["SHOP", "EBAY",  "WMT",  "TGT",  "BABA", "JD",   "ETSY"],
    "AMD":   ["NVDA", "INTC",  "QCOM", "AVGO", "TSM",  "MU",   "MCHP"],
    "NFLX":  ["DIS",  "WBD",   "PARA", "CMCSA","SPOT", "ROKU", "AMZN"],
    "CRM":   ["MSFT", "ORCL",  "NOW",  "WDAY", "ADBE", "INTU", "SAP"],
    # US Finance
    "JPM":   ["BAC",  "WFC",   "GS",   "MS",   "C",    "USB",  "PNC"],
    "BAC":   ["JPM",  "WFC",   "GS",   "MS",   "C",    "USB",  "BK"],
    "GS":    ["MS",   "JPM",   "BAC",  "BX",   "KKR",  "APO",  "C"],
    # US Healthcare
    "JNJ":   ["PFE",  "MRK",   "ABBV", "BMY",  "LLY",  "AMGN", "GILD"],
    "PFE":   ["JNJ",  "MRK",   "ABBV", "BMY",  "LLY",  "MRNA", "BNTX"],
    # US Energy
    "XOM":   ["CVX",  "COP",   "SLB",  "EOG",  "PXD",  "MPC",  "VLO"],
    "CVX":   ["XOM",  "COP",   "SLB",  "EOG",  "PXD",  "PSX",  "HAL"],
    # Indian IT
    "TCS.NS":         ["INFY.NS",      "WIPRO.NS",    "HCLTECH.NS",  "TECHM.NS",    "LTIM.NS",     "PERSISTENT.NS"],
    "INFY.NS":        ["TCS.NS",       "WIPRO.NS",    "HCLTECH.NS",  "TECHM.NS",    "MPHASIS.NS",  "COFORGE.NS"],
    "WIPRO.NS":       ["TCS.NS",       "INFY.NS",     "HCLTECH.NS",  "TECHM.NS",    "LTIM.NS",     "MPHASIS.NS"],
    "HCLTECH.NS":     ["TCS.NS",       "INFY.NS",     "WIPRO.NS",    "TECHM.NS",    "LTIM.NS",     "PERSISTENT.NS"],
    # Indian Banking
    "HDFCBANK.NS":    ["ICICIBANK.NS", "SBIN.NS",     "KOTAKBANK.NS","AXISBANK.NS", "INDUSINDBK.NS","BANDHANBNK.NS"],
    "ICICIBANK.NS":   ["HDFCBANK.NS",  "SBIN.NS",     "KOTAKBANK.NS","AXISBANK.NS", "INDUSINDBK.NS","FEDERALBNK.NS"],
    "SBIN.NS":        ["HDFCBANK.NS",  "ICICIBANK.NS","KOTAKBANK.NS","AXISBANK.NS", "PNB.NS",       "CANBK.NS"],
    # Indian Large Cap
    "RELIANCE.NS":    ["TCS.NS",       "HDFCBANK.NS", "ICICIBANK.NS","INFY.NS",     "HINDUNILVR.NS","BAJFINANCE.NS"],
    "BAJFINANCE.NS":  ["HDFCBANK.NS",  "ICICIBANK.NS","BAJAJFINSV.NS","SBIN.NS",    "CHOLAFIN.NS",  "M&MFIN.NS"],
    "HINDUNILVR.NS":  ["ITC.NS",       "NESTLE.NS",   "BRITANNIA.NS","DABUR.NS",    "MARICO.NS",    "COLPAL.NS"],
    "ITC.NS":         ["HINDUNILVR.NS","NESTLE.NS",   "BRITANNIA.NS","DABUR.NS",    "GODREJCP.NS",  "EMAMILTD.NS"],
}

# Fallback watchlist — shown when portfolio ticker has no peer mapping
US_WATCHLIST = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META",
                "TSLA", "JPM",  "JNJ",   "XOM",  "BRK-B","V",
                "UNH",  "PG",   "HD",    "MA",   "BAC",  "DIS"]

IN_WATCHLIST = ["TCS.NS",      "INFY.NS",     "RELIANCE.NS",  "HDFCBANK.NS",
                "ICICIBANK.NS","HINDUNILVR.NS","BAJFINANCE.NS","SBIN.NS",
                "ITC.NS",      "WIPRO.NS",     "HCLTECH.NS",  "AXISBANK.NS"]


# ══════════════════════════════════════════════════════════
# AUTO-SUGGEST CANDIDATES FROM PORTFOLIO
# ══════════════════════════════════════════════════════════
def suggest_candidates(portfolio_tickers: list[str], max_count: int = MAX_CANDIDATES) -> list[str]:
    """
    Given the user's current holdings, build a candidate pool by:
    1. Adding sector peers for each held ticker (from SECTOR_PEERS map)
    2. Filling remaining slots from the US or Indian watchlist
    3. Removing tickers already in the portfolio (we will still score them
       but the concentration penalty will handle over-weighting)
    4. Capping at max_count to keep runtime reasonable
    """
    pool: list[str] = []

    # Step 1 — Sector peers
    for ticker in portfolio_tickers:
        peers = SECTOR_PEERS.get(ticker, [])
        for p in peers:
            if p not in pool:
                pool.append(p)

    # Step 2 — Fill from watchlist if pool is small
    is_indian = any(".NS" in t or ".BO" in t for t in portfolio_tickers)
    watchlist = IN_WATCHLIST if is_indian else US_WATCHLIST

    for t in watchlist:
        if t not in pool:
            pool.append(t)
        if len(pool) >= max_count * 2:
            break

    # Step 3 — Remove tickers already in portfolio
    pool = [t for t in pool if t not in portfolio_tickers]

    # Step 4 — Cap
    return pool[:max_count]


# ══════════════════════════════════════════════════════════
# YAHOO FINANCE HELPERS
# ══════════════════════════════════════════════════════════
def _candidates_for_ticker(ticker: str) -> list[str]:
    if "." in ticker:
        return [ticker]
    return [ticker, f"{ticker}.NS", f"{ticker}.BO", f"{ticker}.L", f"{ticker}.TO"]


def _download(ticker: str, start: str, end: str, retries: int = 3) -> pd.DataFrame:
    for attempt in range(retries):
        try:
            return yf.download(ticker, start=start, end=end,
                               progress=False, auto_adjust=True)
        except Exception as exc:
            if "RateLimit" in str(exc) or "Too Many" in str(exc):
                if attempt < retries - 1:
                    time.sleep(5 * (attempt + 1))
                    continue
            return pd.DataFrame()
    return pd.DataFrame()


def fetch_ohlcv(ticker: str) -> tuple[pd.DataFrame, str]:
    end   = date.today()
    start = end - timedelta(days=HISTORY_DAYS + 30)

    for candidate in _candidates_for_ticker(ticker):
        df = _download(candidate, start.isoformat(), end.isoformat())
        if df.empty:
            continue
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        needed = {"Open", "High", "Low", "Close", "Volume"}
        if not needed.issubset(df.columns):
            continue
        df = df[list(needed)].dropna().reset_index()
        df.columns = [c.lower() for c in df.columns]
        df["date"]   = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        df["close"]  = pd.to_numeric(df["close"],  errors="coerce")
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
        df = df.dropna()
        if len(df) < MIN_ROWS:
            continue
        return df.tail(HISTORY_DAYS).reset_index(drop=True), candidate

    raise ValueError(f"No data for '{ticker}'")


# ══════════════════════════════════════════════════════════
# FEATURE ENGINEERING
# ══════════════════════════════════════════════════════════
def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    d = close.diff()
    g = d.clip(lower=0).rolling(period).mean()
    l = (-d.clip(upper=0)).rolling(period).mean()
    return 100 - 100 / (1 + g / l.replace(0, np.nan))


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy().sort_values("date").reset_index(drop=True)
    d["ret_1d"]        = d["close"].pct_change(1)
    d["ret_5d"]        = d["close"].pct_change(5)
    d["momentum_20d"]  = d["close"].pct_change(20)
    d["volatility_20d"]= d["close"].pct_change().rolling(20).std()
    d["volume_chg_5d"] = d["volume"].pct_change(5)
    d["rsi_14"]        = _rsi(d["close"])
    d["sma_ratio"]     = d["close"].rolling(10).mean() / d["close"].rolling(20).mean()
    d["target"]        = d["close"].pct_change(FORWARD_DAYS).shift(-FORWARD_DAYS)
    return d.dropna().reset_index(drop=True)


# ══════════════════════════════════════════════════════════
# TRAIN + PREDICT
# ══════════════════════════════════════════════════════════
def train_predict(df_feat: pd.DataFrame) -> dict:
    X = df_feat[FEATURE_COLS].values
    y = df_feat["target"].values
    if len(X) < 20:
        raise ValueError("Not enough rows.")

    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, shuffle=False)
    model = RandomForestRegressor(**RF_PARAMS)
    model.fit(X_tr, y_tr)

    mae  = float(mean_absolute_error(y_te, model.predict(X_te)))
    rmse = float(np.sqrt(mean_squared_error(y_te, model.predict(X_te))))

    latest      = df_feat.iloc[[-1]]
    pred_return = float(model.predict(latest[FEATURE_COLS].values)[0])
    volatility  = float(latest["volatility_20d"].iloc[0])
    last_close  = float(df_feat["close"].iloc[-1])

    return {
        "predicted_return": pred_return,
        "volatility_20d":   volatility,
        "latest_close":     last_close,
        "mae":   mae,
        "rmse":  rmse,
        "model": model,
        "df_feat": df_feat,
    }


# ══════════════════════════════════════════════════════════
# BACKTESTING
# ══════════════════════════════════════════════════════════
def run_backtest(df_feat: pd.DataFrame, model: RandomForestRegressor) -> dict:
    """
    Walk-forward backtest over the last BACKTEST_DAYS rows.

    Strategy rules:
      - Predict 5-day forward return each day
      - predicted_return > 0  → BUY  (enter long, hold 5 days)
      - predicted_return <= 0 → SKIP (stay in cash)

    Tracks:
      - Strategy equity curve vs Buy-and-Hold curve
      - Hit rate: % of buy signals where direction was correct
      - Alpha: strategy return - buy-and-hold return
    """
    n = len(df_feat)
    bt_days = min(BACKTEST_DAYS, n - FORWARD_DAYS - 20)
    if bt_days < 5:
        return {"error": "Not enough data for backtest"}

    test_df = df_feat.iloc[-(bt_days + FORWARD_DAYS):].reset_index(drop=True)

    equity_strategy = [1.0]
    equity_buyhold  = [1.0]
    trades          = []
    correct         = 0
    total_signals   = 0

    for i in range(len(test_df) - FORWARD_DAYS):
        x_pred     = test_df.iloc[[i]][FEATURE_COLS].values
        pred_ret   = float(model.predict(x_pred)[0])
        actual_ret = float(test_df["target"].iloc[i])

        # Buy-and-hold: always in market
        equity_buyhold.append(round(equity_buyhold[-1] * (1 + actual_ret), 6))

        # Strategy: only buy on positive signal
        if pred_ret > 0:
            equity_strategy.append(round(equity_strategy[-1] * (1 + actual_ret), 6))
            total_signals += 1
            direction_correct = (pred_ret > 0) == (actual_ret > 0)
            if direction_correct:
                correct += 1
            trades.append({
                "date":          test_df["date"].iloc[i],
                "signal":        "BUY",
                "predicted_%":   round(pred_ret * 100, 3),
                "actual_%":      round(actual_ret * 100, 3),
                "correct":       direction_correct,
                "pnl_%":         round(actual_ret * 100, 3),
            })
        else:
            equity_strategy.append(equity_strategy[-1])  # hold cash

    strategy_ret = round((equity_strategy[-1] - 1) * 100, 2)
    buyhold_ret  = round((equity_buyhold[-1]  - 1) * 100, 2)
    hit_rate     = round(correct / total_signals * 100, 1) if total_signals else 0.0
    alpha        = round(strategy_ret - buyhold_ret, 2)

    return {
        "period_days":         len(test_df) - FORWARD_DAYS,
        "total_buy_signals":   total_signals,
        "hit_rate_pct":        hit_rate,
        "strategy_return_pct": strategy_ret,
        "buyhold_return_pct":  buyhold_ret,
        "alpha_pct":           alpha,
        "verdict":             "Outperformed" if alpha > 0 else "Underperformed",
        "equity_strategy":     equity_strategy,
        "equity_buyhold":      equity_buyhold,
        "recent_trades":       trades[-10:],
    }


# ══════════════════════════════════════════════════════════
# PORTFOLIO SCORING
# ══════════════════════════════════════════════════════════
def score_and_rank(
    ticker_results: dict[str, dict],
    portfolio_weights: dict[str, float],
    risk_profile: str,
    top_k: int,
) -> list[dict]:
    ra = RISK_AVERSION[risk_profile]
    scored = []

    for ticker, res in ticker_results.items():
        existing_w = portfolio_weights.get(ticker, 0.0)
        pred_ret   = res["predicted_return"]
        vol        = res["volatility_20d"]
        score      = pred_ret - ra * vol - CONC_PENALTY * existing_w

        scored.append({
            "ticker":           ticker,
            "score":            score,
            "predicted_return": pred_ret,
            "volatility_20d":   vol,
            "existing_weight":  existing_w,
            "latest_close":     res["latest_close"],
            "mae":              res["mae"],
            "rmse":             res["rmse"],
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[:top_k]

    # Normalize target weights (proportional to positive scores)
    raw = np.array([max(s["score"], 1e-9) for s in top])
    weights = raw / raw.sum()

    recommendations = []
    for i, s in enumerate(top):
        recommendations.append({
            "rank":             i + 1,
            "ticker":           s["ticker"],
            "score":            round(s["score"],            4),
            "predicted_return": round(s["predicted_return"], 4),
            "volatility_20d":   round(s["volatility_20d"],   4),
            "existing_weight":  round(s["existing_weight"],  4),
            "latest_close":     round(s["latest_close"],     2),
            "target_weight":    round(float(weights[i]),     4),
            "model_mae":        round(s["mae"],              4),
        })

    return recommendations


# ══════════════════════════════════════════════════════════
# MAIN HANDLER
# ══════════════════════════════════════════════════════════
def recommend(
    portfolio_json: str,
    extra_candidates: str,
    risk_profile: str,
    top_k: int,
    run_backtest_flag: bool,
) -> tuple[dict, pd.DataFrame, pd.DataFrame, pd.DataFrame]:

    # ── Parse portfolio ──────────────────────────────────
    try:
        portfolio = json.loads(portfolio_json)
    except json.JSONDecodeError as e:
        raise gr.Error(f"Invalid portfolio JSON: {e}")

    if not isinstance(portfolio, list) or not portfolio:
        raise gr.Error("portfolio_json must be a non-empty array.")

    total_value = sum(float(p["market_value"]) for p in portfolio)
    if total_value <= 0:
        raise gr.Error("Total portfolio value must be > 0.")

    portfolio_weights = {
        p["ticker"].upper(): float(p["market_value"]) / total_value
        for p in portfolio
    }
    portfolio_tickers = list(portfolio_weights.keys())

    # ── Build candidate pool ─────────────────────────────
    # Step 1: Auto-suggest from sector peers
    auto_candidates = suggest_candidates(portfolio_tickers)

    # Step 2: Add any extra tickers the user typed
    extra = [t.strip().upper() for t in extra_candidates.split(",") if t.strip()]
    for t in extra:
        if t not in auto_candidates:
            auto_candidates.append(t)

    # Cap total
    all_candidates = auto_candidates[:MAX_CANDIDATES]

    # ── Fetch data + train per ticker ────────────────────
    ticker_results: dict[str, dict] = {}
    fetch_errors: list[str] = []

    for ticker in all_candidates:
        try:
            df_raw, resolved = fetch_ohlcv(ticker)
            df_feat = build_features(df_raw)
            result  = train_predict(df_feat)
            result["resolved_ticker"] = resolved
            ticker_results[ticker]    = result
        except Exception as e:
            fetch_errors.append(f"{ticker}: {str(e)[:60]}")

    if not ticker_results:
        raise gr.Error("Could not fetch data for any candidate.\n" + "\n".join(fetch_errors))

    # ── Score + rank ─────────────────────────────────────
    recommendations = score_and_rank(
        ticker_results, portfolio_weights, risk_profile, top_k
    )

    # ── Backtest for recommended tickers ────────────────
    backtest_results: dict[str, dict] = {}
    backtest_trades_all: list[dict]   = []

    if run_backtest_flag:
        for rec in recommendations:
            t = rec["ticker"]
            if t in ticker_results:
                bt = run_backtest(
                    ticker_results[t]["df_feat"],
                    ticker_results[t]["model"],
                )
                backtest_results[t] = bt
                for trade in bt.get("recent_trades", []):
                    backtest_trades_all.append({"ticker": t, **trade})

    # ── Build output JSON ────────────────────────────────
    output_json = {
        "risk_profile":       risk_profile,
        "portfolio_total":    round(total_value, 2),
        "portfolio_weights":  {k: round(v, 4) for k, v in portfolio_weights.items()},
        "auto_suggested":     auto_candidates,
        "extra_added":        extra,
        "tickers_scored":     len(ticker_results),
        "fetch_errors":       fetch_errors,
        "recommendations":    recommendations,
        "backtest_summary": {
            t: {
                "period_days":         bt.get("period_days"),
                "total_buy_signals":   bt.get("total_buy_signals"),
                "hit_rate_pct":        bt.get("hit_rate_pct"),
                "strategy_return_pct": bt.get("strategy_return_pct"),
                "buyhold_return_pct":  bt.get("buyhold_return_pct"),
                "alpha_pct":           bt.get("alpha_pct"),
                "verdict":             bt.get("verdict"),
            }
            for t, bt in backtest_results.items()
        },
    }

    # ── Recommendation table ─────────────────────────────
    rec_table = pd.DataFrame([{
        "rank":          r["rank"],
        "ticker":        r["ticker"],
        "score":         r["score"],
        "pred_return":   r["predicted_return"],
        "target_weight": r["target_weight"],
        "close":         r["latest_close"],
        "volatility":    r["volatility_20d"],
        "held_%":        round(r["existing_weight"] * 100, 2),
    } for r in recommendations])

    # ── Backtest summary table ───────────────────────────
    bt_summary_rows = []
    for t, bt in backtest_results.items():
        if "error" not in bt:
            bt_summary_rows.append({
                "ticker":          t,
                "period_days":     bt["period_days"],
                "buy_signals":     bt["total_buy_signals"],
                "hit_rate_%":      bt["hit_rate_pct"],
                "strategy_ret_%":  bt["strategy_return_pct"],
                "buyhold_ret_%":   bt["buyhold_return_pct"],
                "alpha_%":         bt["alpha_pct"],
                "verdict":         bt["verdict"],
            })
    bt_summary_table = pd.DataFrame(bt_summary_rows) if bt_summary_rows else pd.DataFrame(
        columns=["ticker","period_days","buy_signals","hit_rate_%",
                 "strategy_ret_%","buyhold_ret_%","alpha_%","verdict"]
    )

    # ── Recent trades table ──────────────────────────────
    trades_table = pd.DataFrame(backtest_trades_all) if backtest_trades_all else pd.DataFrame(
        columns=["ticker","date","signal","predicted_%","actual_%","correct","pnl_%"]
    )

    return _sanitize(output_json), rec_table, bt_summary_table, trades_table


# ══════════════════════════════════════════════════════════
# SAMPLE DATA
# ══════════════════════════════════════════════════════════
SAMPLE_PORTFOLIO_US = json.dumps([
    {"ticker": "AAPL",  "market_value": 3000},
    {"ticker": "MSFT",  "market_value": 2500},
    {"ticker": "TSLA",  "market_value": 1500},
], indent=2)

SAMPLE_PORTFOLIO_IN = json.dumps([
    {"ticker": "TCS.NS",      "market_value": 50000},
    {"ticker": "HDFCBANK.NS", "market_value": 30000},
    {"ticker": "RELIANCE.NS", "market_value": 20000},
], indent=2)

DESCRIPTION = """
## 📊 Stock Recommendation Engine

**How it works:**
1. You enter your **portfolio** (what you already hold + value)
2. The app **auto-suggests candidates** based on sector peers of your holdings
3. A **RandomForest ML model** fetches live data and predicts 5-day returns for each candidate
4. Stocks are **scored** = `predicted_return − risk_penalty × volatility − concentration_penalty`
5. Optional **backtest** shows how the strategy would have performed over the last 60 days

**Supports:** US stocks (`AAPL`, `NVDA`) and Indian stocks (`TCS.NS`, `RELIANCE.NS`)

> ⚠️ For educational use only — not financial advice.
"""


# ══════════════════════════════════════════════════════════
# GRADIO UI
# ══════════════════════════════════════════════════════════
with gr.Blocks(title="Stock Recommendation Engine") as demo:
    gr.Markdown(DESCRIPTION)

    with gr.Row():
        with gr.Column(scale=1):
            portfolio_input = gr.Textbox(
                label="Your Portfolio (JSON)",
                value=SAMPLE_PORTFOLIO_US,
                lines=8,
                info='Array of {"ticker": "AAPL", "market_value": 3000}',
            )
            extra_input = gr.Textbox(
                label="Add Extra Candidates (optional)",
                value="",
                placeholder="e.g. NFLX, ADBE, COST  — added on top of auto-suggestions",
            )

        with gr.Column(scale=1):
            risk_dropdown = gr.Dropdown(
                choices=["Low", "Medium", "High"],
                value="Medium",
                label="Risk Profile",
                info="Low = penalize volatile stocks more",
            )
            topk_slider = gr.Slider(
                minimum=1, maximum=10, value=5, step=1,
                label="Top-K Recommendations",
            )
            backtest_checkbox = gr.Checkbox(
                value=True,
                label="Run Backtest (last 60 days)",
                info="Tests how signals would have performed historically",
            )
            run_btn = gr.Button("🚀 Analyze & Recommend", variant="primary")

    with gr.Tabs():
        with gr.TabItem("📋 Recommendations"):
            rec_json  = gr.JSON(label="Full Output")
            rec_table = gr.Dataframe(label="Ranked Recommendations", wrap=True)

        with gr.TabItem("📈 Backtest Summary"):
            gr.Markdown(
                "**Strategy vs Buy-and-Hold over last 60 days.**\n\n"
                "- `hit_rate_%` — % of buy signals that got the direction right\n"
                "- `strategy_ret_%` — return if you followed the model's signals\n"
                "- `buyhold_ret_%` — return if you just held the stock\n"
                "- `alpha_%` — how much the model beat buy-and-hold (positive = good)\n"
                "- `verdict` — Outperformed / Underperformed"
            )
            bt_summary_table = gr.Dataframe(label="Backtest Summary per Ticker", wrap=True)

        with gr.TabItem("📝 Recent Trades"):
            gr.Markdown(
                "**Individual buy signals from the backtest.**\n\n"
                "- `predicted_%` — what the model expected\n"
                "- `actual_%` — what actually happened\n"
                "- `correct` — was the direction prediction right?\n"
                "- `pnl_%` — profit/loss on that trade"
            )
            trades_table = gr.Dataframe(label="Recent Trade Log", wrap=True)

    run_btn.click(
        fn=recommend,
        inputs=[portfolio_input, extra_input, risk_dropdown, topk_slider, backtest_checkbox],
        outputs=[rec_json, rec_table, bt_summary_table, trades_table],
    )

    gr.Examples(
        examples=[
            [SAMPLE_PORTFOLIO_US, "",         "Medium", 5, True],
            [SAMPLE_PORTFOLIO_US, "NFLX,ADBE","High",   3, True],
            [SAMPLE_PORTFOLIO_IN, "",         "Low",    3, True],
        ],
        inputs=[portfolio_input, extra_input, risk_dropdown, topk_slider, backtest_checkbox],
    )


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, show_error=True)