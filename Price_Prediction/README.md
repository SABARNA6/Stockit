---
title: price-prediction-model
sdk: gradio
app_file: app.py
---

# Price Prediction Space

This Space predicts upcoming equity prices from recent history.

## Files

- app.py: Gradio app and API endpoint
- train.py: model training script
- requirements.txt: dependencies

## Train locally

```bash
pip install -r requirements.txt
python train.py --input data/price_history.csv --output models/price_model.joblib
```

Required CSV columns:

- ticker
- date
- close

Optional column:

- volume

## Run locally

```bash
python app.py
```

## API access

```python
from gradio_client import Client

client = Client("YOUR_USERNAME/price-prediction-model")
result = client.predict(
    ticker="AAPL",
    recent_prices_json='[{"date":"2026-02-01","close":100.0,"volume":1000000},{"date":"2026-02-02","close":100.7,"volume":1020000}]',
    horizon_days=5,
    api_name="/predict"
)
print(result)
```
