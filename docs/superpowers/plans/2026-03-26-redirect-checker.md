# Redirect Checker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add live redirect chain checking to the viewer's links panel, with support for 5 user agents (Chrome Desktop, Chrome Mobile, Googlebot, Outlook 2019, Apple Mail). Show pre-computed chains instantly; allow live re-checking via Cloudflare Worker.

**Architecture:** Cloudflare Worker fetches URLs and follows redirects, returning the full chain. Frontend conditionally shows pre-computed data (fast) or live results (on-demand). User agent persists in localStorage.

**Tech Stack:** Cloudflare Workers (Wrangler), Jinja2 templates, vanilla JS, CSS grid/flexbox.

---

## File Structure

| File | Purpose | Action |
|---|---|---|
| `wrangler.toml` | Cloudflare Worker config | Create |
| `src/worker.js` | Redirect-following logic | Create |
| `templates/viewer.html` | UA selector, link card display, JS | Modify |
| `src/assets/css/style.css` | Table, loading, error styles | Modify |

---

## Task 1: Create Cloudflare Worker Config

**Files:**
- Create: `wrangler.toml`

- [ ] **Step 1: Create wrangler.toml with Worker metadata**

```toml
name = "archive-news-redirect-checker"
main = "src/worker.js"
compatibility_date = "2026-03-01"
compatibility_flags = ["nodejs_compat"]

[env.production]
routes = [
  { pattern = "*.workers.dev", zone_name = "workers.dev" }
]
```

- [ ] **Step 2: Verify file exists**

Run: `ls -la wrangler.toml`
Expected: File appears, contains `name = "archive-news-redirect-checker"`

---

## Task 2: Create Cloudflare Worker Code

**Files:**
- Create: `src/worker.js`

- [ ] **Step 1: Write Worker handler function**

```javascript
const USER_AGENTS = {
  'chrome-desktop': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
  'chrome-mobile': 'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36',
  'googlebot': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
  'outlook-2019': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; Trident/7.0; rv:11.0) like Gecko',
  'apple-mail': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko)'
};

export default {
  async fetch(request, env, ctx) {
    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type'
        }
      });
    }

    if (request.method !== 'POST') {
      return new Response(JSON.stringify({ success: false, error: 'POST required' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }
      });
    }

    try {
      const { url, userAgent } = await request.json();

      if (!url) {
        return jsonResponse({ success: false, error: 'url parameter required' }, 400);
      }

      // Validate URL format
      let urlObj;
      try {
        urlObj = new URL(url);
      } catch {
        return jsonResponse({ success: false, error: 'Invalid URL format' }, 400);
      }

      if (!['http:', 'https:'].includes(urlObj.protocol)) {
        return jsonResponse({ success: false, error: 'Only http:// and https:// supported' }, 400);
      }

      const ua = USER_AGENTS[userAgent] || USER_AGENTS['chrome-desktop'];
      const startTime = Date.now();
      const chain = await followRedirects(url, ua, 15);
      const elapsedMs = Date.now() - startTime;

      return jsonResponse({
        success: true,
        chain: chain,
        elapsed_ms: elapsedMs
      });
    } catch (error) {
      const message = error.message || 'Unknown error';
      return jsonResponse({
        success: false,
        error: mapErrorMessage(message)
      }, 500);
    }
  }
};

async function followRedirects(url, userAgent, maxHops) {
  const chain = [];
  let currentUrl = url;
  let hopCount = 0;
  const visited = new Set();

  while (hopCount < maxHops) {
    if (visited.has(currentUrl)) {
      break; // Avoid infinite redirect loops
    }
    visited.add(currentUrl);

    try {
      const response = await fetch(currentUrl, {
        method: 'HEAD',
        headers: { 'User-Agent': userAgent },
        redirect: 'manual',
        timeout: 15000
      });

      const status = response.status;
      chain.push({
        status: status,
        url: currentUrl
      });

      // Check if it's a redirect
      if ([301, 302, 303, 307, 308].includes(status)) {
        const location = response.headers.get('Location');
        if (!location) break; // No Location header, treat as final
        currentUrl = new URL(location, currentUrl).toString();
        hopCount++;
      } else {
        // Non-redirect response, we're done
        break;
      }
    } catch (error) {
      // Network error, timeout, etc.
      chain.push({
        status: 'Error',
        url: currentUrl,
        error: mapErrorMessage(error.message)
      });
      break;
    }
  }

  if (hopCount >= maxHops && [301, 302, 303, 307, 308].includes(chain[chain.length - 1]?.status)) {
    chain.push({
      status: 'Error',
      url: 'Too many redirects (>15 hops)',
      error: 'Redirect chain exceeded 15 hops'
    });
  }

  return chain;
}

function mapErrorMessage(err) {
  const msg = err.toLowerCase();
  if (msg.includes('timeout')) return 'Request timed out after 15s';
  if (msg.includes('dns')) return 'Could not resolve hostname';
  if (msg.includes('econnrefused')) return 'Connection failed — host may be offline';
  if (msg.includes('enotfound')) return 'Could not resolve hostname';
  return 'Request failed — try again in a moment';
}

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*'
    }
  });
}
```

