import time
from datetime import datetime
from config import GROQ_KEYS, LIMITS, TIER2_MODEL, TIER3_MODEL, TIER3_QUALITY, FALLBACK
import budget as bgt

# tracks calls per key this minute  {key_id: [timestamp, ...]}
_minute_calls: dict = {"key_a": [], "key_b": []}


def _rpm_ok(key_id: str, model: str) -> bool:
    """Check if this key is under its RPM limit."""
    limit = LIMITS[model]["rpm"]
    now = time.time()
    # keep only calls in the last 60 seconds
    _minute_calls[key_id] = [t for t in _minute_calls[key_id] if now - t < 60]
    return len(_minute_calls[key_id]) < limit


def _wait_for_rpm(key_id: str, model: str):
    """Sleep until this key is under RPM limit."""
    while not _rpm_ok(key_id, model):
        print(f"[router] RPM limit hit on {key_id}, waiting 5s...")
        time.sleep(5)


def _record_call(key_id: str):
    _minute_calls[key_id].append(time.time())


def get_key(tier: int, score: int = 0, est_tokens: int = 500) -> tuple[str, str]:
    """
    Returns (api_key, model_name) for a given tier.
    Handles fallback automatically.

    tier=2 → key_a, 8B model
    tier=3, score<9  → key_b, 8B model
    tier=3, score>=9 → key_b, 70B model (falls back to 8B if exhausted)
    """

    if tier == 2:
        candidates = [
            ("key_a", TIER2_MODEL),
            ("key_b", TIER2_MODEL),   # fallback if key_a exhausted
            ("key_a", FALLBACK),
            ("key_b", FALLBACK),
        ]

    elif tier == 3 and score >= 9:
        candidates = [
            ("key_b", TIER3_QUALITY),  # 70B preferred for direct news
            ("key_a", TIER3_QUALITY),
            ("key_b", TIER3_MODEL),    # fall back to 8B
            ("key_a", TIER3_MODEL),
        ]

    else:  # tier 3 standard
        candidates = [
            ("key_b", TIER3_MODEL),
            ("key_a", TIER3_MODEL),
            ("key_b", FALLBACK),
            ("key_a", FALLBACK),
        ]

    for key_id, model in candidates:
        if bgt.can_afford(key_id, model, est_tokens):
            _wait_for_rpm(key_id, model)
            _record_call(key_id)
            return GROQ_KEYS[key_id], model

    raise RuntimeError(
        f"[router] All keys exhausted for tier={tier}. "
        f"Daily budget used up. Try again tomorrow."
    )
