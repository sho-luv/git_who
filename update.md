### 2026-09-11
- Cloudflare KV write quota (1,000/day) was being exhausted by Meta's crawler walking follower/following links through `/api/profile`, ~400 lookups/day since Sept 5
- Worker now returns 403 to crawler user agents before any KV or GitHub call, serves `/robots.txt` with Disallow all, and wraps the cache write in try/catch so a failed KV put no longer produces a 500
- Deployed with `wrangler deploy`; verified 403 for meta-externalagent and GPTBot, 200 for browsers

### 2026-03-29
- Added gitwho tab to private dashboard (dashboard.sholuv.net) showing profile lookup tracking with IP, geo, ASN, and user agent
- Removed public lookups page from sholuv.net/gitwho - lookup data now only visible in private dashboard
- Added KV namespace (GITWHO_CACHE) for caching and lookup storage
- Deployed updated gitwho Worker with full geo/network logging per lookup
- Redeployed analytics-collector Worker to serve updated dashboard assets

### 2026-03-28
- Built gitwho - GitHub OSINT & Profile Intelligence tool (CLI + web)
- Created Cloudflare Worker backend (gitwho-api) with GitHub API fetching, rule-based analysis, achievement scraping
- Deployed static frontend to sholuv.net/gitwho via GitHub Pages (docs/)
- Added gitwho to tools section on sholuv.net/work.html
- Published blog post: "gitwho: Why I Built a GitHub Profile Intelligence Tool"
- Fixed search page centering on static frontend (CSS #search-page flex fix)
- Fork filtering in language aggregation to avoid skewed stats
- Pagination caps on followers/following/repos to prevent hanging on large profiles