- [ ] **Step 2: Verify file exists and syntax is valid**

Run: `ls -la src/worker.js && node -c src/worker.js`
Expected: File exists, no syntax errors

---

## Task 3: Test Cloudflare Worker Locally

**Files:**
- None (testing only)

- [ ] **Step 1: Install Wrangler (if not already installed)**

Run: `npm install -g wrangler`
Expected: Wrangler command available

- [ ] **Step 2: Start local Worker dev server**

Run: `wrangler dev src/worker.js --local`
Expected: Server starts on `http://localhost:8787` (or similar port shown in output)

- [ ] **Step 3: Test with curl (in separate terminal)**

Run:
```bash
curl -X POST http://localhost:8787 \
  -H "Content-Type: application/json" \
  -d '{"url":"https://httpbin.org/redirect-to?url=https://example.com","userAgent":"chrome-desktop"}'
```

Expected:
```json
{
  "success": true,
  "chain": [
    {"status": 302, "url": "https://httpbin.org/redirect-to?url=https://example.com"},
    {"status": 200, "url": "https://example.com"}
  ],
  "elapsed_ms": 1234
}
```

- [ ] **Step 4: Test error case (bad URL)**

Run:
```bash
curl -X POST http://localhost:8787 \
  -H "Content-Type: application/json" \
  -d '{"url":"https://nonexistent-domain-12345.invalid","userAgent":"chrome-desktop"}'
```

Expected:
```json
{
  "success": false,
  "error": "Could not resolve hostname"
}
```

- [ ] **Step 5: Stop dev server**

Run: Press `Ctrl+C` in the Wrangler terminal
Expected: Server stops gracefully

---

## Task 4: Deploy Cloudflare Worker

**Files:**
- None (deployment only)

- [ ] **Step 1: Authenticate with Cloudflare**

Run: `wrangler login`
Expected: Browser opens, you authorize Claude Code with Cloudflare, returns to terminal with "✓ Authenticated"

- [ ] **Step 2: Deploy Worker**

Run: `wrangler deploy src/worker.js`
Expected: Output shows deployment URL like `https://archive-news-redirect-checker.{your-subdomain}.workers.dev`

- [ ] **Step 3: Copy deployment URL and save it**

Save the full URL (e.g., `https://archive-news-redirect-checker.USERNAME.workers.dev`) — you'll need it in the next task.

- [ ] **Step 4: Test deployed Worker with curl**

Run (replace URL with your actual deployment URL):
```bash
curl -X POST https://archive-news-redirect-checker.USERNAME.workers.dev \
  -H "Content-Type: application/json" \
  -d '{"url":"https://httpbin.org/redirect-to?url=https://example.com","userAgent":"chrome-desktop"}'
```

Expected: Same successful response as local test

---

