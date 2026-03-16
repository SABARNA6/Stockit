from __future__ import annotations

import time
from datetime import date, timedelta

import gradio as gr
import numpy as np
import pandas as pd
import yfinance as yf
from sklearn.ensemble import GradientBoostingRegressor

# ──────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────
CONTEXT_DAYS   = 200
MIN_DATA_POINTS = 30

# Lag & rolling-window sizes (trading days)
LAGS            = [1, 2, 3, 5, 10, 20]
ROLLING_WINDOWS = [5, 10, 20]

# Quantile levels: P10 / P50 / P90
QUANTILES = [0.1, 0.5, 0.9]

# GradientBoostingRegressor hyper-params (fast but solid)
GBM_PARAMS = dict(
    n_estimators=200,
    max_depth=4,
    learning_rate=0.05,
    min_samples_leaf=5,
    subsample=0.8,
    random_state=42,
)


# ──────────────────────────────────────────────
# Yahoo Finance helpers
# ──────────────────────────────────────────────
def _ticker_candidates(ticker: str) -> list[str]:
    """Try bare ticker first, then common exchange suffixes."""
    if "." in ticker:
        return [ticker]
    return [ticker, f"{ticker}.NS", f"{ticker}.BO", f"{ticker}.L", f"{ticker}.TO"]


def _download_with_retry(
    candidate: str,
    start: str,
    end: str,
    retries: int = 3,
    backoff: float = 5.0,
) -> pd.DataFrame:
    """Download with exponential back-off on rate-limit errors."""
    for attempt in range(retries):
        try:
            return yf.download(
                candidate,
                start=start,
                end=end,
                progress=False,
                auto_adjust=True,
            )
        except Exception as exc:
            if "RateLimit" in str(exc) or "Too Many Requests" in str(exc):
                if attempt < retries - 1:
                    time.sleep(backoff * (attempt + 1))
                    continue
            return pd.DataFrame()
    return pd.DataFrame()


def fetch_history(ticker: str) -> tuple[pd.DataFrame, str]:
    """
    Return a clean DataFrame with columns [date, close] and the resolved ticker.
    Raises gr.Error if no data is found for any candidate.
    """
    end   = date.today()
    start = end - timedelta(days=CONTEXT_DAYS + 60)
    candidates = _ticker_candidates(ticker)

    for candidate in candidates:
        df = _download_with_retry(candidate, start.isoformat(), end.isoformat())

        if df.empty:
            continue

        # Flatten MultiIndex columns (newer yfinance versions)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]

        if "Close" not in df.columns:
            continue

        df = (
            df[["Close"]]
            .dropna()
            .tail(CONTEXT_DAYS)
            .reset_index()
        )
        df.columns = [c.lower() for c in df.columns]
        df["date"]  = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        df = df.dropna(subset=["close"])

        if len(df) < MIN_DATA_POINTS:
            continue

        return df, candidate

    raise gr.Error(
        f"No data found for '{ticker}'. Tried: {', '.join(candidates)}. "
        "The symbol may be invalid or Yahoo Finance is rate-limiting — please try again."
    )


# ──────────────────────────────────────────────
# Feature engineering
# ──────────────────────────────────────────────
def make_features(prices: np.ndarray) -> pd.DataFrame:
    """
    Build supervised features from a 1-D price array.
    All features are derived solely from numpy/pandas — zero extra deps.

    Features:
      • Lagged closes         (lag_1 … lag_20)
      • Rolling mean & std    (roll_mean_5/10/20, roll_std_5/10/20)
      • Momentum              (5-day and 20-day % change)
      • Volatility proxy      (20-day rolling std / rolling mean)
    """
    s = pd.Series(prices, dtype=float)
    feats: dict[str, pd.Series] = {}

    for lag in LAGS:
        feats[f"lag_{lag}"] = s.shift(lag)

    for w in ROLLING_WINDOWS:
        rm = s.shift(1).rolling(w).mean()
        rs = s.shift(1).rolling(w).std()
        feats[f"roll_mean_{w}"] = rm
        feats[f"roll_std_{w}"]  = rs

    feats["momentum_5"]  = s.shift(1) / s.shift(6)  - 1
    feats["momentum_20"] = s.shift(1) / s.shift(21) - 1
    feats["volatility"]  = (
        s.shift(1).rolling(20).std() / s.shift(1).rolling(20).mean()
    )

    df = pd.DataFrame(feats)
    df["target"] = s
    return df.dropna()


