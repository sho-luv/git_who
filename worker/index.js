/**
 * gitwho API - Cloudflare Worker
 * GitHub OSINT & Profile Intelligence backend
 */

const API_BASE = "https://api.github.com";

// CORS headers for cross-origin requests from sholuv.net
const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

// ========== Category taxonomy ==========
const CATEGORIES = {
  "Security & Hacking": {
    keywords: [
      "security", "exploit", "pentest", "penetration", "vuln", "vulnerability",
      "ctf", "capture-the-flag", "burp", "nuclei", "nmap", "metasploit",
      "reverse-engineer", "malware", "forensic", "osint", "recon",
      "hack", "infosec", "appsec", "devsecops", "siem", "soc",
      "red-team", "blue-team", "purple-team", "threat", "phishing",
      "xss", "sqli", "injection", "fuzzing", "scanner", "cve",
      "cryptography", "crypto", "cipher", "steganography",
      "honeypot", "ids", "ips", "firewall", "waf",
    ],
    languages: ["Python", "Go", "C", "Assembly", "PowerShell", "Shell"],
  },
  "Web Development": {
    keywords: [
      "react", "vue", "angular", "svelte", "nextjs", "nuxt",
      "frontend", "backend", "fullstack", "full-stack",
      "django", "flask", "fastapi", "express", "nestjs",
      "html", "css", "javascript", "typescript", "tailwind",
      "webpack", "vite", "graphql", "rest-api", "web-app",
      "spa", "pwa", "responsive", "ui", "ux",
    ],
    languages: ["JavaScript", "TypeScript", "HTML", "CSS", "PHP", "Ruby"],
  },
  "DevOps & Infrastructure": {
    keywords: [
      "docker", "kubernetes", "k8s", "terraform", "ansible",
      "ci-cd", "cicd", "jenkins", "github-actions", "gitlab-ci",
      "aws", "gcp", "azure", "cloud", "serverless", "lambda",
      "monitoring", "prometheus", "grafana", "elk",
      "helm", "istio", "nginx", "apache", "linux",
      "infrastructure", "iac", "deploy", "pipeline",
    ],
    languages: ["Shell", "Go", "Python", "HCL", "Dockerfile"],
  },
  "Data Science & ML": {
    keywords: [
      "machine-learning", "deep-learning", "neural-network",
      "tensorflow", "pytorch", "keras", "scikit",
      "data-science", "data-analysis", "data-engineering",
      "nlp", "natural-language", "computer-vision",
      "pandas", "numpy", "jupyter", "notebook",
      "model", "training", "inference", "llm", "gpt",
      "transformer", "bert", "diffusion", "generative",
      "classification", "regression", "clustering",
    ],
    languages: ["Python", "Jupyter Notebook", "R", "Julia"],
  },
  "Systems Programming": {
    keywords: [
      "kernel", "driver", "embedded", "firmware", "rtos",
      "operating-system", "compiler", "interpreter", "parser",
      "memory", "allocator", "garbage-collector",
      "assembly", "low-level", "bare-metal",
      "performance", "optimization", "concurrent",
    ],
    languages: ["C", "C++", "Rust", "Assembly", "Zig"],
  },
  "Mobile Development": {
    keywords: [
      "android", "ios", "swift", "kotlin", "flutter", "dart",
      "react-native", "mobile", "app", "xamarin",
      "swiftui", "jetpack-compose", "cordova",
    ],
    languages: ["Swift", "Kotlin", "Dart", "Objective-C", "Java"],
  },
  "Game Development": {
    keywords: [
      "game", "unity", "unreal", "godot", "gamedev",
      "opengl", "vulkan", "directx", "shader", "render",
      "physics", "2d", "3d", "sprite", "engine",
    ],
    languages: ["C#", "C++", "GDScript", "Lua", "HLSL"],
  },
  "Blockchain & Crypto": {
    keywords: [
      "blockchain", "ethereum", "solidity", "smart-contract",
      "defi", "nft", "web3", "dapp", "token",
      "bitcoin", "cryptocurrency", "wallet", "mining",
    ],
    languages: ["Solidity", "Rust", "Go", "JavaScript"],
  },
};

// ========== GitHub API helpers ==========

function getHeaders(env) {
  const headers = {
    Accept: "application/vnd.github.v3+json",
    "User-Agent": "gitwho",
  };
  if (env.GITHUB_TOKEN) {
    headers.Authorization = `token ${env.GITHUB_TOKEN}`;
  }
  return headers;
}