## Task 5: Add User Agent Selector HTML to viewer.html

**Files:**
- Modify: `templates/viewer.html` (lines 295–310, in `#tab-links` div)

- [ ] **Step 1: Locate the links tab opening div**

Find this section in `templates/viewer.html`:
```html
<div id="tab-links" class="tab-pane">
  <!-- filter row starts here -->
  <div class="link-filter-row">
```

- [ ] **Step 2: Add UA selector header before the filter row**

Insert this HTML **before** the existing filter row:
```html
<div id="ua-selector-container" style="padding: 12px 16px; border-bottom: 1px solid #2a2a35; display: flex; align-items: center; gap: 12px;">
  <label for="ua-select" style="font-size: 11px; color: #888; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">User Agent:</label>
  <select id="ua-select" style="background: #1e1e24; color: #ccc; border: 1px solid #333; border-radius: 4px; padding: 4px 8px; font-size: 12px; font-family: monospace; flex: 1;">
    <option value="chrome-desktop">Chrome Desktop</option>
    <option value="chrome-mobile">Chrome Mobile</option>
    <option value="googlebot">Googlebot</option>
    <option value="outlook-2019">Outlook 2019</option>
    <option value="apple-mail">Apple Mail</option>
  </select>
</div>
```

- [ ] **Step 3: Verify insertion**

Check that the UA selector appears above the existing filter chips in the LINKS tab. The file should now have the selector as the first child of `#tab-links`.

---

## Task 6: Add JavaScript Functions for Redirect Checking

**Files:**
- Modify: `templates/viewer.html` (in the `<script>` section, after existing functions, around line 600)

- [ ] **Step 1: Add toggleSelectUA function**

Insert this function in the `<script>` block:
```javascript
function toggleSelectUA(uaKey) {
  const select = document.getElementById('ua-select');
  if (select) {
    select.value = uaKey;
    localStorage.setItem('linkCheckUA', uaKey);
  }
}

function initializeUASelector() {
  const select = document.getElementById('ua-select');
  const savedUA = localStorage.getItem('linkCheckUA') || 'chrome-desktop';
  if (select) {
    select.value = savedUA;
    select.addEventListener('change', (e) => {
      localStorage.setItem('linkCheckUA', e.target.value);
    });
  }
}
```

- [ ] **Step 2: Add checkRedirects function**

Insert this function in the `<script>` block:
```javascript
async function checkRedirects(linkIndex, workerUrl) {
  const link = emailLinks[linkIndex - 1]; // linkIndex is 1-based
  if (!link) {
    console.error(`Link ${linkIndex} not found`);
    return;
  }

  const card = document.getElementById(`lc-${linkIndex}`);
  if (!card) return;

  const auditLog = card.querySelector('.audit-log-container') ||
                   card.querySelector('.link-audit-log');
  if (!auditLog) return;

  const ua = document.getElementById('ua-select')?.value || 'chrome-desktop';

  // Show loading state
  auditLog.innerHTML = `
    <div style="padding: 12px; display: flex; align-items: center; gap: 8px; color: #888; font-size: 12px;">
      <span style="display: inline-block; width: 12px; height: 12px; border: 2px solid #0aaa8e; border-top-color: transparent; border-radius: 50%; animation: spin 0.6s linear infinite;"></span>
      Checking redirects with ${ua}...
    </div>
  `;

  // Add CSS animation if not already present
  if (!document.getElementById('spin-animation')) {
    const style = document.createElement('style');
    style.id = 'spin-animation';
    style.textContent = `@keyframes spin { to { transform: rotate(360deg); } }`;
    document.head.appendChild(style);
  }

  try {
    const response = await fetch(workerUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: link.original_url, userAgent: ua })
    });

    const data = await response.json();

    if (data.success) {
      displayRedirectChain(linkIndex, data.chain, data.elapsed_ms);
    } else {
      displayRedirectError(linkIndex, data.error);
    }
  } catch (error) {
    displayRedirectError(linkIndex, error.message || 'Request failed');
  }
}
```

