#!/usr/bin/env python3
"""
Create the final formatted output combining EQUITY_L.csv with Industry data
Format: s.no	Company Name	Industry	Symbol	Series	ISIN Code
"""

import csv
from pathlib import Path

def main():
    # Read EQUITY_L.csv
    equity_path = Path(__file__).parent / "EQUITY_L.csv"
    industry_path = Path(__file__).parent / "symbol_industry.csv"
    output_path = Path(__file__).parent / "company_details_formatted.tsv"
    
    # Load industry data
    industry_map = {}
    try:
        with open(industry_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                industry_map[row['Symbol']] = row['Industry']
    except Exception as e:
        print(f"❌ Error reading {industry_path}: {e}")
        return
    
    # Read and process EQUITY_L.csv
    results = []
    try:
        with open(equity_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader, 1):
                symbol = row['SYMBOL'].strip()
                industry = industry_map.get(symbol, 'N/A')
                
                results.append({
                    's.no': idx,
                    'Company Name': row['NAME OF COMPANY'].strip(),
                    'Industry': industry,
                    'Symbol': symbol,
                    'Series': row[' SERIES'].strip(),
                    'ISIN Code': row['ISIN NUMBER'].strip(),
                })
    except Exception as e:
        print(f"❌ Error reading {equity_path}: {e}")
        return
    
    # Write output as TSV (tab-separated)
    try:
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['s.no', 'Company Name', 'Industry', 'Symbol', 'Series', 'ISIN Code']
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')
            
            writer.writeheader()
            writer.writerows(results)
        
        with_industry = sum(1 for r in results if r['Industry'] != 'N/A')
        
        print(f"✅ Output saved to: {output_path}")
        print(f"\n📊 Summary:")
        print(f"   Total entries: {len(results)}")
        print(f"   With industry: {with_industry} ({100*with_industry/len(results):.1f}%)")
        
        # Show sample
        print(f"\n📋 Sample (first 5 rows):")
        with open(output_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i < 6:
                    print(f"   {line.rstrip()}")
                else:
                    break
        
    except Exception as e:
        print(f"❌ Error writing output: {e}")
        return


if __name__ == "__main__":
    main()
