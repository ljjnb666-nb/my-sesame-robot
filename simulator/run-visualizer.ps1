$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $Root
try {
    python ".\visualizer.py" @args
}
finally {
    Pop-Location
}
