"""
=====================================================================
  layers/llm_client.py
  Shared LLM client used by Layer 2 and Layer 3
  Primary  : OpenRouter (Llama 3.3 70B) — 1.35B tokens/week free
  Fallback : Gemini 2.5 Flash Lite      — 20 RPD free
=====================================================================
"""

import os
import json
import time
import requests

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
OPENROUTER_URL   = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "openrouter/free"

GEMINI_URL       = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent"

RETRY_ATTEMPTS   = 3
RETRY_DELAY      = 5


# ─────────────────────────────────────────────
#  OPENROUTER CALL
# ─────────────────────────────────────────────
def _call_openrouter(prompt: str) -> list | None:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("[LLM] ❌ OPENROUTER_API_KEY not set")
        return None

    headers = {
        "Authorization":  f"Bearer {api_key}",
        "Content-Type":   "application/json",
        "HTTP-Referer":   "https://news-pipeline.onrender.com",
        "X-Title":        "News Impact Pipeline",
    }

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {
                "role":    "user",
                "content": prompt
            }
        ],
        "temperature":     0.1,
        "max_tokens":      4096,
        "response_format": {"type": "json_object"},
    }

    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            response = requests.post(
                OPENROUTER_URL,
                headers=headers,
                json=payload,
                timeout=60
            )

            if response.status_code == 429:
                wait = RETRY_DELAY * attempt
                print(f"[OpenRouter] ⚠️ Rate limited. Waiting {wait}s (attempt {attempt})...")
                time.sleep(wait)
                continue

            if response.status_code != 200:
                print(f"[OpenRouter] ❌ HTTP {response.status_code}: {response.text[:200]}")
                return None

            data    = response.json()
            content = data["choices"][0]["message"]["content"].strip()

            # Strip markdown fences if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()

            parsed = json.loads(content)

            # Normalize response — always return a list of dicts with ticker/article_id
            if isinstance(parsed, dict):
                # Try common wrapper keys first
                for key in ["results", "articles", "data", "items", "predictions"]:
                    if key in parsed and isinstance(parsed[key], list):
                        return parsed[key]
                # Single prediction object
                if "ticker" in parsed or "article_id" in parsed:
                    return [parsed]
                # Dict keyed by ticker: {"HDFCBANK": {...}, "TCS": {...}}
                # Inject ticker key into each value
                result = []
                for k, v in parsed.items():
                    if isinstance(v, dict):
                        if "ticker" not in v:
                            v["ticker"] = k
                        result.append(v)
                return result if result else None

            if isinstance(parsed, list):
                return parsed

            return None

        except json.JSONDecodeError as e:
            print(f"[OpenRouter] ❌ JSON parse error: {e}")
            return None
        except Exception as e:
            print(f"[OpenRouter] ❌ Request error (attempt {attempt}): {e}")
            if attempt < RETRY_ATTEMPTS:
                time.sleep(RETRY_DELAY)

    return None


# ─────────────────────────────────────────────
#  GEMINI FALLBACK CALL
# ─────────────────────────────────────────────
def _call_gemini(prompt: str) -> list | None:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[LLM] ❌ GEMINI_API_KEY not set — no fallback available")
        return None

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature":      0.1,
            "maxOutputTokens":  8192,
            "responseMimeType": "application/json",
        }
    }

    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            response = requests.post(
                f"{GEMINI_URL}?key={api_key}",
                json=payload,
                timeout=60
            )

            if response.status_code == 429:
                wait = RETRY_DELAY * attempt
                print(f"[Gemini] ⚠️ Rate limited. Waiting {wait}s (attempt {attempt})...")
                time.sleep(wait)
                continue

            if response.status_code != 200:
                print(f"[Gemini] ❌ HTTP {response.status_code}: {response.text[:200]}")
                return None

            data    = response.json()
            content = data["candidates"][0]["content"]["parts"][0]["text"].strip()

            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]

            content = content.strip()

            # Recovery: if JSON is truncated, try to salvage complete objects
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                # Try truncation recovery — extract complete [...] or {...} blocks
                import re
                # Find all complete JSON objects in the string
                salvaged = []
                for match in re.finditer(r'\{[^{}]*"ticker"[^{}]*\}', content, re.DOTALL):
                    try:
                        obj = json.loads(match.group())
                        salvaged.append(obj)
                    except Exception:
                        pass
                if salvaged:
                    print(f"[Gemini] ⚠️ Truncated JSON — salvaged {len(salvaged)} objects")
                    return salvaged
                print(f"[Gemini] ❌ JSON parse error — could not salvage")
                return None

            if isinstance(parsed, dict):
                for key in ["results", "articles", "data", "items", "predictions"]:
                    if key in parsed and isinstance(parsed[key], list):
                        return parsed[key]
                if "ticker" in parsed or "article_id" in parsed:
                    return [parsed]
                result = []
                for k, v in parsed.items():
                    if isinstance(v, dict):
                        if "ticker" not in v:
                            v["ticker"] = k
                        result.append(v)
                return result if result else None

            if isinstance(parsed, list):
                return parsed

            return None

        except json.JSONDecodeError as e:
            print(f"[Gemini] ❌ JSON parse error: {e}")
            return None
        except Exception as e:
            print(f"[Gemini] ❌ Request error (attempt {attempt}): {e}")
            if attempt < RETRY_ATTEMPTS:
                time.sleep(RETRY_DELAY)

    return None


# ─────────────────────────────────────────────
#  MAIN ENTRY — tries OpenRouter first, Gemini fallback
# ─────────────────────────────────────────────
def call_llm(prompt: str) -> list | None:
    """
    Try OpenRouter first (1.35B tokens/week free).
    Fall back to Gemini if OpenRouter fails.
    """
    print("[LLM] Trying OpenRouter (Llama 3.3 70B)...")
    result = _call_openrouter(prompt)

    if result is not None:
        print("[LLM] ✅ OpenRouter succeeded")
        return result

    print("[LLM] ⚠️ OpenRouter failed — falling back to Gemini...")
    result = _call_gemini(prompt)

    if result is not None:
        print("[LLM] ✅ Gemini fallback succeeded")
        return result

    print("[LLM] ❌ Both OpenRouter and Gemini failed")
    return None