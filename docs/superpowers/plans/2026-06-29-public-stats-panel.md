# Public Stats Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a public, read-only `/stats/` page that shows crawl/report statistics without exposing edit access.

**Architecture:** Extend the existing Pages artifact preparation step to derive `stats.json` from generated report HTML files and the root `index.html`. Copy a new static `web/stats-panel` app to `public/stats`, where browser-side JavaScript renders the JSON into compact summary cards, platform tables, keyword rankings, failures, and report history.

**Tech Stack:** Python standard library for artifact generation, static HTML/CSS/JavaScript for the panel, existing `unittest` test suite.

---

### Task 1: Add Stats Artifact Tests

**Files:**
- Modify: `tests/test_prepare_pages_artifact.py`

- [ ] **Step 1: Write failing tests**

Add tests that create a small fake `output` tree containing `index.html`, dated report HTML, and assert:
- `public/stats.json` exists.
- `manifest.json` contains `stats_panel`.
- the stats JSON includes total reports, latest report path, platform names parsed from report HTML, keyword groups parsed from report HTML, failed platforms parsed from report HTML, and a generated timestamp.
- `web/stats-panel` assets are copied to `public/stats`.

- [ ] **Step 2: Run tests to verify red**

Run: `.venv\Scripts\python.exe -m pytest tests/test_prepare_pages_artifact.py -q`

Expected: fail because `stats.json`, `stats_panel`, and stats panel copying do not exist yet.

### Task 2: Generate `stats.json`

**Files:**
- Modify: `scripts/prepare_pages_artifact.py`

- [ ] **Step 1: Implement minimal stats generation**

Add helper functions that read copied report HTML files and count:
- report count and latest report path.
- platform occurrence counts from source labels.
- keyword/word group counts from report section headers.
- failed platform names from obvious failed-platform text when present.
- generated timestamp in ISO-8601 UTC.

- [ ] **Step 2: Write the output**

Write `public/stats.json` with `ensure_ascii=False`, include `stats_json` and `stats_panel` in manifest when available.

- [ ] **Step 3: Run focused tests**

Run: `.venv\Scripts\python.exe -m pytest tests/test_prepare_pages_artifact.py -q`

Expected: pass.

### Task 3: Add Static Stats Panel

**Files:**
- Create: `web/stats-panel/index.html`
- Create: `web/stats-panel/styles.css`
- Create: `web/stats-panel/app.js`

- [ ] **Step 1: Build the static shell**

Create a public read-only page with links back to `/` and `/config/`.

- [ ] **Step 2: Render real stats**

Fetch `../stats.json`, render summary cards, platform rows, keyword rows, failure list, and report links. Show a clear empty/error state if JSON cannot load.

- [ ] **Step 3: Keep controls read-only**

Do not include token input or write actions on the stats page.

### Task 4: Verify Locally And Deploy

**Files:**
- Modify as needed only if verification finds a real issue.

- [ ] **Step 1: Run tests**

Run: `.venv\Scripts\python.exe -m pytest tests/test_prepare_pages_artifact.py -q`

- [ ] **Step 2: Run full crawler locally**

Run with local storage and notifications disabled to regenerate reports.

- [ ] **Step 3: Prepare public artifact**

Run: `.venv\Scripts\python.exe scripts/prepare_pages_artifact.py --source output --dest public --keep-days 7`

- [ ] **Step 4: Verify static files**

Check `public/stats.json`, `public/stats/index.html`, and key fields in JSON.

- [ ] **Step 5: Commit and push**

Commit the implementation and push `public-free` to `awoele/master`, then watch GitHub Actions and verify:
- `https://awoele.github.io/TrendRadar/stats/`
- `https://awoele.github.io/TrendRadar/stats.json`
