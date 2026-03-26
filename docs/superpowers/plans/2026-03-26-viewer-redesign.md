# Viewer Page Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the email viewer into a focused QA audit tool — removing archive nav links, restructuring the header into three clear zones, and adding a fixed audit scorecard panel to the sidebar.

**Architecture:** All changes are confined to `templates/viewer.html` (HTML structure + Jinja2 scoring) and `src/assets/css/style.css` (layout + new component styles). After editing, `docs/assets/css/style.css` must be synced and all archived viewers regenerated via `--regen-only`.

**Tech Stack:** Jinja2 templates, vanilla CSS (getinside Design System), vanilla JS (existing, unchanged). No new dependencies.

---

## File Map

| File | Role | Changes |
|---|---|---|
| `templates/viewer.html` | Main template | Remove nav links; replace two-row header; add Jinja2 scoring; add summary panel; wrap detail log |
| `src/assets/css/style.css` | Shared CSS | Add three-zone header styles; add summary panel styles; add detail-log layout |
| `docs/assets/css/style.css` | Deployed CSS | Overwrite with copy of `src/assets/css/style.css` after edits |

---

## Existing CSS anchors (do not move)

These selectors exist in `src/assets/css/style.css` and are referenced by tasks below:

- `.viewer-sidebar` — line 806: already `display:flex; flex-direction:column; height:100vh` ✓
- `.sidebar-content` — line 829: currently `flex:1; overflow-y:auto; padding:16px 20px`
- `.viewer-layout .viewer-header` — line 1329: sets `flex-direction:column; padding:0`
- `.vh-top-bar` — line 1339 (will be unused after Task 2)
- `.vh-subject-bar` — line 1350 (will be unused after Task 2)

---

### Task 1: Remove nav links from the viewer

**Files:**
- Modify: `templates/viewer.html`

- [ ] **Step 1: Delete the `gi-topnav-links` block**

In `templates/viewer.html`, find and delete this entire block (lines ~32–39):

```html
            <div class="gi-topnav-links">
                <a href="https://getinside-ops.github.io/handbook/advertisers/" class="gi-topnav-link" target="_blank" rel="noopener">🛍️ Annonceurs</a>
                <a href="https://getinside-ops.github.io/handbook/publishers/" class="gi-topnav-link" target="_blank" rel="noopener">📦 Retailers</a>
                <a href="https://getinside-ops.github.io/handbook/faq/" class="gi-topnav-link" target="_blank" rel="noopener">❓ FAQ</a>
                <a href="https://app.getinside.media/" class="gi-topnav-link gi-topnav-saas" target="_blank" rel="noopener">
                    Accéder au SaaS
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M3.5 3H2a1 1 0 0 0-1 1v5a1 1 0 0 0 1 1h5a1 1 0 0 0 1-1V7.5M7 2h3m0 0v3m0-3L5 7" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
                </a>
            </div>
```

Keep the logo `<a href="https://getinside-ops.github.io/handbook/" ...>` and the `gi-topnav-actions` block (lang picker + theme toggle) untouched.

- [ ] **Step 2: Verify locally**

```bash
cd "/path/to/archive-news-1/docs"
python3 -m http.server 8765
```

Open `http://localhost:8765/<any-id>/index.html`. Confirm: no Annonceurs / Retailers / FAQ / SaaS links. Logo and theme toggle still present. Logo href still points to the handbook URL.

- [ ] **Step 3: Commit**

```bash
git add templates/viewer.html
git commit -m "feat(viewer): remove archive nav links, keep handbook logo"
```

---

### Task 2: Restructure viewer header into three-zone layout

**Files:**
- Modify: `templates/viewer.html` (the `<header class="viewer-header">` block, lines ~65–113)
- Modify: `src/assets/css/style.css` (add styles after line 1337, the end of `.viewer-layout .viewer-header`)

- [ ] **Step 1: Replace the entire `<header class="viewer-header">` block**

