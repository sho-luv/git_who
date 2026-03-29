// gitwho - Static frontend (calls Cloudflare Worker API)

const API_URL = "https://gitwho-api.YOUR-SUBDOMAIN.workers.dev";

// ========== Theme ==========
function toggleTheme() {
  const html = document.documentElement;
  const next = html.getAttribute("data-theme") === "dark" ? "light" : "dark";
  html.setAttribute("data-theme", next);
  localStorage.setItem("gitwho-theme", next);
  updateThemeIcon();
}

function updateThemeIcon() {
  const theme = document.documentElement.getAttribute("data-theme");
  document.querySelectorAll(".theme-icon").forEach((el) => {
    el.textContent = theme === "dark" ? "☀️" : "🌙";
  });
}

(function () {
  const saved = localStorage.getItem("gitwho-theme");
  if (saved) document.documentElement.setAttribute("data-theme", saved);
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", updateThemeIcon);
  else updateThemeIcon();
})();

// ========== Utility ==========
function extractUsername(value) {
  const match = value.trim().match(/https?:\/\/github\.com\/([^\/\s?#]+)\/?/);
  return match ? match[1] : value.trim().replace(/^@/, "");
}

function esc(str) {
  const div = document.createElement("div");
  div.textContent = str || "";
  return div.innerHTML;
}

// ========== Navigation ==========
function showSearchPage() {
  document.getElementById("search-page").style.display = "";
  document.getElementById("results-page").style.display = "none";
  document.getElementById("search-input").focus();
  history.pushState({}, "", window.location.pathname);
}

function showResultsPage() {
  document.getElementById("search-page").style.display = "none";
  document.getElementById("results-page").style.display = "";
}

// ========== Loading states ==========
function showLoading(username) {
  // Index page
  const indicator = document.getElementById("loading-indicator");
  const examples = document.getElementById("examples");
  const searchBtn = document.getElementById("search-btn");
  const loadingUsername = document.getElementById("loading-username");

  if (indicator) { indicator.style.display = "block"; }
  if (examples) { examples.style.display = "none"; }
  if (searchBtn) { searchBtn.disabled = true; searchBtn.textContent = "Analyzing..."; }
  if (loadingUsername) { loadingUsername.textContent = username; }

  // Results page header
  const headerLoading = document.getElementById("header-loading");
  const headerUsername = document.getElementById("header-loading-username");
  const goBtn = document.getElementById("header-go-btn");
  if (headerLoading) { headerLoading.style.display = "inline-flex"; }
  if (headerUsername) { headerUsername.textContent = username; }
  if (goBtn) { goBtn.disabled = true; goBtn.textContent = "..."; }

  // Hide error
  const err = document.getElementById("error-message");
  if (err) err.style.display = "none";
}

function hideLoading() {
  const indicator = document.getElementById("loading-indicator");
  const examples = document.getElementById("examples");
  const searchBtn = document.getElementById("search-btn");
  if (indicator) indicator.style.display = "none";
  if (examples) examples.style.display = "";
  if (searchBtn) { searchBtn.disabled = false; searchBtn.textContent = "Analyze"; }

  const headerLoading = document.getElementById("header-loading");
  const goBtn = document.getElementById("header-go-btn");
  if (headerLoading) headerLoading.style.display = "none";
  if (goBtn) { goBtn.disabled = false; goBtn.textContent = "Go"; }
}

function showError(msg) {
  hideLoading();
  const err = document.getElementById("error-message");
  if (err) { err.textContent = msg; err.style.display = "block"; }
}

// ========== Search ==========
function searchUser(username) {
  document.getElementById("search-input").value = username;
  doSearch(null, username);
}

async function doSearch(event, presetUsername) {
  if (event) event.preventDefault();

  const input = document.getElementById("search-input") || document.getElementById("header-search-input");
  const raw = presetUsername || input.value;
  const username = extractUsername(raw);
  if (!username) return;

  // Update both inputs
  const si = document.getElementById("search-input");
  const hi = document.getElementById("header-search-input");
  if (si) si.value = username;
  if (hi) hi.value = username;

  showLoading(username);

  try {
    const resp = await fetch(`${API_URL}/api/profile/${encodeURIComponent(username)}`);
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      showError(err.error || `User '${username}' not found or API error.`);
      return;
    }
    const result = await resp.json();
    renderResults(result.data, result.analysis);
    showResultsPage();
    hideLoading();
    history.pushState({}, "", `?u=${username}`);
  } catch (e) {
    showError("Network error. Please try again.");
  }
}

// ========== Rendering ==========
function renderResults(data, analysis) {
  const p = data.profile;

  // Sidebar
  document.getElementById("r-avatar").src = p.avatar_url;
  document.getElementById("r-name").textContent = p.name || p.login;
  document.getElementById("r-username").textContent = "@" + p.login;
  document.getElementById("r-org-badge").style.display = p.type === "Organization" ? "block" : "none";

  if (p.bio) { document.getElementById("r-bio").textContent = p.bio; document.getElementById("r-bio").style.display = ""; }
  else { document.getElementById("r-bio").style.display = "none"; }

  document.getElementById("r-followers").textContent = p.followers;
  document.getElementById("r-following").textContent = p.following;
  document.getElementById("r-repos").textContent = p.public_repos;

  // Details
  let details = "";
  if (p.location) details += `<div class="detail"><span class="detail-icon">📍</span> ${esc(p.location)}</div>`;
  if (p.company) details += `<div class="detail"><span class="detail-icon">🏢</span> ${esc(p.company)}</div>`;
  if (p.blog) {
    const href = p.blog.startsWith("http") ? p.blog : "https://" + p.blog;
    details += `<div class="detail"><span class="detail-icon">🔗</span> <a href="${esc(href)}" target="_blank">${esc(p.blog)}</a></div>`;
  }
  if (p.twitter_username) details += `<div class="detail"><span class="detail-icon">𝕏</span> <a href="https://twitter.com/${esc(p.twitter_username)}" target="_blank">@${esc(p.twitter_username)}</a></div>`;
  if (p.email) details += `<div class="detail"><span class="detail-icon">📧</span> ${esc(p.email)}</div>`;
  if (p.created_at) details += `<div class="detail"><span class="detail-icon">📅</span> Joined ${p.created_at.slice(0, 10)}</div>`;
  document.getElementById("r-details").innerHTML = details;

  // Orgs
  const orgs = data.orgs || [];
  if (orgs.length > 0) {
    document.getElementById("r-orgs-section").style.display = "";
    document.getElementById("r-orgs").innerHTML = orgs.map((o) =>
      `<a href="${esc(o.html_url)}" target="_blank" class="org-item" title="${esc(o.login)}"><img src="${esc(o.avatar_url)}" class="org-avatar"><span>${esc(o.login)}</span></a>`
    ).join("");
  } else {
    document.getElementById("r-orgs-section").style.display = "none";
  }

  // Achievements
  const achievements = (data.extras && data.extras.achievements) || [];
  if (achievements.length > 0) {
    document.getElementById("r-achievements-section").style.display = "";
    document.getElementById("r-achievements").innerHTML = achievements.map((a) =>
      `<div class="achievement-item" title="${esc(a.name)}"><span>${esc(a.name)}</span></div>`
    ).join("");
  } else {
    document.getElementById("r-achievements-section").style.display = "none";
  }

  // Analysis
  document.getElementById("r-summary").textContent = analysis.summary;

  document.getElementById("r-focus-areas").innerHTML = (analysis.focus_areas || []).map((f) =>
    `<span class="focus-tag">${esc(f.category)}</span>`
  ).join("");

  // Languages
  const langs = analysis.languages || [];
  if (langs.length > 0) {
    document.getElementById("r-languages-section").style.display = "";
    document.getElementById("r-languages").innerHTML = langs.slice(0, 8).map((l) =>
      `<div class="lang-row"><span class="lang-name">${esc(l.language)}</span><div class="lang-bar-wrapper"><div class="lang-bar" style="width:${l.percentage}%"></div></div><span class="lang-pct">${l.percentage}%</span></div>`
    ).join("");
  } else {
    document.getElementById("r-languages-section").style.display = "none";
  }

  // Metrics
  const m = analysis.metrics || {};
  document.getElementById("r-metrics").innerHTML = `
    <div class="metric-card"><span class="metric-value">${m.total_stars_received || 0}</span><span class="metric-label">Stars Received</span></div>
    <div class="metric-card"><span class="metric-value">${m.pr_merge_rate || 0}%</span><span class="metric-label">PR Merge Rate</span></div>
    <div class="metric-card"><span class="metric-value">${m.follower_ratio || 0}</span><span class="metric-label">Follower Ratio</span></div>
    <div class="metric-card"><span class="metric-value">${m.total_prs_to_others || 0}</span><span class="metric-label">PRs to Others</span></div>
  `;

  // Repos table
  document.getElementById("r-repos-heading").textContent = `Repositories (${data.repos.length})`;
  document.getElementById("r-repos-table").innerHTML = data.repos.slice(0, 50).map((r) =>
    `<tr><td><a href="${esc(r.html_url)}" target="_blank">${esc(r.name)}</a></td><td class="num">⭐ ${r.stars}</td><td class="num">🍴 ${r.forks}</td><td>${esc(r.language || "")}</td><td class="desc">${esc((r.description || "").slice(0, 80))}</td></tr>`
  ).join("");

  // Pull Requests
  const prs = data.pull_requests || { merged: [], open: [], closed: [] };
  const hasPRs = prs.merged.length + prs.open.length + prs.closed.length > 0;
  document.getElementById("prs-section").style.display = hasPRs ? "" : "none";
  if (hasPRs) {
    document.getElementById("r-pr-merged-count").textContent = prs.merged.length;
    document.getElementById("r-pr-open-count").textContent = prs.open.length;
    document.getElementById("r-pr-closed-count").textContent = prs.closed.length;

    renderPRList("pr-merged", prs.merged, "merged");
    renderPRList("pr-open", prs.open, "open");
    renderPRList("pr-closed", prs.closed, "closed");
  }

  // Starred
  const starred = data.starred || [];
  document.getElementById("starred-section").style.display = starred.length > 0 ? "" : "none";
  document.getElementById("r-starred-heading").textContent = `Starred Repositories (${starred.length})`;
  document.getElementById("r-starred-table").innerHTML = starred.slice(0, 30).map((r) =>
    `<tr><td><a href="${esc(r.html_url)}" target="_blank">${esc(r.full_name)}</a></td><td>${esc(r.language || "")}</td><td class="num">⭐ ${r.stars}</td><td class="desc">${esc((r.description || "").slice(0, 80))}</td></tr>`
  ).join("");

  // Network
  const followers = data.followers || [];
  const following = data.following || [];
  const hasNetwork = followers.length + following.length > 0;
  document.getElementById("network-section").style.display = hasNetwork ? "" : "none";
  document.getElementById("r-network-heading").textContent = `Network (${p.followers} followers, ${p.following} following)`;

  const fHead = followers.length < p.followers
    ? `Followers (showing ${followers.length} of <a href="https://github.com/${esc(p.login)}?tab=followers" target="_blank">${p.followers}</a>)`
    : "Followers";
  document.getElementById("r-followers-heading").innerHTML = fHead;
  document.getElementById("r-followers-grid").innerHTML = followers.slice(0, 30).map((u) =>
    `<a href="?u=${esc(u.login)}" class="user-card" title="${esc(u.login)}" onclick="searchUser('${esc(u.login)}'); return false;"><img src="${esc(u.avatar_url)}" class="user-avatar"><span>${esc(u.login)}</span></a>`
  ).join("");

  const gHead = following.length < p.following
    ? `Following (showing ${following.length} of <a href="https://github.com/${esc(p.login)}?tab=following" target="_blank">${p.following}</a>)`
    : "Following";
  document.getElementById("r-following-heading").innerHTML = gHead;
  document.getElementById("r-following-grid").innerHTML = following.slice(0, 30).map((u) =>
    `<a href="?u=${esc(u.login)}" class="user-card" title="${esc(u.login)}" onclick="searchUser('${esc(u.login)}'); return false;"><img src="${esc(u.avatar_url)}" class="user-avatar"><span>${esc(u.login)}</span></a>`
  ).join("");

  // Header search input
  document.getElementById("header-search-input").value = p.login;
  document.title = `${p.login} - gitwho`;
}

function renderPRList(containerId, prs, type) {
  const statusChar = { merged: "✓", open: "○", closed: "✗" }[type];
  const el = document.getElementById(containerId);
  if (prs.length === 0) {
    el.innerHTML = '<p class="empty-state">None found.</p>';
    return;
  }
  el.innerHTML = prs.slice(0, 20).map((pr) =>
    `<div class="pr-item ${type}"><span class="pr-status">${statusChar}</span><a href="${esc(pr.html_url)}" target="_blank">${esc(pr.title)}</a><span class="pr-repo">${esc(pr.repo)}</span></div>`
  ).join("");
}

// ========== Sections ==========
function toggleSection(id) {
  const el = document.getElementById(id);
  if (el) el.classList.toggle("collapsed");
}

function showPRTab(tab, btn) {
  document.querySelectorAll(".pr-content").forEach((el) => el.classList.add("hidden"));
  document.getElementById("pr-" + tab).classList.remove("hidden");
  document.querySelectorAll(".pr-tab").forEach((el) => el.classList.remove("active"));
  btn.classList.add("active");
}

// ========== URL handling ==========
document.addEventListener("DOMContentLoaded", function () {
  // Paste URL parsing
  const input = document.getElementById("search-input");
  if (input) {
    input.addEventListener("paste", function () {
      setTimeout(() => { input.value = extractUsername(input.value); }, 10);
    });
  }

  // Check for ?u= parameter
  const params = new URLSearchParams(window.location.search);
  const u = params.get("u");
  if (u) searchUser(u);
});

// Handle browser back/forward
window.addEventListener("popstate", function () {
  const params = new URLSearchParams(window.location.search);
  const u = params.get("u");
  if (u) searchUser(u);
  else showSearchPage();
});
