"""
Profile analyzer for gitwho.
Rule-based analysis with optional LLM enhancement (Ollama, Hugging Face).
"""

import os
import asyncio
from typing import Dict, Any, List, Tuple, Optional

# Keyword taxonomy for categorization
CATEGORIES = {
    "Security & Hacking": {
        "keywords": [
            "security", "exploit", "pentest", "penetration", "vuln", "vulnerability",
            "ctf", "capture-the-flag", "burp", "nuclei", "nmap", "metasploit",
            "reverse-engineer", "malware", "forensic", "osint", "recon",
            "hack", "infosec", "appsec", "devsecops", "siem", "soc",
            "red-team", "blue-team", "purple-team", "threat", "phishing",
            "xss", "sqli", "injection", "fuzzing", "scanner", "cve",
            "cryptography", "crypto", "cipher", "steganography",
            "honeypot", "ids", "ips", "firewall", "waf",
        ],
        "languages": ["Python", "Go", "C", "Assembly", "PowerShell", "Shell"],
    },
    "Web Development": {
        "keywords": [
            "react", "vue", "angular", "svelte", "nextjs", "nuxt",
            "frontend", "backend", "fullstack", "full-stack",
            "django", "flask", "fastapi", "express", "nestjs",
            "html", "css", "javascript", "typescript", "tailwind",
            "webpack", "vite", "graphql", "rest-api", "web-app",
            "spa", "pwa", "responsive", "ui", "ux",
        ],
        "languages": ["JavaScript", "TypeScript", "HTML", "CSS", "PHP", "Ruby"],
    },
    "DevOps & Infrastructure": {
        "keywords": [
            "docker", "kubernetes", "k8s", "terraform", "ansible",
            "ci-cd", "cicd", "jenkins", "github-actions", "gitlab-ci",
            "aws", "gcp", "azure", "cloud", "serverless", "lambda",
            "monitoring", "prometheus", "grafana", "elk",
            "helm", "istio", "nginx", "apache", "linux",
            "infrastructure", "iac", "deploy", "pipeline",
        ],
        "languages": ["Shell", "Go", "Python", "HCL", "Dockerfile"],
    },
    "Data Science & ML": {
        "keywords": [
            "machine-learning", "deep-learning", "neural-network",
            "tensorflow", "pytorch", "keras", "scikit",
            "data-science", "data-analysis", "data-engineering",
            "nlp", "natural-language", "computer-vision",
            "pandas", "numpy", "jupyter", "notebook",
            "model", "training", "inference", "llm", "gpt",
            "transformer", "bert", "diffusion", "generative",
            "classification", "regression", "clustering",
        ],
        "languages": ["Python", "Jupyter Notebook", "R", "Julia"],
    },
    "Systems Programming": {
        "keywords": [
            "kernel", "driver", "embedded", "firmware", "rtos",
            "operating-system", "compiler", "interpreter", "parser",
            "memory", "allocator", "garbage-collector",
            "assembly", "low-level", "bare-metal",
            "performance", "optimization", "concurrent",
        ],
        "languages": ["C", "C++", "Rust", "Assembly", "Zig"],
    },
    "Mobile Development": {
        "keywords": [
            "android", "ios", "swift", "kotlin", "flutter", "dart",
            "react-native", "mobile", "app", "xamarin",
            "swiftui", "jetpack-compose", "cordova",
        ],
        "languages": ["Swift", "Kotlin", "Dart", "Objective-C", "Java"],
    },
    "Game Development": {
        "keywords": [
            "game", "unity", "unreal", "godot", "gamedev",
            "opengl", "vulkan", "directx", "shader", "render",
            "physics", "2d", "3d", "sprite", "engine",
        ],
        "languages": ["C#", "C++", "GDScript", "Lua", "HLSL"],
    },
    "Blockchain & Crypto": {
        "keywords": [
            "blockchain", "ethereum", "solidity", "smart-contract",
            "defi", "nft", "web3", "dapp", "token",
            "bitcoin", "cryptocurrency", "wallet", "mining",
        ],
        "languages": ["Solidity", "Rust", "Go", "JavaScript"],
    },
}


def _match_text_to_categories(text: str) -> Dict[str, float]:
    """Score text against category keywords. Returns {category: score}."""
    scores = {}
    text_lower = text.lower()
    for category, config in CATEGORIES.items():
        score = 0
        for keyword in config["keywords"]:
            if keyword in text_lower:
                score += 1
        scores[category] = score
    return scores


def _aggregate_languages(languages: Dict[str, int]) -> List[Tuple[str, float]]:
    """Convert language byte counts to sorted percentages."""
    total = sum(languages.values())
    if total == 0:
        return []
    percentages = [(lang, (count / total) * 100) for lang, count in languages.items()]
    return sorted(percentages, key=lambda x: x[1], reverse=True)


