"""
GitHub API data fetching layer for gitwho.
Handles authentication, rate limiting, pagination, and all data collection.
"""

import os
import time
import requests
from typing import List, Dict, Any, Optional, Tuple

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# GitHub API base URL
API_BASE = "https://api.github.com"

# Rate limit state
_rate_limit_remaining = None
_rate_limit_reset = None


def _get_session() -> requests.Session:
    """Create a requests session with optional GitHub token auth."""
    session = requests.Session()
    session.headers.update({
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "gitwho"
    })
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        session.headers["Authorization"] = f"token {token}"
    return session


# Module-level session
_session = _get_session()


def _update_rate_limit(response: requests.Response) -> None:
    """Track rate limit from response headers."""
    global _rate_limit_remaining, _rate_limit_reset
    remaining = response.headers.get("X-RateLimit-Remaining")
    reset = response.headers.get("X-RateLimit-Reset")
    if remaining is not None:
        _rate_limit_remaining = int(remaining)
    if reset is not None:
        _rate_limit_reset = int(reset)


def get_rate_limit_info() -> Dict[str, Any]:
    """Return current rate limit state."""
    return {
        "remaining": _rate_limit_remaining,
        "reset": _rate_limit_reset,
        "reset_in": max(0, (_rate_limit_reset or 0) - int(time.time())),
        "authenticated": "Authorization" in _session.headers
    }


def _api_get(url: str, params: Optional[Dict] = None) -> Optional[requests.Response]:
    """Make a GET request with rate limit tracking."""
    global _rate_limit_remaining
    if _rate_limit_remaining is not None and _rate_limit_remaining < 3:
        reset_in = max(0, (_rate_limit_reset or 0) - int(time.time()))
        print(f"[!] Rate limit nearly exhausted ({_rate_limit_remaining} remaining). Resets in {reset_in}s")
        if _rate_limit_remaining == 0:
            return None

    try:
        response = _session.get(url, params=params, timeout=15)
        _update_rate_limit(response)
        return response
    except requests.RequestException as e:
        print(f"[!] Request failed: {e}")
        return None


def _paginated_fetch(url: str, per_page: int = 100, max_pages: int = 0) -> List[Dict[str, Any]]:
    """Fetch all pages from a paginated endpoint."""
    results = []
    page = 1
    while True:
        if max_pages and page > max_pages:
            break
        response = _api_get(url, params={"page": page, "per_page": per_page})
        if response is None or response.status_code != 200:
            break
        data = response.json()
        if not data or not isinstance(data, list):
            break
        results.extend(data)
        if len(data) < per_page:
            break
        page += 1
    return results


def fetch_user_profile(username: str) -> Optional[Dict[str, Any]]:
    """Fetch user/org profile info."""
    response = _api_get(f"{API_BASE}/users/{username}")
    if response is None or response.status_code != 200:
        return None
    data = response.json()
    if "message" in data:
        return None
    return {
        "login": data.get("login"),
        "name": data.get("name"),
        "type": data.get("type"),  # User or Organization
        "avatar_url": data.get("avatar_url"),
        "bio": data.get("bio"),
        "location": data.get("location"),
        "company": data.get("company"),
        "blog": data.get("blog"),
        "twitter_username": data.get("twitter_username"),
        "email": data.get("email"),
        "public_repos": data.get("public_repos", 0),
        "public_gists": data.get("public_gists", 0),
        "followers": data.get("followers", 0),
        "following": data.get("following", 0),
        "created_at": data.get("created_at"),
        "updated_at": data.get("updated_at"),
        "hireable": data.get("hireable"),
    }


def fetch_repos(username: str, user_type: str = "User", max_pages: int = 10) -> List[Dict[str, Any]]:
    """Fetch repositories, sorted by stars descending (capped at max_pages)."""
    base = "orgs" if user_type == "Organization" else "users"
    url = f"{API_BASE}/{base}/{username}/repos"
    repos = _paginated_fetch(url, max_pages=max_pages)

    processed = []
    for repo in repos:
        processed.append({
            "name": repo.get("name"),
            "full_name": repo.get("full_name"),
            "description": repo.get("description"),
            "language": repo.get("language"),
            "stars": repo.get("stargazers_count", 0),
            "forks": repo.get("forks_count", 0),
            "watchers": repo.get("watchers_count", 0),
            "open_issues": repo.get("open_issues_count", 0),
            "created_at": repo.get("created_at"),
            "updated_at": repo.get("updated_at"),
            "pushed_at": repo.get("pushed_at"),
            "html_url": repo.get("html_url"),
            "fork": repo.get("fork", False),
            "archived": repo.get("archived", False),
            "topics": repo.get("topics", []),
            "size": repo.get("size", 0),
            "default_branch": repo.get("default_branch"),
            "license": repo.get("license", {}).get("spdx_id") if repo.get("license") else None,
        })

    return sorted(processed, key=lambda x: x["stars"], reverse=True)


def fetch_repo_languages(owner: str, repo: str) -> Dict[str, int]:
    """Fetch language breakdown (bytes) for a single repo."""
    response = _api_get(f"{API_BASE}/repos/{owner}/{repo}/languages")
    if response is None or response.status_code != 200:
        return {}
    return response.json()


