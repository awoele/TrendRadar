# Free Public GitHub Pages Setup

This setup publishes TrendRadar reports for free with GitHub Actions and GitHub Pages.

## What Becomes Public

The public site contains only the generated HTML report artifact:

- `public/index.html`
- `public/reports/<date>/*.html`
- `public/manifest.json`

The workflow does not publish local logs, SQLite databases, raw TXT snapshots, or webhook secrets.

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

After the first successful run, the public report URL is:

```text
https://<your-name>.github.io/<repo>/
```

## Local Publish Helper

Run this after changing platforms or keywords:

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

Edit these files locally:

- `config/config.yaml` for platforms and report mode.
- `config/frequency_words.txt` for keyword groups.

Then commit and push the changes. The hourly `Free Public Pages` workflow will publish the next report automatically. You can also run the workflow manually from GitHub Actions.

## Optional Notifications

If you want notifications later, add credentials to GitHub repository secrets instead of committed files:

- `FEISHU_WEBHOOK_URL`
- `WEWORK_WEBHOOK_URL`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `EMAIL_FROM`
- `EMAIL_PASSWORD`
- `EMAIL_TO`

Then set repository variable `ENABLE_NOTIFICATION` to `true`.

## Limits

This is a no-server, no-card setup. GitHub scheduled workflows are best-effort, so runs may be delayed. It is good for hourly public reports, not minute-level real-time monitoring.
