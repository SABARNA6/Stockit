# ─── API KEYS ────────────────────────────────────────────────────────────────
import os
from dotenv import load_dotenv

load_dotenv()  # reads .env file from project root

GROQ_KEYS = {
    "key_a": os.getenv("GROQ_KEY_A"),   # used for Tier 2 (scoring)
    "key_b": os.getenv("GROQ_KEY_B"),   # used for Tier 3 (analysis)
}

# fail early if keys are missing
if not GROQ_KEYS["key_a"] or not GROQ_KEYS["key_b"]:
    raise ValueError("Missing GROQ_KEY_A or GROQ_KEY_B in .env file")

# ─── MODELS ──────────────────────────────────────────────────────────────────
TIER2_MODEL   = "llama-3.1-8b-instant"     # fast, 500K TPD per key
TIER3_MODEL   = "llama-3.1-8b-instant"     # standard analysis
TIER3_QUALITY = "llama-3.3-70b-versatile"  # only for score >= 9 articles
FALLBACK      = "qwen-qwq-32b"             # if 8B exhausted

# ─── GROQ FREE TIER LIMITS (per key per model) ───────────────────────────────
LIMITS = {
    "llama-3.1-8b-instant": {
        "rpm": 30,
        "rpd": 14400,
        "tpm": 6000,
        "tpd": 500_000,
    },
    "llama-3.3-70b-versatile": {
        "rpm": 30,
        "rpd": 1000,
        "tpm": 12000,
        "tpd": 100_000,
    },
    "qwen-qwq-32b": {
        "rpm": 60,
        "rpd": 1000,
        "tpm": 6000,
        "tpd": 500_000,
    },
}

# ─── PIPELINE SETTINGS ───────────────────────────────────────────────────────
TIER2_BATCH_SIZE      = 10    # articles per Tier 2 LLM call
TIER3_BATCH_SIZE      = 5     # articles per Tier 3 LLM call
TIER2_THRESHOLD       = 6     # min score to pass into Tier 3
QUALITY_THRESHOLD     = 9     # min score to use 70B model in Tier 3

# ─── CACHE TTLs (hours) ──────────────────────────────────────────────────────
TTL = {
    "article": 24,
    "sector":  12,
    "equity":  3,    # reduced to 1hr during market hours by cache.py
    "user":    1,
}

MARKET_OPEN  = "09:00"
MARKET_CLOSE = "15:30"

# ─── PATHS ───────────────────────────────────────────────────────────────────
DB_PATH         = "db/cache.db"
EQUITIES_PATH   = "data/equities.json"
KEYWORDS_PATH   = "data/keywords.json"
