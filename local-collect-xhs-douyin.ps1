param(
    [string]$Since = "",
    [string]$Until = "",
    [int]$Days = 7,
    [int]$Max = 300,
    [int]$Scrolls = 5,
    [int]$SearchWaitMs = 6000,
    [int]$ScrollWaitMs = 850,
    [int]$KeywordDelayMs = 3000,
    [int]$WaitLoginMs = 0,
    [int]$KeywordLimit = 0,
    [string]$AgentsRoot = "D:\Documents\agents",
    [switch]$NoPrompt
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = "C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$node = "C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
$nodeModules = "C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules"

function Resolve-DateWindow {
    param([string]$StartValue, [string]$EndValue, [int]$LookbackDays)

    if (!$EndValue) {
        $EndValue = (Get-Date).ToString("yyyy-MM-dd")
    }
    if (!$StartValue) {
        $endDate = [datetime]::ParseExact($EndValue, "yyyy-MM-dd", [Globalization.CultureInfo]::InvariantCulture)
        $StartValue = $endDate.AddDays(-1 * $LookbackDays).ToString("yyyy-MM-dd")
    }
    return @($StartValue, $EndValue)
}

function Get-SearchKeywords {
    param(
        [string]$Path,
        [int]$Limit = 0
    )

    if (!(Test-Path -LiteralPath $Path)) {
        throw "Keyword file not found: $Path"
    }

    $keywords = New-Object System.Collections.Generic.List[string]
    foreach ($rawLine in Get-Content -LiteralPath $Path -Encoding UTF8) {
        $line = $rawLine.Trim()
        if (!$line -or $line.StartsWith("#")) {
            continue
        }
        if ($line -eq "[GLOBAL_FILTER]") {
            break
        }
        if ($line.StartsWith("!") -or $line.StartsWith("@")) {
            continue
        }
        if ($line.StartsWith("+")) {
            $line = $line.Substring(1).Trim()
        }
        if ($line -and !$keywords.Contains($line)) {
            $keywords.Add($line)
        }
    }

    if ($keywords.Count -eq 0) {
        throw "No search keywords found before [GLOBAL_FILTER]."
    }

    if ($Limit -gt 0 -and $keywords.Count -gt $Limit) {
        return (($keywords | Select-Object -First $Limit) -join ",")
    }

    return ($keywords -join ",")
}

if (!(Test-Path -LiteralPath $python)) {
    throw "Runtime Python not found: $python"
}
if (!(Test-Path -LiteralPath $node)) {
    throw "Runtime Node.js not found: $node"
}

$dateWindow = Resolve-DateWindow -StartValue $Since -EndValue $Until -LookbackDays $Days
$Since = $dateWindow[0]
$Until = $dateWindow[1]

$agentsRootPath = (Resolve-Path -LiteralPath $AgentsRoot).Path
$collectScript = Join-Path $agentsRootPath "scripts\collect_authenticated.cjs"
if (!(Test-Path -LiteralPath $collectScript)) {
    throw "Authenticated collector not found: $collectScript"
}

$keywords = Get-SearchKeywords -Path (Join-Path $root "config\frequency_words.txt") -Limit $KeywordLimit
$rawCsv = Join-Path $agentsRootPath ("data\trenderadar_xhs_douyin_raw_{0}_{1}.csv" -f $Since, $Until)
$classifiedDir = Join-Path $agentsRootPath ("out\trenderadar_xhs_douyin_{0}_{1}" -f $Since, $Until)
$importCsv = Join-Path $root ("data\imports\02_xhs_douyin_vibecoding_{0}_{1}.csv" -f $Since, $Until)

$env:NODE_PATH = "$nodeModules;$nodeModules\.pnpm\node_modules"
$env:PYTHONPATH = Join-Path $agentsRootPath "src"

$collectArgs = @(
    $collectScript,
    "--platform", "both",
    "--keywords", $keywords,
    "--out", $rawCsv,
    "--since", $Since,
    "--until", $Until,
    "--today", $Until,
    "--max", [string]$Max,
    "--search-only",
    "--scrolls", [string]$Scrolls,
    "--search-wait-ms", [string]$SearchWaitMs,
    "--scroll-wait-ms", [string]$ScrollWaitMs,
    "--keyword-delay-ms", [string]$KeywordDelayMs
)
if ($WaitLoginMs -gt 0) {
    $collectArgs += @("--wait-login-ms", [string]$WaitLoginMs)
}
if ($NoPrompt) {
    $collectArgs += "--no-prompt"
}

Push-Location $agentsRootPath
try {
    & $node @collectArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Xiaohongshu/Douyin collector failed with exit code $LASTEXITCODE"
    }

    & $python -m vibecase_agent.cli `
        --input $rawCsv `
        --out $classifiedDir `
        --no-web `
        --since $Since `
        --until $Until `
        --today $Until
    if ($LASTEXITCODE -ne 0) {
        throw "Topic classifier failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}

$caseRadarCsv = Join-Path $classifiedDir "case_radar.csv"
if (!(Test-Path -LiteralPath $caseRadarCsv)) {
    throw "Classifier did not create case_radar.csv: $caseRadarCsv"
}

$caseRows = @(Import-Csv -LiteralPath $caseRadarCsv)
if ($caseRows.Count -gt 0) {
    Copy-Item -LiteralPath $caseRadarCsv -Destination $importCsv -Force
    Write-Output "Imported tagged topics: $importCsv"
}
else {
    Write-Output "No tagged topics found; skipped data/imports update."
}

Push-Location $root
try {
    & $python scripts\prepare_pages_artifact.py --source output --dest public
    if ($LASTEXITCODE -ne 0) {
        throw "Panel build failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}

Write-Output "Local panel artifact: $(Join-Path $root 'public\content\index.html')"
Write-Output "Commit and push any new import CSV to publish it on GitHub Pages."
