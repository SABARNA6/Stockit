"""
=====================================================================
  LAYER 3 : PRICE PREDICTION via Gemini + Historical Price API
  Input    : Layer 2 enriched profiles (affected entities)
  Output   : Price prediction per stock
             - Direction (UP/DOWN/NEUTRAL)
             - % move estimate
             - Confidence score
             - Time horizon (intraday/1day/1week)
             - Alert priority (IMMEDIATE/WATCH/INFO/IGNORE)
=====================================================================
"""

import os
import json
import time
import requests
from datetime import datetime

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
PRICE_API_BASE  = "http://34.14.196.114/api/stocks"
GEMINI_MODEL    = "gemini-2.5-flash-lite"
GEMINI_URL      = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
BATCH_SIZE      = 5    # stocks per Gemini call (smaller = more accurate)
RETRY_ATTEMPTS  = 3
RETRY_DELAY     = 5
PRICE_PERIOD    = "1mo"
PRICE_LIMIT     = 8    # last 8 trading days


# ─────────────────────────────────────────────
#  1. FETCH HISTORICAL PRICES
# ─────────────────────────────────────────────
def fetch_price_data(ticker: str) -> dict | None:
    """
    Fetch historical prices from your API.
    Returns computed price context dict or None if failed.
    """
    try:
        url      = f"{PRICE_API_BASE}/{ticker}/historical"
        params   = {"period": PRICE_PERIOD, "page": 1, "limit": PRICE_LIMIT}
        response = requests.get(url, params=params, timeout=10)

        if response.status_code != 200:
            return None

        data   = response.json()
        prices = data.get("data", {}).get("prices", [])

        if not prices or len(prices) < 2:
            return None

        # Prices come newest first — reverse for chronological order
        prices = list(reversed(prices))

        closes       = [p["close"]        for p in prices]
        volumes      = [p["volume"]       for p in prices]
        changes      = [p["changePercent"] for p in prices]
        latest       = prices[-1]
        prev         = prices[-2]

        # ── Technical indicators ──────────────────
        avg_close    = sum(closes) / len(closes)
        current      = closes[-1]
        trend_pct    = ((current - closes[0]) / closes[0]) * 100  # overall trend

        # Volatility = std dev of daily changes
        avg_change   = sum(changes) / len(changes)
        variance     = sum((c - avg_change) ** 2 for c in changes) / len(changes)
        volatility   = variance ** 0.5

        # Volume trend (latest vs avg)
        avg_volume   = sum(volumes) / len(volumes)
        vol_ratio    = volumes[-1] / avg_volume if avg_volume else 1.0

        # Momentum (last 3 days avg change)
        recent_momentum = sum(changes[-3:]) / min(3, len(changes))

        return {
            "ticker":           ticker,
            "current_price":    round(current, 2),
            "prev_close":       round(prev["close"], 2),
            "latest_change_pct":round(latest["changePercent"], 2),
            "trend_8d_pct":     round(trend_pct, 2),
            "volatility":       round(volatility, 2),
            "volume_ratio":     round(vol_ratio, 2),   # >1 = high volume
            "momentum_3d":      round(recent_momentum, 2),
            "high_volume":      latest.get("highVolume", False),
            "price_data_date":  latest["date"],
            "raw_changes":      changes,
        }

    except Exception as e:
        print(f"[PriceAPI] ❌ Failed to fetch {ticker}: {e}")
        return None


# ─────────────────────────────────────────────
#  2. BUILD GEMINI PROMPT FOR PRICE PREDICTION
# ─────────────────────────────────────────────
def _build_prediction_prompt(batch: list[dict]) -> str:
    """
    batch = list of {entity, price_context, news_profile}
    """
    stocks_text = ""
    for i, item in enumerate(batch, 1):
        e     = item["entity"]
        p     = item["price_context"]
        news  = item["news_profile"]
        event = news.get("event", {})
        sent  = news.get("sentiment", {})

        stocks_text += f"""
Stock {i}:
  Ticker       : {e['ticker']} — {e['name']} ({e['industry']})
  Impact Type  : {e['impact_type']} | Direction hint: {e['direction']}
  Confidence   : {e['confidence']}
  Reason       : {e['reason']}

  News Context:
    Title      : {news.get('title', '')}
    Event Type : {event.get('event_type', '')}
    Themes     : {', '.join(event.get('themes', []))}
    Sentiment  : {sent.get('label', '')} (score: {sent.get('compound', 0)})
    Urgency    : {sent.get('urgency_score', 0)}

  Price Context (last 8 trading days):
    Current Price   : ₹{p['current_price']}
    Prev Close      : ₹{p['prev_close']}
    Latest Change   : {p['latest_change_pct']}%
    8-Day Trend     : {p['trend_8d_pct']}%
    Volatility      : {p['volatility']}% (std dev of daily moves)
    Volume Ratio    : {p['volume_ratio']}x avg (>1 = high volume)
    3-Day Momentum  : {p['momentum_3d']}%
    High Volume Day : {p['high_volume']}
    Daily Changes   : {p['raw_changes']}
"""

    return f"""You are a senior quantitative analyst specializing in Indian stock markets (NSE/BSE).

Analyze the following {len(batch)} stocks based on recent news impact and historical price data.
For EACH stock, predict the likely price movement over the next trading session.

{stocks_text}

For each stock return a JSON object with this exact structure:
{{
  "ticker": "NSE_TICKER",
  "direction": "UP | DOWN | NEUTRAL",
  "move_estimate_pct": <float, e.g. 1.5 for +1.5% or -0.8 for -0.8%>,
  "move_range": {{
    "low": <float, conservative estimate>,
    "high": <float, optimistic estimate>
  }},
  "confidence": <float 0.0-1.0>,
  "time_horizon": "intraday | 1day | 1week",
  "alert_priority": "IMMEDIATE | WATCH | INFO | IGNORE",
  "reasoning": "2-3 sentences explaining the prediction",
  "key_risks": "One sentence on what could invalidate this prediction"
}}

Alert priority rules:
- IMMEDIATE : High confidence + significant move (>2%) + DIRECT impact
- WATCH     : Medium confidence OR moderate move (1-2%)
- INFO      : Low confidence OR small move (<1%) OR SECTOR/MACRO impact
- IGNORE    : Contradictory signals OR very low confidence (<0.3)

Return ONLY a valid JSON array, no markdown:
[
  {{ "ticker": "...", "direction": "...", ... }},
  ...
]"""


