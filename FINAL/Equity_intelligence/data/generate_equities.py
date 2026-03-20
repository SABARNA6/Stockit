"""
=====================================================================
  data/generate_equities.py
  Generate equity profiles for equities.json.
  - Financial data pulled from Yahoo Finance (.NS suffix for NSE)
  - Peers, risks, revenue_exposure filled from curated rule maps
  - Local overrides for symbols where yfinance data is incomplete
  - Falls back to sector-level defaults for unknown symbols

  Usage:
    python data/generate_equities.py
    python data/generate_equities.py --symbols RELIANCE BEL NGLFINE
    python data/generate_equities.py --append --symbols SUNPHARMA DRREDDY
    python data/generate_equities.py --preview
=====================================================================
"""

import os
import json
import argparse
import yfinance as yf

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "equities.json")


# ─────────────────────────────────────────────
#  LOCAL OVERRIDES (fix yfinance gaps for specific symbols)
# ─────────────────────────────────────────────
# Use this for symbols where yfinance returns wrong/missing sector/industry
NSE_OVERRIDES: dict[str, dict] = {
    # ── Defense / Capital Goods ──
    "BEL": {
        "name": "Bharat Electronics Limited",
        "sector": "capital_goods",
        "industry": "Aerospace & Defense",
    },
    "HAL": {
        "name": "Hindustan Aeronautics Limited",
        "sector": "capital_goods",
        "industry": "Aerospace & Defense",
    },
    "BDL": {
        "name": "Bharat Dynamics Limited",
        "sector": "capital_goods",
        "industry": "Aerospace & Defense",
    },
    "DATAPATTNS": {
        "name": "Data Patterns (India) Limited",
        "sector": "IT",
        "industry": "Defense Electronics",
    },
    # ── Chemicals / Specialty ──
    "NGLFINE": {
        "name": "NGL Fine-Chem Limited",
        "sector": "chemicals",
        "industry": "Specialty Chemicals",
    },
    "SRF": {
        "name": "SRF Limited",
        "sector": "chemicals",
        "industry": "Specialty Chemicals",
    },
    # ── Small-cap / Niche ──
    "GANDHITUBE": {
        "name": "Gandhi Special Tubes Limited",
        "sector": "metals",
        "industry": "Steel Tubes & Pipes",
    },
    "STYLAMIND": {
        "name": "Stylam Industries Limited",
        "sector": "consumer_cyclical",
        "industry": "Laminates",
    },
}


# ─────────────────────────────────────────────
#  SECTOR MAPPING  (Yahoo Finance → internal)
# ─────────────────────────────────────────────
YF_SECTOR_MAP = {
    "Technology":             "IT",
    "Financial Services":     "banking",
    "Consumer Defensive":     "fmcg",
    "Consumer Cyclical":      "auto",
    "Healthcare":             "pharma",
    "Energy":                 "energy",
    "Basic Materials":        "metals",
    "Communication Services": "telecom",
    "Real Estate":            "realty",
    "Industrials":            "infrastructure",
    "Utilities":              "energy",
    # ── NEW ENTRIES ──
    "Specialty Chemicals":    "chemicals",
    "Capital Goods":          "capital_goods",
    "Logistics":              "infrastructure",
    "Aerospace & Defense":    "capital_goods",
}

# Keyword-based fallback when sector is missing or unmapped
INDUSTRY_KEYWORD_MAP = {
    "bank":        "banking",
    "insurance":   "insurance",
    "software":    "IT",
    "it services": "IT",
    "pharma":      "pharma",
    "drug":        "pharma",
    "automobile":  "auto",
    "auto":        "auto",
    "cement":      "infrastructure",
    "steel":       "metals",
    "metal":       "metals",
    "oil":         "energy",
    "gas":         "energy",
    "telecom":     "telecom",
    "real estate": "realty",
    "consumer":    "fmcg",
    # ── NEW ENTRIES ──
    "chemical":    "chemicals",
    "specialty":   "chemicals",
    "agrochem":    "chemicals",
    "engineering": "capital_goods",
    "heavy mach":  "capital_goods",
    "logistics":   "infrastructure",
    "shipping":    "infrastructure",
    "aviation":    "infrastructure",
    "electronics": "IT",
    "semiconductor": "IT",
    "jewellery":   "consumer_cyclical",
    "defense":     "capital_goods",
    "aerospace":   "capital_goods",
    "radar":       "capital_goods",
    "avionics":    "capital_goods",
}


