"""
=====================================================================
  LAYER 2 : IMPACT PROPAGATION via Gemini AI
  Model    : gemini-2.0-flash (free tier)
  Input    : Layer 1 profiles (batches of 10)
  Output   : Affected entities with impact type + confidence + reason
=====================================================================
"""

import os
import json
import time
import requests
from datetime import datetime

# ─────────────────────────────────────────────
#  Gemini API config
#  Set GEMINI_API_KEY in Render env vars
# ─────────────────────────────────────────────
GEMINI_MODEL   = "gemini-2.0-flash"
GEMINI_URL     = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
BATCH_SIZE     = 10       # articles per Gemini call
RETRY_ATTEMPTS = 3        # retry on rate limit
RETRY_DELAY    = 5        # seconds between retries


# ─────────────────────────────────────────────
#  NSE STOCK LIST (loaded from your Sheet)
# ─────────────────────────────────────────────
_nse_stocks: list = []
_nse_lookup: dict = {}


def load_knowledge_graph(stocks: list) -> None:
    global _nse_stocks, _nse_lookup
    _nse_stocks = []
    _nse_lookup = {}

    for row in stocks:
        ticker   = str(row.get("Symbol",       row.get("ticker", ""))).strip().upper()
        name     = str(row.get("Company Name", row.get("company name", ""))).strip()
        industry = str(row.get("Industry",     row.get("industry", ""))).strip()
        if not ticker:
            continue
        entry = {"ticker": ticker, "name": name, "industry": industry}
        _nse_stocks.append(entry)
        _nse_lookup[ticker] = entry

    print(f"[KG] Loaded {len(_nse_stocks)} NSE stocks into knowledge graph")


def get_nse_stock_list_text() -> str:
    lines = [f"{s['ticker']}|{s['name']}|{s['industry']}" for s in _nse_stocks]
    return "\n".join(lines)


# ─────────────────────────────────────────────
#  GEMINI PROMPT BUILDER
# ─────────────────────────────────────────────
def _build_prompt(batch: list, stock_list_text: str) -> str:
    articles_text = ""
    for i, p in enumerate(batch, 1):
        entities  = ", ".join(e["ticker"] for e in p.get("entities", [])) or "None detected"
        event     = p.get("event", {}).get("event_type", "General")
        themes    = ", ".join(p.get("event", {}).get("themes", [])) or "None"
        sentiment = p.get("sentiment", {}).get("label", "Neutral")
        compound  = p.get("sentiment", {}).get("compound", 0)
        articles_text += f"""
Article {i}:
  ID        : {p.get("id")}
  Title     : {p.get("title")}
  Summary   : {p.get("summary", "")[:300]}
  Entities  : {entities}
  Event Type: {event}
  Themes    : {themes}
  Sentiment : {sentiment} (score: {compound})
"""

    return f"""You are a financial analyst specializing in Indian stock markets (NSE/BSE).

Below is a list of NSE-listed companies (format: TICKER|Company Name|Industry):
{stock_list_text}

Analyze the following {len(batch)} news articles and for EACH article, identify which NSE-listed companies will be affected and how.

{articles_text}

For each article return a JSON array with this structure:
{{
  "article_id": <id>,
  "affected_entities": [
    {{
      "ticker": "NSE_TICKER",
      "name": "Company Name",
      "industry": "Industry",
      "impact_type": "DIRECT | SECTOR | SUPPLY_CHAIN | MACRO | COMPETITOR",
      "direction": "POSITIVE | NEGATIVE | NEUTRAL",
      "confidence": 0.0 to 1.0,
      "reason": "One sentence explaining why this company is affected"
    }}
  ]
}}

Rules:
- Only include companies from the NSE stock list provided
- DIRECT = explicitly mentioned in the article
- SECTOR = same industry as mentioned company
- SUPPLY_CHAIN = upstream or downstream supplier/customer
- MACRO = affected by macro factor (rate, oil, FX, inflation)
- COMPETITOR = direct business rival
- Be conservative: DIRECT max 0.95, SECTOR max 0.65, others max 0.5
- Return ONLY valid JSON array, no markdown, no explanation

[
  {{"article_id": 1, "affected_entities": [...]}},
  ...
]"""