async function apiFetch(url, env, params = {}) {
  const u = new URL(url);
  for (const [k, v] of Object.entries(params)) u.searchParams.set(k, v);
  const resp = await fetch(u.toString(), { headers: getHeaders(env) });
  return resp;
}

function parseLastPage(linkHeader) {
  if (!linkHeader) return null;
  const match = linkHeader.match(/<[^>]*[?&]page=(\d+)[^>]*>;\s*rel="last"/);
  return match ? parseInt(match[1], 10) : null;
}

async function paginatedFetch(url, env, perPage = 100, maxPages = 5) {
  // Fetch page 1 to get data + total page count from Link header
  const firstResp = await apiFetch(url, env, { page: 1, per_page: perPage });
  if (!firstResp.ok) return [];
  const firstData = await firstResp.json();
  if (!Array.isArray(firstData) || firstData.length === 0) return [];
  if (firstData.length < perPage) return firstData;

  // Parse Link header to find last page, then fetch remaining pages in parallel
  const lastPage = Math.min(parseLastPage(firstResp.headers.get("link")) || 1, maxPages);
  if (lastPage <= 1) return firstData;

  const remaining = await Promise.all(
    Array.from({ length: lastPage - 1 }, (_, i) =>
      apiFetch(url, env, { page: i + 2, per_page: perPage })
        .then((r) => (r.ok ? r.json() : []))
        .then((d) => (Array.isArray(d) ? d : []))
    )
  );

  return [firstData, ...remaining].flat();
}

// ========== Data fetching ==========

async function fetchUserProfile(username, env) {
  const resp = await apiFetch(`${API_BASE}/users/${username}`, env);
  if (!resp.ok) return null;
  const d = await resp.json();
  if (d.message) return null;
  return {
    login: d.login, name: d.name, type: d.type,
    avatar_url: d.avatar_url, bio: d.bio, location: d.location,
    company: d.company, blog: d.blog, twitter_username: d.twitter_username,
    email: d.email, public_repos: d.public_repos || 0,
    public_gists: d.public_gists || 0, followers: d.followers || 0,
    following: d.following || 0, created_at: d.created_at,
    updated_at: d.updated_at, hireable: d.hireable,
  };
}

async function fetchRepos(username, userType, env) {
  const base = userType === "Organization" ? "orgs" : "users";
  const repos = await paginatedFetch(`${API_BASE}/${base}/${username}/repos`, env, 100, 10);
  const processed = repos.map((r) => ({
    name: r.name, full_name: r.full_name, description: r.description,
    language: r.language, stars: r.stargazers_count || 0,
    forks: r.forks_count || 0, watchers: r.watchers_count || 0,
    open_issues: r.open_issues_count || 0, created_at: r.created_at,
    updated_at: r.updated_at, pushed_at: r.pushed_at,
    html_url: r.html_url, fork: r.fork || false,
    archived: r.archived || false, topics: r.topics || [],
    size: r.size || 0, license: r.license ? r.license.spdx_id : null,
  }));
  return processed.sort((a, b) => b.stars - a.stars);
}

async function fetchRepoLanguages(owner, repo, env) {
  const resp = await apiFetch(`${API_BASE}/repos/${owner}/${repo}/languages`, env);
  if (!resp.ok) return {};
  return await resp.json();
}

async function fetchAllLanguages(username, repos, env, maxRepos = 20) {
  // Filter eligible repos first
  const eligible = [];
  for (const repo of repos) {
    if (eligible.length >= maxRepos) break;
    if (repo.fork) {
      if (repo.pushed_at && repo.created_at && repo.pushed_at.slice(0, 10) <= repo.created_at.slice(0, 10)) continue;
    }
    eligible.push(repo);
  }

  // Fetch all languages in parallel
  const results = await Promise.all(
    eligible.map((repo) => fetchRepoLanguages(username, repo.name, env))
  );

  const aggregated = {};
  for (const langs of results) {
    for (const [lang, bytes] of Object.entries(langs)) {
      aggregated[lang] = (aggregated[lang] || 0) + bytes;
    }
  }
  return aggregated;
}

async function fetchStarred(username, env) {
  const starred = await paginatedFetch(`${API_BASE}/users/${username}/starred`, env, 100, 2);
  return starred.map((r) => ({
    full_name: r.full_name, description: r.description,
    language: r.language, stars: r.stargazers_count || 0,
    html_url: r.html_url, topics: r.topics || [],
  }));
}