# ─────────────────────────────────────────────
#  PEER MAP  (symbol → known direct competitors)
# ─────────────────────────────────────────────
PEER_MAP: dict[str, list[str]] = {
    # ── IT ──
    "TCS":         ["Infosys", "Wipro", "HCL Technologies", "Tech Mahindra", "LTIMindtree"],
    "INFY":        ["TCS", "Wipro", "HCL Technologies", "Tech Mahindra", "LTIMindtree"],
    "WIPRO":       ["TCS", "Infosys", "HCL Technologies", "Tech Mahindra"],
    "HCLTECH":     ["TCS", "Infosys", "Wipro", "Tech Mahindra"],
    "TECHM":       ["TCS", "Infosys", "Wipro", "HCL Technologies"],
    "LTIM":        ["TCS", "Infosys", "Wipro", "Persistent"],
    "PERSISTENT":  ["LTIM", "Infosys", "TCS", "Coforge"],
    # ── BANKING & FINANCE ──
    "HDFCBANK":    ["ICICI Bank", "SBI", "Kotak Bank", "Axis Bank"],
    "ICICIBANK":   ["HDFC Bank", "SBI", "Kotak Bank", "Axis Bank"],
    "SBIN":        ["HDFC Bank", "ICICI Bank", "Kotak Bank", "Bank of Baroda"],
    "KOTAKBANK":   ["HDFC Bank", "ICICI Bank", "SBI", "Axis Bank"],
    "AXISBANK":    ["HDFC Bank", "ICICI Bank", "SBI", "Kotak Bank"],
    "BAJFINANCE":  ["HDFC Bank", "Shriram Finance", "Cholamandalam", "Muthoot Finance"],
    "SHRIRAMFIN":  ["Bajaj Finance", "Cholamandalam", "Muthoot Finance", "L&T Finance"],
    # ── INSURANCE ──
    "LICI":        ["HDFC Life", "SBI Life", "ICICI Prudential", "Max Life"],
    "HDFCLIFE":    ["LIC", "SBI Life", "ICICI Prudential", "Max Life"],
    "SBILIFE":     ["LIC", "HDFC Life", "ICICI Prudential", "Max Life"],
    # ── ENERGY & CONGLOMERATE ──
    "RELIANCE":    ["ONGC", "IOC", "BPCL", "Adani Enterprises"],
    "ONGC":        ["Reliance Industries", "IOC", "BPCL", "GAIL"],
    "ADANIENT":    ["Reliance Industries", "Tata Steel", "Adani Ports", "JSW Steel"],
    "ADANIPORTS":  ["GPT Infrastructure", "Adani Enterprises", "Container Corp"],
    # ── TELECOM ──
    "BHARTIARTL":  ["Jio", "Vodafone Idea", "BSNL", "Tata Comm"],
    # ── FMCG & CONSUMER ──
    "ITC":         ["HUL", "Nestle India", "Britannia", "Dabur"],
    "HINDUNILVR":  ["ITC", "Nestle India", "Britannia", "Marico"],
    "NESTLEIND":   ["HUL", "ITC", "Britannia", "Dabur"],
    "TITAN":       ["Kalyan Jewellers", "Malabar Gold", "Pidilite", "Fossil India"],
    # ── AUTO ──
    "MARUTI":      ["Tata Motors", "Hyundai India", "Mahindra", "Kia"],
    "TATAMOTORS":  ["Maruti Suzuki", "Mahindra", "Hyundai India", "Kia"],
    "BAJAJ-AUTO":  ["Hero MotoCorp", "TVS Motor", "Eicher Motors", "Honda Moto"],
    "EICHERMOT":   ["Bajaj Auto", "TVS Motor", "Hero MotoCorp", "Royal Enfield"],
    "M&M":         ["Tata Motors", "Mahindra Lifespace", "Sonalika", "TAFE"],
    # ── PHARMA ──
    "SUNPHARMA":   ["Dr. Reddy's", "Cipla", "Lupin", "Aurobindo Pharma"],
    "DRREDDY":     ["Sun Pharma", "Cipla", "Lupin", "Aurobindo Pharma"],
    "CIPLA":       ["Sun Pharma", "Dr. Reddy's", "Lupin", "Aurobindo Pharma"],
    "DIVISLAB":    ["Sun Pharma", "Dr. Reddy's", "Laurus Labs", "Granules"],
    # ── METALS & MINING ──
    "TATASTEEL":   ["JSW Steel", "SAIL", "Hindalco", "Vedanta"],
    "HINDALCO":    ["Tata Steel", "JSW Steel", "Vedanta", "National Aluminium"],
    "JSWSTEEL":    ["Tata Steel", "SAIL", "Hindalco", "AMNS"],
    # ── PAINTS & CHEMICALS ──
    "ASIANPAINT":  ["Berger Paints", "Kansai Nerolac", "Akzo Nobel", "Nippon"],
    "PIDILITIND":  ["Asian Paints", "Berger Paints", "Nerolac"],
    # ── INFRASTRUCTURE & CAPITAL GOODS ──
    "LT":          ["Adani Enterprises", "Siemens", "ABB India", "Thermax"],
    "NTPC":        ["Power Grid", "Adani Power", "Tata Power", "NHPC"],
    "POWERGRID":   ["NTPC", "Adani Transmission", "Sterling Wilson"],
    # ── DEFENSE (NEW) ──
    "BEL":         ["HAL", "BDL", "DATAPATTNS", "PARAS", "ZENTEC"],
    "HAL":         ["BEL", "BDL", "DATAPATTNS", "MTARTECH", "Paras Defence"],
    "BDL":         ["BEL", "HAL", "DATAPATTNS", "Paras Defence"],
    # ── NEW AGE TECH ──
    "ZOMATO":      ["Swiggy", "PB Fintech", "Nykaa", "Paytm"],
    "PAYTM":       ["PB Fintech", "Zomato", "PhonePe", "Razorpay"],
}

