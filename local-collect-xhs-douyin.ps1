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
    [string]$XhsSkillScript = "",
    [switch]$NoPrompt
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$workspaceRoot = Split-Path -Parent $root
$defaultXhsSkillScript = Join-Path $workspaceRoot "skills\xiaohongshu-crawler\scripts\crawl_xhs.py"
$python = "C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

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

function Resolve-TikHubPublishTime {
    param([int]$LookbackDays)

    if ($LookbackDays -le 1) {
        return "1"
    }
    if ($LookbackDays -le 7) {
        return "7"
    }
    return "180"
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

$dateWindow = Resolve-DateWindow -StartValue $Since -EndValue $Until -LookbackDays $Days
$Since = $dateWindow[0]
$Until = $dateWindow[1]
$tikhubPublishTime = Resolve-TikHubPublishTime -LookbackDays $Days

$agentsRootPath = (Resolve-Path -LiteralPath $AgentsRoot).Path
$xhsImporter = Join-Path $root "scripts\import_redfox_xhs.py"
if (!(Test-Path -LiteralPath $xhsImporter)) {
    throw "Xiaohongshu skill importer not found: $xhsImporter"
}

$douyinSearchScript = Join-Path $root "scripts\fetch_tikhub_douyin_search.py"
if (!(Test-Path -LiteralPath $douyinSearchScript)) {
    throw "TikHub Douyin keyword search script not found: $douyinSearchScript"
}

if (!$XhsSkillScript) {
    $XhsSkillScript = $defaultXhsSkillScript
}
if (!(Test-Path -LiteralPath $XhsSkillScript)) {
    throw "xiaohongshu-crawler skill script not found: $XhsSkillScript"
}
$xhsSkillScriptPath = (Resolve-Path -LiteralPath $XhsSkillScript).Path

$keywords = Get-SearchKeywords -Path (Join-Path $root "config\frequency_words.txt") -Limit $KeywordLimit
$tmpDir = Join-Path $root ".tmp"
$xhsRawJson = Join-Path $tmpDir ("xhs_skill_raw_{0}_{1}.json" -f $Since, $Until)
$xhsRawCsv = Join-Path $tmpDir ("xhs_skill_raw_{0}_{1}.csv" -f $Since, $Until)
$xhsClassifiedDir = Join-Path $tmpDir ("xhs_skill_classified_{0}_{1}" -f $Since, $Until)
$xhsImportCsv = Join-Path $root ("data\imports\02_xhs_skill_vibecoding_{0}_{1}.csv" -f $Since, $Until)
$douyinRawCsv = Join-Path $tmpDir ("tikhub_douyin_search_raw_{0}_{1}.csv" -f $Since, $Until)
$douyinClassifiedDir = Join-Path $tmpDir ("tikhub_douyin_search_classified_{0}_{1}" -f $Since, $Until)
$douyinImportCsv = Join-Path $root ("data\imports\03_douyin_tikhub_vibecoding_{0}_{1}.csv" -f $Since, $Until)

$env:PYTHONPATH = Join-Path $agentsRootPath "src"

& $python $xhsImporter `
    --keywords $keywords `
    --start-date $Since `
    --end-date $Until `
    --skill-script $xhsSkillScriptPath `
    --classifier-root $agentsRootPath `
    --raw-json-out $xhsRawJson `
    --raw-csv-out $xhsRawCsv `
    --classified-out-dir $xhsClassifiedDir `
    --import-out $xhsImportCsv
if ($LASTEXITCODE -ne 0) {
    throw "Xiaohongshu skill collector failed with exit code $LASTEXITCODE"
}

if (Test-Path -LiteralPath $xhsImportCsv) {
    $xhsRows = @(Import-Csv -LiteralPath $xhsImportCsv)
    if ($xhsRows.Count -eq 0) {
        Remove-Item -LiteralPath $xhsImportCsv -Force
        Write-Output "No Xiaohongshu skill topics found; skipped XHS import update."
    }
    else {
        Write-Output "Imported Xiaohongshu skill topics: $xhsImportCsv"
    }
}

& $python $douyinSearchScript `
    --keywords $keywords `
    --since $Since `
    --until $Until `
    --today $Until `
    --max-per-keyword $Max `
    --publish-time $tikhubPublishTime `
    --out $douyinRawCsv
if ($LASTEXITCODE -ne 0) {
    throw "TikHub Douyin keyword search failed with exit code $LASTEXITCODE"
}

$douyinRawRows = @()
if (Test-Path -LiteralPath $douyinRawCsv) {
    $douyinRawRows = @(Import-Csv -LiteralPath $douyinRawCsv)
}

if ($douyinRawRows.Count -gt 0) {
    Push-Location $agentsRootPath
    try {
        & $python -m vibecase_agent.cli `
            --input $douyinRawCsv `
            --out $douyinClassifiedDir `
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

    $caseRadarCsv = Join-Path $douyinClassifiedDir "case_radar.csv"
    if (!(Test-Path -LiteralPath $caseRadarCsv)) {
        throw "Classifier did not create case_radar.csv: $caseRadarCsv"
    }

    $caseRows = @(Import-Csv -LiteralPath $caseRadarCsv)
    if ($caseRows.Count -gt 0) {
        Copy-Item -LiteralPath $caseRadarCsv -Destination $douyinImportCsv -Force
        Write-Output "Imported TikHub Douyin keyword topics: $douyinImportCsv"
    }
    else {
        Write-Output "No TikHub Douyin tagged topics found; skipped Douyin import update."
    }
}
else {
    Write-Output "No TikHub Douyin keyword rows found; skipped Douyin import update."
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
