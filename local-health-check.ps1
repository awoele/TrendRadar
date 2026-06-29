$ErrorActionPreference = "Continue"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$output = Join-Path $root "output"
$latestReport = $null

if (Test-Path -LiteralPath $output) {
    $latestReport = Get-ChildItem -LiteralPath $output -Recurse -File -Filter "*.html" |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}

$reportHttp = $null
try {
    $response = Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8080/index.html" -TimeoutSec 10
    $reportHttp = "$($response.StatusCode) ($($response.Content.Length) bytes)"
}
catch {
    $reportHttp = "FAILED: $($_.Exception.Message)"
}

$ports = foreach ($port in 8080, 3333) {
    $conn = netstat -ano -p tcp | Select-String -Pattern (":$port\s+.*LISTENING\s+(\d+)") | Select-Object -First 1
    $processId = if ($conn) { [regex]::Match($conn.Line, "LISTENING\s+(\d+)").Groups[1].Value } else { $null }
    [pscustomobject]@{
        Port = $port
        Listening = [bool]$conn
        ProcessId = $processId
    }
}

$tasks = foreach ($name in "TrendRadar-Crawler", "TrendRadar-KeepAlive", "TrendRadar-ReportServer", "TrendRadar-MCPServer") {
    $task = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
    $info = Get-ScheduledTaskInfo -TaskName $name -ErrorAction SilentlyContinue
    [pscustomobject]@{
        TaskName = $name
        Exists = [bool]$task
        State = if ($task) { $task.State } else { $null }
        LastRunTime = if ($info) { $info.LastRunTime } else { $null }
        LastTaskResult = if ($info) { $info.LastTaskResult } else { $null }
        NextRunTime = if ($info) { $info.NextRunTime } else { $null }
    }
}

[pscustomobject]@{
    ProjectRoot = $root
    ReportUrl = "http://127.0.0.1:8080/index.html"
    ReportHttp = $reportHttp
    LatestReport = if ($latestReport) { $latestReport.FullName } else { $null }
    LatestReportTime = if ($latestReport) { $latestReport.LastWriteTime } else { $null }
}

Write-Output ""
Write-Output "Ports"
$ports | Format-Table -AutoSize

Write-Output ""
Write-Output "Scheduled Tasks"
$tasks | Format-Table -AutoSize
