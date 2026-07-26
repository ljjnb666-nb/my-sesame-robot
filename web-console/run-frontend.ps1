$ErrorActionPreference = "Stop"

$FrontendDir = Join-Path $PSScriptRoot "frontend"
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
  Write-Error "Node.js is required. Install Node, then run npm install in web-console/frontend."
}
if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
  Write-Error "Missing node_modules. Run: cd web-console/frontend; npm install"
}

Write-Host "Starting Sesame frontend at http://127.0.0.1:5173"
Write-Host "REAL HARDWARE DISABLED"
Push-Location $FrontendDir
try {
  npm run dev
} finally {
  Pop-Location
}
