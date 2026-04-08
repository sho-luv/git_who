#!/usr/bin/env python3
"""
gitwho - GitHub OSINT & Profile Intelligence Tool
Fetches comprehensive GitHub profile data and generates analysis.
"""

import argparse
import asyncio
import json
import os
import re
import sys
from typing import List

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich import print as rprint

from github_api import fetch_all, get_rate_limit_info
from analyzer import analyze_profile, enhance_with_llm
from scraper import scrape_profile_extras

console = Console()

BANNER = """[bold cyan]
          _ __          __
   ____ _(_) /__       / /_  ____
  / __ `/ / __/ | /| / / __ \\/ __ \\
 / /_/ / / /_ | |/ |/ / / / / /_/ /
 \\__, /_/\\__/ |__/|__/_/ /_/\\____/
/____/
[/bold cyan]
[dim]GitHub OSINT & Profile Intelligence[/dim]
"""


def is_valid_github_username(username: str) -> bool:
    """Validate GitHub username: alphanumeric + hyphens, max 39 chars."""
    return bool(re.match(r'^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?$', username))


def extract_username(arg: str) -> str:
    """Extract GitHub username from a URL or return as-is."""
    # Match github.com URLs
    match = re.match(r'https?://github\.com/([^/\s?#]+)/?', arg)
    if match:
        return match.group(1)
    # Strip @ prefix if present
    if arg.startswith("@"):
        return arg[1:]
    return arg


def is_file(path: str) -> bool:
    """Check if a path is an existing file."""
    return os.path.isfile(path)


