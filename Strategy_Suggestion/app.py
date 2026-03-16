 from __future__ import annotations

import json
from pathlib import Path

import gradio as gr
import joblib
import numpy as np
import pandas as pd


MODEL_PATH = Path("models/strategy_model.joblib")
FEATURE_COLS = ["ret_1d", "ret_5d", "sma_ratio", "volatility_10d", "rsi_14", "atr_14"]


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift(1)).abs()
    low_close = (df["low"] - df["close"].shift(1)).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    data["date"] = pd.to_datetime(data["date"])
    data = data.sort_values("date").reset_index(drop=True)
    data["ret_1d"] = data["close"].pct_change()
    data["ret_5d"] = data["close"].pct_change(5)
    data["sma_10"] = data["close"].rolling(10).mean()
    data["sma_20"] = data["close"].rolling(20).mean()
    data["sma_ratio"] = data["sma_10"] / data["sma_20"]
    data["volatility_10d"] = data["ret_1d"].rolling(10).std()
    data["rsi_14"] = rsi(data["close"])
    data["atr_14"] = atr(data)
    return data


def load_bundle() -> dict | None:
    if MODEL_PATH.exists():
        return joblib.load(MODEL_PATH)
    return None


MODEL_BUNDLE = load_bundle()


def predict_signal(ticker: str, ohlcv_json: str):
    default_ohlcv = [
        {"date": "2026-01-01", "open": 100, "high": 102, "low": 99, "close": 101, "volume": 1000000},
        {"date": "2026-01-02", "open": 101, "high": 103, "low": 100, "close": 102, "volume": 1100000},
        {"date": "2026-01-03", "open": 102, "high": 103, "low": 101, "close": 102.5, "volume": 900000},
        {"date": "2026-01-04", "open": 102.5, "high": 104, "low": 102, "close": 103.6, "volume": 1200000},
        {"date": "2026-01-05", "open": 103.6, "high": 105, "low": 103, "close": 104.2, "volume": 1250000},
        {"date": "2026-01-06", "open": 104.2, "high": 106, "low": 104, "close": 105.4, "volume": 1300000},
        {"date": "2026-01-07", "open": 105.4, "high": 106, "low": 104.8, "close": 105.1, "volume": 1150000},
        {"date": "2026-01-08", "open": 105.1, "high": 106.2, "low": 104.9, "close": 105.8, "volume": 1180000},
        {"date": "2026-01-09", "open": 105.8, "high": 107.0, "low": 105.5, "close": 106.9, "volume": 1400000},
        {"date": "2026-01-10", "open": 106.9, "high": 108.2, "low": 106.5, "close": 107.7, "volume": 1500000},
        {"date": "2026-01-11", "open": 107.7, "high": 109.1, "low": 107.0, "close": 108.6, "volume": 1600000},
        {"date": "2026-01-12", "open": 108.6, "high": 109.5, "low": 108.2, "close": 109.0, "volume": 1480000},
        {"date": "2026-01-13", "open": 109.0, "high": 109.8, "low": 108.4, "close": 109.2, "volume": 1410000},
        {"date": "2026-01-14", "open": 109.2, "high": 110.4, "low": 108.9, "close": 110.0, "volume": 1620000},
        {"date": "2026-01-15", "open": 110.0, "high": 111.0, "low": 109.5, "close": 110.7, "volume": 1700000},
        {"date": "2026-01-16", "open": 110.7, "high": 112.0, "low": 110.0, "close": 111.6, "volume": 1750000},
        {"date": "2026-01-17", "open": 111.6, "high": 112.3, "low": 111.1, "close": 111.9, "volume": 1690000},
        {"date": "2026-01-18", "open": 111.9, "high": 113.0, "low": 111.4, "close": 112.8, "volume": 1800000},
        {"date": "2026-01-19", "open": 112.8, "high": 114.1, "low": 112.2, "close": 113.7, "volume": 1900000},
        {"date": "2026-01-20", "open": 113.7, "high": 114.4, "low": 113.1, "close": 113.9, "volume": 1880000},
        {"date": "2026-01-21", "open": 113.9, "high": 115.0, "low": 113.5, "close": 114.7, "volume": 1950000},
        {"date": "2026-01-22", "open": 114.7, "high": 116.1, "low": 114.2, "close": 115.8, "volume": 2050000},
        {"date": "2026-01-23", "open": 115.8, "high": 116.4, "low": 115.0, "close": 115.4, "volume": 1980000},
        {"date": "2026-01-24", "open": 115.4, "high": 117.0, "low": 115.1, "close": 116.7, "volume": 2080000},
        {"date": "2026-01-25", "open": 116.7, "high": 118.2, "low": 116.3, "close": 117.9, "volume": 2200000},
        {"date": "2026-01-26", "open": 117.9, "high": 118.6, "low": 117.1, "close": 117.4, "volume": 2100000},
        {"date": "2026-01-27", "open": 117.4, "high": 118.9, "low": 117.0, "close": 118.2, "volume": 2150000},
        {"date": "2026-01-28", "open": 118.2, "high": 119.3, "low": 117.8, "close": 118.9, "volume": 2250000},
        {"date": "2026-01-29", "open": 118.9, "high": 120.0, "low": 118.3, "close": 119.5, "volume": 2300000},
        {"date": "2026-01-30", "open": 119.5, "high": 121.0, "low": 119.2, "close": 120.6, "volume": 2400000}
    ]

    rows = json.loads(ohlcv_json) if ohlcv_json.strip() else default_ohlcv
    df = pd.DataFrame(rows)

    required = {"date", "open", "high", "low", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        raise gr.Error(f"Missing OHLCV fields: {sorted(missing)}")

    feat = add_features(df).dropna(subset=FEATURE_COLS).tail(1)
    if feat.empty:
        raise gr.Error("Need at least 30 rows for stable indicators.")

    close = float(feat["close"].iloc[0])
    atr_val = float(feat["atr_14"].iloc[0])

    if MODEL_BUNDLE is None:
        score = 0.6 * float(feat["ret_5d"].iloc[0]) + 0.4 * float(feat["sma_ratio"].iloc[0] - 1.0)
        if score > 0.005:
            action = "buy"
            confidence = min(0.55 + abs(score) * 10, 0.9)
        elif score < -0.005:
            action = "sell"
            confidence = min(0.55 + abs(score) * 10, 0.9)
        else:
            action = "hold"
            confidence = 0.55
        probs = {
            "sell": round(max(0.0, 0.5 - score), 4),
            "hold": 0.2,
            "buy": round(max(0.0, 0.5 + score), 4),
        }
    else:
        model = MODEL_BUNDLE["model"]
        probs_arr = model.predict_proba(feat[FEATURE_COLS])[0]
        classes = model.classes_
        class_prob = {int(c): float(p) for c, p in zip(classes, probs_arr)}
        idx = max(class_prob, key=class_prob.get)
        action = MODEL_BUNDLE["label_map"][idx]
        confidence = class_prob[idx]
        probs = {
            "sell": round(class_prob.get(-1, 0.0), 4),
            "hold": round(class_prob.get(0, 0.0), 4),
            "buy": round(class_prob.get(1, 0.0), 4),
        }

    if action == "hold":
        pos_size = 0.0
    else:
        pos_size = min(0.02 + confidence * 0.08, 0.1)

    result = {
        "ticker": ticker.upper().strip() or "UNKNOWN",
        "action": action,
        "confidence": round(float(confidence), 4),
        "class_probabilities": probs,
        "suggested_position_size_pct": round(float(pos_size), 4),
        "risk_plan": {
            "stop_loss": round(close - 1.5 * atr_val, 4),
            "take_profit": round(close + 2.0 * atr_val, 4),
        },
        "model_loaded": MODEL_BUNDLE is not None,
        "metrics": MODEL_BUNDLE.get("metrics", {}) if MODEL_BUNDLE else {},
    }

    table = pd.DataFrame([{
        "ticker": result["ticker"],
        "action": result["action"],
        "confidence": result["confidence"],
        "position_size_pct": result["suggested_position_size_pct"],
        "stop_loss": result["risk_plan"]["stop_loss"],
        "take_profit": result["risk_plan"]["take_profit"],
    }])

    return result, table


demo = gr.Interface(
    fn=predict_signal,
    inputs=[
        gr.Textbox(lines=1, label="Ticker", value="AAPL"),
        gr.Textbox(lines=14, label="OHLCV JSON", placeholder='[{"date":"2026-01-01","open":100,"high":101,"low":99,"close":100.5,"volume":1000000}]'),
    ],
    outputs=[
        gr.JSON(label="Strategy Suggestion"),
        gr.Dataframe(label="Decision Table", wrap=True),
    ],
    title="Buy/Sell Strategy Suggestion",
    description="Provide 30+ OHLCV rows. Train your own classifier with train.py and place artifact in models/.",
)


if __name__ == "__main__":
    demo.launch(show_error=True)