In `templates/viewer.html`, replace everything from `<header class="viewer-header">` through `</header>` (covering both `.vh-top-bar` and `.vh-subject-bar`) with:

```html
            <!-- Header: three-zone unified bar -->
            <header class="viewer-header">
                <div class="vh-unified-bar">
                    <!-- Left: Email identity -->
                    <div class="vh-zone-identity">
                        <span class="vh-sender-pill">{{ sender_name }}</span>
                        <h1 class="vh-subject" title="{{ subject }}">{{ subject }}</h1>
                        <span class="crm-badge" data-crm="{{ crm or 'Unknown' }}">{{ crm or 'Unknown' }}</span>
                        <span class="vh-date">{{ email_date }}</span>
                    </div>
                    <div class="vh-zone-divider" aria-hidden="true"></div>
                    <!-- Center: Device toggle (hidden on mobile) -->
                    <div class="vh-zone-view hide-mobile">
                        <div class="device-toggle">
                            <button class="device-btn device-chip active" onclick="setMode('mobile')" title="Mobile (1)" aria-label="Mobile view (1)">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="5" y="2" width="14" height="20" rx="2" ry="2"/><line x1="12" y1="18" x2="12.01" y2="18"/></svg>
                            </button>
                            <button class="device-btn device-chip" onclick="setMode('tablet')" title="Tablet (2)" aria-label="Tablet view (2)">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="2" width="16" height="20" rx="2" ry="2"/><line x1="12" y1="18" x2="12.01" y2="18"/></svg>
                            </button>
                            <button class="device-btn device-chip" onclick="setMode('desktop')" title="Desktop (3)" aria-label="Desktop view (3)">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
                            </button>
                        </div>
                    </div>
                    <div class="vh-zone-divider" aria-hidden="true"></div>
                    <!-- Right: QA Actions -->
                    <div class="vh-zone-actions">
                        <button class="btn btn-secondary" onclick="toggleHighlightLinks()" title="Highlight all links (H)">
                            <span id="highlightBtnText">Show Links</span>
                        </button>
                        <button class="btn btn-secondary" onclick="downloadEmailZip()" title="Download Email (D)">
                            Download
                        </button>
                        <button class="btn btn-secondary" id="shareBtn" onclick="shareEmail(this)" title="Share this email (S)">
                            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="vertical-align:-1px;margin-right:4px"><path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/><polyline points="16 6 12 2 8 6"/><line x1="12" y1="2" x2="12" y2="15"/></svg>Share
                        </button>
                    </div>
                </div>
            </header>
```

- [ ] **Step 2: Add three-zone header CSS**

In `src/assets/css/style.css`, after the `.viewer-layout .viewer-header` block (line ~1337), add:

```css
/* === THREE-ZONE UNIFIED HEADER === */
.vh-unified-bar {
    display: flex;
    align-items: center;
    width: 100%;
    background: var(--vw-sidebar);
    border-bottom: 1px solid var(--vw-border);
    min-height: 48px;
}

.vh-zone-identity {
    display: flex;
    align-items: center;
    gap: 8px;
    flex: 1;
    min-width: 0;
    padding: 8px 14px;
    overflow: hidden;
}

.vh-zone-identity .vh-subject {
    font-size: 0.85rem;
    font-weight: 500;
    margin: 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    flex: 1;
    min-width: 0;
}

.vh-zone-identity .vh-sender-pill {
    flex-shrink: 0;
}

.vh-zone-identity .vh-date {
    flex-shrink: 0;
    font-size: 0.75rem;
    color: var(--text-muted);
}

.vh-zone-divider {
    width: 1px;
    height: 32px;
    background: var(--vw-border);
    flex-shrink: 0;
}

.vh-zone-view {
    display: flex;
    align-items: center;
    padding: 8px 14px;
    flex-shrink: 0;
}

.vh-zone-actions {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 14px;
    flex-shrink: 0;
}
```

