import pandas as pd
import sys
import os
import requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load .env file
load_dotenv()


# ─────────────────────────────────────────────
#  SUPABASE HELPERS
# ─────────────────────────────────────────────
def _get_supabase_headers():
    """Get headers for Supabase API requests."""
    key = os.environ.get("SUPABASE_KEY")
    if not key:
        raise ValueError("SUPABASE_KEY environment variable not set")
    
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }


def _get_supabase_url(table: str) -> str:
    """Build Supabase REST API URL."""
    base = os.environ.get("SUPABASE_URL", "").rstrip("/")
    if not base:
        raise ValueError("SUPABASE_URL environment variable not set")
    return f"{base}/rest/v1/{table}"


def upload_to_supabase(csv_file, table="rss_feeds", encoding='latin-1'):
    """
    Upload RSS feeds from CSV to Supabase rss_feeds table.
    
    ════════════════════════════════════════════════════════════════════
    SCHEMA MAPPING (CSV → Supabase rss_feeds table):
    ════════════════════════════════════════════════════════════════════
      CSV Column       →  DB Column        Type                Required
      ─────────────────────────────────────────────────────────────────
      rss_id           →  (ignored)        -                   -
      name             →  name             TEXT NOT NULL       ✓
      country          →  country          TEXT DEFAULT 'IN'   -
      category         →  category         TEXT                -
      link             →  url              TEXT NOT NULL UNIQUE ✓
      (auto)           →  is_active        BOOLEAN DEFAULT true (auto)
      (auto)           →  created_at       TIMESTAMPTZ NOW()   (auto)
    ════════════════════════════════════════════════════════════════════
    
    Args:
        csv_file (str): Path to CSV file
        table (str): Supabase table name (default: rss_feeds)
        encoding (str): CSV encoding (default: latin-1)
    
    Returns:
        dict: Upload result with success status and counts
    """
    
    try:
        # Read CSV
        df = pd.read_csv(csv_file, encoding=encoding)
        total_rows = len(df)
        print(f"\n📖 Loaded {total_rows} rows from {csv_file}")
        print(f"📋 CSV Columns: {list(df.columns)}")
        print()
        
        # Map CSV columns to Supabase rss_feeds table schema
        rows = []
        skipped = []
        
        for idx, row in df.iterrows():
            try:
                name = str(row.get('name', '')).strip()
                url = str(row.get('link', '')).strip()
                country = str(row.get('country', '')).strip() or 'IN'
                category = str(row.get('category', '')).strip()
                
                # Validate required fields
                if not name:
                    skipped.append(f"Row {idx+1}: Missing name")
                    continue
                if not url:
                    skipped.append(f"Row {idx+1}: Missing URL")
                    continue
                
                # Build row for insertion
                feed = {
                    "name": name,
                    "country": country,
                    "category": category or None,
                    "url": url,
                    "is_active": True,
                }
                
                rows.append(feed)
                
            except Exception as e:
                skipped.append(f"Row {idx+1}: {str(e)}")
                continue
        
        if skipped:
            print(f"⚠️  Skipped {len(skipped)} rows:")
            for msg in skipped[:5]:  # Show first 5
                print(f"   - {msg}")
            if len(skipped) > 5:
                print(f"   ... and {len(skipped) - 5} more")
            print()
        
        if not rows:
            print("❌ No valid rows to upload")
            return {"success": False, "message": "No valid rows"}
        
        # Upload to Supabase with conflict resolution
        print(f"🚀 Uploading {len(rows)} feeds to Supabase/{table}...")
        
        response = requests.post(
            _get_supabase_url(table),
            headers={
                **_get_supabase_headers(),
                "Prefer": "resolution=ignore-duplicates,return=minimal"
            },
            json=rows,
            timeout=30
        )
        
        if response.status_code in (200, 201):
            print(f"✅ Successfully uploaded {len(rows)} feeds to {table}\n")
            print(f"📊 Summary:")
            print(f"   Total rows in CSV:  {total_rows}")
            print(f"   Valid rows:         {len(rows)}")
            print(f"   Skipped:            {len(skipped)}")
            
            return {
                "success": True,
                "rows_uploaded": len(rows),
                "rows_skipped": len(skipped),
                "table": table,
                "timestamp": datetime.now().isoformat()
            }
        else:
            error_msg = response.text[:500]
            print(f"❌ Upload failed — HTTP {response.status_code}")
            print(f"   Error: {error_msg}\n")
            return {
                "success": False,
                "error": error_msg,
                "status_code": response.status_code
            }
    
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error: {error_msg}\n")
        return {"success": False, "error": error_msg}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python import_rss_feeds.py <csv_file>")
        print("\nExample:")
        print("  python import_rss_feeds.py data/seed_data_rss.csv")
        print("\nRequired environment variables (.env):")
        print("  SUPABASE_URL")
        print("  SUPABASE_KEY")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    
    if not Path(csv_file).exists():
        print(f"❌ Error: File '{csv_file}' not found")
        sys.exit(1)
    
    # Upload to Supabase
    result = upload_to_supabase(csv_file)
    
    if result["success"]:
        print(f"✅ Done! {result['rows_uploaded']} RSS feeds imported to Supabase")
    else:
        print(f"❌ Upload failed: {result['error']}")
        sys.exit(1)
