// gitwho - Frontend JavaScript

// Theme toggle
function toggleTheme() {
    const html = document.documentElement;
    const current = html.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', next);
    localStorage.setItem('gitwho-theme', next);
    updateThemeIcon();
}

function updateThemeIcon() {
    const theme = document.documentElement.getAttribute('data-theme');
    const icons = document.querySelectorAll('.theme-icon');
    icons.forEach(icon => {
        icon.textContent = theme === 'dark' ? '☀️' : '🌙';
    });
}

// Load saved theme
(function() {
    const saved = localStorage.getItem('gitwho-theme');
    if (saved) {
        document.documentElement.setAttribute('data-theme', saved);
    }
    // Update icon after DOM loads
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', updateThemeIcon);
    } else {
        updateThemeIcon();
    }
})();

// Extract username from URL or return as-is
function extractUsername(value) {
    const match = value.trim().match(/https?:\/\/github\.com\/([^\/\s?#]+)\/?/);
    return match ? match[1] : value.trim();
}

// Show loading state and submit search
function showLoading(username) {
    // Index page loading indicator
    var loading = document.getElementById('loading-indicator');
    var examples = document.getElementById('examples');
    var searchBtn = document.getElementById('search-btn');

    // Results page inline indicator
    var headerLoading = document.getElementById('header-loading');
    var goBtn = document.getElementById('header-go-btn');

    // Set username in whichever loading element exists
    var loadingUsername = document.getElementById('loading-username');
    if (loadingUsername) loadingUsername.textContent = username;

    // Index page
    if (loading) {
        loading.style.display = 'block';
        if (examples) examples.style.display = 'none';
        if (searchBtn) {
            searchBtn.disabled = true;
            searchBtn.textContent = 'Analyzing...';
        }
    }

    // Results page - inline next to search
    if (headerLoading) {
        headerLoading.style.display = 'inline-flex';
        if (goBtn) {
            goBtn.disabled = true;
            goBtn.textContent = '...';
        }
    }
}

// Search for a user (used by example links)
function searchUser(username) {
    const input = document.getElementById('search-input');
    if (input) input.value = username;
    showLoading(username);
    window.location.href = '/search?username=' + encodeURIComponent(username);
}

// URL parsing in search input + loading on submit
document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('search-input');
    const searchForm = document.getElementById('search-form');

    if (searchInput) {
        searchInput.addEventListener('paste', function(e) {
            setTimeout(function() {
                searchInput.value = extractUsername(searchInput.value);
            }, 10);
        });
    }

    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            const username = extractUsername(searchInput.value);
            if (username) {
                searchInput.value = username;
                showLoading(username);
            }
        });
    }
});

// Collapsible sections
function toggleSection(sectionId) {
    const section = document.getElementById(sectionId);
    if (section) {
        section.classList.toggle('collapsed');
    }
}

// PR tabs
function showPRTab(tab) {
    // Hide all PR content
    document.querySelectorAll('.pr-content').forEach(el => {
        el.classList.add('hidden');
    });
    // Show selected
    const target = document.getElementById('pr-' + tab);
    if (target) {
        target.classList.remove('hidden');
    }
    // Update tab styles
    document.querySelectorAll('.pr-tab').forEach(el => {
        el.classList.remove('active');
    });
    event.target.classList.add('active');
}
