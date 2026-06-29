$ErrorActionPreference = "Continue"

foreach ($name in "TrendRadar-KeepAlive", "TrendRadar-ReportServer", "TrendRadar-MCPServer") {
    Stop-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
}

foreach ($port in 8080, 3333) {
    $connections = netstat -ano -p tcp | Select-String -Pattern (":$port\s+.*LISTENING\s+(\d+)")

    foreach ($connection in $connections) {
        $processId = [regex]::Match($connection.Line, "LISTENING\s+(\d+)").Groups[1].Value
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
    }
}

& (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "local-health-check.ps1")
