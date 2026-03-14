from __future__ import annotations

import json
from pathlib import Path

import gradio as gr
import joblib
import numpy as np
import pandas as pd


MODEL_PATH = Path("models/recommendation_model.joblib")
FEATURE_COLS = ["ret_1d", "ret_5d", "momentum_20d", "volatility_20d", "volume_chg_5d"]


def load_model_bundle() -> dict | None:
    if MODEL_PATH.exists():
        return joblib.load(MODEL_PATH)
    return None


MODEL_BUNDLE = load_model_bundle()


def parse_json(value: str, fallback: list[dict]) -> list[dict]:
    value = value.strip()
    if not value:
        return fallback
    return json.loads(value)


def predict_returns(df: pd.DataFrame) -> np.ndarray:
    if MODEL_BUNDLE is None:
        return (0.6 * df["momentum_20d"] + 0.3 * df["ret_5d"] + 0.1 * df["ret_1d"] - 0.5 * df["volatility_20d"]).to_numpy()

    model = MODEL_BUNDLE["model"]
    return model.predict(df[FEATURE_COLS])


def recommend(portfolio_json: str, candidates_json: str, risk_profile: str, top_k: int):
    default_portfolio = [
        {"ticker": "AAPL", "market_value": 3000},
        {"ticker": "MSFT", "market_value": 2500},
    ]
    default_candidates = [
        {"ticker": "NVDA", "ret_1d": 0.012, "ret_5d": 0.041, "momentum_20d": 0.08, "volatility_20d": 0.032, "volume_chg_5d": 0.11},
        {"ticker": "GOOGL", "ret_1d": -0.003, "ret_5d": 0.013, "momentum_20d": 0.028, "volatility_20d": 0.020, "volume_chg_5d": 0.03},
        {"ticker": "AMZN", "ret_1d": 0.007, "ret_5d": 0.027, "momentum_20d": 0.052, "volatility_20d": 0.029, "volume_chg_5d": 0.09},
    ]

    portfolio = parse_json(portfolio_json, default_portfolio)
    candidates = parse_json(candidates_json, default_candidates)

    p_df = pd.DataFrame(portfolio)
    c_df = pd.DataFrame(candidates)

    for col in FEATURE_COLS + ["ticker"]:
        if col not in c_df.columns:
            raise gr.Error(f"Missing candidate field: {col}")

    c_df["ticker"] = c_df["ticker"].str.upper()
    total_value = float(p_df["market_value"].sum()) if not p_df.empty else 0.0
    weights = {}
    if total_value > 0:
        for _, row in p_df.iterrows():
            weights[str(row["ticker"]).upper()] = float(row["market_value"]) / total_value

    risk_map = {"Low": 1.6, "Medium": 1.0, "High": 0.5}
    risk_aversion = risk_map[risk_profile]

    c_df["predicted_return"] = predict_returns(c_df)
    c_df["existing_weight"] = c_df["ticker"].map(weights).fillna(0.0)
    c_df["score"] = c_df["predicted_return"] - risk_aversion * c_df["volatility_20d"] - 0.8 * c_df["existing_weight"]

    out = c_df.sort_values("score", ascending=False).head(top_k).copy()
    shifted = out["score"] - out["score"].min() + 1e-9
    out["target_weight"] = shifted / shifted.sum()

    recommendations = []
    for _, r in out.iterrows():
        recommendations.append(
            {
                "ticker": r["ticker"],
                "score": round(float(r["score"]), 6),
                "predicted_return": round(float(r["predicted_return"]), 6),
                "target_weight": round(float(r["target_weight"]), 4),
                "reason": "portfolio-adjusted expected return",
            }
        )

    info = {
        "model_loaded": MODEL_BUNDLE is not None,
        "risk_profile": risk_profile,
        "metrics": MODEL_BUNDLE.get("metrics", {}) if MODEL_BUNDLE else {},
        "recommendations": recommendations,
    }

    table = out[["ticker", "score", "predicted_return", "target_weight"]]
    return info, table


demo = gr.Interface(
    fn=recommend,
    inputs=[
        gr.Textbox(lines=8, label="Portfolio JSON", placeholder='[{"ticker":"AAPL","market_value":3000}]'),
        gr.Textbox(lines=10, label="Candidates JSON", placeholder='[{"ticker":"NVDA","ret_1d":0.01,"ret_5d":0.03,"momentum_20d":0.06,"volatility_20d":0.03,"volume_chg_5d":0.1}]'),
        gr.Dropdown(choices=["Low", "Medium", "High"], value="Medium", label="Risk Profile"),
        gr.Slider(1, 10, value=5, step=1, label="Top K"),
    ],
    outputs=[
        gr.JSON(label="Recommendation JSON"),
        gr.Dataframe(label="Top Picks", wrap=True),
    ],
    title="Portfolio-Aware Stock Recommendation",
    description="Train your own model with train.py, upload model artifact to models/, and call this Space via API.",
)


if __name__ == "__main__":
    demo.launch()
