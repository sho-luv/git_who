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

def get_user_activity(username: str) -> Dict[str, Any]:
    """Fetches comprehensive user activity including events and interactions."""
    # Get public events
    events_url = f"https://api.github.com/users/{username}/events/public?per_page=30"
    events_response = requests.get(events_url)
    events_data = events_response.json()
    
    if isinstance(events_data, dict) and 'message' in events_data and 'API rate limit exceeded' in events_data['message']:
        print("[bold red]API rate limit exceeded. Please try again later or authenticate to increase your rate limit.[/bold red]")
        return {}
    
    # Analyze event types and patterns
    event_types = {}
    recent_repos = set()
    languages_engaged = set()
    
    for event in events_data[:20] if isinstance(events_data, list) else []:
        event_type = event.get('type', '')
        event_types[event_type] = event_types.get(event_type, 0) + 1
        
        # Track repositories they're active in
        if 'repo' in event:
            recent_repos.add(event['repo']['name'])
        
        # Extract language info from push events
        if event_type == 'PushEvent' and 'payload' in event:
            # We'll analyze this further in enhanced starred repos
            pass
    
    return {
        'event_types': event_types,
        'recent_repos': list(recent_repos)[:10],
        'total_events': len(events_data) if isinstance(events_data, list) else 0
    }

def get_user_behavior(username: str) -> str:
    """Fetches the last 10 starred repositories and followed users for a given user."""
    starred_repos_url = f"https://api.github.com/users/{username}/starred?per_page=10"
    following_url = f"https://api.github.com/users/{username}/following?per_page=10"
    
    starred_repos_response = requests.get(starred_repos_url)
    following_response = requests.get(following_url)
    
    starred_repos_data: List[Dict[str, Any]] = starred_repos_response.json()
    following_data: List[Dict[str, Any]] = following_response.json()
    
    if 'message' in starred_repos_data and 'API rate limit exceeded' in starred_repos_data['message']:
        print("[bold red]API rate limit exceeded. Please try again later or authenticate to increase your rate limit.[/bold red]")
        return ""
    
    following_list = "\n".join([f"- {user['login']}" for user in following_data])
    
    behavior_summary = f"""
Following:
{following_list}
"""
    return behavior_summary

def get_social_network(username: str) -> Dict[str, Any]:
    """Fetches comprehensive social network information."""
    followers_url = f"https://api.github.com/users/{username}/followers?per_page=30"
    following_url = f"https://api.github.com/users/{username}/following?per_page=100"
    orgs_url = f"https://api.github.com/users/{username}/orgs"
    
    followers_response = requests.get(followers_url)
    following_response = requests.get(following_url)
    orgs_response = requests.get(orgs_url)
    
    followers_data = followers_response.json()
    following_data = following_response.json()
    orgs_data = orgs_response.json()
    
    if isinstance(followers_data, dict) and 'message' in followers_data and 'API rate limit exceeded' in followers_data['message']:
        print("[bold red]API rate limit exceeded. Please try again later or authenticate to increase your rate limit.[/bold red]")
        return {}
    
    # Analyze following patterns
    following_types = {}
    notable_following = []
    
    for user in following_data if isinstance(following_data, list) else []:
        # Get basic info about who they follow
        user_info = {
            'login': user['login'],
            'type': user.get('type', 'User')
        }
        
        if user.get('type') == 'Organization':
            following_types['orgs'] = following_types.get('orgs', 0) + 1
        else:
            following_types['users'] = following_types.get('users', 0) + 1
        
        # Mark notable users (simplified - could be enhanced with follower counts)
        notable_following.append(user_info)
    
    return {
        'followers_count': len(followers_data) if isinstance(followers_data, list) else 0,
        'following_count': len(following_data) if isinstance(following_data, list) else 0,
        'organizations': orgs_data if isinstance(orgs_data, list) else [],
        'following_types': following_types,
        'notable_following': notable_following[:20]  # Top 20
    }

