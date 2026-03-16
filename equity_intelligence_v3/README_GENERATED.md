# Equity Intelligence v3 README (Generated)

## 1. Functionality
`equity_intelligence_v3` is a complete news-to-signal engine focused on Indian equities.
- Ingests RSS feeds and NewsAPI articles.
- Stores and de-duplicates in Supabase (`rss_pool`, `rss_feeds`, `equities`).
- Executes a 3-tier analysis pipeline for each equity.
- Aggregates article-level impacts into `price_impact` score.
- Exposes REST endpoints and command-line batch mode.

## 2. Why this is calculated
- News is noisy; tiered filtering reduces irrelevant data and API costs.
- Tier1 gives deterministic tagging with domain keywords.
- Tier2 gives relevance 0-10 so only strong leads reach deep orders.
- Tier3 translates narrative to action (impact/direction/confidence/horizon).
- Price impact map connects qualitative signals to expected return ranges.

## 3. What formula is used
### Tier1 (free filtering)
- Dedup: SHA256 of title+description (16 hex chars).
- Keyword filter: equity sector keywords + peers + macro keywords.
- Classification:
  - `COMPANY_SPECIFIC` if symbol/name in text.
  - `PEER_NEWS` if peers appear.
  - `MACRO_*`/`SECTOR_LEVEL` using keyword maps.
  - Else `NOISE`.

### Tier2 (relevance scoring)
- Uses Groq LLM with prompt asking 0-10 relevance.
- Uses cache key `sector:hash`.
- Threshold (`TIER2_THRESHOLD`, default `6`): keep only scores >= threshold.

### Tier3 (impact extraction)
- Uses Groq LLM with strict JSON output fields:
  - `impact` (HIGH/MEDIUM/LOW)
  - `direction` (BULLISH/BEARISH/NEUTRAL)
  - `confidence` (HIGH/MEDIUM/LOW)
  - `cause` text with stock-links
  - `horizon` (IMMEDIATE/SHORT_TERM/LONG_TERM)
- Caches non-company-specific outputs by `t3:sector:hash`.

### Price Impact (core/price_impact.py)
- Each article gets low/high estimate from RULE_TABLE by type/impact/direction.
- Normalization:
  - Impact weight: HIGH=3, MEDIUM=2, LOW=1.
  - Confidence coefficient: HIGH=1.0, MEDIUM=0.7, LOW=0.4.
- For each article:
  - center = (low+high)/2
  - half = abs(high-low)/2
  - weight = impact_weight * confidence_factor
- Aggregated portfolio:
  - overall_center = weighted_center / total_weight
  - overall_band = weighted_half / total_weight
  - overall_low = center - band
  - overall_high = center + band
- Direction:
  - center >= 0.2 → BULLISH
  - center <= -0.2 → BEARISH
  - else NEUTRAL

### Sentiment score (core/pipeline.py)
- Weighted score 1-10:
  - directional score: BULLISH=7, NEUTRAL=5, BEARISH=3
  - weights by impact: HIGH=3, MEDIUM=2, LOW=1.
- Overall direction: score >=6→BULLISH, <=4→BEARISH,
  else NEUTRAL.

## 4. API endpoints (quick)
- `GET /api/rss/trigger`
- `GET /api/analyze/<symbol>?hours_back=24&prune_news=false`
- `GET /api/limits`
- `GET|POST /api/equities/sync`

## 5. Run
```bash
cd equity_intelligence_v3
pip install -r requirements.txt
cp .env.example .env
# fill SUPABASE_URL, SUPABASE_KEY, GROQ_KEY_A/B, NEWS_API_KEY
python server.py  # API mode
# or
python main.py    # batch mode
```
