# gitwho

GitHub OSINT & Profile Intelligence Tool

```
python3 gitwho.py

          _ __          __
   ____ _(_) /__       / /_  ____
  / __ `/ / __/ | /| / / __ \/ __ \
 / /_/ / / /_ | |/ |/ / / / / /_/ /
 \__, /_/\__/ |__/|__/_/ /_/\____/
/____/

GitHub OSINT & Profile Intelligence

usage: gitwho.py [-h] [-w] [--port PORT] [-v] [--json] [username ...]
```

Comprehensive GitHub profile intelligence tool that collects and analyzes public GitHub data. Works as both a CLI tool and a web application.

## Features

- **Profile Intelligence**: Bio, location, company, followers, following, account age
- **Repository Analysis**: All repos sorted by stars with language breakdown
- **Pull Request Tracking**: PRs to other projects — merged, pending, and rejected
- **Interest Profiling**: Rule-based analysis of focus areas from repos, starred repos, and languages
- **Community Metrics**: Follower ratio, PR merge rate, star count, org memberships
- **Achievements**: Scraped from GitHub profile (graceful fallback)
- **Web Interface**: Google-like search page with dark/light mode
- **JSON Output**: Machine-readable output for scripting
- **Optional LLM Enhancement**: Ollama (local) or Hugging Face (cloud) for richer summaries

## Installation

```bash
git clone https://github.com/sho-luv/gitwho.git
cd gitwho
pip install -r requirements.txt
```

## Usage

### CLI

```bash
# Analyze a user
python3 gitwho.py sho-luv

# Analyze from GitHub URL
python3 gitwho.py https://github.com/torvalds

# Multiple users
python3 gitwho.py sho-luv torvalds github

# Show all repos (including 0 stars)
python3 gitwho.py sho-luv -v

# JSON output
python3 gitwho.py sho-luv --json

# From a file of usernames
python3 gitwho.py usernames.txt
```

### Web Interface

```bash
# Launch web server
python3 gitwho.py --web

# Custom port
python3 gitwho.py --web --port 8080
```

Open `http://localhost:5000` in your browser.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GITHUB_TOKEN` | No | GitHub personal access token. Increases rate limit from 60 to 5,000 requests/hour. |
| `OLLAMA_URL` | No | Ollama server URL (e.g., `http://localhost:11434`) for local LLM summaries |
| `HF_API_TOKEN` | No | Hugging Face API token for cloud LLM summaries |
| `GITWHO_CACHE_TTL` | No | Web cache TTL in seconds (default: 3600) |

### Getting a GitHub Token (Free)

1. Go to GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens
2. Generate a new token with **no special permissions** (public data only)
3. `export GITHUB_TOKEN=your_token_here`

## Data Collected

- **Profile**: Name, bio, location, company, blog, social links, account creation date
- **Repositories**: All public repos with stars, forks, language, topics, descriptions
- **Languages**: Aggregated byte-count breakdown across top 20 repos
- **Pull Requests**: To other projects — merged (accepted), open (pending), closed (rejected)
- **Starred Repos**: What the user follows/bookmarks
- **Following/Followers**: Full network lists
- **Organizations**: Org memberships
- **Events**: Recent public activity
- **Achievements**: Scraped from profile page (Arctic Code Vault, Pull Shark, etc.)

## Project Structure

```
gitwho/
├── gitwho.py          # CLI entry point
├── github_api.py      # GitHub API data fetching
├── analyzer.py        # Rule-based profile analysis + LLM plugins
├── scraper.py         # HTML scraping for achievements
├── requirements.txt
├── web/
│   ├── app.py         # Flask web application
│   ├── templates/
│   │   ├── index.html     # Search page
│   │   └── results.html   # Results page
│   └── static/
│       ├── style.css      # Dark/light theme
│       └── script.js      # Theme toggle, UI interactions
└── README.md
```

## Requirements

- Python 3.7+
- requests
- rich
- flask
- beautifulsoup4
- aiohttp (optional, for LLM backends)