def display_profile(data: dict, analysis: dict, extras: dict, verbose: bool = False, links: bool = False) -> None:
    """Display profile data in rich terminal format."""
    profile = data["profile"]
    repos = data["repos"]
    prs = data["pull_requests"]

    # Profile header
    name = profile.get("name") or profile.get("login")
    username = profile.get("login")
    user_type = profile.get("type", "User")

    header_parts = [f"[bold green]{name}[/bold green] [dim](@{username})[/dim]"]
    if profile.get("bio"):
        header_parts.append(f"[italic]{profile['bio']}[/italic]")
    if profile.get("location"):
        header_parts.append(f"Location: {profile['location']}")
    if profile.get("company"):
        header_parts.append(f"Company: {profile['company']}")
    if profile.get("blog"):
        header_parts.append(f"Blog: {profile['blog']}")
    if profile.get("twitter_username"):
        header_parts.append(f"Twitter: @{profile['twitter_username']}")

    header_parts.append(
        f"Followers: [bold]{profile.get('followers', 0)}[/bold] | "
        f"Following: [bold]{profile.get('following', 0)}[/bold] | "
        f"Repos: [bold]{profile.get('public_repos', 0)}[/bold]"
    )
    if profile.get("created_at"):
        header_parts.append(f"Joined: {profile['created_at'][:10]}")

    console.print(Panel("\n".join(header_parts), title=f"[bold]{user_type}: {username}[/bold]", border_style="green"))

    # Organizations
    orgs = data.get("orgs", [])
    if orgs:
        org_names = ", ".join([o["login"] for o in orgs])
        console.print(f"\n[bold yellow]Organizations:[/bold yellow] {org_names}")

    # Achievements (scraped)
    achievements = extras.get("achievements", [])
    if achievements:
        achievement_names = ", ".join([a["name"] for a in achievements])
        console.print(f"[bold yellow]Achievements:[/bold yellow] {achievement_names}")

    # Profile Analysis
    console.print(f"\n[bold cyan]Profile Analysis[/bold cyan]")
    console.print(analysis.get("summary", "No analysis available."))

    if analysis.get("llm_summary"):
        console.print(f"\n[bold magenta]AI Enhanced Summary ({analysis.get('llm_source', 'LLM')}):[/bold magenta]")
        console.print(analysis["llm_summary"])

    # Focus areas
    focus_areas = analysis.get("focus_areas", [])
    if focus_areas:
        tags = " | ".join([f"[bold]{fa['category']}[/bold] ({fa['score']})" for fa in focus_areas])
        console.print(f"\n[bold cyan]Focus Areas:[/bold cyan] {tags}")

    # Language breakdown
    languages = analysis.get("languages", [])
    if languages:
        console.print(f"\n[bold cyan]Languages:[/bold cyan]")
        for lang_info in languages[:10]:
            bar_len = int(lang_info["percentage"] / 2)
            bar = "█" * bar_len
            console.print(f"  {lang_info['language']:20s} {bar} {lang_info['percentage']}%")

    # Metrics
    metrics = analysis.get("metrics", {})
    if metrics:
        console.print(f"\n[bold cyan]Community Metrics:[/bold cyan]")
        console.print(f"  Total stars received: {metrics.get('total_stars_received', 0)}")
        console.print(f"  PR merge rate: {metrics.get('pr_merge_rate', 0)}%")
        console.print(f"  Follower ratio: {metrics.get('follower_ratio', 0)}")

    # Recent Activity
    activity_summary = analysis.get("activity_summary", "")
    recent_repos = analysis.get("recent_repos", [])
    if activity_summary:
        console.print(f"\n[bold cyan]Recent Activity[/bold cyan]")
        console.print(f"  {activity_summary}")
    if recent_repos:
        if not activity_summary:
            console.print(f"\n[bold cyan]Recently Active Repos[/bold cyan]")
        else:
            console.print()
        active_table = Table(show_header=True, header_style="bold")
        active_table.add_column("Name", style="green")
        active_table.add_column("Language")
        active_table.add_column("Last Push", style="dim")
        if links:
            active_table.add_column("URL", style="dim")
        for r in recent_repos:
            row = [r["name"], r["language"], r["pushed_at_relative"]]
            if links:
                row.append(r.get("html_url", ""))
            active_table.add_row(*row)
        console.print(active_table)

    # Repositories table
    console.print(f"\n[bold cyan]Repositories ({len(repos)} total)[/bold cyan]")
    repo_table = Table(show_header=True, header_style="bold")
    repo_table.add_column("Name", style="green")
    repo_table.add_column("Stars", justify="right")
    repo_table.add_column("Forks", justify="right")
    repo_table.add_column("Language")
    repo_table.add_column("Description", max_width=50)
    if links:
        repo_table.add_column("URL", style="dim")

    display_repos = repos if verbose else [r for r in repos if r["stars"] > 0]
    if not verbose and len(display_repos) < len(repos):
        console.print(f"  [dim](Showing {len(display_repos)} repos with stars. Use -v for all {len(repos)})[/dim]")

    for repo in display_repos[:30]:
        row = [
            repo["name"],
            str(repo["stars"]),
            str(repo["forks"]),
            repo.get("language") or "",
            (repo.get("description") or "")[:50],
        ]
        if links:
            row.append(repo.get("html_url") or "")
        repo_table.add_row(*row)
    console.print(repo_table)

    # Pull Requests to other repos
    merged = prs.get("merged", [])
    open_prs = prs.get("open", [])
    closed = prs.get("closed", [])

    if merged or open_prs or closed:
        console.print(f"\n[bold cyan]Pull Requests to Other Projects[/bold cyan]")

        if merged:
            console.print(f"\n  [bold green]Merged ({len(merged)}):[/bold green]")
            for pr in merged[:10]:
                line = f"    [green]✓[/green] {pr['repo']}: {pr['title']}"
                if links and pr.get('html_url'):
                    line += f"\n      [dim]{pr['html_url']}[/dim]"
                console.print(line)

        if open_prs:
            console.print(f"\n  [bold yellow]Pending ({len(open_prs)}):[/bold yellow]")
            for pr in open_prs[:10]:
                line = f"    [yellow]○[/yellow] {pr['repo']}: {pr['title']}"
                if links and pr.get('html_url'):
                    line += f"\n      [dim]{pr['html_url']}[/dim]"
                console.print(line)

        if closed:
            console.print(f"\n  [bold red]Closed/Rejected ({len(closed)}):[/bold red]")
            for pr in closed[:10]:
                line = f"    [red]✗[/red] {pr['repo']}: {pr['title']}"
                if links and pr.get('html_url'):
                    line += f"\n      [dim]{pr['html_url']}[/dim]"
                console.print(line)

    # Starred repos summary
    starred = data.get("starred", [])
    if starred:
        console.print(f"\n[bold cyan]Starred Repositories ({len(starred)} fetched)[/bold cyan]")
        for repo in starred[:10]:
            desc = (repo.get("description") or "")[:60]
            console.print(f"  {repo['full_name']}: {desc}")

    # Following
    following = data.get("following", [])
    if following:
        names = ", ".join([u["login"] for u in following[:20]])
        console.print(f"\n[bold cyan]Following ({len(following)}):[/bold cyan] {names}")
        if len(following) > 20:
            console.print(f"  [dim]...and {len(following) - 20} more[/dim]")

    # Rate limit info
    rl = get_rate_limit_info()
    console.print(f"\n[dim]Rate limit: {rl['remaining']} remaining | "
                  f"{'Authenticated' if rl['authenticated'] else 'Unauthenticated (set GITHUB_TOKEN for higher limits)'}[/dim]")