# Sector-level fallback peers when symbol not in PEER_MAP
SECTOR_PEERS: dict[str, list[str]] = {
    "IT":             ["TCS", "Infosys", "Wipro", "HCL Technologies", "LTIMindtree"],
    "banking":        ["HDFC Bank", "ICICI Bank", "SBI", "Kotak Bank", "Axis Bank"],
    "insurance":      ["LIC", "HDFC Life", "SBI Life", "ICICI Prudential"],
    "pharma":         ["Sun Pharma", "Dr. Reddy's", "Cipla", "Lupin", "Divis Labs"],
    "auto":           ["Maruti Suzuki", "Tata Motors", "Mahindra", "Bajaj Auto"],
    "energy":         ["Reliance Industries", "ONGC", "IOC", "BPCL", "Adani Power"],
    "fmcg":           ["HUL", "ITC", "Nestle India", "Britannia", "Dabur"],
    "metals":         ["Tata Steel", "JSW Steel", "SAIL", "Hindalco"],
    "telecom":        ["Bharti Airtel", "Jio", "Vodafone Idea"],
    "realty":         ["DLF", "Godrej Properties", "Prestige", "Oberoi Realty"],
    "infrastructure": ["L&T", "Adani Ports", "NTPC", "Power Grid"],
    # ── NEW ENTRIES ──
    "chemicals":      ["Pidilite", "SRF", "Deepak Nitrite", "Tata Chemicals"],
    "capital_goods":  ["L&T", "Siemens", "ABB India", "Cummins", "BEL", "HAL"],
    "consumer_cyclical": ["Titan", "Trent", "Avenue Supermarts", "Voltas"],
}


