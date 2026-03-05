import os
import math
import requests
import yfinance as yf
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
# ─────────────────────────────────────────────────────────────────────────────
# API IMPORT
# ─────────────────────────────────────────────────────────────────────────────

NEWS_API_KEY     = os.getenv("NEWS_API_KEY")
FINBERT_API_URL  = os.getenv("FINBERT_API_URL")
GOOGLE_SHEETS_URL = os.getenv("GOOGLE_SHEETS_URL")


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _ticker_sym(symbol: str) -> str:
    """Append .NS suffix for NSE equities if not already present."""
    s = symbol.strip().upper()
    return s if s.endswith(".NS") or s.endswith(".BO") else f"{s}.NS"


def _safe_float(val, default=None):
    try:
        v = float(val)
        return None if (math.isnan(v) or math.isinf(v)) else v
    except (TypeError, ValueError):
        return default


def _safe_int(val, default=None):
    try:
        return int(val)
    except (TypeError, ValueError):
        return default