async function fetchFollowing(username, env) {
  const list = await paginatedFetch(`${API_BASE}/users/${username}/following`, env, 100, 3);
  return list.map((u) => ({ login: u.login, avatar_url: u.avatar_url, html_url: u.html_url, type: u.type }));
}

async function fetchFollowers(username, env) {
  const list = await paginatedFetch(`${API_BASE}/users/${username}/followers`, env, 100, 3);
  return list.map((u) => ({ login: u.login, avatar_url: u.avatar_url, html_url: u.html_url, type: u.type }));
}

async function fetchOrgs(username, env) {
  const orgs = await paginatedFetch(`${API_BASE}/users/${username}/orgs`, env, 100, 2);
  return orgs.map((o) => ({
    login: o.login, avatar_url: o.avatar_url,
    description: o.description, html_url: `https://github.com/${o.login}`,
  }));
}

async function fetchEvents(username, env) {
  const events = await paginatedFetch(`${API_BASE}/users/${username}/events/public`, env, 100, 3);
  return events.map((e) => ({
    type: e.type, repo: e.repo ? e.repo.name : null,
    created_at: e.created_at, payload_action: e.payload ? e.payload.action : null,
  }));
}

async function searchPRs(query, env) {
  // Fetch page 1, then remaining pages in parallel
  const firstResp = await apiFetch(`${API_BASE}/search/issues`, env, { q: query, per_page: 100, page: 1 });
  if (!firstResp.ok) return [];
  const firstData = await firstResp.json();
  const firstItems = firstData.items || [];
  if (firstItems.length === 0 || firstItems.length < 100) return firstItems;

  const totalCount = Math.min(firstData.total_count || 0, 300);
  const totalPages = Math.min(Math.ceil(totalCount / 100), 3);
  if (totalPages <= 1) return firstItems;

  const remaining = await Promise.all(
    Array.from({ length: totalPages - 1 }, (_, i) =>
      apiFetch(`${API_BASE}/search/issues`, env, { q: query, per_page: 100, page: i + 2 })
        .then((r) => (r.ok ? r.json() : { items: [] }))
        .then((d) => d.items || [])
    )
  );

  return [firstItems, ...remaining].flat();
}

async function fetchPullRequests(username, env) {
  function processPRs(items) {
    return items
      .map((pr) => {
        const repoUrl = pr.repository_url || "";
        const parts = repoUrl.split("/");
        const repoOwner = parts[parts.length - 2] || "";
        const repoFull = parts.slice(-2).join("/");
        if (repoOwner.toLowerCase() === username.toLowerCase()) return null;
        return {
          title: pr.title, repo: repoFull, html_url: pr.html_url,
          state: pr.state, created_at: pr.created_at, closed_at: pr.closed_at,
        };
      })
      .filter(Boolean);
  }

  const [merged, open, closed] = await Promise.all([
    searchPRs(`author:${username} type:pr is:merged`, env),
    searchPRs(`author:${username} type:pr is:open`, env),
    searchPRs(`author:${username} type:pr is:unmerged is:closed`, env),
  ]);

  return {
    merged: processPRs(merged),
    open: processPRs(open),
    closed: processPRs(closed),
  };
}

// ========== Helpers ==========

