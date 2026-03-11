"""
=====================================================================
  LAYER 2 : IMPACT PROPAGATION
  LLM      : OpenRouter (Llama 3.3 70B) → Gemini fallback
  Input    : Layer 1 profiles (batches of 5)
  Output   : Affected entities with impact type + confidence + reason

  Features:
  - Logs to Supabase after EACH batch (not all at end)
  - Skips articles already in l2_logs (no re-processing)
  - MAX_BATCHES limit to control API usage
=====================================================================
"""

import os
import time
import requests
from datetime import datetime
from layers.llm_client import call_llm

BATCH_SIZE  = 5
MAX_BATCHES = None   # set to e.g. 5 to process only first 5 batches
                     # set to None to process all

# ─────────────────────────────────────────────
#  NSE stock cache
# ─────────────────────────────────────────────
_nse_stocks:  list = []
_nse_lookup:  dict = {}
_sector_index:dict = {}


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


# ─────────────────────────────────────────────
#  CHECK ALREADY PROCESSED (skip duplicates)
# ─────────────────────────────────────────────
def _get_already_processed_ids() -> set:
    """
    Fetch news_ids already in l2_logs from Supabase.
    Skips re-processing articles that already have L2 results.
    """
    try:
        from database.supabase_logger import _get_headers, _url
        response = requests.get(
            _url("l2_logs") + "?select=news_id&limit=5000",
            headers=_get_headers(),
            timeout=10
        )
        if response.status_code == 200:
            rows = response.json()
            ids  = {str(r["news_id"]) for r in rows if r.get("news_id")}
            print(f"[Layer2] Found {len(ids)} already-processed article IDs in l2_logs")
            return ids
        else:
            print(f"[Layer2] ⚠️ Could not fetch processed IDs: {response.status_code}")
            return set()
    except Exception as e:
        print(f"[Layer2] ⚠️ Skip-check failed: {e}")
        return set()


# ─────────────────────────────────────────────
#  LOG BATCH TO SUPABASE IMMEDIATELY
# ─────────────────────────────────────────────
def _log_batch(enriched_profiles: list):
    """Log L2 results for a batch immediately after processing."""
    try:
        from database.supabase_logger import _get_headers, _url
        rows = []
        ts   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for p in enriched_profiles:
            for e in p.get("affected_entities", []):
                rows.append({
                    "news_id":    p.get("id"),
                    "news_title": str(p.get("title", ""))[:300],
                    "ticker":     e.get("ticker", ""),
                    "company":    e.get("name", ""),
                    "industry":   e.get("industry", ""),
                    "impact_type":e.get("impact_type", ""),
                    "direction":  e.get("direction", ""),
                    "confidence": e.get("confidence", 0),
                    "reason":     str(e.get("reason", ""))[:500],
                    "sentiment":  e.get("sentiment", ""),
                })

        if not rows:
            return

        response = requests.post(
            _url("l2_logs"),
            headers=_get_headers(),
            json=rows,
            timeout=10
        )
        if response.status_code in (200, 201):
            print(f"[Layer2] ✅ Logged {len(rows)} entity rows to Supabase")
        else:
            print(f"[Layer2] ❌ Log failed: {response.status_code} {response.text[:100]}")

    except Exception as e:
        print(f"[Layer2] ❌ Log exception: {e}")


# ─────────────────────────────────────────────
#  STOCK FILTERING
# ─────────────────────────────────────────────
def _get_relevant_stocks(batch: list) -> str:
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

    source = filtered.values() if filtered else _nse_stocks
    return "\n".join(f"{s['ticker']}|{s['name']}|{s['industry']}" for s in source)


# ─────────────────────────────────────────────
#  PROMPT BUILDER
# ─────────────────────────────────────────────
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


# ─────────────────────────────────────────────
#  MERGE RESULTS
# ─────────────────────────────────────────────
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


# ─────────────────────────────────────────────
#  MAIN RUNNER
# ─────────────────────────────────────────────
def run_layer2(profiles: list, max_batches: int = None) -> list:
    """
    max_batches: limit number of batches processed this run
                 None = process all
                 e.g. 5 = process first 25 articles only
    """
    if not _nse_stocks:
        print("[Layer2] ⚠️ NSE stock list empty — load_knowledge_graph() not called")

    # ── Skip already processed articles ──────
    already_done = _get_already_processed_ids()
    filtered     = [p for p in profiles
                    if str(p.get("id", "")) not in already_done]
    skipped      = len(profiles) - len(filtered)

    if skipped > 0:
        print(f"[Layer2] Skipping {skipped} already-processed articles")

    if not filtered:
        print("[Layer2] All articles already processed — nothing to do")
        return profiles   # return original with existing data

    # ── Apply max_batches limit ───────────────
    limit        = max_batches or MAX_BATCHES
    if limit:
        max_articles = limit * BATCH_SIZE
        if len(filtered) > max_articles:
            print(f"[Layer2] Limiting to {limit} batches ({max_articles} articles)")
            filtered = filtered[:max_articles]

    total_batches = (len(filtered) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"[Layer2] {len(filtered)} profiles → {total_batches} batches "
          f"(BATCH_SIZE={BATCH_SIZE})")

    all_enriched = []

    for i in range(0, len(filtered), BATCH_SIZE):
        batch     = filtered[i: i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1

        print(f"[Layer2] ── Batch {batch_num}/{total_batches} "
              f"({len(batch)} articles) ──────────")

        results = call_llm(_build_prompt(batch))

        if results:
            enriched    = _merge_results(batch, results)
            total_ents  = sum(e["affected_count"]["total"] for e in enriched)
            print(f"[Layer2] Batch {batch_num} ✅ — {total_ents} entities found")

            # ── Log this batch to Supabase immediately ──
            _log_batch(enriched)

        else:
            print(f"[Layer2] Batch {batch_num} ❌ — LLM failed, logging empty results")
            enriched = []
            for profile in batch:
                enriched.append({
                    **profile,
                    "affected_entities": [],
                    "affected_count": {
                        "total":0,"direct":0,"sector":0,
                        "supply_chain":0,"macro":0,"competitor":0
                    },
                    "layer2_processed_at": datetime.now().isoformat(),
                    "layer2_error": "All LLM calls failed",
                })

        all_enriched.extend(enriched)

        # ── Delay between batches ─────────────
        if batch_num < total_batches:
            time.sleep(2)

    print(f"[Layer2] ✅ Complete — {len(all_enriched)} profiles enriched "
          f"({skipped} skipped as already done)")
    return all_enriched