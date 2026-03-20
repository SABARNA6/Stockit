import json
import re
import time
from groq import Groq
from groq import RateLimitError
from config.config import TIER3_BATCH_SIZE, QUALITY_THRESHOLD, GROQ_KEYS
from core import cache
from core import budget as bgt
from core import router

SYSTEM_PROMPT = """You are a financial analyst. Analyze how each news article affects the given stock.

RULES:
- Reply with ONLY a JSON array. No explanation, no markdown, no code blocks.
- Every article in the input must have exactly one object in the output.
- Use exactly these values:
  impact: HIGH or MEDIUM or LOW
  direction: BULLISH or BEARISH or NEUTRAL
  confidence: HIGH or MEDIUM or LOW
  horizon: IMMEDIATE or SHORT_TERM or LONG_TERM
- cause must explicitly mention the target stock symbol and explain the transmission path
    (for example: revenue demand, input costs, valuation multiples, sector sentiment,
    regulatory exposure, supply chain, or customer concentration).

EXAMPLE OUTPUT for 2 articles:
[{"id":0,"impact":"HIGH","direction":"BULLISH","confidence":"HIGH","cause":"Deal adds 2% to annual revenue directly","horizon":"IMMEDIATE"},{"id":1,"impact":"MEDIUM","direction":"BEARISH","confidence":"MEDIUM","cause":"Rate hike compresses valuation multiples for growth stocks","horizon":"SHORT_TERM"}]"""


def _entity_linked_cause(cause: str, article: dict, equity: dict) -> str:
    """Ensure cause explicitly ties impact to the target equity."""
    symbol = equity.get("symbol", "").upper()
    name = (equity.get("name") or "").strip()
    sector = (equity.get("sector") or "").strip()
    risks = equity.get("risks") or []
    key_risk = risks[0] if risks else "market risk"

    raw = (cause or "").strip()
    if not raw:
        raw = "Insufficient article detail to estimate direct impact"

    lower = raw.lower()
    has_entity = symbol.lower() in lower or (name and name.lower() in lower)

    atype = (article.get("type") or "").upper()
    if atype in ("DIRECT", "COMPANY_SPECIFIC"):
        channel = "via order flow, earnings outlook, or company-specific execution"
    elif atype in ("INDIRECT_REVENUE",):
        channel = "via demand and revenue sensitivity"
    elif atype in ("INDIRECT_COST",):
        channel = "via input-cost and margin pressure"
    elif atype in ("INDIRECT_MACRO", "MACRO_INDIA", "MACRO_GLOBAL"):
        channel = f"via valuation and risk sentiment in {sector or 'its'} stocks"
    else:
        channel = f"via sector sentiment and {key_risk}"

    # Replace parser/debug artifacts with a clean business-facing explanation.
    if "parse error" in lower or "check logs" in lower:
        return (
            f"For {symbol}, this article has weak stock-specific linkage; "
            f"treat as low-confidence neutral-to-marginal impact {channel}."
        )

    # Rewrite overly generic negative/neutral statements into stock-linked phrasing.
    if "no direct impact" in lower or "indirect" in lower and not has_entity:
        return f"For {symbol}, likely indirect impact {channel}; monitor exposure through {key_risk}."

    if has_entity:
        return raw

    return f"For {symbol}, {raw} ({channel})."


def _build_prompt(articles: list[dict], equity: dict) -> str:
    profile = (
        f"Stock: {equity['symbol']} ({equity.get('name', '')}) | "
        f"Sector: {equity['sector']} | "
        f"Revenue: {equity.get('revenue_exposure', 'N/A')} | "
        f"Risks: {', '.join(equity.get('risks', []))}"
    )
    items = "\n".join(
        f"{i}. [{a.get('type', '')} score={a.get('score', '?')}] "
        f"{a['title']} — {a.get('description', '')[:120]}"
        for i, a in enumerate(articles)
    )
    return (
        f"{profile}\n\n"
        f"Analyze impact on {equity['symbol']} for each article below.\n"
        f"Reply ONLY with a JSON array of {len(articles)} objects.\n\n"
        f"{items}"
    )


def _extract_json(text: str) -> str:
    """Strip markdown fences and extract the JSON array."""
    # remove ```json ... ``` or ``` ... ```
    text = re.sub(r"```(?:json)?", "", text).strip("`").strip()
    # find first [ and last ]
    start = text.find("[")
    end   = text.rfind("]")
    if start != -1 and end != -1:
        return text[start:end+1]
    return text


