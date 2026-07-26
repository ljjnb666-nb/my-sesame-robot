$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$AiController = Join-Path $Root "ai-controller"

Push-Location $AiController
try {
    $env:PYTHONPATH = $AiController
    if (-not $env:SESAME_AI_PROVIDER) {
        $env:SESAME_AI_PROVIDER = "mock"
    }
    python -c "import fastapi, pydantic, uvicorn" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Missing web dependencies. Install with: python -m pip install -e '.[web]'"
        exit 2
    }
    Write-Host "LOCAL SIMULATOR ONLY"
    Write-Host "REAL HARDWARE DISABLED"
    python -m sesame_ai_robot.web --host 127.0.0.1 --port 8787
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