# ──────────────────────────────────────────────
# Sklearn quantile-GBM forecast
# ──────────────────────────────────────────────
def sklearn_gbm_forecast(
    close_prices: list[float],
    horizon_days: int,
) -> dict[str, list[float]]:
    """
    Train three GradientBoostingRegressor models (P10 / P50 / P90) on the
    full price history, then iteratively predict `horizon_days` steps ahead.

    Dependencies: numpy, pandas, sklearn — nothing else.
    """
    prices  = np.array(close_prices, dtype=float)
    feat_df = make_features(prices)

    feature_cols = [c for c in feat_df.columns if c != "target"]
    X = feat_df[feature_cols].values
    y = feat_df["target"].values

    # Fit one quantile model per level
    models: dict[float, GradientBoostingRegressor] = {}
    for q in QUANTILES:
        models[q] = GradientBoostingRegressor(
            loss="quantile",
            alpha=q,
            **GBM_PARAMS,
        ).fit(X, y)

    # Iterative multi-step prediction
    forecasts: dict[float, list[float]] = {q: [] for q in QUANTILES}
    running   = prices.copy()

    for _ in range(horizon_days):
        row_df = make_features(running)

        if row_df.empty:
            for q in QUANTILES:
                forecasts[q].append(float(running[-1]))
            running = np.append(running, running[-1])
            continue

        x_pred = row_df[feature_cols].iloc[[-1]].values
        step: dict[float, float] = {q: float(models[q].predict(x_pred)[0]) for q in QUANTILES}

        # Propagate median as the "realised" next price
        running = np.append(running, step[0.5])
        for q in QUANTILES:
            forecasts[q].append(step[q])

    return {
        "p10": forecasts[0.1],
        "p50": forecasts[0.5],
        "p90": forecasts[0.9],
    }


# ──────────────────────────────────────────────
# Main Gradio handler
# ──────────────────────────────────────────────
def predict_price(ticker: str, horizon_days: int) -> tuple[dict, pd.DataFrame]:
    ticker = ticker.upper().strip()

    if not ticker:
        raise gr.Error("Please enter a valid ticker symbol (e.g. AAPL or RELIANCE.NS).")

    hist, resolved_ticker = fetch_history(ticker)
    close_prices: list[float] = hist["close"].astype(float).values.tolist()

    forecast = sklearn_gbm_forecast(close_prices, horizon_days)

    current   = close_prices[-1]
    median_p1 = forecast["p50"][0]
    delta     = median_p1 - current
    delta_pct = (delta / current) * 100

    last_date    = pd.to_datetime(hist["date"].iloc[-1])
    future_dates = [
        (last_date + timedelta(days=i + 1)).strftime("%Y-%m-%d")
        for i in range(horizon_days)
    ]

    summary = {
        "ticker":                   ticker,
        "resolved_ticker":          resolved_ticker,
        "model":                    "sklearn GradientBoostingRegressor (quantile)",
        "data_source":              "Yahoo Finance",
        "context_points":           len(close_prices),
        "last_known_date":          hist["date"].iloc[-1],
        "current_close":            round(current, 4),
        "predicted_next_close_p50": round(median_p1, 4),
        "predicted_change":         round(delta, 4),
        "predicted_change_pct":     round(delta_pct, 4),
        "horizon_days":             horizon_days,
        "forecast_p10":             [round(v, 4) for v in forecast["p10"]],
        "forecast_p50":             [round(v, 4) for v in forecast["p50"]],
        "forecast_p90":             [round(v, 4) for v in forecast["p90"]],
    }

    table = pd.DataFrame({
        "date":              future_dates,
        "pessimistic (P10)": [round(v, 4) for v in forecast["p10"]],
        "median (P50)":      [round(v, 4) for v in forecast["p50"]],
        "optimistic (P90)":  [round(v, 4) for v in forecast["p90"]],
    })

    return summary, table


# ──────────────────────────────────────────────
# Gradio UI  (Gradio 6: theme passed to launch())
# ──────────────────────────────────────────────
DESCRIPTION = """
## 📈 Equity Price Prediction — sklearn GBM + Yahoo Finance

Predicts future closing prices using **scikit-learn's GradientBoostingRegressor**
with quantile loss — a pure **numpy / pandas / sklearn** stack with no extra installs.

Three models are trained per request (P10, P50, P90) and predictions are made
iteratively over the chosen horizon.

**Features used:** lag prices (1–20 days), rolling mean & std (5/10/20 days),
5-day & 20-day momentum, 20-day volatility.

**Supported tickers:** `AAPL`, `TSLA`, `RELIANCE.NS`, `BP.L`, `RY.TO`, etc.

> ⚠️ Forecasts are probabilistic estimates — **not** financial advice.
"""

with gr.Blocks(title="Equity Price Prediction") as demo:
    gr.Markdown(DESCRIPTION)

    with gr.Row():
        ticker_input = gr.Textbox(
            label="Ticker Symbol",
            value="AAPL",
            placeholder="e.g. AAPL, TSLA, MSFT, RELIANCE.NS",
            scale=2,
        )
        horizon_slider = gr.Slider(
            minimum=1,
            maximum=14,
            value=5,
            step=1,
            label="Forecast Horizon (days)",
            scale=1,
        )

    run_btn = gr.Button("🔮 Predict", variant="primary")

    with gr.Row():
        json_output  = gr.JSON(label="Prediction Summary")
        table_output = gr.Dataframe(label="Day-by-Day Forecast", wrap=True)

    run_btn.click(
        fn=predict_price,
        inputs=[ticker_input, horizon_slider],
        outputs=[json_output, table_output],
    )

    gr.Examples(
        examples=[
            ["AAPL", 5],
            ["TSLA", 7],
            ["RELIANCE.NS", 3],
            ["BP.L", 10],
        ],
        inputs=[ticker_input, horizon_slider],
    )


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, show_error=True)