def fetch_all_languages(username: str, repos: List[Dict[str, Any]], max_repos: int = 20) -> Dict[str, int]:
    """Aggregate language bytes across top non-forked repos.
    Forks are excluded unless the user has pushed significant changes
    (pushed_at is more than 1 day after created_at).
    """
    aggregated = {}
    counted = 0
    for repo in repos:
        if counted >= max_repos:
            break
        # Skip forks unless user has pushed significant changes
        if repo.get("fork", False):
            created = repo.get("created_at", "")
            pushed = repo.get("pushed_at", "")
            if created and pushed and pushed[:10] <= created[:10]:
                continue  # Fork with no meaningful push activity
        counted += 1
        langs = fetch_repo_languages(username, repo["name"])
        for lang, bytes_count in langs.items():
            aggregated[lang] = aggregated.get(lang, 0) + bytes_count
    return aggregated


def fetch_starred(username: str, max_pages: int = 5) -> List[Dict[str, Any]]:
    """Fetch starred repos."""
    url = f"{API_BASE}/users/{username}/starred"
    starred = _paginated_fetch(url, per_page=100, max_pages=max_pages)

    processed = []
    for repo in starred:
        processed.append({
            "full_name": repo.get("full_name"),
            "description": repo.get("description"),
            "language": repo.get("language"),
            "stars": repo.get("stargazers_count", 0),
            "html_url": repo.get("html_url"),
            "topics": repo.get("topics", []),
        })
    return processed


def fetch_following(username: str, max_pages: int = 3) -> List[Dict[str, Any]]:
    """Fetch users this person follows (capped to avoid huge fetches)."""
    url = f"{API_BASE}/users/{username}/following"
    following = _paginated_fetch(url, max_pages=max_pages)
    return [{"login": u.get("login"), "avatar_url": u.get("avatar_url"),
             "html_url": u.get("html_url"), "type": u.get("type")}
            for u in following]


def fetch_followers(username: str, max_pages: int = 3) -> List[Dict[str, Any]]:
    """Fetch this person's followers (capped to avoid huge fetches)."""
    url = f"{API_BASE}/users/{username}/followers"
    followers = _paginated_fetch(url, max_pages=max_pages)
    return [{"login": u.get("login"), "avatar_url": u.get("avatar_url"),
             "html_url": u.get("html_url"), "type": u.get("type")}
            for u in followers]


def fetch_orgs(username: str) -> List[Dict[str, Any]]:
    """Fetch organizations the user belongs to."""
    url = f"{API_BASE}/users/{username}/orgs"
    orgs = _paginated_fetch(url)
    return [{"login": o.get("login"), "avatar_url": o.get("avatar_url"),
             "description": o.get("description"), "html_url": f"https://github.com/{o.get('login')}"}
            for o in orgs]


def fetch_events(username: str, max_pages: int = 3) -> List[Dict[str, Any]]:
    """Fetch recent public events."""
    url = f"{API_BASE}/users/{username}/events/public"
    events = _paginated_fetch(url, per_page=100, max_pages=max_pages)

    processed = []
    for event in events:
        processed.append({
            "type": event.get("type"),
            "repo": event.get("repo", {}).get("name"),
            "created_at": event.get("created_at"),
            "payload_action": event.get("payload", {}).get("action"),
        })
    return processed


def _search_prs(query: str, max_pages: int = 3) -> List[Dict[str, Any]]:
    """Search for pull requests using the GitHub search API."""
    url = f"{API_BASE}/search/issues"
    results = []
    page = 1
    while page <= max_pages:
        response = _api_get(url, params={"q": query, "per_page": 100, "page": page})
        if response is None or response.status_code != 200:
            break
        data = response.json()
        items = data.get("items", [])
        if not items:
            break
        results.extend(items)
        if len(items) < 100:
            break
        page += 1
    return results


def fetch_pull_requests(username: str) -> Dict[str, List[Dict[str, Any]]]:
    """Fetch PRs authored by user on OTHER repos (merged, open, closed-unmerged)."""
    def process_prs(items, username):
        processed = []
        for pr in items:
            repo_url = pr.get("repository_url", "")
            repo_full = "/".join(repo_url.split("/")[-2:]) if repo_url else ""
            repo_owner = repo_url.split("/")[-2] if repo_url else ""
            # Skip PRs to own repos
            if repo_owner.lower() == username.lower():
                continue
            processed.append({
                "title": pr.get("title"),
                "repo": repo_full,
                "html_url": pr.get("html_url"),
                "state": pr.get("state"),
                "created_at": pr.get("created_at"),
                "closed_at": pr.get("closed_at"),
                "pull_request": pr.get("pull_request", {}),
            })
        return processed

    merged = _search_prs(f"author:{username} type:pr is:merged")
    open_prs = _search_prs(f"author:{username} type:pr is:open")
    closed_unmerged = _search_prs(f"author:{username} type:pr is:unmerged is:closed")

    return {
        "merged": process_prs(merged, username),
        "open": process_prs(open_prs, username),
        "closed": process_prs(closed_unmerged, username),
    }


def fetch_all(username: str, verbose: bool = False) -> Optional[Dict[str, Any]]:
    """Master function: fetch everything about a GitHub user/org."""
    profile = fetch_user_profile(username)
    if profile is None:
        return None

    user_type = profile.get("type", "User")
    repos = fetch_repos(username, user_type)

    # Language aggregation (cap at top 20 repos to save API calls)
    languages = fetch_all_languages(username, repos, max_repos=20)

    starred = fetch_starred(username)
    following = fetch_following(username)
    followers = fetch_followers(username)
    orgs = fetch_orgs(username)
    events = fetch_events(username)
    pull_requests = fetch_pull_requests(username)

    return {
        "profile": profile,
        "repos": repos,
        "languages": languages,
        "starred": starred,
        "following": following,
        "followers": followers,
        "orgs": orgs,
        "events": events,
        "pull_requests": pull_requests,
        "fetched_at": time.time(),
    }
