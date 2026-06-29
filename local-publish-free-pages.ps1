param(
    [switch]$Stage,
    [switch]$Commit,
    [switch]$Push,
    [string]$Message = "chore: publish free GitHub Pages setup"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $root ".venv\Scripts\python.exe"

if (!(Test-Path -LiteralPath $python)) {
    throw "Virtualenv Python not found: $python"
}

Push-Location $root
try {
    & $python -m unittest tests.test_prepare_pages_artifact
    & $python scripts/prepare_pages_artifact.py --source output --dest public --keep-days 7

    $remote = git remote get-url origin 2>$null
    if (!$remote) {
        Write-Output "No git origin remote is configured yet."
        Write-Output "Create a public GitHub repository, then run:"
        Write-Output "  git remote add origin https://github.com/<your-name>/<repo>.git"
    }
    else {
        Write-Output "Git origin: $remote"
    }

    $files = @(
        ".github/workflows/free-pages.yml",
        ".gitignore",
        "config/config.yaml",
        "config/frequency_words.txt",
        "docs/free-public-github-pages.md",
        "docs/superpowers/plans/2026-06-29-github-pages-free-public.md",
        "local-publish-free-pages.ps1",
        "scripts/prepare_pages_artifact.py",
        "tests/test_prepare_pages_artifact.py"
    )

    if ($Stage -or $Commit -or $Push) {
        git add -- $files
        Write-Output "Staged free Pages files."
    }

    if ($Commit -or $Push) {
        git commit -m $Message
    }

    if ($Push) {
        git push -u origin HEAD
    }

    Write-Output ""
    Write-Output "Next GitHub setup:"
    Write-Output "1. Make the repository public."
    Write-Output "2. Go to Settings > Pages > Build and deployment > Source: GitHub Actions."
    Write-Output "3. Go to Actions > Free Public Pages > Run workflow."
    Write-Output "4. Public URL will be: https://<your-name>.github.io/<repo>/"
}
finally {
    Pop-Location
}