def _score_category_from_repos(repos: List[Dict[str, Any]]) -> Dict[str, float]:
    """Score categories based on repo names, descriptions, topics, and languages."""
    scores = {}
    for repo in repos:
        # Build searchable text from repo metadata
        text_parts = [
            repo.get("name", ""),
            repo.get("description", "") or "",
            " ".join(repo.get("topics", [])),
        ]
        text = " ".join(text_parts)
        star_weight = 1 + (repo.get("stars", 0) * 0.1)  # Stars amplify signal

        cat_scores = _match_text_to_categories(text)
        for cat, score in cat_scores.items():
            scores[cat] = scores.get(cat, 0) + (score * star_weight)

        # Language-based scoring
        repo_lang = repo.get("language", "")
        if repo_lang:
            for cat, config in CATEGORIES.items():
                if repo_lang in config.get("languages", []):
                    scores[cat] = scores.get(cat, 0) + 0.5

    return scores


def _score_category_from_starred(starred: List[Dict[str, Any]]) -> Dict[str, float]:
    """Score categories based on starred repos (what user consumes/follows)."""
    scores = {}
    for repo in starred:
        text_parts = [
            repo.get("full_name", ""),
            repo.get("description", "") or "",
            " ".join(repo.get("topics", [])),
        ]
        text = " ".join(text_parts)
        cat_scores = _match_text_to_categories(text)
        for cat, score in cat_scores.items():
            scores[cat] = scores.get(cat, 0) + (score * 0.5)  # Starred = interest, weighted lower

        repo_lang = repo.get("language", "")
        if repo_lang:
            for cat, config in CATEGORIES.items():
                if repo_lang in config.get("languages", []):
                    scores[cat] = scores.get(cat, 0) + 0.25

    return scores


def _compute_community_metrics(data: Dict[str, Any]) -> Dict[str, Any]:
    """Compute community engagement metrics."""
    profile = data.get("profile", {})
    prs = data.get("pull_requests", {})
    followers = profile.get("followers", 0)
    following = profile.get("following", 0)

    merged_count = len(prs.get("merged", []))
    open_count = len(prs.get("open", []))
    closed_count = len(prs.get("closed", []))
    total_prs = merged_count + open_count + closed_count

    return {
        "followers": followers,
        "following": following,
        "follower_ratio": round(followers / max(following, 1), 2),
        "total_repos": len(data.get("repos", [])),
        "total_stars_received": sum(r.get("stars", 0) for r in data.get("repos", [])),
        "total_prs_to_others": total_prs,
        "pr_merge_rate": round((merged_count / max(total_prs, 1)) * 100, 1),
        "merged_prs": merged_count,
        "open_prs": open_count,
        "closed_prs": closed_count,
        "orgs_count": len(data.get("orgs", [])),
        "starred_count": len(data.get("starred", [])),
    }


def _generate_summary(
    username: str,
    top_categories: List[Tuple[str, float]],
    top_languages: List[Tuple[str, float]],
    metrics: Dict[str, Any],
    profile: Dict[str, Any],
) -> str:
    """Generate a natural-language profile summary from analysis results."""
    parts = []

    # Intro with focus areas
    if top_categories:
        primary = top_categories[0][0]
        if len(top_categories) > 1 and top_categories[1][1] > top_categories[0][1] * 0.4:
            secondary = top_categories[1][0]
            parts.append(f"{username} is primarily focused on {primary} with significant activity in {secondary}.")
        else:
            parts.append(f"{username} is primarily focused on {primary}.")
    else:
        parts.append(f"{username} has a diverse range of projects.")

    # Languages
    if top_languages:
        lang_names = [l[0] for l in top_languages[:3]]
        if len(lang_names) == 1:
            parts.append(f"Their primary language is {lang_names[0]}.")
        else:
            parts.append(f"Their top languages are {', '.join(lang_names[:-1])} and {lang_names[-1]}.")

    # Contributions
    if metrics["total_prs_to_others"] > 0:
        parts.append(
            f"They have contributed to {metrics['total_prs_to_others']} pull requests on other projects "
            f"with a {metrics['pr_merge_rate']}% acceptance rate."
        )

    # Community standing
    if metrics["followers"] > 100:
        parts.append(f"With {metrics['followers']} followers, they have notable community influence.")
    elif metrics["followers"] > 20:
        parts.append(f"They have a growing community presence with {metrics['followers']} followers.")

    # Stars
    if metrics["total_stars_received"] > 100:
        parts.append(f"Their projects have earned {metrics['total_stars_received']} total stars.")

    # Account age
    created = profile.get("created_at", "")
    if created:
        year = created[:4]
        parts.append(f"Active on GitHub since {year}.")

    return " ".join(parts)


