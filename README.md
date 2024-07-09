# Git Who


```
python git_who.py                                   

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

usage: git_who.py [-h] [-v] username [username ...]

Process GitHub usernames or files containing usernames and summarize their repositories.

positional arguments:
  username       GitHub Usernames or Organization. Or files with usernames

options:
  -h, --help     show this help message and exit
  -v, --verbose  Show all repositories, even those with 0 stars
```

This Python script fetches and summarizes information about GitHub repositories for a given user or organization. It leverages the GitHub API and OpenAI to provide detailed insights and summaries of the repositories.

### Features

- Fetches all repositories for a given GitHub username or organization.
- Sorts repositories by star count.
- Summarizes the top repositories and their star counts.
- Uses OpenAI to provide a detailed summary of recent work done on the repositories.

### Requirements
- Python 3.7+
- requests library
- argparse library
- rich library for formatted terminal output
- asyncio library for asynchronous tasks
- typing library for type hints
- OpenAI API access

### Installation
Clone the repository:

```bash
git clone https://github.com/sho-luv/git_who.git
cd git_who
```

### Install the required libraries:

```bash
pip install requests rich
```

Make sure you have access to the OpenAI API and the ask_openai function is properly set up.

### Usage
To use the script, you can provide one or more GitHub usernames or organizations as arguments. You can also provide a file containing usernames.

Examples
Fetch and summarize repositories for a single user:

```bash
python git_who.py octocat
```

Fetch and summarize repositories for multiple users:

```bash
python git_who.py octocat github
```

Fetch and summarize repositories listed in a file:

```bash
python git_who.py usernames.txt
```

Enable verbose mode to show all repositories, even those with 0 stars:

```bash
python git_who.py octocat -v
```
### Sample Output
```yaml
GitHub user: octocat
Total stars: 12345
Most starred repo: Hello-World with 1234 stars

Recent repositories:
- Hello-World: 1234 stars
- Spoon-Knife: 234 stars
- Test: 123 stars
- OctoRepo: 45 stars
- AnotherRepo: 23 stars

AI Summary:
OpenAI generated summary of recent work on the repositories...
```
