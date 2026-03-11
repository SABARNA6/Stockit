#!/usr/bin/env python3
"""
Extract Symbol and Industry from EQUITY_L.csv
Fetches industry for each symbol and creates Symbol, Industry output
"""

import csv
import sys
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

sys.path.insert(0, str(Path(__file__).parent.parent / "server"))

try:
    import yfinance as yf
    _YF_AVAILABLE = True
except ImportError:
    _YF_AVAILABLE = False

_lock = threading.Lock()
_counter = 0
_total = 0


def fetch_industry(item: tuple) -> dict:
    """Fetch industry for a symbol."""
    symbol, idx = item
    global _counter
    
    result = {
        "index": idx,
        "symbol": symbol,
        "industry": "N/A",
    }
    
    try:
        ticker_sym = symbol.upper()
        if not ticker_sym.endswith(".NS") and not ticker_sym.endswith(".BO"):
            ticker_sym = f"{ticker_sym}.NS"
        
        ticker = yf.Ticker(ticker_sym)
        info = ticker.info
        
        if "industry" in info and info["industry"]:
            result["industry"] = info["industry"]
        elif "sector" in info and info["sector"]:
            result["industry"] = info["sector"]
    except:
        pass
    
    with _lock:
        _counter += 1
        if _counter % 50 == 0 or _counter == _total:
            print(f"\r[{_counter:4d}/{_total}]", end="", flush=True)
    
    return result


def main():
    global _counter, _total
    
    # Read from EQUITY_L.csv
    csv_path = Path(__file__).parent / "EQUITY_L.csv"
    
    if not csv_path.exists():
        print(f"❌ File not found: {csv_path}")
        sys.exit(1)
    
    symbols = []
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            symbols = [row['SYMBOL'].strip() for row in reader if row.get('SYMBOL', '').strip()]
    except Exception as e:
        print(f"❌ Error reading EQUITY_L.csv: {e}")
        sys.exit(1)
    
    _total = len(symbols)
    print(f"📊 Fetching industries for {_total} symbols from EQUITY_L.csv...")
    
    results = []
    try:
        with ThreadPoolExecutor(max_workers=16) as executor:
            items = [(sym, idx) for idx, sym in enumerate(symbols, 1)]
            futures = {executor.submit(fetch_industry, item): item[0] for item in items}
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    pass
        
        print("\n")
        
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted")
        sys.exit(1)
    
    # Sort by index
    results.sort(key=lambda x: x['index'])
    
    # Write output
    output_path = Path(__file__).parent / "symbol_industry.csv"
    
    try:
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['Symbol', 'Industry']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            writer.writeheader()
            for result in results:
                writer.writerow({
                    'Symbol': result['symbol'],
                    'Industry': result['industry'],
                })
        
        with_industry = sum(1 for r in results if r['industry'] != 'N/A')
        
        print(f"✅ Saved to: {output_path}")
        print(f"📝 Total: {_total} | With industry: {with_industry} ({100*with_industry/_total:.1f}%)")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
