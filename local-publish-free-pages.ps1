param(
    [switch]$Stage,
    [switch]$Commit,
    [switch]$Push,
    [string]$Message = "chore: publish xhs douyin panels"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = "C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if (!(Test-Path -LiteralPath $python)) {
    throw "Runtime Python not found: $python"
}

Push-Location $root
try {
    & $python -m unittest discover -s tests
    if ($LASTEXITCODE -ne 0) {
        throw "Tests failed with exit code $LASTEXITCODE"
    }

    & $python scripts\prepare_pages_artifact.py --source output --dest public
    if ($LASTEXITCODE -ne 0) {
        throw "Panel build failed with exit code $LASTEXITCODE"
    }

    $files = @(
        ".github/workflows/free-pages.yml",
        ".gitignore",
        "README.md",
        "config/config.yaml",
        "config/frequency_words.txt",
        "data/imports",
        "docs/free-public-github-pages.md",
        "local-collect-xhs-douyin.ps1",
        "local-publish-free-pages.ps1",
        "scripts/import_redfox_xhs.py",
        "scripts/prepare_pages_artifact.py",
        "tests",
        "web/config-panel",
        "web/content-panel",
        "web/stats-panel"
    )

    if ($Stage -or $Commit -or $Push) {
        git add -- $files
        Write-Output "Staged Xiaohongshu/Douyin panel files."
    }

    if ($Commit -or $Push) {
        git commit -m $Message
    }

    if ($Push) {
        git push awoele HEAD:master
    }

    Write-Output ""
    Write-Output "Local content panel: $root\public\content\index.html"
    Write-Output "Public content panel: https://awoele.github.io/TrendRadar/content/"
    Write-Output "Owner config panel: https://awoele.github.io/TrendRadar/config/"
}
finally {
    Pop-Location
}
