# GitHub Actions CI

The repository CI is defined in `.github/workflows/ci.yml`.

GitHub Actions validates software tests, simulator behavior, Python syntax, firmware compilation, and firmware size thresholds. It does not validate real robot hardware.

## Triggers

- Pull requests targeting any branch.
- Pushes to `main`.
- Manual `workflow_dispatch`.

The workflow uses `permissions: contents: read`, a per-ref concurrency group, and a 25-minute job timeout.

## Runner and Toolchain

- Runner: `windows-latest`.
- Python: `3.11`.
- Arduino CLI: `1.5.1`.
- ESP32 Arduino core: `esp32:esp32@3.3.10`.
- Board FQBN: `esp32:esp32:lolin_s2_mini`.
- Firmware libraries:
  - `ArduinoJson@6.21.5`
  - `ESP32Servo@3.0.9`
  - `Adafruit SSD1306@2.5.17`
  - `Adafruit GFX Library@1.12.6`

The workflow caches Arduino package and library directories, but every run still performs the firmware compile.

## CI Steps

The workflow runs these checks:

```powershell
git diff --check <event-specific-range>
powershell -ExecutionPolicy Bypass -File ".\run-tests.ps1"                # in ai-controller
python -m unittest discover -s scripts/tests
powershell -ExecutionPolicy Bypass -File ".\run-cli.ps1" runtime-step --mode mock --dry-run
powershell -ExecutionPolicy Bypass -File ".\run-cli.ps1" runtime-run --mode simulator --steps 3 --dry-run
powershell -ExecutionPolicy Bypass -File ".\run-cli.ps1" runtime-confirmation-demo --mode mock --dry-run
powershell -ExecutionPolicy Bypass -File ".\simulator\run-scenarios.ps1"
powershell -ExecutionPolicy Bypass -File ".\simulator\run-advanced-scenarios.ps1"
powershell -ExecutionPolicy Bypass -File ".\simulator\run-integrated-scenarios.ps1"
python -m compileall ai-controller simulator scripts
powershell -ExecutionPolicy Bypass -File ".\scripts\firmware-build.ps1"
python ".\scripts\check_firmware_size.py" --build-log artifacts\firmware-build.log
```

`runtime-confirmation-demo` covers confirmation request, valid consume, replay rejection, wrong action rejection, context changed rejection, and expired rejection.

## Firmware Size Guard

Firmware size is parsed from the real Arduino CLI build log. The guard does not hard-code the current 86% result.

Current thresholds:

- Flash warning: `88%`
- Flash failure: `92%`

The warning threshold writes a visible warning but does not fail CI. The failure threshold exits non-zero and fails CI. Parser failures and invalid size values also fail CI.

The CI summary includes:

- Flash used, max, percentage, and remaining bytes.
- RAM used, max, percentage, and remaining bytes.
- Warning and failure thresholds.

## Artifacts

Successful firmware builds upload a 14-day artifact named:

```text
sesame-firmware-<short-sha>-ci
```

The artifact includes:

- Files from `.build/output/*`
- `artifacts/firmware-build.log`
- `artifacts/firmware-size.md`

Do not upload dependency caches, package manager directories, local logs, private data, or unrelated temporary directories.

## What CI Does Not Do

GitHub Actions only validates software, simulator behavior, and firmware compilation. It does not mean the robot has passed real hardware acceptance.

CI must not:

- Upload or flash firmware.
- Open serial monitors.
- Connect to USB devices.
- Control real servos or motors.
- Start standing, walking, self-righting, or charging dock behavior on real hardware.
- Use a real camera or microphone.
- Run in real robot mode.

Use `docs/hardware-validation-plan.md` for staged physical validation after CI passes.

## Common Failures

- Python test failure: run `ai-controller/run-tests.ps1` locally and inspect the failing unittest.
- CLI dry-run failure: run the same `run-cli.ps1` command locally; it should use mock or simulator mode only.
- Simulator failure: run the matching simulator script and inspect the scenario name printed as `FAIL`.
- Firmware dependency failure: check Arduino CLI, ESP32 core, and pinned library versions.
- Firmware size failure: inspect `artifacts/firmware-size.md` and compare the flash percentage with the 92% failure threshold.
- Hygiene failure: remove generated files such as `.build/`, `__pycache__/`, `*.pyc`, `*.log`, or temporary files from Git tracking.

## Branch Protection Recommendation

After the first workflow run succeeds on a PR, configure `main` protection in GitHub:

1. Open repository Settings.
2. Go to Branches or Rulesets.
3. Add a rule for `main`.
4. Enable "Require a pull request before merging".
5. Enable "Require status checks to pass".
6. Select the required check named `Runtime, Simulator, and Firmware`.
7. Enable "Require branches to be up to date before merging" if available.
8. Disable force pushes and branch deletion for `main`.

If repository permissions do not allow this configuration, keep it as a documented residual risk.
