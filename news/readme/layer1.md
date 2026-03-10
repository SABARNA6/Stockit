# """

LAYER 1 : CONTENT UNDERSTANDING — News Impact Pipeline
Target Market : Indian Stocks (NSE / BSE)
Tools : VADER Sentiment, Rule-based NER, Keyword Classifier
Input : CSV / Google Sheet (RSS_POOL)
Output : unified_news_profiles.json + Flask API endpoint
=====================================================================
"""

import json
import re
import hashlib
import pandas as pd
from datetime import datetime, timedelta
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# ─────────────────────────────────────────────

# 1. INDIAN COMPANY → NSE TICKER DICTIONARY

# (extend this list freely)

# ─────────────────────────────────────────────

INDIAN_COMPANIES = { # Conglomerates / Large-caps
"reliance": "RELIANCE", "reliance industries": "RELIANCE",
"tata": "TATAMOTORS", "tata motors": "TATAMOTORS",
"tata steel": "TATASTEEL", "tata consultancy": "TCS", "tcs": "TCS",
"tata power": "TATAPOWER", "tata chemicals": "TATACHEM",
"infosys": "INFY", "wipro": "WIPRO",
"hdfc bank": "HDFCBANK", "hdfc": "HDFCBANK",
"icici bank": "ICICIBANK", "icici": "ICICIBANK",
"sbi": "SBIN", "state bank": "SBIN", "state bank of india": "SBIN",
"axis bank": "AXISBANK",
"kotak": "KOTAKBANK", "kotak mahindra": "KOTAKBANK",
"bajaj finance": "BAJFINANCE", "bajaj finserv": "BAJAJFINSV",
"bajaj auto": "BAJAJ-AUTO",
"maruti": "MARUTI", "maruti suzuki": "MARUTI",
"hero motocorp": "HEROMOTOCO", "hero": "HEROMOTOCO",
"asian paints": "ASIANPAINT",
"hindustan unilever": "HINDUNILVR", "hul": "HINDUNILVR",
"itc": "ITC",
"sun pharma": "SUNPHARMA", "sun pharmaceutical": "SUNPHARMA",
"dr reddy": "DRREDDY", "dr. reddy": "DRREDDY",
"cipla": "CIPLA",
"divis laboratories": "DIVISLAB", "divi's": "DIVISLAB",
"ongc": "ONGC", "oil and natural gas": "ONGC",
"ntpc": "NTPC",
"power grid": "POWERGRID",
"coal india": "COALINDIA",
"adani": "ADANIENT", "adani enterprises": "ADANIENT",
"adani ports": "ADANIPORTS", "adani green": "ADANIGREEN",
"adani power": "ADANIPOWER", "adani total gas": "ATGL",
"jsw steel": "JSWSTEEL",
"hindalco": "HINDALCO",
"ultratech cement": "ULTRACEMCO", "ultratech": "ULTRACEMCO",
"grasim": "GRASIM",
"l&t": "LT", "larsen": "LT", "larsen and toubro": "LT",
"tech mahindra": "TECHM",
"hcl tech": "HCLTECH", "hcl technologies": "HCLTECH",
"titan": "TITAN",
"nestle": "NESTLEIND", "nestle india": "NESTLEIND",
"britannia": "BRITANNIA",
"eicher motors": "EICHERMOT", "royal enfield": "EICHERMOT",
"m&m": "M&M", "mahindra": "M&M", "mahindra and mahindra": "M&M",
"indusind bank": "INDUSINDBK",
"yes bank": "YESBANK",
"zomato": "ZOMATO",
"paytm": "PAYTM", "one97": "PAYTM",
"nykaa": "NYKAA", "fss": "NYKAA",
"ola": "OLA",
"flipkart": "FLIPKART",
"airtel": "BHARTIARTL", "bharti airtel": "BHARTIARTL",
"vodafone idea": "IDEA", "vi": "IDEA",
"jio": "RELIANCE",
"bpcl": "BPCL", "bharat petroleum": "BPCL",
"ioc": "IOC", "indian oil": "IOC",
"hpcl": "HPCL", "hindustan petroleum": "HPCL",
"sebi": None, # regulator — not a stock
"rbi": None, # central bank — not a stock
"nse": None,
"bse": None,
}

# Sector keywords → sector label

SECTOR_KEYWORDS = {
"Banking & Finance": ["bank", "rbi", "repo rate", "credit", "npa", "loan", "nbfc",
"sebi", "interest rate", "monetary policy", "inflation", "fin"],
"IT & Technology": ["software", "it sector", "tech", "digital", "ai ", "cloud",
"cybersecurity", "saas", "startup"],
"Energy & Oil": ["oil", "gas", "petroleum", "crude", "opec", "ongc", "bpcl",
"energy", "power", "renewable", "solar", "coal"],
"Pharma & Health": ["pharma", "drug", "medicine", "fda", "cdsco", "clinical",
"hospital", "health", "vaccine", "biotech"],
"Auto": ["automobile", "auto", "vehicle", "ev ", "electric vehicle",
"car", "suv", "two-wheeler", "scooter"],
"Real Estate": ["real estate", "realty", "housing", "property", "reit",
"construction", "cement"],
"FMCG": ["fmcg", "consumer goods", "packaged food", "beverage",
"personal care", "retail"],
"Metals & Mining": ["steel", "aluminium", "copper", "iron ore", "mining",
"metal", "zinc"],
"Telecom": ["telecom", "spectrum", "5g", "broadband", "airtel",
"vodafone", "jio"],
"Agriculture": ["agri", "crop", "monsoon", "kharif", "rabi", "msp",
"fertilizer", "irrigation"],
}

# Event type keyword patterns

EVENT_PATTERNS = {
"Rate/Policy": ["repo rate", "rbi", "monetary policy", "inflation", "interest rate",
"rate hike", "rate cut", "mpc", "gdp", "budget", "fiscal"],
"Earnings": ["earnings", "quarterly result", "profit", "revenue", "ebitda",
"q1", "q2", "q3", "q4", "annual result", "net profit", "loss"],
"M&A": ["merger", "acquisition", "takeover", "stake", "buyout",
"joint venture", "deal", "bid", "acquire"],
"Regulatory": ["sebi", "regulation", "compliance", "penalty", "fine", "probe",
"investigation", "ban", "license", "approval"],
"Management": ["ceo", "cfo", "md ", "resign", "appoint", "board", "chairman",
"director", "leadership"],
"Product/Launch":["launch", "new product", "expansion", "plant", "factory",
"capacity", "contract", "order", "deal worth"],
"Macro/Global": ["us fed", "federal reserve", "dollar", "rupee", "fx",
"global market", "china", "geopolit", "war", "sanction",
"import", "export", "tariff"],
"Political": ["election", "government", "minister", "parliament", "policy",
"bjp", "congress", "modi", "budget", "scheme"],
"General": [], # fallback
}

# ─────────────────────────────────────────────

# 2. HELPER : NOVELTY CHECK

# ─────────────────────────────────────────────

\_seen_hashes: set = set() # in-memory; swap for Redis/DB in production

def \_news_hash(title: str) -> str:
"""Create a short hash from a normalised title for dedup."""
normalised = re.sub(r"[^a-z0-9 ]", "", title.lower().strip())
normalised = re.sub(r"\s+", " ", normalised)
return hashlib.md5(normalised.encode()).hexdigest()

def check_novelty(title: str, publish_date_str: str) -> dict:
"""
Returns:
is_duplicate – seen this headline before?
is_stale – older than 24 h?
novelty_score – 0.0 (stale/dup) → 1.0 (fresh & unique)
"""
h = \_news_hash(title)
is_dup = h in \_seen_hashes
if not is_dup:
\_seen_hashes.add(h)

    is_stale = False
    try:
        pub = pd.to_datetime(publish_date_str, dayfirst=True)
        age_hours = (datetime.now() - pub.replace(tzinfo=None)).total_seconds() / 3600
        is_stale = age_hours > 24
    except Exception:
        pass

    novelty_score = 0.0 if is_dup else (0.4 if is_stale else 1.0)
    return {"is_duplicate": is_dup, "is_stale": is_stale, "novelty_score": round(novelty_score, 2)}

# ─────────────────────────────────────────────

# 3. ENTITY NER (Rule-based, NSE-aware)

# ─────────────────────────────────────────────

def extract_entities(text: str) -> list[dict]:
"""
Scan text for known Indian company names.
Returns list of {name, ticker, confidence, role}.
"""
text_lower = text.lower()
found: dict[str, dict] = {} # ticker → entity (dedup)

    for keyword, ticker in INDIAN_COMPANIES.items():
        if ticker is None:
            continue
        # word-boundary safe match
        pattern = r'\b' + re.escape(keyword) + r'\b'
        if re.search(pattern, text_lower):
            confidence = 0.95 if len(keyword.split()) > 1 else 0.75
            if ticker not in found or found[ticker]["confidence"] < confidence:
                found[ticker] = {
                    "name":       keyword.title(),
                    "ticker":     ticker,
                    "confidence": confidence,
                    "role":       "subject",    # Layer 2 will refine this
                    "exchange":   "NSE"
                }

    return list(found.values())

# ─────────────────────────────────────────────

# 4. EVENT CLASSIFIER

# ─────────────────────────────────────────────

def classify_event(title: str, summary: str) -> dict:
"""
Returns primary event_type + matched_themes list.
"""
combined = (title + " " + (summary or "")).lower()
scores: dict[str, int] = {}

    for event_type, keywords in EVENT_PATTERNS.items():
        if event_type == "General":
            continue
        score = sum(1 for kw in keywords if kw in combined)
        if score:
            scores[event_type] = score

    if not scores:
        primary = "General"
        themes = []
    else:
        primary = max(scores, key=scores.get)
        themes = [k for k, v in sorted(scores.items(), key=lambda x: -x[1])]

    # sector detection
    sector_hits = []
    for sector, keywords in SECTOR_KEYWORDS.items():
        if any(kw in combined for kw in keywords):
            sector_hits.append(sector)

    return {
        "event_type":    primary,
        "themes":        themes,
        "sectors":       sector_hits,
        "event_score":   scores.get(primary, 0),
    }

# ─────────────────────────────────────────────

# 5. SENTIMENT ANALYSER (VADER + urgency)

# ─────────────────────────────────────────────

\_vader = SentimentIntensityAnalyzer()

# Finance-domain words to boost VADER lexicon

FINANCE_LEXICON = {
"surge": 2.0, "rally": 1.8, "soar": 2.2, "outperform": 1.5,
"downgrade": -2.0, "crash": -2.5, "plunge": -2.3, "default": -2.5,
"probe": -1.5, "fine": -1.2, "ban": -2.0, "penalty": -1.8,
"acquisition": 1.2, "merger": 1.0, "dividend": 1.5,
"loss": -1.8, "profit": 1.8, "growth": 1.5, "decline": -1.5,
"inflation": -1.0, "rate hike": -1.2, "rate cut": 1.2,
}
for word, score in FINANCE_LEXICON.items():
\_vader.lexicon[word] = score

URGENCY_TRIGGERS = [
"breaking", "urgent", "alert", "exclusive", "just in",
"immediate", "emergency", "crash", "halt", "suspend",
"rbi", "sebi order", "ban", "circuit", "probe"
]

def analyse_sentiment(title: str, summary: str) -> dict:
"""
Returns compound score, label, urgency_score, urgency_triggers_found.
"""
combined = (title + ". " + (summary or "")).strip()
scores = \_vader.polarity_scores(combined)
compound = scores["compound"]

    if compound >= 0.05:
        label = "Positive"
    elif compound <= -0.05:
        label = "Negative"
    else:
        label = "Neutral"

    text_lower = combined.lower()
    triggers_found = [t for t in URGENCY_TRIGGERS if t in text_lower]
    urgency_score  = min(1.0, len(triggers_found) * 0.25 + (0.3 if abs(compound) > 0.5 else 0))

    return {
        "compound":          round(compound, 4),
        "positive":          round(scores["pos"], 4),
        "negative":          round(scores["neg"], 4),
        "neutral":           round(scores["neu"], 4),
        "label":             label,
        "urgency_score":     round(urgency_score, 2),
        "urgency_triggers":  triggers_found,
    }

# ─────────────────────────────────────────────

# 6. UNIFIED NEWS PROFILE (combines all above)

# ─────────────────────────────────────────────

def build_unified_profile(row: dict) -> dict:
"""
Takes one RSS_POOL row, returns a Unified News Profile dict.
Expected keys: id, title, link, summary, publish_date, source
"""
title = str(row.get("title", ""))
summary = str(row.get("summary", "") or "")
pub_date = str(row.get("publish_date", ""))
full_text = title + " " + summary

    entities  = extract_entities(full_text)
    event     = classify_event(title, summary)
    sentiment = analyse_sentiment(title, summary)
    novelty   = check_novelty(title, pub_date)

    # Overall relevance: is this news financially relevant?
    has_entities    = len(entities) > 0
    has_fin_event   = event["event_type"] != "General"
    has_fin_sector  = len(event["sectors"]) > 0
    is_relevant     = has_entities or has_fin_event or has_fin_sector

    relevance_score = (
        (0.4 if has_entities   else 0) +
        (0.3 if has_fin_event  else 0) +
        (0.2 if has_fin_sector else 0) +
        (0.1 * novelty["novelty_score"])
    )

    return {
        # ── Raw fields ──────────────────────────────
        "id":           row.get("id"),
        "title":        title,
        "link":         row.get("link", ""),
        "source":       row.get("source", ""),
        "publish_date": pub_date,
        "updated_on":   str(row.get("updated_on", "")),

        # ── Layer 1 outputs ─────────────────────────
        "entities":         entities,           # → feeds Layer 2
        "event":            event,              # → feeds Layer 2 + 3
        "sentiment":        sentiment,          # → feeds Layer 3
        "novelty":          novelty,            # → dedup filter

        # ── Summary flags ───────────────────────────
        "is_financially_relevant": is_relevant,
        "relevance_score":         round(relevance_score, 3),
        "processed_at":            datetime.now().isoformat(),
    }

# ─────────────────────────────────────────────

# 7. DATA LOADERS

# ─────────────────────────────────────────────

def load*from_csv(filepath: str) -> pd.DataFrame:
df = pd.read_csv(filepath)
df.columns = [c.strip().lower().replace(" ", "*") for c in df.columns]
return df

def load_from_google_sheet(sheet_url: str, credentials_json_path: str) -> pd.DataFrame:
"""
sheet_url : full Google Sheets URL
credentials_json_path: path to your service-account JSON key
"""
import gspread
from oauth2client.service_account import ServiceAccountCredentials

    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds  = ServiceAccountCredentials.from_json_keyfile_name(credentials_json_path, scope)
    client = gspread.authorize(creds)

    # Extract sheet ID from URL
    sheet_id = sheet_url.split("/d/")[1].split("/")[0]
    sheet    = client.open_by_key(sheet_id).sheet1
    data     = sheet.get_all_records()
    df       = pd.DataFrame(data)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return df

# ─────────────────────────────────────────────

# 8. MAIN PIPELINE RUNNER

# ─────────────────────────────────────────────

def run_pipeline(df: pd.DataFrame, output_path: str = "unified_news_profiles.json") -> list[dict]:
"""
Process all rows through Layer 1 and save output JSON.
"""
profiles = []
skipped = 0

    for _, row in df.iterrows():
        profile = build_unified_profile(row.to_dict())

        if profile["novelty"]["is_duplicate"]:
            skipped += 1
            continue                          # skip exact duplicates

        profiles.append(profile)

    # Sort by relevance (most relevant first)
    profiles.sort(key=lambda x: x["relevance_score"], reverse=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Layer 1 complete.")
    print(f"   Total rows      : {len(df)}")
    print(f"   Duplicates skip : {skipped}")
    print(f"   Profiles saved  : {len(profiles)}")
    print(f"   Output file     : {output_path}")

    # Quick stats
    relevant = [p for p in profiles if p["is_financially_relevant"]]
    print(f"   Financially relevant: {len(relevant)} / {len(profiles)}")

    return profiles

# ─────────────────────────────────────────────

# 9. FLASK API (expose Layer 1 as REST endpoint)

# ─────────────────────────────────────────────

from flask import Flask, request, jsonify

app = Flask(**name**)

@app.route("/api/layer1/process", methods=["POST"])
def api_process():
"""
POST /api/layer1/process
Body : JSON list of RSS_POOL rows
OR { "csv_path": "path/to/file.csv" }
"""
body = request.get_json(force=True)

    if isinstance(body, list):
        df = pd.DataFrame(body)
    elif isinstance(body, dict) and "csv_path" in body:
        df = load_from_csv(body["csv_path"])
    else:
        return jsonify({"error": "Send a JSON array of rows or {csv_path: '...'}"}), 400

    profiles = run_pipeline(df, output_path="unified_news_profiles.json")
    return jsonify({"status": "ok", "count": len(profiles), "profiles": profiles})

@app.route("/api/layer1/single", methods=["POST"])
def api_single():
"""
POST /api/layer1/single
Body : one RSS_POOL row as JSON object
"""
row = request.get_json(force=True)
profile = build_unified_profile(row)
return jsonify(profile)

@app.route("/api/layer1/health", methods=["GET"])
def health():
return jsonify({"status": "Layer 1 running", "timestamp": datetime.now().isoformat()})

# ─────────────────────────────────────────────

# 10. ENTRY POINT

# ─────────────────────────────────────────────

if **name** == "**main**":
import sys

    if len(sys.argv) > 1:
        # CLI usage:  python layer1_pipeline.py data.csv
        csv_path = sys.argv[1]
        df = load_from_csv(csv_path)
        run_pipeline(df)
    else:
        # Start Flask server
        print("🚀 Starting Layer 1 Flask API on http://localhost:5001")
        app.run(debug=True, port=5001)
