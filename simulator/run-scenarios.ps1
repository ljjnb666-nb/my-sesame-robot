$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $Root
try {
    python ".\scenario_runner.py" @args
}
finally {
    Pop-Location
}
