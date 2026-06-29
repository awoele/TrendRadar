$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path

function Register-TrendRadarTask {
    param(
        [string]$Name,
        [string]$ScriptPath,
        [Microsoft.Management.Infrastructure.CimInstance]$Trigger,
        [string]$Description
    )

    $action = New-ScheduledTaskAction `
        -Execute "powershell.exe" `
        -Argument ('-NoProfile -ExecutionPolicy Bypass -File "{0}"' -f $ScriptPath) `
        -WorkingDirectory $root

    $settings = New-ScheduledTaskSettingsSet `
        -StartWhenAvailable `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -MultipleInstances IgnoreNew `
        -ExecutionTimeLimit (New-TimeSpan -Seconds 0) `
        -RestartCount 3 `
        -RestartInterval (New-TimeSpan -Minutes 1)

    Register-ScheduledTask `
        -TaskName $Name `
        -Action $action `
        -Trigger $Trigger `
        -Settings $settings `
        -Description $Description `
        -Force | Out-Null
}

$crawlerScript = Join-Path $root "local-run-once.ps1"
$keepAliveScript = Join-Path $root "local-ensure-services.ps1"

foreach ($legacyTask in "TrendRadar-ReportServer", "TrendRadar-MCPServer") {
    if (Get-ScheduledTask -TaskName $legacyTask -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $legacyTask -Confirm:$false
    }
}

$crawlerTrigger = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date).AddMinutes(30) `
    -RepetitionInterval (New-TimeSpan -Minutes 30) `
    -RepetitionDuration (New-TimeSpan -Days 3650)

Register-TrendRadarTask `
    -Name "TrendRadar-Crawler" `
    -ScriptPath $crawlerScript `
    -Trigger $crawlerTrigger `
    -Description "Run TrendRadar crawler every 30 minutes."

$logonTrigger = New-ScheduledTaskTrigger -AtLogOn
$keepAliveTrigger = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes 5) `
    -RepetitionDuration (New-TimeSpan -Days 3650)

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument ('-NoProfile -ExecutionPolicy Bypass -File "{0}"' -f $keepAliveScript) `
    -WorkingDirectory $root

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10)

Register-ScheduledTask `
    -TaskName "TrendRadar-KeepAlive" `
    -Action $action `
    -Trigger @($logonTrigger, $keepAliveTrigger) `
    -Settings $settings `
    -Description "Keep TrendRadar report and MCP services running." `
    -Force | Out-Null

& $keepAliveScript