- [ ] **Step 3: Verify locally**

```bash
cd docs && python3 -m http.server 8765
```

Open a viewer. Confirm:
- Header is a single horizontal bar: identity left, device toggle center (with dividers), actions right
- Subject text truncates with ellipsis if long
- Keyboard shortcuts `?` button is gone
- Show Links, Download, Share buttons all work
- Device toggle chips switch iframe width (mobile/tablet/desktop)
- Dark mode: toggle theme, header colors flip correctly

- [ ] **Step 4: Commit**

```bash
git add templates/viewer.html src/assets/css/style.css
git commit -m "feat(viewer): three-zone unified header — identity | view | actions"
```

---

### Task 3: Add Jinja2 audit scoring variables

**Files:**
- Modify: `templates/viewer.html` (add scoring block just before `<aside class="viewer-sidebar"`)

No visual change in this task — only sets template variables used by the summary panel in Task 4.

- [ ] **Step 1: Insert the scoring block**

In `templates/viewer.html`, immediately before `<aside class="viewer-sidebar" role="region" aria-label="Sidebar">`, insert:

```jinja2
        {# === AUDIT SCORING (computed at render time, no new data required) === #}

        {# Metadata: FAIL if preheader or subject missing, WARN if clipping risk #}
        {% set _meta_preheader_ok = preheader and preheader | trim | length > 0 %}
        {% set _meta_subject_ok = subject and subject | trim | length > 0 %}
        {% set metadata_score = 'fail' if (not _meta_preheader_ok or not _meta_subject_ok) else ('warn' if email_size > 102000 else 'pass') %}

        {# Pixels: FAIL if no pixels detected #}
        {% set pixels_score = 'fail' if not detected_pixels else 'pass' %}

        {# Links: FAIL if any HTTP or DEV link; WARN if no tracking links (and links exist) #}
        {% set _http_links = links | selectattr('is_secure', 'equalto', false) | list %}
        {% set _dev_links = links | selectattr('is_dev') | list %}
        {% set _tracking_links = links | selectattr('is_tracking') | list %}
        {% set _links_fail = (_http_links | length > 0) or (_dev_links | length > 0) %}
        {% set _links_warn = (_tracking_links | length == 0) and (links | length > 0) %}
        {% set links_score = 'fail' if _links_fail else ('warn' if _links_warn else 'pass') %}
        {% set flagged_links_count = (_http_links | length) + (_dev_links | length) %}

        {# Overall: FAIL if any FAIL, WARN if any WARN, PASS if all PASS #}
        {% set _any_fail = metadata_score == 'fail' or pixels_score == 'fail' or links_score == 'fail' %}
        {% set _any_warn = metadata_score == 'warn' or pixels_score == 'warn' or links_score == 'warn' %}
        {% set overall_score = 'fail' if _any_fail else ('warn' if _any_warn else 'pass') %}
```

- [ ] **Step 2: Verify the template still renders without errors**

```bash
cd "/path/to/archive-news-1"
source .venv/bin/activate
python process_email.py --regen-only
```

Expected: no Jinja2 `UndefinedError` or `TemplateSyntaxError`. All existing viewer pages regenerate cleanly. If you see `UndefinedError: 'detected_pixels' is undefined`, check that the metadata.json for that viewer has a `detected_pixels` key — it should, per the parser output.

- [ ] **Step 3: Commit**

```bash
git add templates/viewer.html
git commit -m "feat(viewer): Jinja2 audit scoring — metadata/pixels/links/overall"
```

---

### Task 4: Add the fixed summary panel HTML and wrap the detail log

**Files:**
- Modify: `templates/viewer.html` (the `<aside class="viewer-sidebar">` section)

- [ ] **Step 1: Replace the sidebar inner HTML**

In `templates/viewer.html`, find the sidebar section. Replace everything between `<aside class="viewer-sidebar" role="region" aria-label="Sidebar">` and `</aside>` with:

