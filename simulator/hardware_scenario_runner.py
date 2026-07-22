from __future__ import annotations

from dataclasses import dataclass
import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AI_CONTROLLER = ROOT / "ai-controller"
if str(AI_CONTROLLER) not in sys.path:
    sys.path.insert(0, str(AI_CONTROLLER))

from sesame_ai_robot.virtual_hardware import (  # noqa: E402
    HardwareDispatchError,
    HardwareSafetyError,
    ManualClock,
    SimulatorHardwareAdapter,
    VirtualRobotState,
)


@dataclass(frozen=True)
class HardwareScenarioResult:
    path: Path
    passed: bool
    failures: tuple[str, ...]


def discover_scenarios(paths: list[Path]) -> list[Path]:
    scenarios: list[Path] = []
    for path in paths:
        if path.is_dir():
            scenarios.extend(sorted(path.glob("*.json")))
        else:
            scenarios.append(path)
    return scenarios


def run_hardware_scenario(path: Path) -> HardwareScenarioResult:
    scenario = json.loads(path.read_text(encoding="utf-8"))
    clock = ManualClock(float(scenario.get("clockStart", 0.0)))
    state = VirtualRobotState()
    _apply_initial_state(state, scenario.get("initialState", {}))
    hardware = SimulatorHardwareAdapter(state=state, clock=clock)
    failures: list[str] = []
    last_error: str | None = None

    for index, step in enumerate(scenario.get("steps", []), start=1):
        label = step.get("name", f"step {index}")
        expected_error = step.get("expectError")
        last_error = None
        try:
            _run_step(hardware, clock, step)
        except (ValueError, HardwareDispatchError, HardwareSafetyError) as exc:
            last_error = str(exc)
            if expected_error is None:
                failures.append(f"{label}: unexpected error {last_error!r}")
        if expected_error is not None and (last_error is None or expected_error not in last_error):
            failures.append(f"{label}: expected error containing {expected_error!r}, got {last_error!r}")
        if "expect" in step:
            snapshot = {"state": hardware.state.snapshot(), "events": hardware.events}
            for key, expected in step["expect"].items():
                try:
                    actual = _get_path(snapshot, key)
                except KeyError:
                    failures.append(f"{label}: missing field {key}")
                    continue
                if actual != expected:
                    failures.append(f"{label}: expected {key}={expected!r}, got {actual!r}")

    if scenario.get("expectSafeAtEnd", False):
        unsafe = [
            motor for motor in hardware.state.motors.values()
            if motor.current_output != 0.0 or motor.direction != "stop"
        ]
        if unsafe:
            failures.append("end: expected all motors stopped")

    return HardwareScenarioResult(path, not failures, tuple(failures))


def _run_step(hardware: SimulatorHardwareAdapter, clock: ManualClock, step: dict[str, Any]) -> None:
    if "clearFault" in step:
        value = step["clearFault"]
        hardware.clear_fault(None if value == "all" else str(value))
    if "injectFault" in step:
        hardware.inject_fault(str(step["injectFault"]))
    if "setServo" in step:
        payload = step["setServo"]
        hardware.set_servo(int(payload["servoId"]), float(payload["angle"]), float(payload.get("speed", 90.0)))
    if "setMotor" in step:
        payload = step["setMotor"]
        hardware.set_motor(int(payload["motorId"]), float(payload["power"]), float(payload["duration"]))
    if "stopAllActuators" in step:
        hardware.stop_all_actuators()
    if "captureCameraFrame" in step:
        hardware.capture_camera_frame()
    if "captureAudio" in step:
        hardware.capture_audio(float(step["captureAudio"].get("duration", 0.1)))
    if "readBattery" in step:
        hardware.read_battery()
    if "readPose" in step:
        hardware.read_pose()
    if "readChargingState" in step:
        hardware.read_charging_state()
    if "advanceSeconds" in step:
        clock.advance(float(step["advanceSeconds"]))
        hardware.tick()


def _apply_initial_state(state: VirtualRobotState, initial: dict[str, Any]) -> None:
    if "batteryPercent" in initial:
        state.battery_percent = initial["batteryPercent"]
    if "batteryVoltage" in initial:
        state.battery_voltage = initial["batteryVoltage"]
    if "communicationState" in initial:
        state.communication_state = str(initial["communicationState"])
    if "hardwareEnabled" in initial:
        state.hardware_enabled = bool(initial["hardwareEnabled"])
    if "experimentEnabled" in initial:
        state.experiment_enabled = bool(initial["experimentEnabled"])
    if "emergencyStop" in initial:
        state.emergency_stop = bool(initial["emergencyStop"])
    if "pose" in initial:
        state.robot_pose = str(initial["pose"].get("state", state.robot_pose))
        state.imu_roll_deg = initial["pose"].get("rollDeg", state.imu_roll_deg)
        state.imu_pitch_deg = initial["pose"].get("pitchDeg", state.imu_pitch_deg)


def _get_path(payload: dict[str, Any], dotted_path: str) -> Any:
    current: Any = payload
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(dotted_path)
        current = current[part]
    return current


def main() -> int:
    parser = argparse.ArgumentParser(description="Run virtual hardware JSON scenarios")
    parser.add_argument("paths", nargs="*", type=Path, default=[Path(__file__).parent / "scenarios" / "hardware"])
    args = parser.parse_args()

    results = [run_hardware_scenario(path) for path in discover_scenarios(args.paths)]
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"{status} {result.path}")
        for failure in result.failures:
            print(f"  - {failure}")
    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