- [ ] **Step 3: Add displayRedirectChain function**

Insert this function in the `<script>` block:
```javascript
function displayRedirectChain(linkIndex, chain, elapsedMs) {
  const card = document.getElementById(`lc-${linkIndex}`);
  if (!card) return;

  const auditLog = card.querySelector('.audit-log-container') ||
                   card.querySelector('.link-audit-log');
  if (!auditLog) return;

  let tableHTML = `
    <div style="padding: 12px; font-size: 11px;">
      <table style="width: 100%; border-collapse: collapse; margin-bottom: 8px;">
        <thead>
          <tr style="border-bottom: 1px solid #2a2a35;">
            <th style="text-align: left; padding: 4px 6px; color: #666; font-weight: 600; width: 28px;">#</th>
            <th style="text-align: left; padding: 4px 6px; color: #666; font-weight: 600; width: 48px;">Status</th>
            <th style="text-align: left; padding: 4px 6px; color: #666; font-weight: 600;">URL</th>
          </tr>
        </thead>
        <tbody>
  `;

  chain.forEach((hop, i) => {
    const statusNum = hop.status;
    let statusBg, statusColor;

    if (typeof statusNum === 'string') {
      statusBg = '#8B3A3A';
      statusColor = '#FF6B6B';
    } else if (statusNum >= 300 && statusNum < 400) {
      statusBg = '#2d3a4a';
      statusColor = '#6AB0E7';
    } else if (statusNum >= 200 && statusNum < 300) {
      statusBg = '#0aaa8e33';
      statusColor = '#0aaa8e';
    } else {
      statusBg = '#8B3A3A';
      statusColor = '#FF6B6B';
    }

    const isLast = i === chain.length - 1;
    const finalDestClass = isLast && typeof statusNum === 'number' && statusNum < 300 ? ' ✓' : '';
    const finalStyle = isLast && typeof statusNum === 'number' && statusNum < 300
      ? 'border: 1px solid #0aaa8e44; background: #0aaa8e11;'
      : '';

    tableHTML += `
      <tr style="border-bottom: 1px solid #1e1e24; ${finalStyle}">
        <td style="padding: 6px; color: #666; font-size: 10px;">${i + 1}</td>
        <td style="padding: 6px;">
          <span style="background: ${statusBg}; color: ${statusColor}; padding: 1px 6px; border-radius: 3px; font-weight: 700; font-size: 11px;">
            ${statusNum}
          </span>
        </td>
        <td style="padding: 6px; color: ${isLast && typeof statusNum === 'number' && statusNum < 300 ? '#fff' : '#ccc'}; word-break: break-all; font-size: 11px; ${isLast && typeof statusNum === 'number' && statusNum < 300 ? 'font-weight: 500;' : ''}" title="${hop.url}">
          ${hop.url}${finalDestClass}
        </td>
      </tr>
    `;
  });

  tableHTML += `
        </tbody>
      </table>
      <div style="text-align: right; color: #666; font-size: 10px;">
        Checked in ${elapsedMs}ms
      </div>
    </div>
  `;

  auditLog.innerHTML = tableHTML;

  // Replace button with "Re-check live" if pre-computed data
  const checkBtn = card.querySelector('[data-action="check-redirects"]');
  if (!checkBtn?.closest('[data-has-precomputed="true"]')) {
    const existingRecheck = card.querySelector('[data-action="recheck-redirects"]');
    if (!existingRecheck) {
      const recheckBtn = document.createElement('button');
      recheckBtn.textContent = 'Re-check live';
      recheckBtn.dataset.action = 'recheck-redirects';
      recheckBtn.style.cssText = 'background: #0aaa8e; color: #fff; border: none; border-radius: 4px; padding: 4px 12px; font-size: 11px; cursor: pointer; margin-top: 8px;';
      auditLog.appendChild(recheckBtn);
      recheckBtn.addEventListener('click', () => {
        checkRedirects(linkIndex, window.WORKER_URL);
      });
    }
  }
}
```