function relativeTime(isoStr) {
  try {
    const dt = new Date(isoStr);
    const now = Date.now();
    const seconds = Math.floor((now - dt.getTime()) / 1000);
    if (seconds < 60) return "just now";
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes} minute${minutes !== 1 ? "s" : ""} ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours} hour${hours !== 1 ? "s" : ""} ago`;
    const days = Math.floor(hours / 24);
    if (days < 30) return `${days} day${days !== 1 ? "s" : ""} ago`;
    const months = Math.floor(days / 30);
    if (months < 12) return `${months} month${months !== 1 ? "s" : ""} ago`;
    const years = Math.floor(days / 365);
    return `${years} year${years !== 1 ? "s" : ""} ago`;
  } catch {
    return "unknown";
  }
}

// ========== Analysis ==========

function matchTextToCategories(text) {
  const scores = {};
  const lower = text.toLowerCase();
  for (const [cat, config] of Object.entries(CATEGORIES)) {
    let score = 0;
    for (const kw of config.keywords) {
      if (lower.includes(kw)) score++;
    }
    scores[cat] = score;
  }
  return scores;
}

function analyzeProfile(data) {
  const { profile, repos, starred, languages } = data;
  const username = profile.login;

  // Score categories from repos
  const repoScores = {};
  for (const repo of repos) {
    const text = [repo.name, repo.description || "", (repo.topics || []).join(" ")].join(" ");
    const starWeight = 1 + (repo.stars || 0) * 0.1;
    const catScores = matchTextToCategories(text);
    for (const [cat, score] of Object.entries(catScores)) {
      repoScores[cat] = (repoScores[cat] || 0) + score * starWeight;
    }
    if (repo.language) {
      for (const [cat, config] of Object.entries(CATEGORIES)) {
        if (config.languages.includes(repo.language)) {
          repoScores[cat] = (repoScores[cat] || 0) + 0.5;
        }
      }
    }
  }

  // Score from starred
  const starredScores = {};
  for (const repo of starred) {
    const text = [repo.full_name || "", repo.description || "", (repo.topics || []).join(" ")].join(" ");
    const catScores = matchTextToCategories(text);
    for (const [cat, score] of Object.entries(catScores)) {
      starredScores[cat] = (starredScores[cat] || 0) + score * 0.5;
    }
    if (repo.language) {
      for (const [cat, config] of Object.entries(CATEGORIES)) {
        if (config.languages.includes(repo.language)) {
          starredScores[cat] = (starredScores[cat] || 0) + 0.25;
        }
      }
    }
  }

  // Combine
  const combined = {};
  const allCats = new Set([...Object.keys(repoScores), ...Object.keys(starredScores)]);
  for (const cat of allCats) {
    combined[cat] = (repoScores[cat] || 0) + (starredScores[cat] || 0);
  }

  const topCategories = Object.entries(combined)
    .filter(([, s]) => s > 0)
    .sort((a, b) => b[1] - a[1]);

  // Language breakdown
  const totalBytes = Object.values(languages).reduce((a, b) => a + b, 0);
  const topLanguages = totalBytes > 0
    ? Object.entries(languages)
        .map(([lang, bytes]) => ({ language: lang, percentage: Math.round((bytes / totalBytes) * 1000) / 10 }))
        .sort((a, b) => b.percentage - a.percentage)
    : [];

  // Metrics
  const prs = data.pull_requests;
  const mergedCount = prs.merged.length;
  const openCount = prs.open.length;
  const closedCount = prs.closed.length;
  const totalPRs = mergedCount + openCount + closedCount;

  const metrics = {
    followers: profile.followers,
    following: profile.following,
    follower_ratio: Math.round((profile.followers / Math.max(profile.following, 1)) * 100) / 100,
    total_repos: repos.length,
    total_stars_received: repos.reduce((sum, r) => sum + (r.stars || 0), 0),
    total_prs_to_others: totalPRs,
    pr_merge_rate: Math.round((mergedCount / Math.max(totalPRs, 1)) * 1000) / 10,
    merged_prs: mergedCount,
    open_prs: openCount,
    closed_prs: closedCount,
    orgs_count: data.orgs.length,
    starred_count: starred.length,
  };

  // Summary
  const parts = [];
  if (topCategories.length > 0) {
    const primary = topCategories[0][0];
    if (topCategories.length > 1 && topCategories[1][1] > topCategories[0][1] * 0.4) {
      parts.push(`${username} is primarily focused on ${primary} with significant activity in ${topCategories[1][0]}.`);
    } else {
      parts.push(`${username} is primarily focused on ${primary}.`);
    }
  } else {
    parts.push(`${username} has a diverse range of projects.`);
  }

  if (topLanguages.length > 0) {
    const langNames = topLanguages.slice(0, 3).map((l) => l.language);
    if (langNames.length === 1) parts.push(`Their primary language is ${langNames[0]}.`);
    else parts.push(`Their top languages are ${langNames.slice(0, -1).join(", ")} and ${langNames[langNames.length - 1]}.`);
  }

  if (totalPRs > 0) {
    parts.push(`They have contributed to ${totalPRs} pull requests on other projects with a ${metrics.pr_merge_rate}% acceptance rate.`);
  }

  if (metrics.followers > 100) parts.push(`With ${metrics.followers} followers, they have notable community influence.`);
  else if (metrics.followers > 20) parts.push(`They have a growing community presence with ${metrics.followers} followers.`);

  if (metrics.total_stars_received > 100) parts.push(`Their projects have earned ${metrics.total_stars_received} total stars.`);

  if (profile.created_at) parts.push(`Active on GitHub since ${profile.created_at.slice(0, 4)}.`);

  // Recent activity
  const reposWithPush = repos.filter((r) => r.pushed_at).sort((a, b) => b.pushed_at.localeCompare(a.pushed_at));
  const recentRepos = reposWithPush.slice(0, 10).map((r) => ({
    name: r.name, language: r.language || "", pushed_at: r.pushed_at,
    pushed_at_relative: relativeTime(r.pushed_at), html_url: r.html_url || "",
  }));

  let activitySummary = "";
  const events = data.events || [];
  if (events.length > 0) {
    const typeCounts = {};
    const eventRepos = new Set();
    for (const e of events) {
      typeCounts[e.type] = (typeCounts[e.type] || 0) + 1;
      if (e.repo) eventRepos.add(e.repo);
    }
    const timestamps = events.filter((e) => e.created_at).map((e) => e.created_at).sort();
    let spanDays = 30;
    if (timestamps.length > 0) {
      // Drop bottom 10% to exclude outliers
      const trimIdx = timestamps.length > 2 ? Math.max(1, Math.floor(timestamps.length / 10)) : 0;
      const earliest = new Date(timestamps[trimIdx]);
      spanDays = Math.max(1, Math.round((Date.now() - earliest.getTime()) / 86400000));
    }
    const friendlyNames = {
      PushEvent: "pushes", PullRequestEvent: "pull requests", IssuesEvent: "issues",
      CreateEvent: "repo/branch creations", WatchEvent: "stars given", ForkEvent: "forks",
      IssueCommentEvent: "issue comments", PullRequestReviewEvent: "PR reviews",
      DeleteEvent: "deletions", ReleaseEvent: "releases",
    };
    const sortedTypes = Object.entries(typeCounts).sort((a, b) => b[1] - a[1]);
    const topActivities = sortedTypes.slice(0, 3).map(([t, c]) => `${c} ${friendlyNames[t] || t.replace("Event", "").toLowerCase() + " events"}`);
    const totalEvents = Object.values(typeCounts).reduce((a, b) => a + b, 0);
    activitySummary = `${totalEvents} events across ${eventRepos.size} repos in the last ${spanDays} days.`;
    if (topActivities.length > 0) activitySummary += ` Primarily ${topActivities.join(", ")}.`;
  }

  return {
    summary: parts.join(" "),
    focus_areas: topCategories.slice(0, 6).map(([cat, score]) => ({ category: cat, score: Math.round(score * 10) / 10 })),
    languages: topLanguages,
    metrics,
    recent_repos: recentRepos,
    activity_summary: activitySummary,
  };
}

// ========== Achievement scraping ==========

async function scrapeAchievements(username) {
  try {
    const resp = await fetch(`https://github.com/${username}`, {
      headers: { "User-Agent": "gitwho" },
    });
    if (!resp.ok) return [];
    const html = await resp.text();

    const achievements = [];
    // Match achievement images
    const regex = /alt="(Achievement: [^"]+)"/g;
    let match;
    while ((match = regex.exec(html)) !== null) {
      const name = match[1];
      if (!achievements.find((a) => a.name === name)) {
        achievements.push({ name });
      }
    }
    return achievements;
  } catch {
    return [];
  }
}

