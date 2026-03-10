"""
=====================================================================
  LAYER 2 : IMPACT PROPAGATION via Gemini AI
  Model    : gemini-2.5-flash-lite (free tier, 1000 RPD)
  Input    : Layer 1 profiles (batches of 10)
  Output   : Affected entities with impact type + confidence + reason
  Optimized: Only sends relevant sector stocks to reduce token usage
=====================================================================
"""

import os
import json
import time
import requests
from datetime import datetime

# ─────────────────────────────────────────────
#  Gemini config
# ─────────────────────────────────────────────
GEMINI_MODEL   = "gemini-2.5-flash-lite"  # free, 1000 RPD
GEMINI_URL     = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
BATCH_SIZE     = 10
RETRY_ATTEMPTS = 3
RETRY_DELAY    = 5

# ─────────────────────────────────────────────
#  NSE stock cache
# ─────────────────────────────────────────────
_nse_stocks: list = []
_nse_lookup: dict = {}
_sector_index: dict = {}   # industry → [list of stocks]


def load_knowledge_graph(stocks: list) -> None:
    global _nse_stocks, _nse_lookup, _sector_index
    _nse_stocks   = []
    _nse_lookup   = {}
    _sector_index = {}

    for row in stocks:
        ticker   = str(row.get("Symbol",       row.get("ticker", ""))).strip().upper()
        name     = str(row.get("Company Name", row.get("company name", ""))).strip()
        industry = str(row.get("Industry",     row.get("industry", ""))).strip()
        if not ticker:
            continue
        entry = {"ticker": ticker, "name": name, "industry": industry}
        _nse_stocks.append(entry)
        _nse_lookup[ticker] = entry
        if industry:
            _sector_index.setdefault(industry, []).append(entry)

    print(f"[KG] Loaded {len(_nse_stocks)} stocks across {len(_sector_index)} sectors ✅")


def _get_relevant_stocks(batch: list) -> str:
    """
    Instead of sending ALL 500 stocks every call,
    only send stocks from sectors mentioned in this batch.
    Reduces tokens by ~80%.
    """
    # Collect all sectors mentioned across the batch
    relevant_sectors = set()
    mentioned_tickers = set()

    for p in batch:
        # Sectors from event classifier
        for s in p.get("event", {}).get("sectors", []):
            relevant_sectors.add(s)
        # Direct entities — include their sector too
        for e in p.get("entities", []):
            ticker = e.get("ticker", "")
            if ticker in _nse_lookup:
                industry = _nse_lookup[ticker].get("industry", "")
                if industry:
                    relevant_sectors.add(industry)
            mentioned_tickers.add(ticker)

    # If no sectors found, send all stocks (fallback)
    if not relevant_sectors:
        lines = [f"{s['ticker']}|{s['name']}|{s['industry']}" for s in _nse_stocks]
        return "\n".join(lines)

    # Build filtered stock list: direct mentions + sector peers
    filtered = {}
    for sector in relevant_sectors:
        for stock in _sector_index.get(sector, []):
            filtered[stock["ticker"]] = stock

    # Always include directly mentioned tickers
    for ticker in mentioned_tickers:
        if ticker in _nse_lookup:
            filtered[ticker] = _nse_lookup[ticker]

    lines = [f"{s['ticker']}|{s['name']}|{s['industry']}"
             for s in filtered.values()]
    return "\n".join(lines)


