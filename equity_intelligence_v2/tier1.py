import json
import hashlib
from config import KEYWORDS_PATH


def _load_keywords() -> dict:
    with open(KEYWORDS_PATH) as f:
        return json.load(f)


KEYWORDS = _load_keywords()

ARTICLE_TYPES = [
    "COMPANY_SPECIFIC",
    "PEER_NEWS",
    "SECTOR_LEVEL",
    "MACRO_INDIA",
    "MACRO_GLOBAL",
    "NOISE",
]


# ─── STEP 1: DEDUPLICATION ────────────────────────────────────────────────────

def dedup(articles: list[dict]) -> list[dict]:
    """Remove duplicate articles by content hash."""
    seen = set()
    unique = []
    for a in articles:
        h = hashlib.sha256(
            (a.get("title", "") + a.get("description", "")).lower().encode()
        ).hexdigest()[:16]
        if h not in seen:
            seen.add(h)
            a["hash"] = h
            unique.append(a)
    removed = len(articles) - len(unique)
    if removed:
        print(f"[tier1] dedup removed {removed} duplicate articles")
    return unique


# ─── STEP 2: KEYWORD FILTER ───────────────────────────────────────────────────

def keyword_filter(articles: list[dict], equity: dict) -> list[dict]:
    """
    Keep articles that match equity's sector keywords,
    company name, or peer names.
    """
    sector   = equity.get("sector", "").lower()
    symbol   = equity.get("symbol", "").lower()
    name     = equity.get("name", "").lower()
    peers    = [p.lower() for p in equity.get("peers", [])]

    # sector keywords from keywords.json
    sector_kw = [k.lower() for k in KEYWORDS.get(sector, [])]

    # always-keep global macro keywords
    macro_kw = [k.lower() for k in KEYWORDS.get("macro_global", [])]
    india_kw = [k.lower() for k in KEYWORDS.get("macro_india", [])]

    all_keywords = sector_kw + macro_kw + india_kw + [symbol, name] + peers

    kept = []
    for a in articles:
        text = (a.get("title", "") + " " + a.get("description", "")).lower()
        if any(kw in text for kw in all_keywords):
            kept.append(a)

    removed = len(articles) - len(kept)
    print(f"[tier1] keyword filter: {len(articles)} → {len(kept)} ({removed} dropped)")
    return kept


# ─── STEP 3: CLASSIFY ─────────────────────────────────────────────────────────

def classify(article: dict, equity: dict) -> str:
    """
    Tag article type without any LLM call.
    Returns one of: COMPANY_SPECIFIC, PEER_NEWS, SECTOR_LEVEL,
                    MACRO_INDIA, MACRO_GLOBAL, NOISE
    """
    text   = (article.get("title", "") + " " + article.get("description", "")).lower()
    symbol = equity.get("symbol", "").lower()
    name   = equity.get("name", "").lower()
    peers  = [p.lower() for p in equity.get("peers", [])]

    macro_india_kw  = [k.lower() for k in KEYWORDS.get("macro_india", [])]
    macro_global_kw = [k.lower() for k in KEYWORDS.get("macro_global", [])]

    if symbol in text or name in text:
        return "COMPANY_SPECIFIC"
    if any(p in text for p in peers):
        return "PEER_NEWS"
    if any(k in text for k in macro_global_kw):
        return "MACRO_GLOBAL"
    if any(k in text for k in macro_india_kw):
        return "MACRO_INDIA"

    sector = equity.get("sector", "").lower()
    sector_kw = [k.lower() for k in KEYWORDS.get(sector, [])]
    if any(k in text for k in sector_kw):
        return "SECTOR_LEVEL"

    return "NOISE"


# ─── MAIN ENTRY ───────────────────────────────────────────────────────────────

def run(articles: list[dict], equity: dict) -> list[dict]:
    """
    Full Tier 1 pipeline. Returns filtered + classified articles.
    Cost: $0.00
    """
    articles = dedup(articles)
    articles = keyword_filter(articles, equity)
    for a in articles:
        a["type"] = classify(a, equity)
    # drop NOISE that slipped through keyword filter
    articles = [a for a in articles if a["type"] != "NOISE"]
    print(f"[tier1] final: {len(articles)} articles classified")
    return articles
