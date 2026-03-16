from typing import Tuple


IMPACT_LEVELS = {"HIGH": 3, "MEDIUM": 2, "MED": 2, "LOW": 1}
CONFIDENCE_LEVELS = {"HIGH": 1.0, "MEDIUM": 0.7, "MED": 0.7, "LOW": 0.4}

# Base move rules in percentage points.
# Tuples are (low, high) and keep natural sign for the direction.
RULE_TABLE = {
    "COMPANY_SPECIFIC": {
        "HIGH": {"BULLISH": (3.0, 6.0), "BEARISH": (-6.0, -3.0), "NEUTRAL": (-0.4, 0.4)},
        "MEDIUM": {"BULLISH": (1.0, 3.0), "BEARISH": (-3.0, -1.0), "NEUTRAL": (-0.3, 0.3)},
        "LOW": {"BULLISH": (0.2, 1.0), "BEARISH": (-1.0, -0.2), "NEUTRAL": (-0.2, 0.2)},
    },
    "SECTOR_LEVEL": {
        "HIGH": {"BULLISH": (0.5, 1.5), "BEARISH": (-2.0, -0.8), "NEUTRAL": (-0.3, 0.3)},
        "MEDIUM": {"BULLISH": (0.2, 0.8), "BEARISH": (-1.0, -0.4), "NEUTRAL": (-0.2, 0.2)},
        "LOW": {"BULLISH": (0.0, 0.4), "BEARISH": (-0.4, 0.0), "NEUTRAL": (-0.1, 0.1)},
    },
    "MACRO_INDIA": {
        "HIGH": {"BULLISH": (0.5, 1.5), "BEARISH": (-2.0, -0.5), "NEUTRAL": (-0.3, 0.3)},
        "MEDIUM": {"BULLISH": (0.2, 0.8), "BEARISH": (-0.8, -0.2), "NEUTRAL": (-0.2, 0.2)},
        "LOW": {"BULLISH": (0.0, 0.3), "BEARISH": (-0.3, 0.0), "NEUTRAL": (-0.1, 0.1)},
    },
    "MACRO_GLOBAL": {
        "HIGH": {"BULLISH": (0.3, 1.0), "BEARISH": (-1.5, -0.5), "NEUTRAL": (-0.3, 0.3)},
        "MEDIUM": {"BULLISH": (0.1, 0.5), "BEARISH": (-0.7, -0.2), "NEUTRAL": (-0.2, 0.2)},
        "LOW": {"BULLISH": (0.0, 0.2), "BEARISH": (-0.2, 0.0), "NEUTRAL": (-0.1, 0.1)},
    },
    "NOISE": {
        "HIGH": {"BULLISH": (0.0, 0.2), "BEARISH": (-0.2, 0.0), "NEUTRAL": (-0.1, 0.1)},
        "MEDIUM": {"BULLISH": (0.0, 0.1), "BEARISH": (-0.1, 0.0), "NEUTRAL": (-0.1, 0.1)},
        "LOW": {"BULLISH": (0.0, 0.1), "BEARISH": (-0.1, 0.0), "NEUTRAL": (-0.1, 0.1)},
    },
}

TYPE_ALIAS = {
    "DIRECT": "COMPANY_SPECIFIC",
    "COMPANY_SPECIFIC": "COMPANY_SPECIFIC",
    "INDIRECT_REVENUE": "SECTOR_LEVEL",
    "INDIRECT_COST": "SECTOR_LEVEL",
    "SECTOR_LEVEL": "SECTOR_LEVEL",
    "PEER_NEWS": "SECTOR_LEVEL",
    "INDIRECT_MACRO": "MACRO_INDIA",
    "MACRO_INDIA": "MACRO_INDIA",
    "MACRO_GLOBAL": "MACRO_GLOBAL",
    "NOISE": "NOISE",
}


def _norm_impact(value: str) -> str:
    raw = (value or "LOW").upper()
    if raw == "MED":
        return "MEDIUM"
    return raw if raw in ("HIGH", "MEDIUM", "LOW") else "LOW"


def _norm_direction(value: str) -> str:
    raw = (value or "NEUTRAL").upper()
    return raw if raw in ("BULLISH", "BEARISH", "NEUTRAL") else "NEUTRAL"


def _norm_type(value: str) -> str:
    raw = (value or "NOISE").upper()
    return TYPE_ALIAS.get(raw, "NOISE")


def _format_pct(v: float) -> str:
    if v > 0:
        return f"+{v:.1f}%"
    return f"{v:.1f}%"


def _range_text(low: float, high: float) -> str:
    return f"{_format_pct(low)} to {_format_pct(high)}"


def estimate_article(article: dict) -> Tuple[float, float, str]:
    kind = _norm_type(article.get("type"))
    impact = _norm_impact(article.get("impact"))
    direction = _norm_direction(article.get("direction"))

    low, high = RULE_TABLE[kind][impact][direction]
    reason = article.get("cause") or f"Rule-based estimate from {kind}, {impact}, {direction}"
    return low, high, reason


def apply(articles: list[dict]) -> tuple[list[dict], dict]:
    if not articles:
        summary = {
            "overall_move_low": 0.0,
            "overall_move_high": 0.0,
            "overall_move_range": "0.0% to 0.0%",
            "overall_direction": "NEUTRAL",
            "signals": {"bullish": 0, "bearish": 0, "neutral": 0},
        }
        return articles, summary

    weighted_center = 0.0
    weighted_half = 0.0
    total_weight = 0.0
    bullish = bearish = neutral = 0

    for a in articles:
        low, high, reason = estimate_article(a)
        a["predicted_move_low"] = round(low, 1)
        a["predicted_move_high"] = round(high, 1)
        a["predicted_move_range"] = _range_text(low, high)
        a["predicted_move_reason"] = reason

        center = (low + high) / 2.0
        half = abs(high - low) / 2.0

        impact = _norm_impact(a.get("impact"))
        conf = _norm_impact(a.get("confidence"))
        w = IMPACT_LEVELS.get(impact, 1) * CONFIDENCE_LEVELS.get(conf, 0.4)

        weighted_center += center * w
        weighted_half += half * w
        total_weight += w

        direction = _norm_direction(a.get("direction"))
        if direction == "BULLISH":
            bullish += 1
        elif direction == "BEARISH":
            bearish += 1
        else:
            neutral += 1

    center = weighted_center / total_weight if total_weight else 0.0
    band = weighted_half / total_weight if total_weight else 0.0
    low = round(center - band, 1)
    high = round(center + band, 1)

    if center >= 0.2:
        overall = "BULLISH"
    elif center <= -0.2:
        overall = "BEARISH"
    else:
        overall = "NEUTRAL"

    summary = {
        "overall_move_low": low,
        "overall_move_high": high,
        "overall_move_range": _range_text(low, high),
        "overall_direction": overall,
        "signals": {"bullish": bullish, "bearish": bearish, "neutral": neutral},
    }
    return articles, summary