def analyze_profile(data: Dict[str, Any]) -> Dict[str, Any]:
    """Run complete rule-based profile analysis."""
    profile = data.get("profile", {})
    repos = data.get("repos", [])
    starred = data.get("starred", [])
    username = profile.get("login", "unknown")

    # Score categories from repos and starred
    repo_scores = _score_category_from_repos(repos)
    starred_scores = _score_category_from_starred(starred)

    # Merge scores
    combined_scores = {}
    all_cats = set(list(repo_scores.keys()) + list(starred_scores.keys()))
    for cat in all_cats:
        combined_scores[cat] = repo_scores.get(cat, 0) + starred_scores.get(cat, 0)

    # Top categories (filter out zero scores)
    top_categories = sorted(
        [(cat, score) for cat, score in combined_scores.items() if score > 0],
        key=lambda x: x[1],
        reverse=True
    )

    # Language breakdown
    languages = data.get("languages", {})
    top_languages = _aggregate_languages(languages)

    # Community metrics
    metrics = _compute_community_metrics(data)

    # Generate summary
    summary = _generate_summary(username, top_categories, top_languages, metrics, profile)

    return {
        "summary": summary,
        "focus_areas": [{"category": cat, "score": round(score, 1)} for cat, score in top_categories[:6]],
        "languages": [{"language": lang, "percentage": round(pct, 1)} for lang, pct in top_languages],
        "metrics": metrics,
    }


async def _enhance_with_ollama(analysis: Dict[str, Any], data: Dict[str, Any]) -> Optional[str]:
    """Enhance analysis with local Ollama LLM."""
    ollama_url = os.environ.get("OLLAMA_URL", "").rstrip("/")
    if not ollama_url:
        return None

    try:
        import aiohttp
        profile = data.get("profile", {})
        repos = data.get("repos", [])[:10]
        repo_names = [r["name"] for r in repos]

        prompt = (
            f"Analyze this GitHub user profile and provide a concise intelligence summary:\n"
            f"Username: {profile.get('login')}\n"
            f"Bio: {profile.get('bio', 'N/A')}\n"
            f"Location: {profile.get('location', 'N/A')}\n"
            f"Top repos: {', '.join(repo_names)}\n"
            f"Focus areas: {', '.join(a['category'] for a in analysis.get('focus_areas', []))}\n"
            f"Rule-based summary: {analysis.get('summary', '')}\n\n"
            f"Provide a 2-3 sentence enhanced profile summary."
        )

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{ollama_url}/api/generate",
                json={"model": "llama3.2", "prompt": prompt, "stream": False},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result.get("response", "")
    except Exception:
        pass
    return None


async def _enhance_with_huggingface(analysis: Dict[str, Any], data: Dict[str, Any]) -> Optional[str]:
    """Enhance analysis with Hugging Face Inference API."""
    hf_token = os.environ.get("HF_API_TOKEN")
    if not hf_token:
        return None

    try:
        import aiohttp
        profile = data.get("profile", {})
        repos = data.get("repos", [])[:10]
        repo_names = [r["name"] for r in repos]

        prompt = (
            f"Analyze this GitHub user profile:\n"
            f"Username: {profile.get('login')}\n"
            f"Bio: {profile.get('bio', 'N/A')}\n"
            f"Top repos: {', '.join(repo_names)}\n"
            f"Focus areas: {', '.join(a['category'] for a in analysis.get('focus_areas', []))}\n"
            f"Summary: {analysis.get('summary', '')}\n\n"
            f"Provide an enhanced 2-3 sentence profile analysis."
        )

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2",
                headers={"Authorization": f"Bearer {hf_token}"},
                json={"inputs": prompt, "parameters": {"max_new_tokens": 200}},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if isinstance(result, list) and result:
                        return result[0].get("generated_text", "")
    except Exception:
        pass
    return None


async def enhance_with_llm(analysis: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    """Try to enhance analysis with available LLM backends. Returns updated analysis."""
    # Try Ollama first (local), then HuggingFace (cloud)
    enhanced = await _enhance_with_ollama(analysis, data)
    if enhanced:
        analysis["llm_summary"] = enhanced
        analysis["llm_source"] = "ollama"
        return analysis

    enhanced = await _enhance_with_huggingface(analysis, data)
    if enhanced:
        analysis["llm_summary"] = enhanced
        analysis["llm_source"] = "huggingface"
        return analysis

    return analysis
