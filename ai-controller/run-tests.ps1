$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $Root
try {
    $env:PYTHONPATH = $Root
    python -m unittest discover -s tests
}
finally {
    Pop-Location
}
