"""
=====================================================================
  LAYER 4 : LLM REASONING ENGINE
  Input    : L3 enriched profiles (from run_layer3)
  Tasks:
    1. Validate automated predictions (flag low-confidence)
    2. Refine magnitude estimates (be conservative)
    3. Generate plain-English rationale per entity
    4. Identify missed opportunities
    5. Assign final alert priority: IMMEDIATE | WATCH | INFO | IGNORE
  Output   : Final validated profiles + logs to l4_logs table
=====================================================================
"""

import requests
import time
from datetime import datetime
from layers.llm_client import call_llm


# ─────────────────────────────────────────────
#  CHECK ALREADY PROCESSED
# ─────────────────────────────────────────────
def _get_already_processed_ids() -> set:
    try:
        from database.supabase_logger import _get_headers, _url
        response = requests.get(
            _url("l4_logs") + "?select=news_id&limit=5000",
            headers=_get_headers(),
            timeout=10
        )
        if response.status_code == 200:
            ids = {str(r["news_id"]) for r in response.json() if r.get("news_id")}
            print(f"[Layer4] {len(ids)} already-processed IDs in l4_logs")
            return ids
        return set()
    except Exception as e:
        print(f"[Layer4] ⚠️ Skip-check failed: {e}")
        return set()


# ─────────────────────────────────────────────
#  LOG PROFILE TO SUPABASE IMMEDIATELY
# ─────────────────────────────────────────────
def _log_profile(profile: dict, entities: list, reasoning_summary: str):
    try:
        from database.supabase_logger import _get_headers, _url
        rows = []
        for e in entities:
            pred = e.get("prediction", {})
            pc   = e.get("price_context", {})
            rows.append({
                "news_id":           profile.get("id"),
                "news_title":        str(profile.get("title", ""))[:300],
                "ticker":            e.get("ticker", ""),
                "company":           e.get("name", ""),
                "impact_type":       e.get("impact_type", ""),
                "direction":         pred.get("direction", ""),
                "move_estimate_pct": pred.get("move_estimate_pct"),
                "move_range_low":    pred.get("move_range", {}).get("low"),
                "move_range_high":   pred.get("move_range", {}).get("high"),
                "confidence":        pred.get("confidence"),
                "time_horizon":      pred.get("time_horizon", ""),
                "current_price":     pc.get("current_price"),
                "alert_priority":    e.get("final_priority", pred.get("alert_priority", "")),
                "l4_rationale":      str(e.get("l4_rationale", ""))[:500],
                "l4_flag":           e.get("l4_flag", ""),
                "l4_refined_move":   e.get("l4_refined_move"),
                "reasoning_summary": str(reasoning_summary)[:800],
            })

        if not rows:
            return

        response = requests.post(
            _url("l4_logs"),
            headers=_get_headers(),
            json=rows,
            timeout=10
        )
        if response.status_code in (200, 201):
            print(f"[Layer4] ✅ Logged {len(rows)} rows to l4_logs")
        else:
            print(f"[Layer4] ❌ Log failed: {response.status_code} {response.text[:100]}")
    except Exception as e:
        print(f"[Layer4] ❌ Log exception: {e}")


# ─────────────────────────────────────────────
#  BUILD PROMPT
# ─────────────────────────────────────────────
def _build_prompt(profile: dict, entities: list) -> str:
    news_block = f"""
News Article:
  ID        : {profile.get('id')}
  Title     : {profile.get('title')}
  Summary   : {str(profile.get('summary', ''))[:300]}
  Event     : {profile.get('event', {}).get('event_type', '')}
  Themes    : {', '.join(profile.get('event', {}).get('themes', []))}
  Sentiment : {profile.get('sentiment', {}).get('label', '')} 
              (compound: {profile.get('sentiment', {}).get('compound', 0)},
               urgency: {profile.get('sentiment', {}).get('urgency_score', 0)})
"""

    entities_block = ""
    for i, e in enumerate(entities, 1):
        pred = e.get("prediction", {})
        pc   = e.get("price_context", {})
        entities_block += f"""
Entity {i}:
  Ticker        : {e.get('ticker')} — {e.get('name')} ({e.get('industry')})
  Impact Type   : {e.get('impact_type')} | L2 Direction: {e.get('direction')}
  L2 Confidence : {e.get('confidence')}
  L2 Reason     : {e.get('reason', '')}

  L3 Prediction :
    Direction   : {pred.get('direction')}
    Move Est    : {pred.get('move_estimate_pct')}%
    Move Range  : [{pred.get('move_range', {}).get('low')}%, {pred.get('move_range', {}).get('high')}%]
    Confidence  : {pred.get('confidence')}
    Priority    : {pred.get('alert_priority')}
    Time Horizon: {pred.get('time_horizon')}
    Reasoning   : {pred.get('reasoning', '')}
    Key Risks   : {pred.get('key_risks', '')}

  Price Context :
    Current     : ₹{pc.get('current_price')}
    8d Trend    : {pc.get('trend_8d_pct')}%
    Volatility  : {pc.get('volatility')}%
    Volume Ratio: {pc.get('volume_ratio')}x
    Momentum 3d : {pc.get('momentum_3d')}%
"""

    return f"""You are a senior fund manager reviewing automated stock impact predictions for Indian markets (NSE/BSE).

{news_block}

Automated predictions to validate:
{entities_block}

Your tasks:
1. VALIDATE each prediction — is the direction and magnitude reasonable?
2. REFINE move estimate — be conservative, avoid overestimating
3. GENERATE plain-English rationale for each entity (2-3 sentences max)
4. FLAG issues: low_confidence | contradictory_signals | stale_news | macro_override
5. ASSIGN final alert priority considering all factors
6. IDENTIFY any missed stocks that should be affected but are not in the list

Return a JSON object:
{{
  "reasoning_summary": "2-3 sentence overall market context for this news",
  "missed_opportunities": ["TICKER1 — reason why it's affected", "TICKER2 — reason"],
  "entities": [
    {{
      "ticker": "NSE_TICKER",
      "validated": true/false,
      "l4_rationale": "Plain English explanation of why and how this stock is affected",
      "l4_flag": "none|low_confidence|contradictory_signals|stale_news|macro_override",
      "l4_refined_move": <float — your refined move estimate %>,
      "final_priority": "IMMEDIATE|WATCH|INFO|IGNORE",
      "final_direction": "UP|DOWN|NEUTRAL"
    }}
  ]
}}

Rules:
- Be conservative — if L3 says +2%, consider +1.2% unless very strong signals
- Flag low_confidence if L3 confidence < 0.5
- Flag contradictory_signals if price trend contradicts news sentiment
- IMMEDIATE only if: direct impact + confidence > 0.75 + move > 1.5%
- Return ONLY valid JSON, no markdown"""