# ─────────────────────────────────────────────
#  RISK MAP  (symbol-specific, then sector fallback)
# ─────────────────────────────────────────────
SYMBOL_RISKS: dict[str, list[str]] = {
    # ── IT ──
    "TCS":        ["US IT spending slowdown", "USD/INR exchange rate", "H1-B visa policy", "AI disruption to services", "client concentration"],
    "INFY":       ["US IT spending slowdown", "BFSI sector slowdown", "USD/INR exchange rate", "visa policy changes", "talent attrition"],
    "WIPRO":      ["US IT spending slowdown", "USD/INR exchange rate", "deal ramp-up delays", "margin pressure", "AI disruption"],
    "HCLTECH":    ["US IT spending", "USD/INR exchange rate", "products revenue volatility", "visa restrictions", "AI disruption"],
    "LTIM":       ["Merger integration risks", "US spending slowdown", "talent retention", "currency volatility"],
    # ── BANKING ──
    "HDFCBANK":   ["RBI rate policy", "NPA levels", "credit growth slowdown", "FII outflows", "margin compression"],
    "ICICIBANK":  ["RBI rate policy", "NPA levels", "retail credit stress", "FII outflows", "competition from fintechs"],
    "SBIN":       ["RBI rate policy", "PSU bank NPA levels", "government policy", "rural credit stress", "recapitalisation needs"],
    "BAJFINANCE": ["RBI rate hikes", "consumer credit stress", "NPA in unsecured lending", "competition from banks", "regulatory tightening"],
    # ── CONGLOMERATE & ENERGY ──
    "RELIANCE":   ["crude oil price volatility", "refining margin compression", "Jio competition", "retail capex cycle", "regulatory risk"],
    "ADANIENT":   ["regulatory scrutiny", "debt levels", "commodity price cycles", "project execution delays", "ESG concerns"],
    "ONGC":       ["oil price volatility", "windfall tax", "production shortfalls", "capex inefficiency", "green transition risk"],
    # ── TELECOM ──
    "BHARTIARTL": ["ARPU pressure", "spectrum cost", "Jio competition", "5G capex", "regulatory risk"],
    # ── AUTO ──
    "MARUTI":     ["commodity cost inflation", "EV transition risk", "yen/INR rate", "rural demand slowdown", "competition from Korean OEMs"],
    "TATAMOTORS": ["Jaguar Land Rover chip shortage", "EV margin pressure", "USD/GBP exposure", "commodity costs", "India CV cycle"],
    "BAJAJ-AUTO": ["export market demand", "EV transition speed", "commodity costs", "rural income slowdown", "competition from TVS"],
    # ── PHARMA ──
    "SUNPHARMA":  ["USFDA inspection risk", "US generics pricing pressure", "branded India market competition", "FX exposure", "litigation risk"],
    "DIVISLAB":   ["USFDA compliance", "client concentration", "currency fluctuation", "raw material cost", "patent cliffs"],
    # ── METALS ──
    "TATASTEEL":  ["global steel demand", "China dumping", "energy costs", "carbon tax (CBAM)", "debt servicing"],
    "HINDALCO":   ["LME aluminium prices", "energy costs", "China demand", "auto sector slowdown", "carbon regulations"],
    # ── FMCG & CONSUMER ──
    "ITC":        ["regulatory tax changes", "agri input costs", "FMCG competition", "hotel capex", "ESG pressure"],
    "TITAN":      ["gold price volatility", "rural demand slowdown", "competition from online jewellers", "import duty on gold", "wedding seasonality"],
    # ── INFRA / CAPITAL GOODS ──
    "LT":         ["project execution delays", "capital raising risk", "government policy", "commodity cost", "interest rate exposure"],
    "NTPC":       ["coal supply availability", "tariff regulations", "renewable transition capex", "environmental norms", "payment delays by DISCOMs"],
    # ── DEFENSE (NEW) ──
    "BEL":        ["MoD budget allocation delays", "order execution timeline risk", "import dependency for semiconductors", "geopolitical supply chain disruption", "pricing pressure from government contracts"],
    "HAL":        ["defense budget cycles", "technology transfer delays", "foreign dependency for engines/avionics", "order book concentration", "execution delays"],
    "BDL":        ["MoD order timing", "missile program delays", "raw material cost inflation", "single-customer dependency", "export approval risks"],
    # ── NEW AGE ──
    "ZOMATO":     ["path to profitability", "competition from Swiggy", "regulatory gig-worker laws", "advertising spend efficiency", "quick-commerce burn"],
}

