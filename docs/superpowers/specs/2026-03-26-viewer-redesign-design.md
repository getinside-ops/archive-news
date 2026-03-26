# Viewer Page Redesign — Design Spec

**Date:** 2026-03-26
**Scope:** `templates/viewer.html` + related CSS in `src/assets/css/style.css`

---

## Context

The viewer page is a QA/audit tool for email campaigns. Both internal team members and external stakeholders (advertisers, brands) use it to validate a specific email — checking that URLs, tracking pixels, and redirect chains are correctly set up, and that the email renders correctly across device sizes.

Users receive a direct link to a specific email. They should not be able to easily navigate to the archive homepage or between emails. The viewer must integrate visually into the handbook ecosystem (`https://getinside-ops.github.io/handbook/`).

---

## 1. Navigation

### What changes
- The `gi-topnav-links` block is removed entirely (Annonceurs, Retailers, FAQ, SaaS links).
- The logo `<a>` keeps its `href="https://getinside-ops.github.io/handbook/"` — unchanged. This is the only navigation allowed.
- The language picker and theme toggle remain in `gi-topnav-actions`.

### Result
```
[logo → handbook] ————————————— [lang] [theme toggle]
```

### What does NOT change
- No prev/next email navigation is added anywhere.
- No "back to archive" link anywhere on the page.

---

## 2. Header

### What changes
The current two-row header (`vh-top-bar` + `vh-subject-bar`) is replaced by a single horizontal bar with three distinct zones separated by subtle visual dividers:

```
[Sender · Subject · CRM badge · Date]  |  [Mobile  Tablet  Desktop]  |  [Show Links  Download  Share]
         LEFT: email identity                  CENTER: view                    RIGHT: actions
```

**Left — Email identity:**
- Sender pill
- Truncated subject (with `title` for full text on hover)
- CRM badge (moved from `vh-top-bar`)
- Date

**Center — View controls:**
- Device toggle chips: Mobile / Tablet / Desktop
- Visually labeled or grouped so it reads as a rendering tool, not a QA action

**Right — QA actions:**
- Show Links button
- Download button
- Share button
- The keyboard shortcuts `?` button is removed (low value for external stakeholders)

### Rationale
Device toggle and QA actions were mixed in `vh-top-bar` without visual hierarchy. Separating them into three zones makes the header scannable and self-explanatory.

---

## 3. Sidebar

### Structure
The sidebar is split into two stacked panels:

#### 3a. Fixed Summary Panel (top, ~220px, no scroll)

A pinned audit scorecard always visible regardless of scroll position.

**Overall score** — large colored indicator + label:
- `PASS` — green
- `WARN` — yellow/orange
- `FAIL` — red

**Three category rows**, each showing: icon · name · status chip · key count

| Category | Icon | Count shown |
|---|---|---|
| Metadata | document | — |
| Pixels | tracking dot | pixel count |
| Links | chain | flagged link count / total |

#### 3b. Scrollable Detail Log (bottom, fills remaining height)

The existing tab-bar (META / PIXELS / LINKS) and all tab content is moved here, unchanged. Users drill into details after reading the summary.

The `sidebar-footer` (contact emails, copyright) remains pinned at the very bottom.

---

## 4. Scoring Logic

All scores are computed at Jinja2 render time from existing template variables. No new backend data is required.

### Metadata score

| Condition | Score |
|---|---|
| `preheader` is empty or missing | FAIL |
| `subject` is empty | FAIL |
| `email_size > 102000` (clipping risk) | WARN |
| All clear | PASS |

### Pixels score

| Condition | Score |
|---|---|
| `detected_pixels` is empty | FAIL |
| At least one pixel detected | PASS |

### Links score

| Condition | Score |
|---|---|
| Any link has `is_dev = true` | FAIL |
| Any link has `is_secure = false` | FAIL |
| No links have `is_tracking = true` AND `links\|length > 0` | WARN |
| All clear | PASS |

### Overall score

| Condition | Score |
|---|---|
| Any category is FAIL | FAIL |
| Any category is WARN (no FAIL) | WARN |
| All categories PASS | PASS |

---

## 5. Files Affected

| File | Change |
|---|---|
| `templates/viewer.html` | Nav links removed, header restructured, sidebar summary panel added |
| `src/assets/css/style.css` | New styles for summary panel, three-zone header, category rows |
| `docs/assets/css/style.css` | Synced copy of the above (manual copy after edit) |

The `apply_changes.py` script should be run after changes to backfill existing archived viewers.

---

## 6. Out of Scope

- No authentication or URL-param-based audience switching (both internal and external see the same view)
- No backend changes — all scoring computed from existing Jinja2 variables
- No changes to the index page (`templates/index.html`)
- No new data fetched by the parser — scoring uses what is already in `metadata.json`
