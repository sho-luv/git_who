"""
GitHub profile HTML scraper for data not available via API.
Extracts achievements, highlights, and other profile metadata.
Falls back gracefully if scraping fails.
"""

import requests
from typing import List, Dict, Any

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False


def scrape_achievements(username: str) -> List[Dict[str, Any]]:
    """Scrape achievement badges from a GitHub profile page."""
    if not BS4_AVAILABLE:
        return []

    try:
        response = requests.get(
            f"https://github.com/{username}",
            headers={"User-Agent": "gitwho"},
            timeout=10
        )
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        achievements = []

        # GitHub achievements are in the sidebar under "Achievements" heading
        # Look for achievement badge elements
        achievement_items = soup.select("img.achievement-badge-sidebar")
        if not achievement_items:
            # Try alternate selectors as GitHub HTML may vary
            achievement_items = soup.select("[data-hovercard-type='achievement'] img")

        for item in achievement_items:
            name = item.get("alt", "").strip()
            src = item.get("src", "")
            if name:
                achievements.append({
                    "name": name,
                    "icon_url": src,
                })

        # Try another approach: look for achievement links
        if not achievements:
            achievement_links = soup.select("a[href*='achievements']")
            for link in achievement_links:
                img = link.find("img")
                if img:
                    name = img.get("alt", "").strip()
                    src = img.get("src", "")
                    if name and "achievement" in src.lower():
                        achievements.append({
                            "name": name,
                            "icon_url": src,
                        })

        return achievements

    except Exception:
        return []


def scrape_profile_extras(username: str) -> Dict[str, Any]:
    """Scrape additional profile data not available via API."""
    if not BS4_AVAILABLE:
        return {}

    try:
        response = requests.get(
            f"https://github.com/{username}",
            headers={"User-Agent": "gitwho"},
            timeout=10
        )
        if response.status_code != 200:
            return {}

        soup = BeautifulSoup(response.text, "html.parser")
        extras = {}

        # Try to get pinned repositories
        pinned = []
        pinned_items = soup.select(".pinned-item-list-item-content")
        for item in pinned_items:
            repo_link = item.select_one("a.text-bold")
            desc = item.select_one("p.pinned-item-desc")
            if repo_link:
                pinned.append({
                    "name": repo_link.text.strip(),
                    "description": desc.text.strip() if desc else "",
                    "url": f"https://github.com{repo_link.get('href', '')}",
                })
        if pinned:
            extras["pinned_repos"] = pinned

        # Try to get contribution count from the profile
        contrib_text = soup.select_one("h2.f4.text-normal.mb-2")
        if contrib_text:
            text = contrib_text.text.strip()
            if "contribution" in text.lower():
                extras["contribution_text"] = text

        # Achievements
        achievements = scrape_achievements(username)
        if achievements:
            extras["achievements"] = achievements

        # Status
        status_elem = soup.select_one(".user-status-message-wrapper")
        if status_elem:
            extras["status"] = status_elem.text.strip()

        return extras

    except Exception:
        return {}