- [ ] **Step 4: Add displayRedirectError function**

Insert this function in the `<script>` block:
```javascript
function displayRedirectError(linkIndex, errorMsg) {
  const card = document.getElementById(`lc-${linkIndex}`);
  if (!card) return;

  const auditLog = card.querySelector('.audit-log-container') ||
                   card.querySelector('.link-audit-log');
  if (!auditLog) return;

  const html = `
    <div style="padding: 12px; background: #3d1a1a; border: 1px solid #8B3A3A; border-radius: 4px; display: flex; align-items: flex-start; gap: 8px;">
      <span style="color: #FF6B6B; font-size: 14px; flex-shrink: 0;">❌</span>
      <div>
        <div style="color: #FF6B6B; font-size: 11px; font-weight: 600; margin-bottom: 6px;">Failed to check redirects</div>
        <div style="color: #ccc; font-size: 11px; margin-bottom: 8px;">${errorMsg}</div>
        <button style="background: #0aaa8e; color: #fff; border: none; border-radius: 4px; padding: 3px 10px; font-size: 10px; cursor: pointer;" onclick="checkRedirects(${linkIndex}, window.WORKER_URL)">
          Retry
        </button>
      </div>
    </div>
  `;

  auditLog.innerHTML = html;
}
```

- [ ] **Step 5: Call initializeUASelector on page load**

Find the existing `<script>` initialization code (look for document event listeners). Add or modify to include:
```javascript
document.addEventListener('DOMContentLoaded', () => {
  initializeUASelector();
  // ... existing code ...
});
```

If DOMContentLoaded is already there, just add the `initializeUASelector()` call at the beginning.

- [ ] **Step 6: Set global Worker URL**

In the same initialization section, add:
```javascript
// Replace with your deployed Worker URL from Task 4
window.WORKER_URL = 'https://archive-news-redirect-checker.USERNAME.workers.dev';
```

---

## Task 7: Modify Link Card Rendering in Jinja2

**Files:**
- Modify: `templates/viewer.html` (lines 180–230, link card rendering loop)

- [ ] **Step 1: Locate link card rendering section**

Find this loop:
```jinja2
{% for link in links %}
  <div class="link-card-v2" id="lc-{{ link.index }}">
    <!-- link card content -->
  </div>
{% endfor %}
```

- [ ] **Step 2: Modify card to show conditional content**

