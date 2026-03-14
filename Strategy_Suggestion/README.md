---
title: strategy-suggestion-model
sdk: gradio
app_file: app.py
---

# Strategy Suggestion Space

This Space predicts buy, hold, or sell and suggests risk parameters.

## Files

- app.py: Gradio app and API endpoint
- train.py: model training script
- requirements.txt: dependencies

## Train locally

```bash
pip install -r requirements.txt
python train.py --input data/ohlcv.csv --output models/strategy_model.joblib
```

Required CSV columns:

- ticker
- date
- open
- high
- low
- close
- volume

## Run locally

```bash
python app.py
```

## API access

```python
from gradio_client import Client

client = Client("YOUR_USERNAME/strategy-suggestion-model")
result = client.predict(
    ticker="AAPL",
    ohlcv_json='[{"date":"2026-01-01","open":100,"high":101,"low":99,"close":100.5,"volume":1000000}]',
    api_name="/predict"
)
print(result)
```