```html
            <!-- Fixed: Audit Summary Panel -->
            <div class="audit-summary-panel">
                <div class="audit-overall audit-overall--{{ overall_score }}">
                    <span class="audit-overall-dot"></span>
                    <span class="audit-overall-label">{{ overall_score | upper }}</span>
                </div>
                <div class="audit-categories">
                    <div class="audit-category-row">
                        <svg class="audit-cat-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                        <span class="audit-cat-name">Metadata</span>
                        <span class="audit-cat-spacer"></span>
                        <span class="audit-cat-chip audit-chip--{{ metadata_score }}">{{ metadata_score | upper }}</span>
                    </div>
                    <div class="audit-category-row">
                        <svg class="audit-cat-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
                        <span class="audit-cat-name">Pixels</span>
                        <span class="audit-cat-count">{{ detected_pixels | length }}</span>
                        <span class="audit-cat-spacer"></span>
                        <span class="audit-cat-chip audit-chip--{{ pixels_score }}">{{ pixels_score | upper }}</span>
                    </div>
                    <div class="audit-category-row">
                        <svg class="audit-cat-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
                        <span class="audit-cat-name">Links</span>
                        <span class="audit-cat-count">{{ flagged_links_count }}/{{ links | length }}</span>
                        <span class="audit-cat-spacer"></span>
                        <span class="audit-cat-chip audit-chip--{{ links_score }}">{{ links_score | upper }}</span>
                    </div>
                </div>
            </div>

            <!-- Scrollable: Detail Log (existing tab content) -->
            <div class="audit-detail-log">
                <div class="tab-bar">
                    <button class="tab-btn active" data-tab="meta" onclick="showTab('meta')" data-i18n="tab_meta">META</button>
                    <button class="tab-btn" data-tab="pixels" onclick="showTab('pixels')"{% if not detected_pixels %} style="display:none"{% endif %} data-i18n="tab_pixels">PIXELS</button>
                    <button class="tab-btn" data-tab="links" onclick="showTab('links')"><span data-i18n="tab_links">LINKS</span> <span class="tab-count-badge">{{ links|length }}</span></button>
                </div>

                <div class="sidebar-content">

                    <!-- META Tab -->
                    <div class="tab-pane" id="tab-meta">
                        <div class="stat-grid">
                            <div class="stat-cell">
                                <span class="sc-label" data-i18n="meta_sender">Sender</span>
                                <span class="sc-value">{{ sender_name }}</span>
                            </div>
                            <div class="stat-cell">
                                <span class="sc-label" data-i18n="meta_crm">CRM</span>
                                <span class="sc-value text-cyan">{{ crm or 'Unknown' }}</span>
                            </div>
                            <div class="stat-cell sc-wide">
                                <span class="sc-label" data-i18n="meta_subject">Subject</span>
                                <span class="sc-value" title="{{ subject }}">{{ subject }}</span>
                            </div>
                            <div class="stat-cell sc-wide">
                                <span class="sc-label" data-i18n="meta_preheader">Preheader</span>
                                <span class="sc-value" title="{{ preheader }}">{{ preheader }}</span>
                            </div>
                            <div class="stat-cell">
                                <span class="sc-label" data-i18n="meta_received">Received</span>
                                <span class="sc-value">{{ email_date }}</span>
                            </div>
                            <div class="stat-cell">
                                <span class="sc-label" data-i18n="meta_size">Size</span>
                                <span class="sc-value text-yellow">{{ (email_size / 1024)|round(1) }} KB</span>
                            </div>
                            <div class="stat-cell">
                                <span class="sc-label" data-i18n="meta_clipping">Clipping Risk</span>
                                <span class="sc-value {% if email_size > 102000 %}text-orange{% else %}text-green{% endif %}">
                                    {% if email_size > 102000 %}High{% else %}Low{% endif %}
                                </span>
                            </div>
                            <div class="stat-cell">
                                <span class="sc-label" data-i18n="meta_links">Links</span>
                                <span class="sc-value">{{ links|length }}</span>
                            </div>
                        </div>
                    </div>

                    <!-- PIXELS Tab -->
                    <div class="tab-pane" id="tab-pixels" style="display:none;">
                        {% if detected_pixels %}
                        <div style="padding: 8px 10px;">
                            {% for pixel in detected_pixels %}
                            <div class="link-card-v2" id="px-{{ loop.index }}">
                                <div class="card-v2-header" onclick="toggleExpand(this.closest('.link-card-v2'))">
                                    <span class="card-v2-index">P</span>
                                    <span class="card-v2-domain">{{ pixel.domain or 'Unknown Provider' }}</span>
                                    <div style="display: flex; gap: 4px;">
                                        <span class="card-v2-tag tag-pixel">PIXEL</span>
                                    </div>
                                </div>
                                <div class="card-v2-url-preview" onclick="toggleExpand(this.closest('.link-card-v2'))">
                                    <code class="card-v2-url-truncated">{{ pixel.url }}</code>
                                    <button class="btn-card" title="Copy URL" onclick="event.stopPropagation(); copyLink(this, {{ pixel.url | tojson }})">
                                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                                    </button>
                                </div>
                                <div class="card-expand-zone">
                                    <div class="card-v2-body">
                                        <div class="card-v2-text">{{ pixel.status }}</div>
                                        <div class="card-v2-url-zone" style="flex-direction: column; align-items: stretch;">
                                            <code class="card-v2-url">{{ pixel.url }}</code>
                                            <div style="display: flex; gap: 8px; margin-top: 8px; justify-content: flex-end;">
                                                <button class="btn-card" title="Copy URL" onclick="event.stopPropagation(); copyLink(this, {{ pixel.url | tojson }})">
                                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            {% endfor %}
                        </div>
                        {% endif %}
                    </div>

                    <!-- LINKS Tab -->
                    <div class="tab-pane" id="tab-links" style="display:none;">
                        <div class="lf-filter-row" id="linkFilterRow">
                            <button class="lf-chip active" onclick="filterLinks('all')" data-i18n="filter_all">All</button>
                            <button class="lf-chip" onclick="filterLinks('tracking')" data-i18n="filter_tracking">Tracking</button>
                            <button class="lf-chip" onclick="filterLinks('http')" data-i18n="filter_http">HTTP</button>
                        </div>
                        <div style="padding: 8px 10px;">
                            {% for link in links %}
                            <div class="link-card-v2" id="lc-{{ link.index }}">
                                <div class="card-v2-header" onclick="toggleExpand(this.closest('.link-card-v2'))">
                                    <span class="card-v2-index" onclick="event.stopPropagation(); highlightLink({{ link.index }})">{{ link.index }}</span>
                                    <span class="card-v2-domain">{{ link.domain or 'External Link' }}</span>
                                    <div style="display: flex; gap: 4px;">
                                        {% if link.is_tracking %}<span class="card-v2-tag tag-tracking"><svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg> TRACK</span>{% endif %}
                                        {% if not link.is_secure %}<span class="card-v2-tag tag-unsecure"><svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg> HTTP</span>{% endif %}
                                        {% if link.is_dev %}<span class="card-v2-tag tag-dev"><svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg> DEV</span>{% endif %}
                                    </div>
                                </div>
                                <div class="card-v2-url-preview" onclick="toggleExpand(this.closest('.link-card-v2'))">
                                    <code class="card-v2-url-truncated">{{ link.original_url }}</code>
                                    <button class="btn-card" title="Copy URL" onclick="event.stopPropagation(); copyLink(this, {{ link.original_url | tojson }})">
                                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                                    </button>
                                </div>
                                <div class="card-expand-zone">
                                    <div class="card-v2-body">
                                        <div class="card-v2-text">{{ link.txt }}</div>
                                        <div class="card-v2-url-zone" style="flex-direction: column; align-items: stretch;">
                                            <code class="card-v2-url">{{ link.original_url }}</code>
                                            <div style="display: flex; gap: 8px; margin-top: 8px; justify-content: flex-end;">
                                                <button class="btn-card" title="Verify Link" onclick="event.stopPropagation(); runAudit(this, {{ link.original_url | tojson }}, {{ link.index }})">
                                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                                                </button>
                                                <button class="btn-card" title="Copy URL" onclick="event.stopPropagation(); copyLink(this, {{ link.original_url | tojson }})">
                                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                                                </button>
                                            </div>
                                        </div>
                                        <!-- Audit Log Container -->
                                        <div class="audit-log-container">
                                            <div class="audit-status-bar">
                                                <span class="audit-status-text">Scanning...</span>
                                            </div>
                                            <div class="audit-timeline"></div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            {% endfor %}
                        </div>
                    </div>

                </div><!-- /.sidebar-content -->
            </div><!-- /.audit-detail-log -->

            <!-- Sticky Footer -->
            <div class="sidebar-footer">
                <p style="font-size:0.72rem;color:var(--text-muted);text-align:center;margin:0;line-height:1.7;">
                    Contact Opérations : <a href="mailto:benoit@getinside.fr" style="color:var(--accent-primary);text-decoration:underline dotted;">benoit@getinside.fr</a>
                    · Studio : <a href="mailto:studio@getinside.fr" style="color:var(--accent-primary);text-decoration:underline dotted;">studio@getinside.fr</a><br>
                    © 2026 getinside. Tous droits réservés.
                </p>
            </div>
```