// ========== Main fetch ==========

async function fetchAll(username, env) {
  const profile = await fetchUserProfile(username, env);
  if (!profile) return null;

  const userType = profile.type || "User";

  // Fetch repos + languages as a chain, parallel with everything else
  async function fetchReposAndLanguages() {
    const repos = await fetchRepos(username, userType, env);
    const languages = await fetchAllLanguages(username, repos, env, 20);
    return { repos, languages };
  }

  const [reposAndLangs, starred, following, followers, orgs, events, pullRequests, achievements] = await Promise.all([
    fetchReposAndLanguages(),
    fetchStarred(username, env),
    fetchFollowing(username, env),
    fetchFollowers(username, env),
    fetchOrgs(username, env),
    fetchEvents(username, env),
    fetchPullRequests(username, env),
    scrapeAchievements(username),
  ]);

  const { repos, languages } = reposAndLangs;

  const data = {
    profile, repos, languages, starred, following,
    followers, orgs, events, pull_requests: pullRequests,
    extras: { achievements },
    fetched_at: Date.now() / 1000,
  };

  const analysis = analyzeProfile(data);

  return { data, analysis };
}

// ========== Worker handler ==========

// Automated crawlers (Meta, OpenAI, Anthropic, Bytedance, generic scrapers) were walking
// the follower/following graph through this API, burning the KV write quota and the
// GitHub API budget. The API is for the gitwho UI and CLI, not for bulk crawling.
const CRAWLER_UA = /bot|crawl|spider|slurp|externalagent|externalhit|scrapy|python-requests|python-urllib|go-http-client|java\/|libwww|wget/i;