# ─────────────────────────────────────────────
#  GEMINI API CALL
# ─────────────────────────────────────────────
def _call_gemini(prompt: str):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[Gemini] ERROR: GEMINI_API_KEY not set")
        return None

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature":      0.1,
            "maxOutputTokens":  8192,
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
                print(f"[Gemini] Rate limited. Waiting {wait}s (attempt {attempt})...")
                time.sleep(wait)
                continue

            if response.status_code != 200:
                print(f"[Gemini] HTTP {response.status_code}: {response.text[:200]}")
                return None

            data = response.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"].strip()

            # Strip markdown fences if present
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text.strip())

        except json.JSONDecodeError as e:
            print(f"[Gemini] JSON parse error: {e}")
            return None
        except Exception as e:
            print(f"[Gemini] Request error (attempt {attempt}): {e}")
            if attempt < RETRY_ATTEMPTS:
                time.sleep(RETRY_DELAY)

    return None


# ─────────────────────────────────────────────
#  MERGE RESULTS BACK INTO PROFILES
# ─────────────────────────────────────────────
def _merge_results(batch: list, gemini_results: list) -> list:
    results_map = {str(item.get("article_id", "")): item.get("affected_entities", [])
                   for item in gemini_results}

    enriched = []
    for profile in batch:
        pid      = str(profile.get("id", ""))
        entities = results_map.get(pid, [])
        entities.sort(key=lambda x: x.get("confidence", 0), reverse=True)

        enriched.append({
            **profile,
            "affected_entities": entities,
            "affected_count": {
                "total":        len(entities),
                "direct":       sum(1 for e in entities if e.get("impact_type") == "DIRECT"),
                "sector":       sum(1 for e in entities if e.get("impact_type") == "SECTOR"),
                "supply_chain": sum(1 for e in entities if e.get("impact_type") == "SUPPLY_CHAIN"),
                "macro":        sum(1 for e in entities if e.get("impact_type") == "MACRO"),
                "competitor":   sum(1 for e in entities if e.get("impact_type") == "COMPETITOR"),
            },
            "layer2_processed_at": datetime.now().isoformat(),
        })
    return enriched


# ─────────────────────────────────────────────
#  BATCH RUNNER — main entry point
# ─────────────────────────────────────────────
def run_layer2(profiles: list) -> list:
    if not _nse_stocks:
        print("[Layer2] WARNING: NSE stock list empty — call load_knowledge_graph() first")

    stock_list_text = get_nse_stock_list_text()
    all_enriched    = []
    total_batches   = (len(profiles) + BATCH_SIZE - 1) // BATCH_SIZE

    print(f"[Layer2] {len(profiles)} profiles → {total_batches} Gemini batches...")

    for i in range(0, len(profiles), BATCH_SIZE):
        batch     = profiles[i: i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1

        print(f"[Layer2] Batch {batch_num}/{total_batches}...")
        gemini_results = _call_gemini(_build_prompt(batch, stock_list_text))

        if gemini_results:
            enriched = _merge_results(batch, gemini_results)
            all_enriched.extend(enriched)
            total_entities = sum(e["affected_count"]["total"] for e in enriched)
            print(f"[Layer2] Batch {batch_num} ✅ — {total_entities} entities found")
        else:
            print(f"[Layer2] Batch {batch_num} ❌ — Gemini failed, passing through empty")
            for profile in batch:
                all_enriched.append({
                    **profile,
                    "affected_entities": [],
                    "affected_count":    {"total": 0, "direct": 0, "sector": 0,
                                          "supply_chain": 0, "macro": 0, "competitor": 0},
                    "layer2_processed_at": datetime.now().isoformat(),
                    "layer2_error": "Gemini API call failed"
                })

        # 4s gap between batches — stays within 15 req/min free limit
        if batch_num < total_batches:
            time.sleep(4)

    print(f"[Layer2] Complete. {len(all_enriched)} profiles enriched.")
    return all_enriched