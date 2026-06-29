# GitHub Pages Free Public Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish TrendRadar reports publicly for free using GitHub Actions and GitHub Pages while keeping local Windows usage intact.

**Architecture:** Add a separate Pages workflow that runs the crawler on a schedule, packages only the public report artifacts, and deploys them with GitHub Pages. Keep private/local scripts separate from public publishing so the local long-running setup and cloud publishing do not depend on each other.

**Tech Stack:** GitHub Actions, GitHub Pages, Python 3.12, existing TrendRadar Python package.

---

### Task 1: Package Public Pages Output

**Files:**
- Create: `scripts/prepare_pages_artifact.py`
- Test by running: `python scripts/prepare_pages_artifact.py --source output --dest public --keep-days 7`

- [ ] **Step 1: Create a packaging script**

Create a Python script that copies `output/index.html`, recent HTML reports, and a small manifest into `public/`.

- [ ] **Step 2: Run the script locally**

Run: `python scripts/prepare_pages_artifact.py --source output --dest public --keep-days 7`

Expected: `public/index.html` exists and `public/manifest.json` lists copied files.

### Task 2: Add GitHub Pages Workflow

**Files:**
- Create: `.github/workflows/free-pages.yml`

- [ ] **Step 1: Add scheduled workflow**

Create a workflow that checks out the repo, installs dependencies, runs `python -m trendradar`, packages `public/`, uploads a Pages artifact, and deploys it.

- [ ] **Step 2: Keep permissions narrow**

Use `contents: read`, `pages: write`, and `id-token: write`.

### Task 3: Add Local Free-Publish Helper

**Files:**
- Create: `local-publish-free-pages.ps1`
- Create: `docs/free-public-github-pages.md`

- [ ] **Step 1: Add a local helper**

Create a script that checks the current git remote, validates required files, stages the public publishing files plus config, and prints the exact GitHub setup steps.

- [ ] **Step 2: Document setup**

Document the no-cost setup: public GitHub repository, Pages enabled from GitHub Actions, optional notification secrets, and the public URL pattern.

### Task 4: Verify

**Files:**
- Run against created files.

- [ ] **Step 1: Validate YAML shape**

Run a parser over `.github/workflows/free-pages.yml` to ensure it is valid YAML.

- [ ] **Step 2: Generate public artifact**

Run the packaging script locally and verify `public/index.html` and `public/manifest.json`.

