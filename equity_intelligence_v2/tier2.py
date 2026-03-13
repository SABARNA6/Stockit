import json
from groq import Groq
from config import TIER2_BATCH_SIZE, TIER2_THRESHOLD
import cache
import budget as bgt
import router

SYSTEM_PROMPT = """You are a financial news relevance scorer.
Score each article's relevance to the given stock on a scale of 0-10.
Respond ONLY with a valid JSON array of objects, no other text.
Format: [{"id": 0, "score": 7, "type": "INDIRECT_REVENUE"}, ...]
Types: DIRECT, INDIRECT_REVENUE, INDIRECT_COST, INDIRECT_MACRO, NOISE"""


def _build_prompt(articles: list[dict], equity: dict) -> str:
    profile = (
        f"Stock: {equity['symbol']} | Sector: {equity['sector']} | "
        f"Revenue: {equity.get('revenue_exposure', 'N/A')} | "
        f"Key risks: {', '.join(equity.get('risks', []))}"
    )
    items = "\n".join(
        f"{i}. {a['title']} — {a.get('description', '')[:100]}"
        for i, a in enumerate(articles)
    )
    return f"{profile}\n\nScore these articles 0-10 for relevance:\n{items}"


def _parse_scores(text: str, count: int) -> list[dict]:
    """Parse LLM JSON response safely."""
    try:
        # strip markdown fences if present
        text = text.strip().strip("```json").strip("```").strip()
        results = json.loads(text)
        if isinstance(results, list) and len(results) == count:
            return results
    except Exception:
        pass
    # fallback: return neutral scores so pipeline can continue
    print(f"[tier2] WARNING: failed to parse scores, using fallback")
    return [{"id": i, "score": 5, "type": "SECTOR_LEVEL"} for i in range(count)]


def _score_batch(articles: list[dict], equity: dict) -> list[dict]:
    """Score one batch of up to TIER2_BATCH_SIZE articles."""
    est_tokens = 500
    api_key, model = router.get_key(tier=2, est_tokens=est_tokens)
    client = Groq(api_key=api_key)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": _build_prompt(articles, equity)},
        ],
        temperature=0.1,
        max_tokens=400,
    )

    tokens_used = response.usage.total_tokens
    key_id = "key_a" if api_key == router.GROQ_KEYS["key_a"] else "key_b"
    bgt.record(key_id, model, tokens_used)

    text    = response.choices[0].message.content
    results = _parse_scores(text, len(articles))
    return results


# ─── MAIN ENTRY ───────────────────────────────────────────────────────────────

def run(articles: list[dict], equity: dict) -> list[dict]:
    """
    Score all articles for relevance to this equity.
    Returns only articles scoring >= TIER2_THRESHOLD.
    Uses SQLite cache — repeated articles cost $0.
    """
    scored    = []
    to_score  = []   # articles not in cache
    cached_results = []

    # check cache for each article
    for a in articles:
        key = cache.sector_key(equity["sector"]) + ":" + a["hash"]
        cached = cache.get(key)
        if cached:
            # attach score from cache
            a.update(cached)
            cached_results.append(a)
        else:
            to_score.append(a)

    print(f"[tier2] {len(cached_results)} cache hits, {len(to_score)} to score")

    # score uncached articles in batches
    for i in range(0, len(to_score), TIER2_BATCH_SIZE):
        batch   = to_score[i : i + TIER2_BATCH_SIZE]
        results = _score_batch(batch, equity)

        for article, result in zip(batch, results):
            score = result.get("score", 0)
            atype = result.get("type", "NOISE")
            article["score"] = score
            article["type"]  = atype

            # cache the score for this article+sector
            key = cache.sector_key(equity["sector"]) + ":" + article["hash"]
            cache.set(key, "sector", {"score": score, "type": atype})
            scored.append(article)

    all_articles = cached_results + scored

    # filter by threshold
    passed = [a for a in all_articles if a.get("score", 0) >= TIER2_THRESHOLD]
    dropped = len(all_articles) - len(passed)
    print(f"[tier2] threshold={TIER2_THRESHOLD}: {len(passed)} passed, {dropped} dropped")
    return passed