SECTOR_RISKS: dict[str, list[str]] = {
    "IT":             ["US IT spending slowdown", "USD/INR exchange rate", "visa restrictions", "AI disruption to services", "client attrition"],
    "banking":        ["RBI monetary policy", "NPA and credit quality", "credit growth slowdown", "FII outflows", "fintech competition"],
    "insurance":      ["interest rate changes", "equity market volatility", "regulatory changes", "claims ratio", "distribution channel risk"],
    "pharma":         ["USFDA inspection risk", "US generics price erosion", "domestic pricing regulation", "FX exposure", "R&D pipeline risk"],
    "auto":           ["commodity cost inflation", "EV transition", "demand cyclicality", "import tariffs", "fuel price sensitivity"],
    "energy":         ["crude oil price volatility", "refining margin compression", "government pricing policy", "ESG transition risk", "regulatory risk"],
    "fmcg":           ["input cost inflation", "rural demand slowdown", "competitive intensity", "private label growth", "distribution disruption"],
    "metals":         ["global commodity price cycles", "China demand", "energy cost", "anti-dumping duties", "environmental regulations"],
    "telecom":        ["ARPU pressure", "spectrum auction costs", "5G capex burden", "competition", "regulatory risk"],
    "realty":         ["interest rate sensitivity", "inventory overhang", "regulatory approvals", "land acquisition", "economic slowdown"],
    "infrastructure": ["project execution delays", "capital raising risk", "government policy", "commodity cost", "interest rate exposure"],
    # ── NEW ENTRIES ──
    "chemicals":      ["China import dependency", "environmental regulations", "raw material volatility", "global demand slowdown", "currency exposure"],
    "capital_goods":  ["order book execution", "steel price inflation", "interest rate sensitivity", "government capex cycle", "import dependency", "defense budget allocation risk"],
    "consumer_cyclical": ["discretionary spending slowdown", "inflation impact", "gold price volatility", "competition", "supply chain disruption"],
}


