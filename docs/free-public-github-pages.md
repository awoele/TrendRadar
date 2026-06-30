# Free Public GitHub Pages Setup

This setup publishes the TrendRadar content library for free with GitHub Actions and GitHub Pages.

## What Becomes Public

The public site contains the static content, stats, and owner configuration panels:

- `public/index.html`
- `public/content/index.html`
- `public/stats/index.html`
- `public/config/index.html`
- `public/content.json`
- `public/stats.json`
- `public/manifest.json`

The workflow does not run the legacy report crawler and does not publish local logs, SQLite databases, raw TXT snapshots, generated report HTML, or webhook secrets.

Your repository will be public, so these files are visible to others:

- `config/config.yaml`
- `config/frequency_words.txt`

Do not put private webhook URLs, email passwords, Telegram tokens, or other secrets in committed files. Put them in GitHub repository secrets.

## One-Time GitHub Setup

1. Create a public GitHub repository.
2. Push this repository to GitHub.
3. Open the repository on GitHub.
4. Go to `Settings > Pages`.
5. Set `Build and deployment > Source` to `GitHub Actions`.
6. Go to `Actions > Free Public Pages`.
7. Click `Run workflow`.

After the first successful run, the public content URL is:

```text
https://<your-name>.github.io/<repo>/content/
```

The owner-only configuration panel is:

```text
https://<your-name>.github.io/<repo>/config/
```

## Local Publish Helper

Run this after changing panels or imported content data:

```powershell
powershell -ExecutionPolicy Bypass -File "D:\Documents\热点库\TrendRadar\local-publish-free-pages.ps1"
```

To stage the files for commit:

```powershell
powershell -ExecutionPolicy Bypass -File "D:\Documents\热点库\TrendRadar\local-publish-free-pages.ps1" -Stage
```

To commit and push:

```powershell
powershell -ExecutionPolicy Bypass -File "D:\Documents\热点库\TrendRadar\local-publish-free-pages.ps1" -Push
```

## Updating Public Configuration

You can use the web configuration panel or edit these files locally:

- `config/config.yaml` for platforms and settings.
- `config/frequency_words.txt` for keyword groups.

The panel is published as a static GitHub Pages page, so it does not contain a server-side login system. It stays owner-only by requiring a GitHub token that has write access to this repository before it can load or save configuration.

Recommended fine-grained token permissions:

- Repository: `awoele/TrendRadar`
- Contents: `Read and write`
- Actions: `Read and write`

Saving from the panel commits changes to `master`. The `Free Public Pages` workflow runs on those config pushes and republishes the static content panels. The panel also attempts to trigger the workflow immediately after saving.

Do not paste webhook URLs, email passwords, Telegram tokens, or other secrets into the public config files. Put secrets in GitHub repository secrets instead.

## Limits

This is a no-server, static Pages setup. It republishes committed/imported content data; it does not crawl platforms or generate the legacy final report page by itself.