- [ ] **Step 2: Verify template renders**

```bash
source .venv/bin/activate
python process_email.py --regen-only
```

Expected: no errors. Open one regenerated viewer in the browser. Summary panel should appear above the tab bar. Chips show text (PASS/WARN/FAIL) but may not be styled yet — that's fine, CSS comes in Task 5.

- [ ] **Step 3: Commit**

```bash
git add templates/viewer.html
git commit -m "feat(viewer): two-panel sidebar — fixed audit summary + scrollable detail log"
```

---

### Task 5: Add CSS for summary panel and sidebar two-panel layout

**Files:**
- Modify: `src/assets/css/style.css`

- [ ] **Step 1: Fix `.sidebar-content` inside the detail log**

The current `.sidebar-content` rule (line 829) has `flex:1; overflow-y:auto`. Inside `.audit-detail-log` this would create a nested scroll. Add a scoped override after the existing `.sidebar-content` rule:

```css
/* Inside audit-detail-log, let the log container scroll, not sidebar-content */
.audit-detail-log .sidebar-content {
    flex: none;
    overflow-y: visible;
    padding: 0;
}
```

- [ ] **Step 2: Add the detail log and summary panel CSS**

In `src/assets/css/style.css`, after the `.vh-zone-actions` block added in Task 2, add:

