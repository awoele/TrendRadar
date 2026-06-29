param(
    [int]$Port = 3333
)

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

$existing = netstat -ano -p tcp | Select-String -Pattern (":$Port\s+.*LISTENING\s+(\d+)")

if ($existing) {
    $processId = [regex]::Match($existing.Line, "LISTENING\s+(\d+)").Groups[1].Value
    Write-Output "MCP server already listening on 127.0.0.1:$Port (PID $processId)."
    return
}

$logFile = Join-Path $logs "mcp-server.log"
$stdoutLog = Join-Path $logs "mcp-server.stdout.log"
$stderrLog = Join-Path $logs "mcp-server.stderr.log"

Push-Location $root
try {
    $env:PYTHONUTF8 = "1"
    $env:PYTHONWARNINGS = "ignore::DeprecationWarning"
    Write-Output "$(Get-Date -Format s) Starting MCP server on http://127.0.0.1:$Port/mcp" | Tee-Object -FilePath $logFile -Append
    $arguments = "-m mcp_server.server --transport http --host 127.0.0.1 --port $Port --project-root `"$root`""
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
}
finally {
    Pop-Location
}
