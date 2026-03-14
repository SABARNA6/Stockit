from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


LABEL_MAP = {-1: "sell", 0: "hold", 1: "buy"}


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
    data = data.sort_values(["ticker", "date"]).reset_index(drop=True)

    grp = data.groupby("ticker", group_keys=False)
    data["ret_1d"] = grp["close"].pct_change()
    data["ret_5d"] = grp["close"].pct_change(5)
    data["sma_10"] = grp["close"].rolling(10).mean().reset_index(level=0, drop=True)
    data["sma_20"] = grp["close"].rolling(20).mean().reset_index(level=0, drop=True)
    data["sma_ratio"] = data["sma_10"] / data["sma_20"]
    data["volatility_10d"] = grp["ret_1d"].rolling(10).std().reset_index(level=0, drop=True)
    data["rsi_14"] = grp["close"].transform(rsi)
    data["atr_14"] = grp.apply(lambda x: atr(x)).reset_index(level=0, drop=True)

    future_3d = grp["close"].shift(-3) / data["close"] - 1.0
    data["label"] = np.where(future_3d > 0.015, 1, np.where(future_3d < -0.015, -1, 0))
    return data


def train(input_csv: str, output_model: str) -> dict:
    df = pd.read_csv(input_csv)
    required = {"ticker", "date", "open", "high", "low", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    data = add_features(df)
    feature_cols = ["ret_1d", "ret_5d", "sma_ratio", "volatility_10d", "rsi_14", "atr_14"]
    data = data.dropna(subset=feature_cols + ["label"])

    split = int(0.8 * len(data))
    train_df = data.iloc[:split]
    test_df = data.iloc[split:]

    model = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            (
                "rf",
                RandomForestClassifier(
                    n_estimators=300,
                    max_depth=8,
                    random_state=42,
                    class_weight="balanced_subsample",
                    n_jobs=-1,
                ),
            ),
        ]
    )

    model.fit(train_df[feature_cols], train_df["label"])
    pred = model.predict(test_df[feature_cols])

    metrics = {
        "accuracy": float(accuracy_score(test_df["label"], pred)),
        "train_rows": float(len(train_df)),
        "test_rows": float(len(test_df)),
    }

    out = Path(output_model)
    out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "feature_columns": feature_cols, "metrics": metrics, "label_map": LABEL_MAP}, out)
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="CSV with ticker,date,open,high,low,close,volume")
    parser.add_argument("--output", default="models/strategy_model.joblib")
    args = parser.parse_args()

    metrics = train(args.input, args.output)
    print("training complete")
    print(metrics)


if __name__ == "__main__":
    main()
