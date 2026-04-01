import threading
import atexit
from ingestion.rss_fetcher import fetch_all_feeds

def start_rss_pool_thread(interval_hours: int = 5):
    """Run `fetch_all_feeds` in a background thread every `interval_hours`."""
    _stop_event = threading.Event()

    def run():
        while not _stop_event.is_set():
            print(f"[background] triggering scheduled RSS pull")
            fetch_all_feeds()
            _stop_event.wait(interval_hours * 3600)

    print(f"[background] starting RSS pull thread (runs every {interval_hours}h)")
    t = threading.Thread(target=run, daemon=True)
    t.start()

    def _shutdown():
        _stop_event.set()
        t.join(timeout=10)

    atexit.register(_shutdown)
    return _shutdown
