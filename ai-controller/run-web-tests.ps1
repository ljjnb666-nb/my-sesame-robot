$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $Root
try {
    $env:PYTHONPATH = $Root
    $env:SESAME_AI_PROVIDER = "mock"
    python -c "import fastapi, pydantic, uvicorn; from fastapi.testclient import TestClient"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Web optional dependencies are required. Install with: python -m pip install -e '.[web]'"
        exit $LASTEXITCODE
    }
    @'
import sys
import unittest

loader = unittest.defaultTestLoader
suite = loader.discover("tests", pattern="test_web_*.py")
result = unittest.TextTestRunner(verbosity=1).run(suite)
print(f"Web API tests: ran={result.testsRun} skipped={len(result.skipped)} failures={len(result.failures)} errors={len(result.errors)}")
if result.skipped:
    for test, reason in result.skipped:
        print(f"SKIPPED {test}: {reason}")
if not result.wasSuccessful() or result.skipped:
    sys.exit(1)
'@ | python -
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
