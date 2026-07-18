$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $Root
try {
    $env:PYTHONPATH = $Root
    python -m sesame_ai_robot.cli mock-server
}
finally {
    Pop-Location
}