# ─────────────────────────────────────────────
#  3. GEMINI API CALL
# ─────────────────────────────────────────────
def _call_gemini(prompt: str) -> list | None:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[Gemini L3] ❌ GEMINI_API_KEY not set")
        return None

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature":      0.1,
            "maxOutputTokens":  4096,
            "responseMimeType": "application/json",
        }
    }

    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            response = requests.post(
                f"{GEMINI_URL}?key={api_key}",
                json=payload,
                timeout=60
            )
            if response.status_code == 429:
                wait = RETRY_DELAY * attempt
                print(f"[Gemini L3] ⚠️ Rate limited. Waiting {wait}s...")
                time.sleep(wait)
                continue

            if response.status_code != 200:
                print(f"[Gemini L3] ❌ HTTP {response.status_code}: {response.text[:200]}")
                return None

            data = response.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text.strip())

        except json.JSONDecodeError as e:
            print(f"[Gemini L3] ❌ JSON parse error: {e}")
            return None
        except Exception as e:
            print(f"[Gemini L3] ❌ Request error (attempt {attempt}): {e}")
            if attempt < RETRY_ATTEMPTS:
                time.sleep(RETRY_DELAY)

    return None


# ─────────────────────────────────────────────
#  4. MAIN RUNNER
# ─────────────────────────────────────────────
def run_layer3(l2_profiles: list) -> list:
    """
    Takes Layer 2 enriched profiles.
    Returns profiles with price predictions added to each entity.
    """
    print(f"[Layer3] Starting price prediction for {len(l2_profiles)} profiles...")

    results = []

    for profile in l2_profiles:
        entities = profile.get("affected_entities", [])
        if not entities:
            results.append({**profile, "predictions": []})
            continue

        # ── Fetch price data for each entity ──
        batch_items = []
        for entity in entities:
            ticker       = entity.get("ticker", "")
            price_context = fetch_price_data(ticker)

            if price_context:
                batch_items.append({
                    "entity":        entity,
                    "price_context": price_context,
                    "news_profile":  profile,
                })
            else:
                print(f"[Layer3] ⚠️ No price data for {ticker} — skipping")

        if not batch_items:
            results.append({**profile, "predictions": []})
            continue

        # ── Send to Gemini in batches of BATCH_SIZE ──
        all_predictions = []
        total_batches   = (len(batch_items) + BATCH_SIZE - 1) // BATCH_SIZE

        for i in range(0, len(batch_items), BATCH_SIZE):
            batch     = batch_items[i: i + BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1

            print(f"[Layer3] Profile {profile.get('id')} — "
                  f"Batch {batch_num}/{total_batches} ({len(batch)} stocks)...")

            predictions = _call_gemini(_build_prediction_prompt(batch))

            if predictions:
                all_predictions.extend(predictions)
                print(f"[Layer3] ✅ {len(predictions)} predictions received")
            else:
                print(f"[Layer3] ❌ Gemini failed for batch {batch_num}")

            if batch_num < total_batches:
                time.sleep(4)

        # ── Merge predictions back into profile ──
        pred_map = {p["ticker"]: p for p in all_predictions}

        # Attach prediction to each entity
        enriched_entities = []
        for item in batch_items:
            ticker     = item["entity"]["ticker"]
            prediction = pred_map.get(ticker, {})
            enriched_entities.append({
                **item["entity"],
                "price_context": item["price_context"],
                "prediction":    prediction,
            })

        # Sort by alert priority then confidence
        priority_order = {"IMMEDIATE": 0, "WATCH": 1, "INFO": 2, "IGNORE": 3}
        enriched_entities.sort(key=lambda x: (
            priority_order.get(x.get("prediction", {}).get("alert_priority", "INFO"), 2),
            -x.get("prediction", {}).get("confidence", 0)
        ))

        results.append({
            **profile,
            "affected_entities": enriched_entities,
            "predictions_count": {
                "total":     len(enriched_entities),
                "immediate": sum(1 for e in enriched_entities if e.get("prediction", {}).get("alert_priority") == "IMMEDIATE"),
                "watch":     sum(1 for e in enriched_entities if e.get("prediction", {}).get("alert_priority") == "WATCH"),
                "info":      sum(1 for e in enriched_entities if e.get("prediction", {}).get("alert_priority") == "INFO"),
                "ignore":    sum(1 for e in enriched_entities if e.get("prediction", {}).get("alert_priority") == "IGNORE"),
            },
            "layer3_processed_at": datetime.now().isoformat(),
        })

        # Small delay between profiles
        time.sleep(2)

    print(f"[Layer3] ✅ Complete — {len(results)} profiles with predictions")
    return results