def _parse_analysis(text: str, count: int) -> list[dict]:
    """Parse LLM JSON response with detailed error logging."""
    try:
        cleaned = _extract_json(text)
        results = json.loads(cleaned)
        if isinstance(results, list):
            # pad if model returned fewer items than expected
            while len(results) < count:
                results.append({
                    "id": len(results),
                    "impact": "LOW",
                    "direction": "NEUTRAL",
                    "confidence": "LOW",
                    "cause": "insufficient data",
                    "horizon": "SHORT_TERM"
                })
            return results[:count]
    except Exception as e:
        print(f"[tier3] JSON parse error: {e}")
        print(f"[tier3] Raw LLM output was:\n{text[:500]}")

    # hard fallback
    return [
        {
            "id": i, "impact": "LOW", "direction": "NEUTRAL",
            "confidence": "LOW",
            "cause": "Insufficient article-specific signal; treat as low-confidence neutral impact",
            "horizon": "SHORT_TERM"
        }
        for i in range(count)
    ]


def _is_bad_cached_cause(cause: str) -> bool:
    """Detect low-quality cached causes that should be recomputed."""
    text = (cause or "").lower()
    markers = ["parse error", "insufficient data", "check logs"]
    return any(m in text for m in markers)


def _analyze_batch(articles: list[dict], equity: dict) -> list[dict]:
    """Analyze one batch of up to TIER3_BATCH_SIZE articles."""
    max_score  = max(a.get("score", 0) for a in articles)
    est_tokens = 800

    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        api_key, model = router.get_key(
            tier=3,
            score=max_score,
            est_tokens=est_tokens
        )
        client = Groq(api_key=api_key)

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": _build_prompt(articles, equity)},
                ],
                temperature=0.0,       # deterministic — better JSON compliance
                max_tokens=800,        # increased to avoid truncation
            )

            tokens_used = response.usage.total_tokens
            key_id = "key_a" if api_key == GROQ_KEYS["key_a"] else "key_b"
            bgt.record(key_id, model, tokens_used)

            raw = response.choices[0].message.content
            print(f"[tier3] model={model} tokens={tokens_used}")
            return _parse_analysis(raw, len(articles))
        except RateLimitError as e:
            msg = str(e)
            wait_s = 2.0 * attempt
            m = re.search(r"try again in\s*([0-9.]+)s", msg, flags=re.IGNORECASE)
            if m:
                wait_s = max(wait_s, float(m.group(1)) + 0.5)
            print(f"[tier3] rate-limited on attempt {attempt}/{max_attempts}; sleeping {wait_s:.1f}s")
            if attempt == max_attempts:
                print("[tier3] max retries reached, using low-confidence fallback analysis")
                return _parse_analysis("[]", len(articles))
            time.sleep(wait_s)
        except Exception as e:
            print(f"[tier3] batch analysis failed: {e}")
            return _parse_analysis("[]", len(articles))

    return _parse_analysis("[]", len(articles))


# ─── MAIN ENTRY ───────────────────────────────────────────────────────────────

def run(articles: list[dict], equity: dict) -> list[dict]:
    """
    Deep analysis for all articles that passed Tier 2.
    Returns enriched articles with impact/direction/cause/horizon.
    """
    to_analyze     = []
    cached_results = []

    for a in articles:
        if a.get("type") == "COMPANY_SPECIFIC":
            to_analyze.append(a)
            continue

        key    = "t3:" + cache.sector_key(equity["sector"]) + ":" + a["hash"]
        cached = cache.get(key)
        if cached:
            # Recompute stale fallback-style cached causes.
            if _is_bad_cached_cause(cached.get("cause", "")):
                to_analyze.append(a)
                continue
            a.update(cached)
            cached_results.append(a)
        else:
            to_analyze.append(a)

    print(f"[tier3] {len(cached_results)} cache hits, {len(to_analyze)} to analyze")

    analyzed = []
    for i in range(0, len(to_analyze), TIER3_BATCH_SIZE):
        batch   = to_analyze[i : i + TIER3_BATCH_SIZE]
        results = _analyze_batch(batch, equity)

        for article, result in zip(batch, results):
            article["impact"]     = result.get("impact",     "LOW")
            article["direction"]  = result.get("direction",  "NEUTRAL")
            article["confidence"] = result.get("confidence", "LOW")
            article["cause"]      = _entity_linked_cause(result.get("cause", ""), article, equity)
            article["horizon"]    = result.get("horizon",    "SHORT_TERM")

            # cache shared (non company-specific) articles
            if article.get("type") != "COMPANY_SPECIFIC":
                key = "t3:" + cache.sector_key(equity["sector"]) + ":" + article["hash"]
                cache.set(key, "sector", {
                    "impact":     article["impact"],
                    "direction":  article["direction"],
                    "confidence": article["confidence"],
                    "cause":      article["cause"],
                    "horizon":    article["horizon"],
                })
            analyzed.append(article)

    all_results = cached_results + analyzed

    # sort by impact
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    all_results.sort(key=lambda x: order.get(x.get("impact", "LOW"), 2))
    return all_results

