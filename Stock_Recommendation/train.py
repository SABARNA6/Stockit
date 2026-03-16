from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    data["date"] = pd.to_datetime(data["date"])
    data = data.sort_values(["ticker", "date"]).reset_index(drop=True)

    grp = data.groupby("ticker", group_keys=False)
    data["ret_1d"] = grp["close"].pct_change()
    data["ret_5d"] = grp["close"].pct_change(5)
    data["momentum_20d"] = grp["close"].pct_change(20)
    data["volatility_20d"] = grp["ret_1d"].rolling(20).std().reset_index(level=0, drop=True)
    data["volume_chg_5d"] = grp["volume"].pct_change(5)
    data["target_next_return"] = grp["close"].shift(-1) / data["close"] - 1.0

    feature_cols = ["ret_1d", "ret_5d", "momentum_20d", "volatility_20d", "volume_chg_5d"]
    data[feature_cols] = data[feature_cols].replace([np.inf, -np.inf], np.nan)
    return data


def train(input_csv: str, output_model: str) -> dict:
    df = pd.read_csv(input_csv)
    required = {"ticker", "date", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    data = build_features(df)
    feature_cols = ["ret_1d", "ret_5d", "momentum_20d", "volatility_20d", "volume_chg_5d"]
    data = data.dropna(subset=feature_cols + ["target_next_return"])

    split = int(0.8 * len(data))
    train_df = data.iloc[:split]
    test_df = data.iloc[split:]

    model = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            ("rf", RandomForestRegressor(n_estimators=300, max_depth=8, random_state=42, n_jobs=-1)),
        ]
    )

    model.fit(train_df[feature_cols], train_df["target_next_return"])
    pred = model.predict(test_df[feature_cols])

    metrics = {
        "mae": float(mean_absolute_error(test_df["target_next_return"], pred)),
        "rmse": float(np.sqrt(mean_squared_error(test_df["target_next_return"], pred))),
        "train_rows": float(len(train_df)),
        "test_rows": float(len(test_df)),
    }

    out = Path(output_model)
    out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "feature_columns": feature_cols, "metrics": metrics}, out)
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="CSV with ticker,date,close,volume")
    parser.add_argument("--output", default="models/recommendation_model.joblib")
    args = parser.parse_args()

    metrics = train(args.input, args.output)
    print("training complete")
    print(metrics)


if __name__ == "__main__":
    main()
