# Newsletter Archiver - Project Context

## Project Overview

This is an automated DevOps solution that captures incoming newsletters from Gmail, sanitizes them, and archives them as a static, responsive website hosted on GitHub Pages. The pipeline runs every 30 minutes via GitHub Actions.

### Core Architecture

**Data Flow:**
```
Gmail Inbox → IMAP Fetch → process_email.py → Parser → Generator → docs/ → GitHub Pages
```

**4-Stage Pipeline:**
1. **Fetch** (`src/imap_client.py`): Connects to Gmail IMAP, fetches emails from `Github/archive-newsletters` label
2. **Parse** (`src/parser.py`): BeautifulSoup HTML parsing, image localization, tracking pixel detection, link audit, redirect resolution
3. **Generate** (`src/generator.py`): Jinja2 templates render viewer HTML and index page
4. **Deploy**: Static files in `docs/` served via GitHub Pages

## Building and Running

### Setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### Environment Variables
Required secrets (set in GitHub Repo or `.env`):
- `GMAIL_USER`: Gmail address
- `GMAIL_PASSWORD`: App password
- `GMAIL_LABEL`: Target label (default: `Github/archive-newsletters`)

### Commands
```bash
# Run full pipeline (fetches new emails from Gmail)
GMAIL_USER=you@gmail.com GMAIL_PASSWORD=app_password python process_email.py

# Force re-generate all existing archives
FORCE_UPDATE=true python process_email.py

# Re-render all viewer HTML from existing metadata (no IMAP, no image download)
python process_email.py --regen-only

# Quick-check for new emails (CI optimization)
# exits 0 = new emails found, exits 2 = nothing new
python process_email.py --check-new

# Manual injector (Streamlit UI for one-off uploads)
streamlit run injector.py

# Debug IMAP connection
python debug_gmail.py
```

### CI/CD
- **Workflow**: `.github/workflows/check_mail.yml` runs every 30 minutes
- **Optimization**: `--check-new` skips pipeline if no new emails
- **Manual trigger**: `workflow_dispatch` with `force_update` boolean input
- **Deployment**: Commits `docs/*` changes automatically via `git-auto-commit-action`

## Key Technical Concepts

### Smart Inversion Dark Mode
Instead of CSS re-theming, the viewer applies `filter: invert(1) hue-rotate(180deg)` to the email iframe. CSS variables use "pre-inverted" values so highlights flip back to intended colors when the filter is active.

### Multi-Zone Link Cards
Links are parsed into structured objects with:
- Header: Index, Clean Domain, Tracking Tag
- Body: Anchor text
- URL Zone: Monospace URL + clipboard interaction

### Badge Overlays
Link number badges render in the **parent** window using `getBoundingClientRect()` on iframe elements (necessary because the email iframe is sandboxed). Badges hide via clipping logic when links scroll out of viewport.

### Deterministic Email IDs
Each email gets a 12-char SHA-256 ID from `subject|date|message-id` for skip logic.

### JSON Injection Safety
In `generator.py`, `</script>` is escaped to `<\/script>` inside embedded JSON before being marked `Markup`-safe to prevent template injection.

## Development Conventions

### CSS Architecture
- Use `var(--vp-c-*)` and `var(--text-*)` variables from the getinside Design System
- Key tokens: `#0aaa8e` brand primary (light), `#6AE7C8` mint accent, `#F7F6F3` light bg, `#1b1b1f` dark bg
- After editing `src/assets/css/style.css`, copy to `docs/assets/css/style.css` (auto-done on pipeline run)
- Viewer-specific overrides live in `.viewer-layout .viewer-content` blocks (~line 1315 in style.css)

### Parser Changes
When adding new metadata:
1. Update `EmailParser` in `src/parser.py` first
2. Ensure returned dict keys match Jinja2 template expectations in `templates/viewer.html`
3. **Never pass URLs via `onclick="{{ url | tojson }}"`** — `tojson` produces double-quoted strings that break HTML attribute parsing. Use `data-url="{{ url }}"` and read `btn.dataset.url` in JS.
4. **Link target="_blank"**: The parser injects `<base target="_blank">` into email HTML via `inject_base_target()` so links open in new tabs.

