# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

Automated pipeline that fetches newsletters from a Gmail label via IMAP, sanitizes and archives them as a static responsive website, then deploys to GitHub Pages. The GitHub Actions workflow runs every 30 minutes.

## Running the pipeline

```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run the main pipeline (requires env vars)
GMAIL_USER=you@gmail.com GMAIL_PASSWORD=app_password python process_email.py

# Force re-generate all existing archives
FORCE_UPDATE=true python process_email.py

# Manual injector (Streamlit UI for one-off uploads)
streamlit run injector.py
```

No test suite exists in this project.

## Architecture

The pipeline has 4 stages orchestrated by `process_email.py`:

1. **Fetch** (`src/imap_client.py` — `EmailFetcher`): Connects to Gmail IMAP, fetches headers for all emails in the `Github/archive-newsletters` label. Each email gets a deterministic 12-char SHA-256 ID from `subject|date|message-id`. Already-archived IDs are skipped unless `FORCE_UPDATE=true`.

2. **Parse** (`src/parser.py` — `EmailParser`): Takes raw HTML + IMAP attachments. Runs in sequence:
   - `detect_crm()` — identifies the ESP (Mailchimp, Brevo, Klaviyo, etc.) from headers then URL patterns
   - `clean_and_process()` — detects/hides tracking pixels, extracts preheader text, builds structured link list with audit flags (`is_tracking`, `is_secure`, `is_dev`)
   - `resolve_redirects_parallel()` — follows redirect chains for all links (10 workers, up to 15 hops each) so the static viewer doesn't need CORS requests
   - `download_images_parallel()` — localizes all remote images to `docs/<id>/img_N.ext` (5 workers); handles `cid:` inline attachments, lazy-load attrs

3. **Generate** (`src/generator.py`): Renders Jinja2 templates from `templates/`. Produces:
   - `docs/<id>/index.html` — the viewer (fixed sidebar, iframe for email, link audit panel)
   - `docs/index.html` — the archive landing page
   - Copies `src/assets/` → `docs/assets/` after each run

4. **Output** (`docs/`): Static site root served by GitHub Pages. Each archived email lives in `docs/<12-char-id>/` alongside its localized images and `metadata.json`.

## Key design notes

**Incremental sync**: `metadata.json` presence is the skip signal. If it exists and `FORCE_UPDATE` is false, the email is loaded from disk and not re-fetched.

**Smart Inversion dark mode**: The viewer applies `filter: invert(1) hue-rotate(180deg)` to the email iframe. CSS variables in `templates/viewer.html` use "pre-inverted" values so highlights/shadows flip back to the intended colors when the filter is active.

**Badge overlays**: Link number badges are rendered in the parent window using `getBoundingClientRect()` on iframe elements — necessary because the email iframe is sandboxed. Badges are hidden via clipping logic when links scroll out of the iframe viewport.

**JSON injection safety**: In `generator.py`, `</script>` is escaped to `<\/script>` inside embedded JSON before being marked `Markup`-safe to prevent template injection.

## Deployment

This repo deploys to **`getinside-ops/archive-news`** on GitHub. GitHub Pages serves from `main /docs`.

- **Single remote**: `getinside` → `https://github.com/getinside-ops/archive-news.git`. Always push with `git push getinside main`. There is no `origin` remote — if one appears, remove it with `git remote remove origin`.
- Required secrets: `GMAIL_USER` + `GMAIL_PASSWORD` only. `GEMINI_API_KEY` is **not** referenced in any `.py` file — do not add it.
- To reconfigure Pages source: `gh api repos/getinside-ops/archive-news/pages --method PUT -f 'source[branch]=main' -f 'source[path]=/docs'`
  (JSON object format is rejected by the API — use nested `-f` field syntax only.)

## Contributing rules (from README)

- **Parser changes**: Update `EmailParser` in `src/parser.py` first; ensure the returned dict keys match Jinja2 template expectations in `templates/viewer.html`.
- **Template updates**: Maintain the JS-based sidebar logic; be careful with variable escaping when injecting JSON into `<script>` tags.
- **Assets**: All archived images must be saved to `docs/assets/` (via `copy_assets`) or per-email folders — never referenced from `src/`.
- **CSS**: Use the getinside Design System palette defined in `src/assets/css/style.css` and documented in `DESIGN-SYSTEM.md`. Key tokens: `#0aaa8e` brand primary (light), `#6AE7C8` mint accent, `#F7F6F3` light bg, `#1b1b1f` dark bg. After editing CSS, copy `src/assets/css/style.css` → `docs/assets/css/style.css`.