Replace the link card inner content with this logic:
```jinja2
{% for link in links %}
  <div class="link-card-v2" id="lc-{{ link.index }}" data-has-precomputed="{% if link.redirect_chain %}true{% else %}false{% endif %}">
    <!-- Card header (existing, unchanged) -->
    <div class="link-card-header" onclick="toggleExpand(this)">
      <span class="link-index">{{ link.index }}</span>
      <span class="link-domain">{{ link.domain }}</span>
      {% if link.is_tracking %}<span class="tag tag-tracking">tracking</span>{% endif %}
      {% if not link.is_secure %}<span class="tag tag-unsecure">http</span>{% endif %}
      {% if link.is_dev %}<span class="tag tag-dev">dev</span>{% endif %}
    </div>

    <!-- Card body (expanded content) -->
    <div class="link-card-body">
      <div class="link-text" title="{{ link.txt }}">{{ link.txt }}</div>
      <div class="link-url">{{ link.original_url }}</div>

      <!-- Actions: existing copy button + check/recheck button -->
      <div style="display: flex; gap: 8px; margin-top: 8px;">
        <button class="link-action-btn" onclick="copyLink(this, '{{ link.original_url }}')">
          Copy
        </button>
        <button class="link-action-btn"
                data-action="{% if link.redirect_chain %}recheck-redirects{% else %}check-redirects{% endif %}"
                onclick="checkRedirects({{ link.index }}, window.WORKER_URL)"
                style="background: #0aaa8e; color: #fff;">
          {% if link.redirect_chain %}Re-check live{% else %}Check Redirects{% endif %}
        </button>
      </div>

      <!-- Redirect chain display (if pre-computed) or audit log container -->
      <div class="audit-log-container" style="margin-top: 12px;">
        {% if link.redirect_chain %}
          <div style="font-size: 11px;">
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 8px;">
              <thead>
                <tr style="border-bottom: 1px solid #2a2a35;">
                  <th style="text-align: left; padding: 4px 6px; color: #666; font-weight: 600; width: 28px;">#</th>
                  <th style="text-align: left; padding: 4px 6px; color: #666; font-weight: 600; width: 48px;">Status</th>
                  <th style="text-align: left; padding: 4px 6px; color: #666; font-weight: 600;">URL</th>
                </tr>
              </thead>
              <tbody>
                {% for hop in link.redirect_chain %}
                  {% set status = hop.status %}
                  {% set is_last = loop.last %}
                  {% set is_error = status is string %}
                  {% set status_color = 'text-error' if is_error else ('text-success' if status < 300 else 'text-redirect') %}
                  {% set status_bg = 'bg-error' if is_error else ('bg-success' if status < 300 else 'bg-redirect') %}
                  <tr style="border-bottom: 1px solid #1e1e24; {% if is_last and not is_error and status < 300 %}border: 1px solid #0aaa8e44; background: #0aaa8e11;{% endif %}">
                    <td style="padding: 6px; color: #666; font-size: 10px;">{{ loop.index }}</td>
                    <td style="padding: 6px;">
                      <span style="{% if is_error %}background: #8B3A3A; color: #FF6B6B;{% elif status < 300 %}background: #0aaa8e33; color: #0aaa8e;{% else %}background: #2d3a4a; color: #6AB0E7;{% endif %} padding: 1px 6px; border-radius: 3px; font-weight: 700; font-size: 11px;">
                        {{ status }}
                      </span>
                    </td>
                    <td style="padding: 6px; color: {% if is_last and not is_error and status < 300 %}#fff{% else %}#ccc{% endif %}; word-break: break-all; font-size: 11px; {% if is_last and not is_error and status < 300 %}font-weight: 500;{% endif %}" title="{{ hop.url }}">
                      {{ hop.url }}{% if is_last and not is_error and status < 300 %} ✓{% endif %}
                    </td>
                  </tr>
                {% endfor %}
              </tbody>
            </table>
            <div style="text-align: right; color: #666; font-size: 10px;">
              Checked on {{ link.audit_date }}
            </div>
          </div>
        {% endif %}
      </div>
    </div>
  </div>
{% endfor %}
```

- [ ] **Step 3: Verify structure**

Reload the viewer in a browser and check that:
- Pre-computed chains display in a table format
- "Check Redirects" button appears for links without chains
- "Re-check live" button appears for links with chains

---

## Task 8: Add CSS for Table, Loading, and Error States

**Files:**
- Modify: `src/assets/css/style.css` (append at end)

- [ ] **Step 1: Add table and redirect chain styles**

