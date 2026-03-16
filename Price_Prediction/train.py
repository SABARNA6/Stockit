"""
Chronos is a zero-shot model — no training is required.
This script evaluates forecast accuracy of Chronos on your own data
by backtesting on a held-out window (walk-forward validation).

Usage:
    python train.py --input data/price_history.csv --horizon 5

Required CSV columns: ticker, date, close
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd
import torch
from chronos import ChronosPipeline


def backtest(
    df: pd.DataFrame,
    ticker: str,
    horizon: int,
    context_len: int = 60,
    step: int = 5,
) -> dict:
    series = (
        df[df["ticker"] == ticker]
        .sort_values("date")["close"]
        .astype(float)
        .tolist()
    )

    if len(series) < context_len + horizon:
        raise ValueError(
            f"Need at least {context_len + horizon} rows for ticker {ticker}."
        )

    pipeline = ChronosPipeline.from_pretrained(
        "amazon/chronos-t5-tiny",
        device_map="cpu",
        torch_dtype=torch.float32,
    )

    errors = []
    indices = range(context_len, len(series) - horizon, step)

    for i in indices:
        context = torch.tensor(series[i - context_len : i], dtype=torch.float32).unsqueeze(0)
        samples = pipeline.predict(context=context, prediction_length=horizon, num_samples=20)
        median = np.quantile(samples[0].numpy(), 0.5, axis=0)  # [horizon]
        actual = np.array(series[i : i + horizon])
        errors.append(np.abs(median - actual).mean())

    mae = float(np.mean(errors))
    print(f"Backtest | ticker={ticker} | horizon={horizon}d | windows={len(errors)} | MAE={mae:.4f}")
    return {"ticker": ticker, "horizon": horizon, "windows": len(errors), "mae": mae}


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest Chronos on your price data (no training needed)")
    parser.add_argument("--input", required=True, help="CSV with ticker,date,close")
    parser.add_argument("--horizon", type=int, default=5, help="Forecast horizon in days")
    parser.add_argument("--ticker", default=None, help="Specific ticker to evaluate (default: all)")
    parser.add_argument("--context", type=int, default=60, help="Context window size (rows)")
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    required = {"ticker", "date", "close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    tickers = [args.ticker] if args.ticker else df["ticker"].unique().tolist()
    for t in tickers:
        try:
            backtest(df, t, args.horizon, args.context)
        except ValueError as exc:
            print(f"Skipping {t}: {exc}")


if __name__ == "__main__":
    main()
