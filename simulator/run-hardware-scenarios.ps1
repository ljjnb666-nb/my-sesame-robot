$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Repo = Split-Path -Parent $Root
Push-Location $Repo
try {
    $env:PYTHONPATH = Join-Path $Repo "ai-controller"
    python .\simulator\hardware_scenario_runner.py @args
    $ExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}
exit $ExitCode
