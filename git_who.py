import argparse
import requests
import os
import sys
import asyncio
from rich import print
from typing import List, Dict, Any, Optional
from ask_openai import ask_openai

# Banner for the program
banner = """
             .                                                                         .   
           .o8                                                                       .o8   
 .oooo.o .o888oo  .oooo.   oooo d8b       .ooooo oo oooo  oooo   .ooooo.   .oooo.o .o888oo 
d88(  "8   888   `P  )88b  `888""8P      d88' `888  `888  `888  d88' `88b d88(  "8   888   
`"Y88b.    888    .oP"888   888          888   888   888   888  888ooo888 `"Y88b.    888   
o.  )88b   888 . d8(  888   888          888   888   888   888  888    .o o.  )88b   888 . 
8""888P'   "888" `Y888""8o d888b         `V8bod888   `V88V"V8P' `Y8bod8P' 8""888P'   "888" 
                                               888.                                        
                                               8P'                                         
                                               "                                           
"""

# GitHub repository fetching functions
def get_user_or_org_type(username: str) -> Optional[str]:
    """Determines if the username corresponds to a user or an organization."""
    url = f'https://api.github.com/users/{username}'
    response = requests.get(url)
    user_data: Dict[str, Any] = response.json()
    
    if 'message' in user_data and 'API rate limit exceeded' in user_data['message']:
        print("[bold red]API rate limit exceeded. Please try again later or authenticate to increase your rate limit.[/bold red]")
        return None
    
    if 'type' in user_data:
        return user_data['type']  # Can be 'User' or 'Organization'
    
    return None

def get_all_repos(username: str, is_org: bool = False) -> List[Dict[str, Any]]:
    """Fetches all repositories for a given user or organization, sorted by star count."""
    repos: List[Dict[str, Any]] = []
    page: int = 1
    base_url: str = "https://api.github.com/orgs/" if is_org else "https://api.github.com/users/"
    url: str = f"{base_url}{username}/repos"

    while True:
        response = requests.get(f"{url}?page={page}&per_page=100")
        page_data: List[Dict[str, Any]] = response.json()

        if response.status_code != 200 or not page_data:
            break

        repos.extend(page_data)
        page += 1

    if isinstance(repos, list):
        return sorted(repos, key=lambda x: x['stargazers_count'], reverse=True)
    else:
        print(f"{username} not found or error fetching repos.")
        return []

def summarize_repos(repos: List[Dict[str, Any]], username: str) -> str:
    """Summarizes the repository information for a user or organization."""
    if not repos:
        return f"No repositories found for {username}."

    most_starred_repo = repos[0]
    total_stars = sum(repo['stargazers_count'] for repo in repos)
    
    repo_list = "\n".join([f"- {repo['name']}: {repo['stargazers_count']} stars" for repo in repos[:5]])

    summary = f"""
GitHub user: [bold green]{username}[/bold green]
Total stars: [bold white]{total_stars}[/bold white]
Most starred repo: [bold white]{most_starred_repo['name']}[/bold white] with {most_starred_repo['stargazers_count']} stars

Recent repositories:
{repo_list}
"""
    return summary

async def ask_openai_summary(repos: List[Dict[str, Any]]) -> str:
    """Ask OpenAI to summarize the latest repositories."""
    repo_names = [repo['name'] for repo in repos[:5]]
    question = f"Summarize the recent work done on these GitHub repositories: {', '.join(repo_names)}."
    context = "Consider factors like repository updates, commits, and activity."
    answer = await ask_openai(question, context)
    return answer

async def process_username(username: str, verbose: bool = False) -> None:
    """Processes a GitHub username or organization."""
    user_type = get_user_or_org_type(username)
    if user_type is None:
        print(f"{username} does not exist")
        return
    
    is_org = user_type == 'Organization'
    repos = get_all_repos(username, is_org)
    summary = summarize_repos(repos, username)
    print(summary)
    
    ai_summary = await ask_openai_summary(repos)
    print(f"\n[bold green]AI Summary:[/bold green]\n{ai_summary}")

def process_file(file_path: str, verbose: bool = False) -> None:
    """Processes each username in the given file."""
    try:
        with open(file_path, 'r') as file:
            for line in file:
                username = line.strip()
                if username:
                    asyncio.run(process_username(username, verbose))
    except FileNotFoundError:
        print(f"File {file_path} not found.")

def is_file(path):
    """Check if a path is an existing file."""
    return os.path.isfile(path)

# Initialize parser
parser = argparse.ArgumentParser(description='Process GitHub usernames or files containing usernames and summarize their repositories.')
parser.add_argument('username', nargs='+', help='GitHub Usernames or Organization. Or files with usernames')
parser.add_argument('-v','--verbose', action='store_true', help='Show all repositories, even those with 0 stars')

if len(sys.argv) == 1:
    print(f"{banner}")
    parser.print_help()
    sys.exit(1)

# Parse arguments
args = parser.parse_args()

for arg in args.username:
    if is_file(arg):
        process_file(arg, args.verbose)
    else:
        asyncio.run(process_username(arg, args.verbose))