### Template Updates
- Maintain JS-based sidebar logic in `templates/viewer.html`
- Be careful with variable escaping when injecting JSON into `<script>` tags
- Device mockup Chrome HTML structure lives in `#deviceFrame` with `.device-mockup[data-mode="mobile|tablet|desktop"]` selectors
- Iframe sandbox must include `allow-popups-to-escape-sandbox` for link clicks to work

### CSS Gotchas
- **Generic `header` selector** has `margin-bottom: 32px` — override with `.viewer-layout .viewer-header { margin-bottom: 0; }` to remove unwanted gaps
- **Mobile/Tablet borders**: Use `border-width: 3px` for clearer device outlines in light mode
- **Light mode devices**: Mobile/tablet use same light color scheme as desktop (no dark chrome override)

### Asset Isolation
All archived images MUST be saved to `docs/<id>/` or `docs/assets/` — never referenced from `src/`.

### Remote Configuration
- **Single remote**: `getinside` → `https://github.com/getinside-ops/archive-news.git`
- Always push with `git push getinside main`
- No `origin` remote — remove if it appears: `git remote remove origin`

## Component Map

| Component | File | Responsibility |
|-----------|------|----------------|
| Orchestrator | `process_email.py` | Main entry point, Gmail auth, IMAP fetching, triggers parsing/generation |
| IMAP Client | `src/imap_client.py` | `EmailFetcher` class, IMAP connection, header/full message fetching |
| Parser | `src/parser.py` | `EmailParser` class, BeautifulSoup logic, image localization, tracking detection, link audit, redirect resolution |
| Generator | `src/generator.py` | Jinja2 rendering, creates `index.html` and viewer files, asset copying |
| Viewer UI | `templates/viewer.html` | Responsive dashboard, fixed sidebar, mobile simulator, link interaction logic |
| Theme/UX | `src/assets/js/main.js` | Client-side theme toggling, search filtering, smart inversion |
| Manual Injector | `injector.py` | Streamlit app for out-of-band archival, fixes lazy-loading and relative paths |
| Worker | `src/worker.js` | Cloudflare serverless function for live viewer operations |

## Utility Scripts

- **`apply_changes.py`**: Applies bulk template/generator changes to existing archived viewers without re-running IMAP pipeline
- **`apply_base_target.py`**: Injects `<base target="_blank">` into all existing `docs/*/index.html` files so links open in new tabs
- **`debug_gmail.py`**: Standalone IMAP connection debugger — lists labels and message counts
- **`test_parser.py`**: Ad-hoc parser test script for checking parse output on local HTML files
- **`backfill_audit_data.py`**: Backfills audit metadata for existing archives

## Testing & Verification

### Playwright Testing (Before Committing)
Always test changes with Playwright before pushing:

```bash
# Navigate to viewer page and test link clicks
# Use browser_run_code to click links and verify popup opens
async (page) => {
  await page.waitForSelector('#emailFrame');
  const iframe = page.frameLocator('#emailFrame');
  const link = iframe.locator('a[href="https://example.com"]').first();
  const popupPromise = page.waitForEvent('popup', { timeout: 5000 });
  await link.click();
  const popup = await popupPromise;
  return { opened: popup !== null, url: popup?.url() };
}
```

### Local Preview
Playwright blocks `file://` URLs. Run a local server:
```bash
cd docs && python3 -m http.server 8765
```

## Dependencies

```
jinja2>=3.0,<4.0
beautifulsoup4>=4.12,<5.0
requests>=2.31,<3.0
lxml>=4.9,<6.0
streamlit>=1.35,<2.0
python-dotenv>=1.0,<2.0
```

## Legal

- **Author**: Benoît Prentout
- **License**: MIT
- Contents remain the property of their respective authors (technical demonstration)
