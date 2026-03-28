"""
Flask web application for gitwho.
Provides a search interface and profile results page.
"""

import time
import os
import sys

from flask import Flask, render_template, request, jsonify

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from github_api import fetch_all, get_rate_limit_info
from analyzer import analyze_profile, enhance_with_llm
from scraper import scrape_profile_extras
from gitwho import extract_username

import asyncio

# In-memory cache: {username: {"data": ..., "analysis": ..., "extras": ..., "timestamp": ...}}
_cache = {}
CACHE_TTL = int(os.environ.get("GITWHO_CACHE_TTL", 3600))  # Default 1 hour


def _get_cached(username: str):
    """Get cached profile or None if expired/missing."""
    entry = _cache.get(username)
    if entry and (time.time() - entry["timestamp"]) < CACHE_TTL:
        return entry
    return None


def _set_cache(username: str, data: dict, analysis: dict, extras: dict):
    """Cache profile data."""
    _cache[username] = {
        "data": data,
        "analysis": analysis,
        "extras": extras,
        "timestamp": time.time(),
    }


def _fetch_profile(username: str):
    """Fetch and analyze a profile (with caching)."""
    cached = _get_cached(username)
    if cached:
        return cached["data"], cached["analysis"], cached["extras"]

    data = fetch_all(username)
    if data is None:
        return None, None, None

    analysis = analyze_profile(data)

    # Try LLM enhancement
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        analysis = loop.run_until_complete(enhance_with_llm(analysis, data))
    finally:
        loop.close()

    extras = scrape_profile_extras(username)
    data["extras"] = extras

    _set_cache(username, data, analysis, extras)
    return data, analysis, extras


def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
        static_folder=os.path.join(os.path.dirname(__file__), "static"),
    )

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/search")
    def search():
        raw_username = request.args.get("username", "").strip()
        if not raw_username:
            return render_template("index.html", error="Please enter a GitHub username or URL.")

        username = extract_username(raw_username)
        data, analysis, extras = _fetch_profile(username)

        if data is None:
            return render_template("index.html", error=f"User '{username}' not found or API error.")

        rate_limit = get_rate_limit_info()
        cache_stats = {
            "total_cached": len(_cache),
            "cache_ttl": CACHE_TTL,
        }

        return render_template(
            "results.html",
            data=data,
            analysis=analysis,
            extras=extras,
            rate_limit=rate_limit,
            cache_stats=cache_stats,
        )

    @app.route("/api/profile/<username>")
    def api_profile(username):
        username = extract_username(username)
        data, analysis, extras = _fetch_profile(username)

        if data is None:
            return jsonify({"error": f"User '{username}' not found"}), 404

        return jsonify({
            "data": data,
            "analysis": analysis,
            "rate_limit": get_rate_limit_info(),
        })

    return app
