$ErrorActionPreference = "Continue"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path

$ports = foreach ($port in 3333) {
    $conn = netstat -ano -p tcp | Select-String -Pattern (":$port\s+.*LISTENING\s+(\d+)") | Select-Object -First 1
    $processId = if ($conn) { [regex]::Match($conn.Line, "LISTENING\s+(\d+)").Groups[1].Value } else { $null }
    [pscustomobject]@{
        Port = $port
        Listening = [bool]$conn
        ProcessId = $processId
    }
}

$tasks = foreach ($name in "TrendRadar-KeepAlive", "TrendRadar-MCPServer") {
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
    LocalMcpUrl = "http://127.0.0.1:3333/"
}

Write-Output ""
Write-Output "Ports"
$ports | Format-Table -AutoSize

Write-Output ""
Write-Output "Scheduled Tasks"
$tasks | Format-Table -AutoSize
