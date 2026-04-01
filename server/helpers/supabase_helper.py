# helpers/supabase_helper.py
#
# Supabase 2.x compatible client helper.
#
# Correct pattern for supabase-py 2.x:
#   client = create_client(URL, ANON_KEY)
#   client.postgrest.auth(user_jwt)        ← sets Bearer token on queries
#   client.table("portfolio").select("*").execute()
#
# DO NOT use ClientOptions(auto_refresh_token=...) — 'storage' attr missing in 2.x

from __future__ import annotations
import os
import json
import base64
import time
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL  = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SVC  = os.getenv("SUPABASE_KEY", "")

# ── Shared base client (created once with anon key) ───────────────────────────
_base_client = None

def _get_base_client():
    global _base_client
    if _base_client is None:
        key = SUPABASE_ANON or SUPABASE_SVC
        if not SUPABASE_URL or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in .env")
        from supabase import create_client
        _base_client = create_client(SUPABASE_URL, key)
    return _base_client


# ── JWT helpers ───────────────────────────────────────────────────────────────

def _decode_jwt(token: str) -> dict | None:
    """Decode JWT payload without signature verification (for inspection only)."""
    try:
        parts = token.strip().split(".")
        if len(parts) != 3:
            return None
        pad     = 4 - len(parts[1]) % 4
        payload = parts[1] + ("=" * pad if pad != 4 else "")
        return json.loads(base64.urlsafe_b64decode(payload))
    except Exception:
        return None


def _verify_jwt_with_supabase(token: str) -> dict | None:
    """
    Verify JWT by calling Supabase's /auth/v1/user endpoint.
    This cryptographically validates the token against Supabase's signing key.
    Returns user info dict or None if invalid/expired.
    """
    try:
        resp = requests.get(
            f"{SUPABASE_URL}/auth/v1/user",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        if resp.status_code == 200:
            user_data = resp.json()
            return {
                "id": user_data.get("id"),
                "email": user_data.get("email", ""),
            }
        return None
    except Exception as e:
        print(f"[_verify_jwt_with_supabase] Verification failed: {e}")
        return None


def get_user_from_token(token: str) -> dict | None:
    """
    Verify a Supabase JWT via Supabase auth API and return {id, email}.
    Returns None if token is missing, malformed, expired, or forged.
    """
    try:
        if not token:
            return None
        # First do a quick structural decode to check expiry locally (fast path)
        payload = _decode_jwt(token)
        if not payload:
            return None
        if payload.get("exp") and time.time() > payload["exp"]:
            print("[get_user_from_token] Token expired")
            return None
        user_id = payload.get("sub")
        if not user_id:
            return None
        # Cryptographically verify the token with Supabase
        verified = _verify_jwt_with_supabase(token)
        if verified and verified.get("id") == user_id:
            return verified
        print("[get_user_from_token] Token verification failed — possible forgery")
        return None
    except Exception as e:
        print(f"[get_user_from_token] {e}")
        return None


# ── Authenticated client ──────────────────────────────────────────────────────

def get_client_for_user(user_token: str):
    """
    Returns the shared Supabase client authenticated with the user's JWT.

    In supabase-py 2.x the correct pattern is:
        client.postgrest.auth(token)

    This sets  Authorization: Bearer <token>  on all PostgREST queries
    so Supabase RLS enforces per-user row isolation automatically.
    """
    client = _get_base_client()
    # Set user JWT on the postgrest client — correct supabase 2.x API
    client.postgrest.auth(user_token)
    return client