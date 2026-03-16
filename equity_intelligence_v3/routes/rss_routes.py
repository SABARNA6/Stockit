"""
=====================================================================
  routes/rss_routes.py
  API endpoints for RSS feed operations
=====================================================================
"""

from flask import Blueprint, jsonify
from ingestion.rss_fetcher import fetch_all_feeds

rss_bp = Blueprint("rss", __name__, url_prefix="/api/rss")


@rss_bp.route("/trigger", methods=["GET", "POST"])
def trigger_rss_fetch():
    """
    Manually trigger RSS feed fetch and save to Supabase.
    
    Usage:
      GET  /api/rss/trigger
      POST /api/rss/trigger
    
    Response:
      {
        "status": "success|error",
        "feeds_fetched": int,
        "total_new": int,
        "total_skipped": int,
        "saved_to_db": int,
        "message": str,
        "feed_results": [...]
      }
    """
    try:
        result = fetch_all_feeds()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"RSS fetch failed: {str(e)}"
        }), 500


@rss_bp.route("/status", methods=["GET"])
def rss_status():
    """Health check endpoint for RSS service."""
    return jsonify({
        "status": "ok",
        "service": "equity_intelligence_v3 RSS Fetcher",
        "endpoints": {
            "trigger": "GET|POST /api/rss/trigger",
            "status": "GET /api/rss/status",
        }
    }), 200
