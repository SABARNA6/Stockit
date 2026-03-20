"""
=====================================================================
  ingestion/equity_sync.py
  Syncs equities.json to Supabase `equities` table.
  - Reads symbols from equities.json
  - Checks which are missing in Supabase
  - Generates profiles for missing ones via yfinance + rule maps
  - Upserts all to Supabase
=====================================================================
"""

import os
import json
import sys
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Import the generator logic directly (no subprocess needed)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from data.generate_equities import generate_equity


# ─────────────────────────────────────────────
#  SUPABASE CLIENT
# ─────────────────────────────────────────────
def _client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in .env file")
    return create_client(url, key)


# ─────────────────────────────────────────────
#  FETCH SYMBOLS ALREADY IN SUPABASE
# ─────────────────────────────────────────────
def _get_supabase_symbols() -> set[str]:
    """Return set of symbols already present in Supabase equities table."""
    try:
        client = _client()
        response = client.table("equities").select("symbol").execute()
        symbols = {row["symbol"] for row in (response.data or [])}
        print(f"[equity_sync] {len(symbols)} equities already in Supabase")
        return symbols
    except Exception as e:
        print(f"[equity_sync] ⚠️  Could not fetch Supabase equities: {e}")
        return set()


# ─────────────────────────────────────────────
#  UPSERT PROFILES TO SUPABASE
# ─────────────────────────────────────────────
def _upsert(profiles: list[dict]) -> int:
    """Upsert equity profiles to Supabase equities table. Returns saved count."""
    if not profiles:
        return 0
    try:
        client = _client()
        response = (
            client.table("equities")
            .upsert(profiles, on_conflict="symbol")
            .execute()
        )
        count = len(response.data or profiles)
        print(f"[equity_sync] ✅ Upserted {count} equities to Supabase")
        return count
    except Exception as e:
        print(f"[equity_sync] ❌ Upsert failed: {e}")
        return 0


# ─────────────────────────────────────────────
#  MAIN SYNC FUNCTION
# ─────────────────────────────────────────────
def sync(equities_path: str) -> int:
    """
    Check equities.json against Supabase.
    Generate and upsert any missing symbols.
    Returns number of new equities added.
    """
    # Load local equities.json
    with open(equities_path) as f:
        local_equities: list[dict] = json.load(f)

    local_symbols = [e["symbol"] for e in local_equities]

    # Find which are missing from Supabase
    existing = _get_supabase_symbols()
    missing  = [s for s in local_symbols if s not in existing]

    if not missing:
        print(f"[equity_sync] All {len(local_symbols)} equities are up-to-date in Supabase")
        return 0

    print(f"[equity_sync] {len(missing)} equities missing from Supabase: {', '.join(missing)}")

    # Generate profiles for missing symbols via yfinance + rule maps
    new_profiles = []
    failed       = []

    for symbol in missing:
        # Prefer the local equities.json entry (already has peers/risks/exposure)
        local = next((e for e in local_equities if e["symbol"] == symbol), None)

        if local and all(k in local for k in ("name", "sector", "peers", "risks", "revenue_exposure")):
            # Local entry is complete — use it directly
            new_profiles.append(local)
            print(f"[equity_sync] ✅ {symbol} — using local equities.json entry")
        else:
            # Local entry is incomplete or missing — fetch from yfinance
            profile = generate_equity(symbol)
            if profile:
                new_profiles.append(profile)
                # Also update equities.json with fresh data
                _update_local(equities_path, local_equities, profile)
            else:
                failed.append(symbol)

    # Upsert all new profiles to Supabase
    saved = _upsert(new_profiles)

    if failed:
        print(f"[equity_sync] ⚠️  Could not generate profiles for: {', '.join(failed)}")

    return saved


# ─────────────────────────────────────────────
#  UPDATE LOCAL equities.json
# ─────────────────────────────────────────────
def _update_local(equities_path: str, existing: list[dict], new_profile: dict):
    """Replace or append a profile in the local equities.json."""
    symbol = new_profile["symbol"]
    updated = [e if e["symbol"] != symbol else new_profile for e in existing]
    if not any(e["symbol"] == symbol for e in existing):
        updated.append(new_profile)
    with open(equities_path, "w") as f:
        json.dump(updated, f, indent=2)