def get_content_creation_patterns(username: str) -> Dict[str, Any]:
    """Analyzes user's content creation patterns including gists and repository activity."""
    gists_url = f"https://api.github.com/users/{username}/gists?per_page=30"
    events_url = f"https://api.github.com/users/{username}/events/public?per_page=100"
    
    gists_response = requests.get(gists_url)
    events_response = requests.get(events_url)
    
    gists_data = gists_response.json()
    events_data = events_response.json()
    
    if isinstance(gists_data, dict) and 'message' in gists_data and 'API rate limit exceeded' in gists_data['message']:
        print("[bold red]API rate limit exceeded. Please try again later or authenticate to increase your rate limit.[/bold red]")
        return {}
    
    # Analyze gists
    gist_languages = {}
    public_gists = 0
    recent_gists = []
    
    for gist in gists_data if isinstance(gists_data, list) else []:
        if gist.get('public'):
            public_gists += 1
        
        # Analyze gist languages
        for filename, file_info in gist.get('files', {}).items():
            language = file_info.get('language')
            if language:
                gist_languages[language] = gist_languages.get(language, 0) + 1
        
        recent_gists.append({
            'description': gist.get('description', 'No description'),
            'public': gist.get('public', False),
            'created_at': gist.get('created_at'),
            'files_count': len(gist.get('files', {}))
        })
    
    # Analyze creation patterns from events
    creation_events = {}
    fork_events = []
    
    for event in events_data if isinstance(events_data, list) else []:
        event_type = event.get('type')
        
        if event_type == 'CreateEvent':
            ref_type = event.get('payload', {}).get('ref_type', 'unknown')
            creation_events[ref_type] = creation_events.get(ref_type, 0) + 1
        
        elif event_type == 'ForkEvent':
            fork_info = {
                'repo': event.get('repo', {}).get('name'),
                'created_at': event.get('created_at')
            }
            fork_events.append(fork_info)
    
    return {
        'total_gists': len(gists_data) if isinstance(gists_data, list) else 0,
        'public_gists': public_gists,
        'gist_languages': gist_languages,
        'recent_gists': recent_gists[:10],
        'creation_events': creation_events,
        'recent_forks': fork_events[:10]
    }