# ─────────────────────────────────────────────
#  MERGE L4 RESULTS INTO PROFILE
# ─────────────────────────────────────────────
def _merge_results(profile: dict, entities: list, l4_result: dict) -> tuple[list, str]:
    reasoning_summary   = l4_result.get("reasoning_summary", "")
    missed              = l4_result.get("missed_opportunities", [])
    l4_entities_map     = {
        e["ticker"]: e
        for e in l4_result.get("entities", [])
        if isinstance(e, dict) and "ticker" in e
    }

    enriched = []
    for e in entities:
        ticker = e.get("ticker", "")
        l4     = l4_entities_map.get(ticker, {})
        pred   = e.get("prediction", {})

        enriched.append({
            **e,
            "prediction": {
                **pred,
                # Override with L4 refined values
                "direction":         l4.get("final_direction",  pred.get("direction")),
                "move_estimate_pct": l4.get("l4_refined_move",  pred.get("move_estimate_pct")),
                "alert_priority":    l4.get("final_priority",   pred.get("alert_priority")),
            },
            "final_priority":  l4.get("final_priority",  pred.get("alert_priority", "INFO")),
            "l4_rationale":    l4.get("l4_rationale",   ""),
            "l4_flag":         l4.get("l4_flag",         "none"),
            "l4_refined_move": l4.get("l4_refined_move"),
            "validated":       l4.get("validated",       True),
        })

    # Sort by final priority then confidence
    priority_order = {"IMMEDIATE": 0, "WATCH": 1, "INFO": 2, "IGNORE": 3}
    enriched.sort(key=lambda x: (
        priority_order.get(x.get("final_priority", "INFO"), 2),
        -x.get("prediction", {}).get("confidence", 0)
    ))

    return enriched, reasoning_summary, missed


# ─────────────────────────────────────────────
#  MAIN RUNNER
# ─────────────────────────────────────────────
def run_layer4(l3_profiles: list) -> list:
    print(f"[Layer4] Starting reasoning for {len(l3_profiles)} profiles...")

    already_done = _get_already_processed_ids()
    results      = []

    for profile in l3_profiles:
        pid      = str(profile.get("id", ""))
        entities = [
            e for e in profile.get("affected_entities", [])
            if e.get("prediction")   # only entities that have L3 predictions
        ]

        # ── Skip already processed ────────────
        if pid in already_done:
            print(f"[Layer4] Skipping {pid} — already in l4_logs")
            results.append(profile)
            continue

        if not entities:
            results.append({
                **profile,
                "reasoning_summary":     "",
                "missed_opportunities":  [],
                "layer4_processed_at":   datetime.now().isoformat(),
            })
            continue

        print(f"[Layer4] Profile {pid} — reasoning over {len(entities)} entities...")

        l4_result = call_llm(_build_prompt(profile, entities))

        if not l4_result or not isinstance(l4_result, dict):
            print(f"[Layer4] ❌ LLM failed for profile {pid}")
            results.append({**profile, "layer4_error": "LLM failed"})
            continue

        enriched_entities, reasoning_summary, missed = _merge_results(
            profile, entities, l4_result
        )

        # ── Log immediately ───────────────────
        _log_profile(profile, enriched_entities, reasoning_summary)

        results.append({
            **profile,
            "affected_entities":    enriched_entities,
            "reasoning_summary":    reasoning_summary,
            "missed_opportunities": missed,
            "layer4_processed_at":  datetime.now().isoformat(),
        })

        print(f"[Layer4] ✅ Profile {pid} done — "
              f"{len(enriched_entities)} entities, "
              f"{len(missed)} missed opportunities")

        time.sleep(1)

    print(f"[Layer4] ✅ Complete — {len(results)} profiles reasoned")
    return results