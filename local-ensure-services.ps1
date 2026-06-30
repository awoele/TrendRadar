$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$logs = Join-Path $root "logs"

if (!(Test-Path -LiteralPath $logs)) {
    New-Item -ItemType Directory -Path $logs | Out-Null
}

function Test-PortListening {
    param([int]$Port)

    $conn = netstat -ano -p tcp | Select-String -Pattern (":$Port\s+.*LISTENING\s+(\d+)") | Select-Object -First 1

    return [bool]$conn
}

function Start-ServiceScript {
    param(
        [string]$Name,
        [string]$ScriptPath,
        [int]$Port
    )

    if (Test-PortListening -Port $Port) {
        Write-Output "$Name already listening on 127.0.0.1:$Port"
        return
    }

    Write-Output "$(Get-Date -Format s) Starting $Name on port $Port"
    Start-Process `
        -FilePath "powershell.exe" `
        -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $ScriptPath) `
        -WorkingDirectory $root `
        -WindowStyle Hidden | Out-Null
}

Start-ServiceScript `
    -Name "TrendRadar MCP server" `
    -ScriptPath (Join-Path $root "local-start-mcp-http.ps1") `
    -Port 3333

$deadline = (Get-Date).AddSeconds(45)
do {
    $mcpOk = Test-PortListening -Port 3333
    if ($mcpOk) { break }
    Start-Sleep -Seconds 2
} while ((Get-Date) -lt $deadline)

& (Join-Path $root "local-health-check.ps1")