Append this CSS to `src/assets/css/style.css`:
```css
/* Redirect chain table styles */
.audit-log-container table {
  width: 100%;
  border-collapse: collapse;
  font-family: 'Courier New', monospace;
  font-size: 11px;
}

.audit-log-container table thead {
  border-bottom: 1px solid #2a2a35;
}

.audit-log-container table th {
  text-align: left;
  padding: 6px;
  color: #666;
  font-weight: 600;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.audit-log-container table tbody tr {
  border-bottom: 1px solid #1e1e24;
}

.audit-log-container table td {
  padding: 6px;
  color: #ccc;
  word-break: break-all;
}

.audit-log-container table tbody tr:last-child {
  border-bottom: none;
}

/* Status badge colors in table */
.audit-log-container .status-badge {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 3px;
  font-weight: 700;
  font-size: 10px;
  white-space: nowrap;
}

.status-badge.redirect {
  background: #2d3a4a;
  color: #6AB0E7;
}

.status-badge.success {
  background: #0aaa8e33;
  color: #0aaa8e;
  border: 1px solid #0aaa8e;
}

.status-badge.error {
  background: #8B3A3A;
  color: #FF6B6B;
}

/* Final destination row highlight */
.audit-log-container table tbody tr:last-child td {
  color: #fff;
}

.audit-log-container table tbody tr:last-child {
  border: 1px solid #0aaa8e44;
  background: #0aaa8e11;
}

/* Link action buttons */
.link-action-btn {
  background: #1e1e24;
  color: #ccc;
  border: 1px solid #333;
  border-radius: 4px;
  padding: 4px 10px;
  font-size: 11px;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.2s ease;
}

.link-action-btn:hover {
  background: #2a2a35;
  border-color: #444;
  color: #fff;
}

.link-action-btn[style*="background: #0aaa8e"] {
  border-color: #0aaa8e;
}

.link-action-btn[style*="background: #0aaa8e"]:hover {
  background: #088b7a !important;
}

/* Loading spinner */
@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.redirect-check-loading {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid #0aaa8e;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

/* Error state box */
.redirect-check-error {
  padding: 12px;
  background: #3d1a1a;
  border: 1px solid #8B3A3A;
  border-radius: 4px;
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-top: 8px;
}

.redirect-check-error-icon {
  color: #FF6B6B;
  font-size: 14px;
  flex-shrink: 0;
}

.redirect-check-error-title {
  color: #FF6B6B;
  font-size: 11px;
  font-weight: 600;
  margin-bottom: 6px;
}

.redirect-check-error-message {
  color: #ccc;
  font-size: 11px;
  margin-bottom: 8px;
}

.redirect-check-error-retry {
  background: #0aaa8e;
  color: #fff;
  border: none;
  border-radius: 4px;
  padding: 3px 10px;
  font-size: 10px;
  cursor: pointer;
  transition: background 0.2s ease;
}

.redirect-check-error-retry:hover {
  background: #088b7a;
}

/* UA selector styling */
#ua-selector-container {
  padding: 12px 16px;
  border-bottom: 1px solid #2a2a35;
  display: flex;
  align-items: center;
  gap: 12px;
}

#ua-select {
  background: #1e1e24;
  color: #ccc;
  border: 1px solid #333;
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 12px;
  font-family: monospace;
  flex: 1;
  cursor: pointer;
  transition: all 0.2s ease;
}

#ua-select:hover {
  border-color: #444;
  background: #2a2a35;
}

#ua-select:focus {
  outline: none;
  border-color: #0aaa8e;
  background: #1e1e24;
}
```

