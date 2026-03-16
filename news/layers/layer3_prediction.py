"""
=====================================================================
  LAYER 3 : PRICE PREDICTION
  LLM      : OpenRouter (Llama 3.3 70B) → Gemini fallback
  Input    : Layer 2 enriched profiles
  Output   : Price prediction per stock
  Features : Logs to Supabase after each profile (not at end)
             Skips articles already in l3_logs
=====================================================================
"""

import os
import time
import requests
from datetime import datetime
from layers.llm_client import call_llm

PRICE_API_BASE = "http://34.14.196.114/api/stocks"
BATCH_SIZE     = 5
PRICE_PERIOD   = "1mo"
PRICE_LIMIT    = 8


# ─────────────────────────────────────────────
#  CHECK ALREADY PROCESSED
# ─────────────────────────────────────────────
def _get_already_processed_ids() -> set:
    try:
        from database.supabase_logger import _get_headers, _url
        response = requests.get(
            _url("l3_logs") + "?select=news_id&limit=5000",
            headers=_get_headers(),
            timeout=10
        )
        if response.status_code == 200:
            rows = response.json()
            ids  = {str(r["news_id"]) for r in rows if r.get("news_id")}
            print(f"[Layer3] Found {len(ids)} already-processed IDs in l3_logs")
            return ids
        return set()
    except Exception as e:
        print(f"[Layer3] ⚠️ Skip-check failed: {e}")
        return set()


# ─────────────────────────────────────────────
#  LOG PROFILE TO SUPABASE IMMEDIATELY
# ─────────────────────────────────────────────
def _log_profile(profile: dict, enriched_entities: list):
    """Log L3 predictions for one profile immediately after processing."""
    try:
        from database.supabase_logger import _get_headers, _url
        rows = []
        for e in enriched_entities:
            pred = e.get("prediction", {})
            if not pred:
                continue
            pc = e.get("price_context", {})
            mr = pred.get("move_range", {})
            rows.append({
                "news_id":           profile.get("id"),
                "news_title":        str(profile.get("title", ""))[:300],
                "ticker":            e.get("ticker", ""),
                "company":           e.get("name", ""),
                "alert_priority":    pred.get("alert_priority", ""),
                "direction":         pred.get("direction", ""),
                "move_estimate_pct": pred.get("move_estimate_pct"),
                "move_range_low":    mr.get("low"),
                "move_range_high":   mr.get("high"),
                "confidence":        pred.get("confidence"),
                "time_horizon":      pred.get("time_horizon", ""),
                "current_price":     pc.get("current_price"),
                "trend_8d_pct":      pc.get("trend_8d_pct"),
                "volatility":        pc.get("volatility"),
                "reasoning":         str(pred.get("reasoning", ""))[:500],
                "key_risks":         str(pred.get("key_risks", ""))[:300],
            })

        if not rows:
            return

        response = requests.post(
            _url("l3_logs"),
            headers=_get_headers(),
            json=rows,
            timeout=10
        )
        if response.status_code in (200, 201):
            print(f"[Layer3] ✅ Logged {len(rows)} predictions to Supabase")
        else:
            print(f"[Layer3] ❌ Log failed: {response.status_code} {response.text[:100]}")
    except Exception as e:
        print(f"[Layer3] ❌ Log exception: {e}")


# ─────────────────────────────────────────────
#  FETCH HISTORICAL PRICES
# ─────────────────────────────────────────────
def fetch_price_data(ticker: str) -> dict | None:
    try:
        url      = f"{PRICE_API_BASE}/{ticker}/historical"
        params   = {"period": PRICE_PERIOD, "page": 1, "limit": PRICE_LIMIT}
        response = requests.get(url, params=params, timeout=10)

        if response.status_code != 200:
            return None

        prices = response.json().get("data", {}).get("prices", [])
        if not prices or len(prices) < 2:
            return None

        prices  = list(reversed(prices))
        closes  = [p["close"]         for p in prices]
        volumes = [p["volume"]        for p in prices]
        changes = [p["changePercent"] for p in prices]
        latest  = prices[-1]

        avg_change = sum(changes) / len(changes)
        variance   = sum((c - avg_change) ** 2 for c in changes) / len(changes)
        avg_volume = sum(volumes) / len(volumes)

        return {
            "ticker":            ticker,
            "current_price":     round(closes[-1], 2),
            "prev_close":        round(closes[-2], 2),
            "latest_change_pct": round(latest["changePercent"], 2),
            "trend_8d_pct":      round(((closes[-1] - closes[0]) / closes[0]) * 100, 2),
            "volatility":        round((variance ** 0.5), 2),
            "volume_ratio":      round(volumes[-1] / avg_volume if avg_volume else 1.0, 2),
            "momentum_3d":       round(sum(changes[-3:]) / min(3, len(changes)), 2),
            "high_volume":       latest.get("highVolume", False),
            "price_data_date":   latest["date"],
            "raw_changes":       changes,
        }
    except Exception as e:
        print(f"[PriceAPI] ❌ {ticker}: {e}")
        return None