```css
/* === SIDEBAR TWO-PANEL LAYOUT === */
.audit-detail-log {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
}

/* === AUDIT SUMMARY PANEL === */
.audit-summary-panel {
    flex-shrink: 0;
    padding: 14px 14px 12px;
    border-bottom: 1px solid var(--border-color);
    background: var(--bg-glass);
}

.audit-overall {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 12px;
}

.audit-overall-dot {
    width: 14px;
    height: 14px;
    border-radius: 50%;
    flex-shrink: 0;
}

.audit-overall--pass .audit-overall-dot {
    background: var(--accent-green);
    box-shadow: 0 0 8px rgba(46, 204, 113, 0.4);
}
.audit-overall--warn .audit-overall-dot {
    background: var(--accent-orange);
    box-shadow: 0 0 8px rgba(230, 126, 34, 0.4);
}
.audit-overall--fail .audit-overall-dot {
    background: var(--accent-red);
    box-shadow: 0 0 8px rgba(231, 76, 60, 0.4);
}

.audit-overall-label {
    font-family: var(--font-mono);
    font-size: 0.8rem;
    font-weight: 700;
    letter-spacing: 0.08em;
}

.audit-overall--pass .audit-overall-label { color: var(--accent-green); }
.audit-overall--warn .audit-overall-label { color: var(--accent-orange); }
.audit-overall--fail .audit-overall-label { color: var(--accent-red); }

.audit-categories {
    display: flex;
    flex-direction: column;
    gap: 7px;
}

.audit-category-row {
    display: flex;
    align-items: center;
    gap: 7px;
    font-size: 0.78rem;
}

.audit-cat-icon {
    color: var(--text-muted);
    flex-shrink: 0;
}

.audit-cat-name {
    color: var(--text-secondary);
    font-weight: 500;
}

.audit-cat-count {
    font-family: var(--font-mono);
    font-size: 0.72rem;
    color: var(--text-muted);
}

.audit-cat-spacer {
    flex: 1;
}

.audit-cat-chip {
    font-family: var(--font-mono);
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    padding: 2px 7px;
    border-radius: 4px;
    flex-shrink: 0;
}

.audit-chip--pass {
    background: rgba(46, 204, 113, 0.12);
    color: var(--accent-green);
    border: 1px solid rgba(46, 204, 113, 0.3);
}
.audit-chip--warn {
    background: rgba(230, 126, 34, 0.12);
    color: var(--accent-orange);
    border: 1px solid rgba(230, 126, 34, 0.3);
}
.audit-chip--fail {
    background: rgba(231, 76, 60, 0.12);
    color: var(--accent-red);
    border: 1px solid rgba(231, 76, 60, 0.3);
}
```