# ─────────────────────────────────────────────
#  EXPOSURE MAP  (symbol-specific overrides)
# ─────────────────────────────────────────────
SYMBOL_EXPOSURE: dict[str, str] = {
    # ── IT ──
    "TCS":        "~85% USD revenue from US (55%) and Europe (30%) clients across BFSI, retail, and manufacturing",
    "INFY":       "~80% USD revenue; strong in banking and financial services (~30%), retail, and energy verticals",
    "WIPRO":      "~75% USD revenue, diversified across BFSI, healthcare, consumer, and technology sectors",
    "HCLTECH":    "~80% USD revenue; strong in products & platforms segment alongside IT services",
    "LTIM":       "~90% USD revenue; heavy exposure to North America banking and insurance sectors",
    # ── BANKING ──
    "HDFCBANK":   "Entirely INR domestic; retail lending (~55%), wholesale banking (~30%), treasury (~15%)",
    "ICICIBANK":  "Entirely INR domestic; retail loans (~60%), corporate banking, and international operations (~5%)",
    "SBIN":       "Primarily INR domestic; large corporate and retail portfolio with international branches",
    "BAJFINANCE": "100% INR domestic; consumer durable, personal loan, SME lending across India",
    # ── CONGLOMERATE & ENERGY ──
    "RELIANCE":   "O2C (~40%), Retail (~30%), Jio (~20%), E&P (~5%); partially USD-linked via refining",
    "ADANIENT":   "Diversified: Ports, Energy, Roads, Data Centers; significant USD debt exposure for capex",
    "ONGC":       "100% INR revenue; costs linked to global oil equipment prices; USD dividends",
    # ── TELECOM ──
    "BHARTIARTL": "India mobile (~65%), Africa (~20%), enterprise (~15%); Africa segment USD/local currency mix",
    # ── AUTO ──
    "MARUTI":     "Primarily INR domestic; ~15% export revenue; key input exposure to steel, aluminum, yen via Suzuki JV",
    "TATAMOTORS": "~65% revenue from Jaguar Land Rover (GBP/EUR), ~35% India (CV + PV); heavy FX exposure",
    "BAJAJ-AUTO": "~45% export revenue (Africa/LATAM/ASEAN); INR domestic; USD/INR hedge beneficial",
    # ── PHARMA ──
    "SUNPHARMA":  "~58% international (US generics ~25%, ROW ~33%), ~42% India branded generics",
    "DIVISLAB":   "~65% export revenue (US/EU); high dependency on USD/INR rates; low domestic exposure",
    # ── METALS ──
    "TATASTEEL":  "~55% revenue from Europe (UK/NL), ~45% India; heavy GBP/EUR exposure; import coking coal",
    "HINDALCO":   "~35% export revenue (US/EU); Novelis segment USD-denominated; domestic INR sales",
    # ── FMCG & CONSUMER ──
    "ITC":        "100% INR domestic; Agri exports minor; Hotels segment has import equipment exposure",
    "TITAN":      "100% INR domestic revenue; ~80% gold imports (USD linked); luxury watches imported",
    # ── INFRA / CAPITAL GOODS ──
    "LT":         "Primarily domestic INR project revenues; some USD-linked equipment imports; Middle East exposure (~10%)",
    "NTPC":       "100% INR domestic; coal imports (USD) for coastal plants; sovereign guarantees",
    # ── DEFENSE (NEW) ──
    "BEL":        "~90-95% revenue from Indian Ministry of Defence orders (INR-denominated); ~2-5% exports to friendly nations (USD/EUR); import dependency for semiconductors, RF components, and specialized electronics",
    "HAL":        "~85% MoD/Indian Armed Forces orders (INR); ~15% exports/MRO (USD); critical import dependency for jet engines, avionics",
    "BDL":        "~95% revenue from Indian defense forces (INR); missile systems export potential (USD); raw material import exposure",
    # ── NEW AGE ──
    "ZOMATO":     "100% INR domestic; server costs USD-linked; no direct revenue FX exposure",
}

SECTOR_EXPOSURE: dict[str, str] = {
    "IT":             "Majority USD revenue from US and European clients; INR cost base provides natural hedge",
    "banking":        "Domestic INR-denominated lending and deposits; limited direct FX exposure",
    "insurance":      "Domestic INR premium income; large equity and bond investment portfolio",
    "pharma":         "Mix of US generics exports and domestic branded formulations; USD revenue exposure",
    "auto":           "Primarily domestic INR sales; commodity input costs and export exposure vary by company",
    "energy":         "Revenue linked to global crude prices; domestic pricing partially regulated by government",
    "fmcg":           "Primarily domestic INR revenue; input costs linked to global commodity prices",
    "metals":         "Revenue linked to global metal prices; mix of domestic and export sales",
    "telecom":        "Primarily domestic INR ARPU-driven revenue; spectrum and capex USD-denominated",
    "realty":         "100% domestic INR revenue tied to residential and commercial property cycles",
    "infrastructure": "Primarily domestic INR project revenues; some USD-linked equipment imports",
    # ── NEW ENTRIES ──
    "chemicals":      "High export orientation (USD/EUR); significant import dependency for intermediates (China/ME)",
    "capital_goods":  "Domestic INR order books; import dependency for high-tech components (EUR/USD); defense segment: MoD budget-driven",
    "consumer_cyclical": "Domestic INR revenue; import duties on luxury components/gold affect margins",
}