async def process_username(username: str, verbose: bool = False, output_json: bool = False, links: bool = False) -> None:
    """Process a single GitHub username."""
    username = extract_username(username)
    if not is_valid_github_username(username):
        console.print(f"[bold red]Invalid GitHub username: '{username}'[/bold red]")
        return
    console.print(f"\n[bold]Fetching data for [green]{username}[/green]...[/bold]")

    # Fetch all GitHub data
    data = fetch_all(username, verbose)
    if data is None:
        console.print(f"[bold red]User '{username}' not found or API error.[/bold red]")
        return

    # Run analysis
    analysis = analyze_profile(data)

    # Try LLM enhancement
    analysis = await enhance_with_llm(analysis, data)

    # Scrape extras (achievements etc.)
    extras = scrape_profile_extras(username)

    # Add extras to data
    data["extras"] = extras

    if output_json:
        output = {
            "data": data,
            "analysis": analysis,
        }
        print(json.dumps(output, indent=2, default=str))
    else:
        display_profile(data, analysis, extras, verbose, links)


def process_file(file_path: str, verbose: bool = False, output_json: bool = False, links: bool = False) -> None:
    """Process each username in a file."""
    try:
        with open(file_path, 'r') as f:
            for line in f:
                username = line.strip()
                if username and not username.startswith("#"):
                    asyncio.run(process_username(username, verbose, output_json, links))
    except FileNotFoundError:
        console.print(f"[bold red]File {file_path} not found.[/bold red]")


def main():
    parser = argparse.ArgumentParser(
        description="gitwho - GitHub OSINT & Profile Intelligence Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "username", nargs="*",
        help="GitHub username(s), URL(s), or file(s) containing usernames"
    )
    parser.add_argument("-w", "--web", action="store_true", help="Launch web interface")
    parser.add_argument("--port", type=int, default=5000, help="Web server port (default: 5000)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show all repos including 0 stars")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    parser.add_argument("-l", "--links", action="store_true", help="Show URLs for PRs and repos")

    if len(sys.argv) == 1:
        rprint(BANNER)
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()

    if args.web:
        from web.app import create_app
        app = create_app()
        console.print(f"\n[bold green]Starting gitwho web server on port {args.port}...[/bold green]")
        console.print(f"[bold]Open http://localhost:{args.port} in your browser[/bold]\n")
        app.run(host="0.0.0.0", port=args.port, debug=os.environ.get("FLASK_DEBUG", "").lower() == "true")
    elif args.username:
        for arg in args.username:
            if is_file(arg):
                process_file(arg, args.verbose, args.json, args.links)
            else:
                asyncio.run(process_username(arg, args.verbose, args.json, args.links))
    else:
        rprint(BANNER)
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