# ─────────────────────────────────────────────
#  BUILD PROMPT
# ─────────────────────────────────────────────
def _build_prompt(batch: list) -> str:
    stocks_text = ""
    for i, item in enumerate(batch, 1):
        e    = item["entity"]
        p    = item["price_context"]
        news = item["news_profile"]
        sent = news.get("sentiment", {})
        event= news.get("event", {})

        stocks_text += f"""
Stock {i}:
  Ticker        : {e['ticker']} — {e['name']} ({e['industry']})
  Impact Type   : {e['impact_type']} | Direction hint: {e['direction']}
  Confidence    : {e['confidence']}
  Reason        : {e['reason']}

  News:
    Title       : {news.get('title','')}
    Event       : {event.get('event_type','')} | Themes: {', '.join(event.get('themes',[]))}
    Sentiment   : {sent.get('label','')} (score: {sent.get('compound',0)})
    Urgency     : {sent.get('urgency_score',0)}

  Price (last 8 days):
    Current     : ₹{p['current_price']} | Prev Close: ₹{p['prev_close']}
    Latest Chg  : {p['latest_change_pct']}%
    8d Trend    : {p['trend_8d_pct']}%
    Volatility  : {p['volatility']}%
    Volume Ratio: {p['volume_ratio']}x avg
    Momentum 3d : {p['momentum_3d']}%
    Daily chgs  : {p['raw_changes']}
"""

    return f"""You are a senior quantitative analyst for Indian stock markets (NSE/BSE).

Analyze these {len(batch)} stocks based on news impact + historical price data.
Predict likely price movement for each over the next trading session.

{stocks_text}

Return a JSON array — one object per stock:
[
  {{
    "ticker": "NSE_TICKER",
    "direction": "UP|DOWN|NEUTRAL",
    "move_estimate_pct": <float e.g. 1.5 or -0.8>,
    "move_range": {{"low": <float>, "high": <float>}},
    "confidence": <float 0.0-1.0>,
    "time_horizon": "intraday|1day|1week",
    "alert_priority": "IMMEDIATE|WATCH|INFO|IGNORE",
    "reasoning": "2-3 sentences explaining the prediction",
    "key_risks": "One sentence on what could invalidate this"
  }}
]

Alert priority:
- IMMEDIATE : confidence >0.7 + move >2% + DIRECT impact
- WATCH     : confidence >0.5 OR move 1-2%
- INFO      : confidence <0.5 OR move <1% OR indirect impact
- IGNORE    : contradictory signals OR confidence <0.3

Return ONLY valid JSON array, no markdown, no explanation."""


# ─────────────────────────────────────────────
#  MAIN RUNNER
# ─────────────────────────────────────────────
def run_layer3(l2_profiles: list) -> list:
    print(f"[Layer3] Starting predictions for {len(l2_profiles)} profiles...")

    # ── Skip already processed ───────────────
    already_done = _get_already_processed_ids()
    results      = []

    for profile in l2_profiles:
        pid      = str(profile.get("id", ""))
        entities = profile.get("affected_entities", [])

        # ── Skip if already in l3_logs ────────
        if pid in already_done:
            print(f"[Layer3] Skipping profile {pid} — already in l3_logs")
            results.append({**profile, "predictions_count": {"total": 0}})
            continue

        if not entities:
            results.append({**profile, "predictions_count": {"total": 0}})
            continue

        # ── Fetch price data per entity ───────
        batch_items = []
        for entity in entities:
            pc = fetch_price_data(entity.get("ticker", ""))
            if pc:
                batch_items.append({
                    "entity":        entity,
                    "price_context": pc,
                    "news_profile":  profile,
                })
            else:
                print(f"[Layer3] ⚠️ No price data for {entity.get('ticker')} — skipping")

        if not batch_items:
            results.append({**profile, "predictions_count": {"total": 0}})
            continue

        # ── Send to LLM in batches ────────────
        all_predictions = []
        total_batches   = (len(batch_items) + BATCH_SIZE - 1) // BATCH_SIZE

        for i in range(0, len(batch_items), BATCH_SIZE):
            batch     = batch_items[i: i + BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1

            print(f"[Layer3] Profile {pid} — "
                  f"Batch {batch_num}/{total_batches} ({len(batch)} stocks)...")

            preds = call_llm(_build_prompt(batch))

            # Normalize response type
            if isinstance(preds, dict):
                preds = list(preds.values())

            if preds and isinstance(preds, list):
                preds = [p for p in preds if isinstance(p, dict) and "ticker" in p]
                all_predictions.extend(preds)
                print(f"[Layer3] ✅ {len(preds)} predictions received")
            else:
                print(f"[Layer3] ❌ LLM failed for batch {batch_num}")

            if batch_num < total_batches:
                time.sleep(2)

        # ── Merge predictions into entities ───
        pred_map = {p["ticker"]: p for p in all_predictions}

        enriched_entities = []
        for item in batch_items:
            ticker = item["entity"]["ticker"]
            enriched_entities.append({
                **item["entity"],
                "price_context": item["price_context"],
                "prediction":    pred_map.get(ticker, {}),
            })

        # Sort by alert priority then confidence
        priority_order = {"IMMEDIATE": 0, "WATCH": 1, "INFO": 2, "IGNORE": 3}
        enriched_entities.sort(key=lambda x: (
            priority_order.get(x.get("prediction", {}).get("alert_priority", "INFO"), 2),
            -x.get("prediction", {}).get("confidence", 0)
        ))

        # ── Log to Supabase immediately ───────
        _log_profile(profile, enriched_entities)

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

        time.sleep(1)

    print(f"[Layer3] ✅ Complete — {len(results)} profiles with predictions")
    return results