"""
=====================================================================
  LAYER 2 : IMPACT PROPAGATION
  LLM      : OpenRouter (Llama 3.3 70B) → Gemini fallback
  Input    : Layer 1 profiles (batches of 10)
  Output   : Affected entities with impact type + confidence + reason
=====================================================================
"""

import time
from datetime import datetime
from layers.llm_client import call_llm

BATCH_SIZE = 5

# ─────────────────────────────────────────────
#  NSE stock cache
# ─────────────────────────────────────────────
_nse_stocks:  list = []
_nse_lookup:  dict = {}
_sector_index:dict = {}


def load_knowledge_graph(stocks: list) -> None:
    global _nse_stocks, _nse_lookup, _sector_index
    _nse_stocks    = []
    _nse_lookup    = {}
    _sector_index  = {}

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
    """Only send stocks from sectors relevant to this batch — saves tokens."""
    relevant_sectors  = set()
    mentioned_tickers = set()

    for p in batch:
        for s in p.get("event", {}).get("sectors", []):
            relevant_sectors.add(s)
        for e in p.get("entities", []):
            ticker = e.get("ticker", "")
            if ticker in _nse_lookup:
                industry = _nse_lookup[ticker].get("industry", "")
                if industry:
                    relevant_sectors.add(industry)
            mentioned_tickers.add(ticker)

    filtered = {}
    for sector in relevant_sectors:
        for stock in _sector_index.get(sector, []):
            filtered[stock["ticker"]] = stock
    for ticker in mentioned_tickers:
        if ticker in _nse_lookup:
            filtered[ticker] = _nse_lookup[ticker]

    # Fallback — send all if no sectors found
    source = filtered.values() if filtered else _nse_stocks
    return "\n".join(f"{s['ticker']}|{s['name']}|{s['industry']}" for s in source)


def _build_prompt(batch: list) -> str:
    stock_list    = _get_relevant_stocks(batch)
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

Relevant NSE-listed companies (TICKER|Name|Industry):
{stock_list}

Analyze these {len(batch)} news articles. For EACH article identify which NSE companies are affected.

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
- DIRECT=mentioned, SECTOR=same industry, SUPPLY_CHAIN=upstream/downstream
- MACRO=rate/oil/FX/inflation effect, COMPETITOR=direct rival
- Confidence: DIRECT≤0.95, SECTOR≤0.65, others≤0.5
- Return ONLY valid JSON array, no markdown, no explanation"""


def _merge_results(batch: list, results: list) -> list:
    results_map = {
        str(item.get("article_id", "")): item.get("affected_entities", [])
        for item in results
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


def run_layer2(profiles: list) -> list:
    if not _nse_stocks:
        print("[Layer2] ⚠️ NSE stock list empty — call load_knowledge_graph() first")

    all_enriched  = []
    total_batches = (len(profiles) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"[Layer2] {len(profiles)} profiles → {total_batches} batches...")

    for i in range(0, len(profiles), BATCH_SIZE):
        batch     = profiles[i: i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1

        print(f"[Layer2] Batch {batch_num}/{total_batches} ({len(batch)} articles)...")
        results = call_llm(_build_prompt(batch))

        if results:
            enriched = _merge_results(batch, results)
            all_enriched.extend(enriched)
            total_e = sum(e["affected_count"]["total"] for e in enriched)
            print(f"[Layer2] Batch {batch_num} ✅ — {total_e} entities found")
        else:
            print(f"[Layer2] Batch {batch_num} ❌ — both LLMs failed")
            for profile in batch:
                all_enriched.append({
                    **profile,
                    "affected_entities": [],
                    "affected_count":    {"total":0,"direct":0,"sector":0,
                                          "supply_chain":0,"macro":0,"competitor":0},
                    "layer2_processed_at": datetime.now().isoformat(),
                    "layer2_error": "All LLM calls failed"
                })

        if batch_num < total_batches:
            time.sleep(2)   # shorter delay — OpenRouter is more generous

    print(f"[Layer2] ✅ Complete — {len(all_enriched)} profiles enriched.")
    return all_enriched