$ErrorActionPreference = "Stop"

& (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "local-ensure-services.ps1")