def get_enhanced_starred_repos(username: str) -> Dict[str, Any]:
    """Fetches and analyzes starred repositories with detailed insights."""
    starred_repos_url = f"https://api.github.com/users/{username}/starred?sort=created&direction=desc&per_page=50"
    starred_repos_response = requests.get(starred_repos_url)
    starred_repos_data = starred_repos_response.json()
    
    if isinstance(starred_repos_data, dict) and 'message' in starred_repos_data and 'API rate limit exceeded' in starred_repos_data['message']:
        print("[bold red]API rate limit exceeded. Please try again later or authenticate to increase your rate limit.[/bold red]")
        return {}
    
    if not isinstance(starred_repos_data, list):
        return {}
    
    # Analyze patterns in starred repositories
    languages = {}
    topics = {}
    repo_types = {'original': 0, 'fork': 0}
    recent_stars = starred_repos_data[:10]  # Most recent 10
    
    for repo in starred_repos_data:
        # Language analysis
        if repo.get('language'):
            lang = repo['language']
            languages[lang] = languages.get(lang, 0) + 1
        
        # Topics/tags analysis
        if repo.get('topics'):
            for topic in repo['topics']:
                topics[topic] = topics.get(topic, 0) + 1
        
        # Repository type
        if repo.get('fork'):
            repo_types['fork'] += 1
        else:
            repo_types['original'] += 1
    
    # Get top languages and topics
    top_languages = sorted(languages.items(), key=lambda x: x[1], reverse=True)[:5]
    top_topics = sorted(topics.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return {
        'recent_stars': recent_stars,
        'total_starred': len(starred_repos_data),
        'top_languages': top_languages,
        'top_topics': top_topics,
        'repo_types': repo_types
    }

def summarize_starred_repos(starred_repos: List[Dict[str, Any]]) -> str:
    """Summarizes the information for starred repositories."""
    if not starred_repos:
        return "No starred repositories found."

    repo_list = "\n".join([f"- {repo['full_name']}: {repo['stargazers_count']} stars - {repo['description']}" for repo in starred_repos])

    summary = f"""
Starred Repositories:
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

async def ask_openai_profile_analysis(user_data: Dict[str, Any], username: str) -> str:
    """Generate comprehensive behavioral profile using AI analysis."""
    
    # Prepare context with all collected data
    context = f"""
GitHub User Profile Data for {username}:

Repository Activity:
- Total repositories: {len(user_data.get('repos', []))}
- Most starred repo: {user_data.get('most_starred_repo', 'None')}

Activity Patterns:
- Recent event types: {user_data.get('activity', {}).get('event_types', {})}
- Active repositories: {user_data.get('activity', {}).get('recent_repos', [])}

Interest Analysis (from starred repos):
- Total starred: {user_data.get('starred_analysis', {}).get('total_starred', 0)}
- Top languages: {user_data.get('starred_analysis', {}).get('top_languages', [])}
- Top topics: {user_data.get('starred_analysis', {}).get('top_topics', [])}

Social Network:
- Following: {user_data.get('social', {}).get('following_count', 0)} users/orgs
- Followers: {user_data.get('social', {}).get('followers_count', 0)}
- Organizations: {len(user_data.get('social', {}).get('organizations', []))}

Content Creation:
- Total gists: {user_data.get('content', {}).get('total_gists', 0)}
- Creation patterns: {user_data.get('content', {}).get('creation_events', {})}
- Recent forks: {len(user_data.get('content', {}).get('recent_forks', []))}
"""

    question = f"""Based on this GitHub activity data, provide a comprehensive behavioral profile for {username}. 

Analyze and describe:
1. Their primary technical interests and expertise areas
2. Learning patterns and exploration behavior  
3. Social/professional engagement style
4. Content creation and sharing preferences
5. Overall developer personality and work style
6. Potential career focus or specialization areas

Focus on insights that reveal WHO this person is as a developer and what drives their GitHub activity."""

    return await ask_openai(question, context)

async def process_username(username: str, verbose: bool = False) -> None:
    """Processes a GitHub username or organization with comprehensive profiling."""
    user_type = get_user_or_org_type(username)
    if user_type is None:
        print(f"{username} does not exist")
        return
    
    print(f"\n[bold blue]═══ COMPREHENSIVE PROFILE FOR {username} ═══[/bold blue]\n")
    
    is_org = user_type == 'Organization'
    repos = get_all_repos(username, is_org)
    summary = summarize_repos(repos, username)
    print(summary)
    
    # Collect all profile data
    print("[dim]Gathering comprehensive profile data...[/dim]")
    
    activity_data = get_user_activity(username)
    social_data = get_social_network(username)
    starred_data = get_enhanced_starred_repos(username)
    content_data = get_content_creation_patterns(username)
    
    # Display enhanced profiling sections
    if activity_data:
        print(f"\n[bold green]🎯 ACTIVITY PATTERNS:[/bold green]")
        print(f"Recent Activity Types: {dict(list(activity_data.get('event_types', {}).items())[:5])}")
        print(f"Active in {len(activity_data.get('recent_repos', []))} repositories recently")
        print(f"Total events tracked: {activity_data.get('total_events', 0)}")
    
    if social_data:
        print(f"\n[bold green]🌐 SOCIAL NETWORK:[/bold green]")
        print(f"Following: {social_data.get('following_count', 0)} | Followers: {social_data.get('followers_count', 0)}")
        print(f"Organizations: {len(social_data.get('organizations', []))}")
        if social_data.get('following_types'):
            print(f"Following breakdown: {social_data['following_types']}")
    
    if starred_data:
        print(f"\n[bold green]⭐ INTEREST ANALYSIS:[/bold green]")
        print(f"Total starred: {starred_data.get('total_starred', 0)}")
        if starred_data.get('top_languages'):
            lang_list = ", ".join([f"{lang}({count})" for lang, count in starred_data['top_languages']])
            print(f"Top languages: {lang_list}")
        if starred_data.get('top_topics'):
            topic_list = ", ".join([f"{topic}({count})" for topic, count in starred_data['top_topics'][:5]])
            print(f"Top topics: {topic_list}")
    
    if content_data:
        print(f"\n[bold green]🛠️  CONTENT CREATION:[/bold green]")
        print(f"Total gists: {content_data.get('total_gists', 0)} (Public: {content_data.get('public_gists', 0)})")
        if content_data.get('creation_events'):
            print(f"Creation activity: {content_data['creation_events']}")
        print(f"Recent forks: {len(content_data.get('recent_forks', []))}")
    
    # Enhanced AI Profile Analysis
    user_profile_data = {
        'repos': repos,
        'most_starred_repo': repos[0]['name'] if repos else 'None',
        'activity': activity_data,
        'social': social_data,
        'starred_analysis': starred_data,
        'content': content_data
    }
    
    ai_profile = await ask_openai_profile_analysis(user_profile_data, username)
    print(f"\n[bold green]🤖 AI BEHAVIORAL PROFILE:[/bold green]\n{ai_profile}")
    
    # Legacy sections (keeping for compatibility)
    behavior_summary = get_user_behavior(username)
    print(f"\n[bold green]👥 SOCIAL CONNECTIONS:[/bold green]\n{behavior_summary}")

    starred_repos_url = f"https://api.github.com/users/{username}/starred?per_page=10"
    starred_repos_response = requests.get(starred_repos_url)
    starred_repos_data: List[Dict[str, Any]] = starred_repos_response.json()
    starred_summary = summarize_starred_repos(starred_repos_data)
    print(f"\n[bold green]📚 RECENT STARRED REPOS:[/bold green]\n{starred_summary}")

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