- [ ] **Step 2: Copy CSS to docs/assets/css/**

Run:
```bash
cp src/assets/css/style.css docs/assets/css/style.css
```

Expected: File copied successfully

- [ ] **Step 3: Verify styles apply**

Reload the viewer in a browser and check:
- Pre-computed chains display with correct colors
- UA selector has proper styling
- Buttons have hover effects

---

## Task 9: Manual Testing

**Files:**
- None (testing only)

- [ ] **Step 1: Test pre-computed chain display**

1. Open a local viewer by running `python3 -m http.server 8765` in the `docs/` directory
2. Navigate to `http://localhost:8765/` and open an archived email
3. Click the LINKS tab
4. Look for links with a table displaying redirect hops
5. Verify: table shows #, Status, and URL columns with correct colors (blue for 3xx, green for 2xx)

Expected: Pre-computed chains display immediately in table format

- [ ] **Step 2: Test "Check Redirects" button for missing chains**

1. In the LINKS tab, look for links without pre-computed chains (older archives)
2. Verify these links show a "Check Redirects" button instead of a table

Expected: Button is visible and clickable

- [ ] **Step 3: Test live redirect checking**

1. Click "Check Redirects" button
2. Verify: loading spinner appears with "Checking redirects..." text
3. Wait for result (should take 1-3 seconds)
4. Verify: table appears with redirect chain from live check

Expected: Table updates with live data from Worker

- [ ] **Step 4: Test user agent selection**

1. In the LINKS tab header, change the UA dropdown to "Chrome Mobile"
2. Click "Re-check live" on a pre-computed chain or "Check Redirects" on a missing chain
3. Verify: request is made with Chrome Mobile user agent

Expected: Result may differ from Chrome Desktop (if server has UA-specific behavior)

- [ ] **Step 5: Test localStorage persistence**

1. Change UA to "Googlebot"
2. Reload the page
3. Verify: UA dropdown still shows "Googlebot"

Expected: Selection persists across page reloads

- [ ] **Step 6: Test error handling**

1. Click "Check Redirects" on a link pointing to a bad/nonexistent domain
2. Verify: error message displays (e.g., "Could not resolve hostname")
3. Verify: "Retry" button appears
4. Click "Retry"
5. Verify: same error message re-appears (as expected)

Expected: Error handling works gracefully

- [ ] **Step 7: Test with various real URLs**

1. Find or create a test link with known redirect behavior (e.g., a bit.ly link, Amazon short URL)
2. Click "Check Redirects"
3. Verify: the full redirect chain displays correctly
4. Manually verify with `curl -L -v` that the Worker result matches actual behavior

Expected: Results match manual redirect tracing

---

## Task 10: Commit Changes

**Files:**
- Multiple (design + implementation)

- [ ] **Step 1: Stage all changes**

Run:
```bash
git add \
  wrangler.toml \
  src/worker.js \
  templates/viewer.html \
  src/assets/css/style.css \
  docs/assets/css/style.css \
  docs/superpowers/plans/2026-03-26-redirect-checker.md
```

Expected: Files staged successfully

- [ ] **Step 2: Verify staged files**

Run: `git status`

Expected: All files listed under "Changes to be committed"

- [ ] **Step 3: Create commit**

Run:
```bash
git commit -m "feat: add live redirect checking with Cloudflare Worker

- Deploy serverless Worker to check redirect chains on demand
- Support 5 user agents: Chrome Desktop/Mobile, Googlebot, Outlook 2019, Apple Mail
- Show pre-computed chains instantly; allow live re-checking
- Add UA selector to links tab with localStorage persistence
- Display chains in compact table format (status code + URL per hop)
- Handle errors: timeout, DNS failure, max hops exceeded
- All code backwards-compatible with existing archives

Implements design from docs/superpowers/plans/2026-03-26-redirect-checker.md"
```

Expected: Commit succeeds with message

- [ ] **Step 4: Verify commit**

Run: `git log --oneline -5`

Expected: New commit appears at top of log with message starting with "feat: add live redirect checking"

---

## Testing Checklist

Use this checklist during manual testing to verify all features:

- [ ] Pre-computed chains display in table format (if `redirect_chain` exists in metadata)
- [ ] "Check Redirects" button appears for links without pre-computed chains
- [ ] "Re-check live" button works to refresh pre-computed chains
- [ ] Loading spinner shows while fetching
- [ ] Final result displays with correct status colors (3xx=blue, 2xx=green, 4xx+=red)
- [ ] User agent dropdown persists selection in localStorage
- [ ] Error messages display properly for network failures
- [ ] "Retry" button works after error
- [ ] Table shows full redirect chain (all intermediate hops)
- [ ] Final destination row is highlighted differently
- [ ] UA selector is visible and accessible in LINKS tab
- [ ] Worker endpoint URL is correct in viewer.html

---

## Notes

- **Worker URL:** Replace `https://archive-news-redirect-checker.USERNAME.workers.dev` with your actual deployed Worker URL in Task 6, Step 6
- **No pipeline changes:** The feature works with existing `redirect_chain` data structure
- **Backwards compatible:** Old archives without chains still work; users just click "Check Redirects"
- **Rate limiting:** Cloudflare free tier allows 100k requests/day; not a concern for small user base
- **CORS handled:** Worker response includes `Access-Control-Allow-Origin: *` header
