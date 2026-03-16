"""
=====================================================================
  test_rss_api.py
  Example script to test the RSS fetcher API
=====================================================================
"""

import requests
import json
import time
from typing import Dict, Any

BASE_URL = "http://localhost:5000"


def check_service_status() -> bool:
    """Check if API server is running."""
    try:
        response = requests.get(f"{BASE_URL}/api/rss/status", timeout=5)
        if response.status_code == 200:
            print("✅ API server is running")
            print(json.dumps(response.json(), indent=2))
            return True
        else:
            print(f"❌ API returned status {response.status_code}")
            return False
    except requests.ConnectionError:
        print("❌ Cannot connect to API. Is server running?")
        print(f"   Start with: python server.py")
        return False


def trigger_rss_fetch() -> Dict[str, Any]:
    """Trigger RSS feed fetch via API."""
    print("\n[Test] Triggering RSS fetch...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/rss/trigger",
            timeout=120  # Allow 2 minutes for fetch
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ RSS Fetch successful!")
            print(f"   Feeds fetched: {result.get('feeds_fetched', 0)}")
            print(f"   New articles: {result.get('total_new', 0)}")
            print(f"   Skipped (duplicates): {result.get('total_skipped', 0)}")
            print(f"   Saved to database: {result.get('saved_to_db', 0)}")
            print(f"   Total in pool: {result.get('total_pool', 0)}")
            
            if result.get('feed_results'):
                print(f"\n   Per-feed results:")
                for feed in result['feed_results']:
                    print(f"     • {feed['source']}: {feed['new']} new, {feed['skipped']} skipped")
            
            return result
        else:
            print(f"❌ API returned status {response.status_code}")
            print(f"   Response: {response.text}")
            return {}
    except requests.Timeout:
        print("❌ Request timed out. Fetch may still be running.")
    except Exception as e:
        print(f"❌ Error: {e}")
        return {}


def test_multiple_fetches(count: int = 3):
    """Run multiple fetch tests with delay."""
    print(f"\n[Test] Running {count} sequential fetch tests...\n")
    
    for i in range(1, count + 1):
        print(f"{'='*60}")
        print(f"Test {i}/{count}")
        print(f"{'='*60}")
        
        result = trigger_rss_fetch()
        
        if i < count:
            print(f"\nWaiting 30 seconds before next fetch...")
            time.sleep(30)
    
    print(f"\n{'='*60}")
    print("All tests complete!")
    print(f"{'='*60}")


def main():
    """Main test routine."""
    print(f"\n{'='*60}")
    print("  RSS Fetcher API Test Suite")
    print(f"{'='*60}")
    
    # Check if server is running
    if not check_service_status():
        return
    
    # Single fetch test
    print(f"\n{'='*60}")
    print("Running initial fetch test...")
    print(f"{'='*60}")
    trigger_rss_fetch()
    
    # Ask if user wants more tests
    print(f"\n{'='*60}")
    print("Test complete!")
    print(f"{'='*60}")
    print("\nUsage:")
    print("  • To trigger RSS manually: curl http://localhost:5000/api/rss/trigger")
    print("  • Check status: curl http://localhost:5000/api/rss/status")
    print("  • Articles will be available in Supabase rss_pool table")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
