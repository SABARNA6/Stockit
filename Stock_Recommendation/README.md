---
title: stock-recommendation-model
sdk: gradio
app_file: app.py
---

# Stock Recommendation Space

This Space hosts a portfolio-aware stock recommendation model.

## Files

- app.py: Gradio app and API endpoint
- train.py: model training script
- requirements.txt: dependencies

## Train locally

```bash
pip install -r requirements.txt
python train.py --input data/stock_history.csv --output models/recommendation_model.joblib
```

Required CSV columns:

- ticker
- date
- close
- volume

## Run locally

```bash
python app.py
```

## API access

```python
from gradio_client import Client

client = Client("YOUR_USERNAME/stock-recommendation-model")
result = client.predict(
    portfolio_json='[{"ticker":"AAPL","market_value":3000}]',
    candidates_json='[{"ticker":"NVDA","ret_1d":0.01,"ret_5d":0.03,"momentum_20d":0.06,"volatility_20d":0.03,"volume_chg_5d":0.1}]',
    risk_profile="Medium",
    top_k=3,
    api_name="/predict"
)
print(result)
```