# ─────────────────────────────────────────────
#  HELPER FUNCTIONS
# ─────────────────────────────────────────────

def _map_sector(yf_sector: str, industry: str) -> str:
    """Map Yahoo Finance sector/industry to internal sector name."""
    if yf_sector in YF_SECTOR_MAP:
        return YF_SECTOR_MAP[yf_sector]
    
    industry_lower = (industry or "").lower()
    for kw, sector in INDUSTRY_KEYWORD_MAP.items():
        if kw in industry_lower:
            return sector
    
    return yf_sector.lower() if yf_sector else "unknown"


def fetch_from_yfinance(symbol: str) -> dict | None:
    """
    Fetch equity info from Yahoo Finance using .NS suffix for NSE stocks.
    Returns dict with keys: name, sector, industry, marketCap | None on failure.
    """
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        info = ticker.info
        
        # Detect failed fetch — yfinance returns minimal dict on error
        name = info.get("longName") or info.get("shortName") or ""
        if not name:
            return None

        return {
            "name": name,
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "marketCap": info.get("marketCap") or 0,
        }

    except Exception as e:
        print(f"[yfinance] ⚠️  {symbol} — Fetch failed: {e}")
        return None


def generate_equity(symbol: str) -> dict | None:
    """
    Generate equity profile:
    1. Fetch from yfinance (.NS suffix)
    2. Apply local override if available (for sector/industry fixes)
    3. Map to internal sector using curated maps
    4. Attach peers/risks/exposure from rule maps
    """
    print(f"[gen] Fetching {symbol} from Yahoo Finance...")

    # ── Step 1: Fetch from yfinance ─────────────
    data = fetch_from_yfinance(symbol)
    
    # ── Step 2: Apply local override if available ─
    if symbol in NSE_OVERRIDES:
        override = NSE_OVERRIDES[symbol]
        if data:
            # Merge: override takes precedence for non-empty values
            data.update({k: v for k, v in override.items() if v})
        else:
            # Use override as base if yfinance failed completely
            data = override.copy()
        print(f"[gen] {symbol} — Applied local override")

    # ── Step 3: Validate & process ──────────────
    if not data or not data.get("name"):
        print(f"[gen] ❌ {symbol} — Not found on Yahoo Finance (tried {symbol}.NS)")
        return None

    name = data["name"]
    yf_sector = data.get("sector", "")
    industry = data.get("industry", "")
    sector = _map_sector(yf_sector, industry)
    
    market_cap = data.get("marketCap") or 0
    priority = 1 if market_cap >= 1_000_000_000_000 else 2  # ₹1T threshold

    # ── Step 4: Attach curated metadata ─────────
    peers = PEER_MAP.get(symbol) or SECTOR_PEERS.get(sector, [])
    risks = SYMBOL_RISKS.get(symbol) or SECTOR_RISKS.get(sector, ["market risk", "regulatory risk"])
    exposure = SYMBOL_EXPOSURE.get(symbol) or SECTOR_EXPOSURE.get(sector, "Primarily domestic INR revenue")

    profile = {
        "symbol": symbol,
        "name": name,
        "sector": sector,
        "industry": industry,
        "priority": priority,
        "peers": peers,
        "revenue_exposure": exposure,
        "risks": risks,
    }

    print(f"[gen] ✅ {symbol} → {name} | {sector} | cap={market_cap:,.0f} | P{priority}")
    return profile