# ─────────────────────────────────────────────
#  PROMPT BUILDER
# ─────────────────────────────────────────────
def _build_prompt(batch: list) -> str:
    stock_list = _get_relevant_stocks(batch)

    articles_text = ""
    for i, p in enumerate(batch, 1):
        entities  = ", ".join(e["ticker"] for e in p.get("entities", [])) or "None"
        event     = p.get("event", {}).get("event_type", "General")
        themes    = ", ".join(p.get("event", {}).get("themes", [])) or "None"
        sentiment = p.get("sentiment", {}).get("label", "Neutral")
        compound  = p.get("sentiment", {}).get("compound", 0)
        articles_text += f"""
Article {i} (ID: {p.get("id")}):
  Title     : {p.get("title")}
  Summary   : {str(p.get("summary", ""))[:200]}
  Entities  : {entities}
  Event     : {event} | Themes: {themes}
  Sentiment : {sentiment} ({compound})
"""

    return f"""You are a financial analyst for Indian stock markets (NSE/BSE).

Relevant NSE-listed companies for this batch (TICKER|Name|Industry):
{stock_list}

Analyze these {len(batch)} news articles. For EACH, identify affected NSE companies.

{articles_text}

Return a JSON array — one object per article:
[
  {{
    "article_id": <id>,
    "affected_entities": [
      {{
        "ticker": "NSE_TICKER",
        "name": "Company Name",
        "industry": "Industry",
        "impact_type": "DIRECT|SECTOR|SUPPLY_CHAIN|MACRO|COMPETITOR",
        "direction": "POSITIVE|NEGATIVE|NEUTRAL",
        "confidence": 0.0-1.0,
        "reason": "One sentence why this company is affected"
      }}
    ]
  }}
]

Rules:
- Only use tickers from the stock list above
- DIRECT=mentioned in article, SECTOR=same industry, SUPPLY_CHAIN=upstream/downstream
- MACRO=affected by rate/oil/FX/inflation, COMPETITOR=direct rival
- Confidence: DIRECT≤0.95, SECTOR≤0.65, others≤0.5
- Return ONLY valid JSON, no markdown"""


# ─────────────────────────────────────────────
#  GEMINI API CALL
# ─────────────────────────────────────────────
def _call_gemini(prompt: str):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[Gemini] ❌ GEMINI_API_KEY not set in environment")
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
                print(f"[Gemini] ⚠️  Rate limited. Waiting {wait}s (attempt {attempt}/{RETRY_ATTEMPTS})...")
                time.sleep(wait)
                continue

            if response.status_code != 200:
                print(f"[Gemini] ❌ HTTP {response.status_code}: {response.text[:200]}")
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
            print(f"[Gemini] ❌ JSON parse error: {e}")
            return None
        except Exception as e:
            print(f"[Gemini] ❌ Request error (attempt {attempt}): {e}")
            if attempt < RETRY_ATTEMPTS:
                time.sleep(RETRY_DELAY)

    return None


# ─────────────────────────────────────────────
#  MERGE RESULTS
# ─────────────────────────────────────────────
def _merge_results(batch: list, gemini_results: list) -> list:
    results_map = {
        str(item.get("article_id", "")): item.get("affected_entities", [])
        for item in gemini_results
    }

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
#  BATCH RUNNER
# ─────────────────────────────────────────────
def run_layer2(profiles: list) -> list:
    if not _nse_stocks:
        print("[Layer2] ⚠️  NSE stock list empty — call load_knowledge_graph() first")

    all_enriched  = []
    total_batches = (len(profiles) + BATCH_SIZE - 1) // BATCH_SIZE

    print(f"[Layer2] {len(profiles)} profiles → {total_batches} Gemini batches "
          f"(model: {GEMINI_MODEL})")

    for i in range(0, len(profiles), BATCH_SIZE):
        batch     = profiles[i: i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1

        print(f"[Layer2] Batch {batch_num}/{total_batches} ({len(batch)} articles)...")

        gemini_results = _call_gemini(_build_prompt(batch))

        if gemini_results:
            enriched = _merge_results(batch, gemini_results)
            all_enriched.extend(enriched)
            total_entities = sum(e["affected_count"]["total"] for e in enriched)
            print(f"[Layer2] Batch {batch_num} ✅ — {total_entities} entities found")
        else:
            print(f"[Layer2] Batch {batch_num} ❌ — passing through with no entities")
            for profile in batch:
                all_enriched.append({
                    **profile,
                    "affected_entities": [],
                    "affected_count":    {"total": 0, "direct": 0, "sector": 0,
                                          "supply_chain": 0, "macro": 0, "competitor": 0},
                    "layer2_processed_at": datetime.now().isoformat(),
                    "layer2_error": "Gemini API call failed"
                })

        # 4s gap = ~15 req/min, safe for free tier
        if batch_num < total_batches:
            time.sleep(4)

    print(f"[Layer2] ✅ Complete — {len(all_enriched)} profiles enriched.")
    return all_enriched