$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $root ".venv\Scripts\python.exe"
$logs = Join-Path $root "logs"

if (!(Test-Path -LiteralPath $python)) {
    throw "Virtualenv Python not found: $python. Run uv sync from the project root first."
}

if (!(Test-Path -LiteralPath $logs)) {
    New-Item -ItemType Directory -Path $logs | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$logFile = Join-Path $logs "crawler-$timestamp.log"

Push-Location $root
try {
    $env:PYTHONUTF8 = "1"
    & $python -m trendradar *>&1 | Tee-Object -FilePath $logFile
    if ($LASTEXITCODE -ne 0) {
        throw "TrendRadar crawler failed with exit code $LASTEXITCODE. See $logFile"
    }
}
finally {
    Pop-Location
}