def load_existing() -> list[dict]:
    """Load existing equities.json if it exists."""
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE) as f:
            return json.load(f)
    return []


def save_equities(equities: list[dict]):
    """Save equities list to equities.json."""
    with open(OUTPUT_FILE, "w") as f:
        json.dump(equities, f, indent=2)
    print(f"\n[gen] 💾 Saved {len(equities)} equities to {OUTPUT_FILE}")


def preview(equities: list[dict]):
    """Print a summary table of all equities."""
    print(f"\n{'─'*80}")
    print(f"  {'SYMBOL':<12} {'NAME':<35} {'SECTOR':<14} P")
    print(f"{'─'*80}")
    for e in equities:
        print(f"  {e['symbol']:<12} {e['name'][:34]:<35} {e['sector']:<14} {e['priority']}")
    print(f"{'─'*80}")
    print(f"  Total: {len(equities)} equities")


# ─────────────────────────────────────────────
#  DEFAULT SYMBOLS (Nifty 50 + Defense + Small-caps)
# ─────────────────────────────────────────────
DEFAULT_SYMBOLS = [
    "RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS",
    "BHARTIARTL", "LICI", "SBIN", "HINDUNILVR", "BAJFINANCE",
    "ITC", "KOTAKBANK", "AXISBANK", "ASIANPAINT", "MARUTI",
    "SUNPHARMA", "TATAMOTORS", "WIPRO", "ULTRACEMCO", "NTPC",
    # ── Defense / Capital Goods ──
    "BEL", "HAL", "BDL", "LT",
    # ── Chemicals / Specialty ──
    "NGLFINE", "SRF", "PIDILITIND",
    # ── Small-cap / Lesser-known ──
    "GANDHITUBE", "STYLAMIND", "DATAPATTNS",
]


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Generate equity profiles using Yahoo Finance")
    parser.add_argument(
        "--symbols", nargs="+", metavar="SYMBOL",
        help="NSE symbols to generate (e.g. RELIANCE INFY BEL NGLFINE)"
    )
    parser.add_argument(
        "--append", action="store_true",
        help="Append to existing equities.json instead of overwriting"
    )
    parser.add_argument(
        "--preview", action="store_true",
        help="Preview current equities.json and exit"
    )
    args = parser.parse_args()

    # ── Preview mode ─────────────────────────
    if args.preview:
        existing = load_existing()
        if existing:
            preview(existing)
        else:
            print("[gen] equities.json is empty or does not exist")
        return

    # ── Determine symbols to generate ────────
    symbols = [s.upper() for s in args.symbols] if args.symbols else DEFAULT_SYMBOLS

    # ── Load existing if appending ────────────
    existing = load_existing() if args.append else []
    existing_symbols = {e["symbol"] for e in existing}

    to_generate = [s for s in symbols if s not in existing_symbols]
    skipped = [s for s in symbols if s in existing_symbols]

    if skipped:
        print(f"[gen] Skipping {len(skipped)} already existing: {', '.join(skipped)}")

    if not to_generate:
        print("[gen] Nothing to generate.")
        preview(existing)
        return

    print(f"\n[gen] Generating {len(to_generate)} equity profiles...\n")

    # ── Generate each symbol ──────────────────
    new_profiles = []
    failed = []

    for symbol in to_generate:
        profile = generate_equity(symbol)
        if profile:
            new_profiles.append(profile)
        else:
            failed.append(symbol)

    # ── Save ──────────────────────────────────
    all_equities = existing + new_profiles
    save_equities(all_equities)
    preview(all_equities)

    if failed:
        print(f"\n[gen] ⚠️  Failed symbols: {', '.join(failed)}")
        print(f"[gen]    Tip: Add to NSE_OVERRIDES or retry with --symbols {' '.join(failed)}")


if __name__ == "__main__":
    main()