const ROBOTS_TXT = "User-agent: *\nDisallow: /\n";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // CORS preflight
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: CORS_HEADERS });
    }

    // Tell well-behaved crawlers to stay out entirely
    if (url.pathname === "/robots.txt") {
      return new Response(ROBOTS_TXT, { headers: { "Content-Type": "text/plain" } });
    }

    // Route: /api/profile/:username
    const profileMatch = url.pathname.match(/^\/api\/profile\/([^/]+)$/);
    if (profileMatch) {
      const username = profileMatch[1];

      // Validate username
      if (!/^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?$/.test(username)) {
        return new Response(JSON.stringify({ error: "Invalid GitHub username" }), {
          status: 400,
          headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
        });
      }

      // Refuse crawlers before touching KV or GitHub. Nothing is logged for them.
      const ua = request.headers.get("user-agent") || "";
      if (CRAWLER_UA.test(ua)) {
        return new Response(JSON.stringify({ error: "Automated crawling of this API is not permitted" }), {
          status: 403,
          headers: { ...CORS_HEADERS, "Content-Type": "application/json", "X-Robots-Tag": "noindex, nofollow" },
        });
      }

      // Log lookup
      if (env.GITWHO_CACHE) {
        const lookup = {
          username: username.toLowerCase(),
          timestamp: new Date().toISOString(),
          ip: request.headers.get("cf-connecting-ip") || "unknown",
          country: request.cf?.country || "unknown",
          city: request.cf?.city || "unknown",
          region: request.cf?.region || "unknown",
          latitude: request.cf?.latitude || null,
          longitude: request.cf?.longitude || null,
          asn: request.cf?.asOrganization || "unknown",
          user_agent: request.headers.get("user-agent") || "unknown",
        };
        try {
          const logKey = `lookup:${Date.now()}:${username.toLowerCase()}`;
          await env.GITWHO_CACHE.put(logKey, JSON.stringify(lookup), { expirationTtl: 86400 * 30 });

          // Update lookup list (last 500)
          const listRaw = await env.GITWHO_CACHE.get("lookups:recent", "json");
          const list = listRaw || [];
          list.unshift(lookup);
          if (list.length > 500) list.length = 500;
          await env.GITWHO_CACHE.put("lookups:recent", JSON.stringify(list));
        } catch (e) { /* don't fail the request if logging fails */ }
      }

      // Check cache
      const cacheKey = `gitwho:v2:${username}`;
      const cacheTTL = parseInt(env.CACHE_TTL || "3600");

      if (env.GITWHO_CACHE) {
        const cached = await env.GITWHO_CACHE.get(cacheKey, "json");
        if (cached) {
          return new Response(JSON.stringify(cached), {
            headers: { ...CORS_HEADERS, "Content-Type": "application/json", "X-Cache": "HIT" },
          });
        }
      }

      // Fetch and analyze
      const result = await fetchAll(username, env);
      if (!result) {
        return new Response(JSON.stringify({ error: `User '${username}' not found` }), {
          status: 404,
          headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
        });
      }

      // Store in cache. A failed write (for example the daily KV write quota being
      // exhausted) must not turn a successful lookup into a 500.
      if (env.GITWHO_CACHE) {
        try {
          await env.GITWHO_CACHE.put(cacheKey, JSON.stringify(result), { expirationTtl: cacheTTL });
        } catch (e) { /* serve the result uncached */ }
      }

      return new Response(JSON.stringify(result), {
        headers: { ...CORS_HEADERS, "Content-Type": "application/json", "X-Cache": "MISS" },
      });
    }

    // Route: /api/lookups
    if (url.pathname === "/api/lookups") {
      if (!env.GITWHO_CACHE) {
        return new Response(JSON.stringify([]), {
          headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
        });
      }
      const list = await env.GITWHO_CACHE.get("lookups:recent", "json") || [];
      return new Response(JSON.stringify(list), {
        headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
      });
    }

    // Health check
    if (url.pathname === "/health") {
      return new Response(JSON.stringify({ status: "ok", service: "gitwho-api" }), {
        headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
      });
    }

    return new Response("gitwho API - use /api/profile/:username", {
      headers: { ...CORS_HEADERS, "Content-Type": "text/plain" },
    });
  },
};
