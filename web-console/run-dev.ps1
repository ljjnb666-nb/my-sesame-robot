$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$FrontendDir = Join-Path $PSScriptRoot "frontend"
$AiDir = Join-Path $RepoRoot "ai-controller"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  Write-Error "Python is required. Install Python 3.11+, then install ai-controller web extras."
}
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
  Write-Error "Node.js is required. Install Node, then run npm install in web-console/frontend."
}
if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
  Write-Error "Missing frontend node_modules. Run: cd web-console/frontend; npm install"
}

Push-Location $AiDir
try {
  python -c "import fastapi, uvicorn, pydantic; import sesame_ai_robot.web.app" | Out-Null
} finally {
  Pop-Location
}
if ($LASTEXITCODE -ne 0) {
  Write-Error "Missing Python web extras. Run: cd ai-controller; python -m pip install -e `".[web]`""
}

$env:SESAME_AI_PROVIDER = if ($env:SESAME_AI_PROVIDER) { $env:SESAME_AI_PROVIDER } else { "mock" }
Write-Host "Sesame Web Simulator Console"
Write-Host "API:      http://127.0.0.1:8787"
Write-Host "Frontend: http://127.0.0.1:5173"
Write-Host "REAL HARDWARE DISABLED"

$api = $null
$frontend = $null
$exitCode = 0
try {
  $api = Start-Process powershell -WindowStyle Hidden -PassThru -WorkingDirectory $AiDir -ArgumentList @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-Command", "python -m sesame_ai_robot.web --host 127.0.0.1 --port 8787"
  )
  $frontend = Start-Process powershell -WindowStyle Hidden -PassThru -WorkingDirectory $FrontendDir -ArgumentList @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-Command", "npm run dev"
  )

  while ($true) {
    Start-Sleep -Milliseconds 500
    foreach ($proc in @($api, $frontend)) {
      if ($proc -and $proc.HasExited) {
        $exitCode = $proc.ExitCode
        if ($exitCode -eq 0) { $exitCode = 1 }
        Write-Host "Child process exited: PID=$($proc.Id), exit=$($proc.ExitCode)"
        break
      }
    }
    if (($api -and $api.HasExited) -or ($frontend -and $frontend.HasExited)) {
      break
    }
  }
} finally {
  foreach ($proc in @($frontend, $api)) {
    if ($proc -and -not $proc.HasExited) {
      Stop-Process -Id $proc.Id -Force
    }
  }
}

exit $exitCode
