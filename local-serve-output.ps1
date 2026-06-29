param(
    [int]$Port = 8080
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $root ".venv\Scripts\python.exe"
$output = Join-Path $root "output"
$logs = Join-Path $root "logs"

if (!(Test-Path -LiteralPath $python)) {
    throw "Virtualenv Python not found: $python. Run uv sync from the project root first."
}

if (!(Test-Path -LiteralPath $output)) {
    New-Item -ItemType Directory -Path $output | Out-Null
}

if (!(Test-Path -LiteralPath $logs)) {
    New-Item -ItemType Directory -Path $logs | Out-Null
}

$existing = netstat -ano -p tcp | Select-String -Pattern (":$Port\s+.*LISTENING\s+(\d+)")

if ($existing) {
    $processId = [regex]::Match($existing.Line, "LISTENING\s+(\d+)").Groups[1].Value
    Write-Output "Report server already listening on 127.0.0.1:$Port (PID $processId)."
    return
}

$logFile = Join-Path $logs "report-server.log"
$stdoutLog = Join-Path $logs "report-server.stdout.log"
$stderrLog = Join-Path $logs "report-server.stderr.log"
Write-Output "$(Get-Date -Format s) Starting report server on http://127.0.0.1:$Port/" | Tee-Object -FilePath $logFile -Append
$arguments = "-m http.server $Port --bind 127.0.0.1 --directory `"$output`""
$process = Start-Process `
    -FilePath $python `
    -ArgumentList $arguments `
    -WorkingDirectory $root `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError $stderrLog `
    -Wait `
    -PassThru `
    -WindowStyle Hidden

exit $process.ExitCode
