#!/usr/bin/env python
from helpers.stock_helper import get_chart_data, get_volume_data
import json

cd = get_chart_data('INFY', '3M')
vd = get_volume_data('INFY', '3M')

print("=" * 60)
print("CHART DATA (first 3 candles):")
print("=" * 60)
print(json.dumps(cd['candles'][:3] if cd.get('candles') else [], indent=2))
print(f"\nTotal candles: {len(cd.get('candles', []))}")

print("\n" + "=" * 60)
print("VOLUME DATA (first 3 volumes):")
print("=" * 60)
print(json.dumps(vd['volumes'][:3] if vd.get('volumes') else [], indent=2))
print(f"Avg Volume: {vd.get('avgVolume')}")
print(f"Total volumes: {len(vd.get('volumes', []))}")

print("\n" + "=" * 60)
print("Checking for null values...")
print("=" * 60)
for i, candle in enumerate(cd['candles'][:5]):
    if any(v is None for v in candle.values()):
        print(f"Candle {i} has None: {candle}")
    else:
        print(f"Candle {i}: ✓ All values present")