- [ ] **Step 3: Verify the full layout**

```bash
cd docs && python3 -m http.server 8765
```

Open a viewer and check all of the following:
- Summary panel is pinned at top of sidebar, does not scroll away when scrolling link list
- Summary panel shows overall dot + label (green PASS / orange WARN / red FAIL)
- Each category row shows icon, name, count, and colored chip
- Tab bar and detail content scroll independently below the summary panel
- Sidebar footer stays pinned at the bottom
- Toggle dark mode: panel and chips remain legible with correct colors
- Test with an email that has HTTP links — Links chip should show FAIL in red
- Test with an email with no preheader — Metadata chip should show FAIL in red

- [ ] **Step 4: Commit**

```bash
git add src/assets/css/style.css
git commit -m "feat(viewer): audit summary panel CSS and two-panel sidebar layout"
```

---

### Task 6: Sync CSS and regenerate all archived viewers

**Files:**
- Overwrite: `docs/assets/css/style.css`
- Regenerate: all `docs/<id>/index.html` files

- [ ] **Step 1: Sync CSS to docs**

```bash
cp "src/assets/css/style.css" "docs/assets/css/style.css"
```

- [ ] **Step 2: Regenerate all viewer pages from updated template**

```bash
source .venv/bin/activate
python process_email.py --regen-only
```

Expected: script prints progress for each archived email, no errors. All `docs/<id>/index.html` files are rewritten from the updated template.

- [ ] **Step 3: Final visual check across multiple viewers**

```bash
cd docs && python3 -m http.server 8765
```

Open 3–4 different archived viewers (pick ones with known issues — e.g. one with HTTP links, one without pixels). Confirm:
- No nav links in any viewer
- Three-zone header correct in all
- Summary panel scores are different across emails (not all PASS — that would indicate scoring logic isn't working)
- Tab switching (META / PIXELS / LINKS) still works
- Link highlighting and "Show Links" still works
- Download and Share buttons still work

- [ ] **Step 4: Final commit**

```bash
git add docs/assets/css/style.css docs/
git commit -m "feat(viewer): sync CSS and regenerate all archived viewers"
```
