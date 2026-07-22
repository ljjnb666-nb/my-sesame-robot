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

from sesame_ai_robot.advanced import AdvancedBehaviorPlanner, AdvancedFeatureConfig, PostureState, RuntimeMode
from sesame_ai_robot.safety import SensorSnapshot


@dataclass(frozen=True)
class AdvancedScenarioResult:
    path: Path
    passed: bool
    failures: tuple[str, ...]


def load_advanced_scenario(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def discover_advanced_scenarios(paths: list[Path]) -> list[Path]:
    scenarios: list[Path] = []
    for path in paths:
        if path.is_dir():
            scenarios.extend(sorted(path.glob("*.json")))
        else:
            scenarios.append(path)
    return scenarios


def run_advanced_scenario(path: Path) -> AdvancedScenarioResult:
    scenario = load_advanced_scenario(path)
    planner = AdvancedBehaviorPlanner(_config_from_json(scenario.get("config", {})))
    failures: list[str] = []

    for index, step in enumerate(scenario.get("steps", []), start=1):
        label = step.get("name", f"step {index}")
        decision = _run_step(planner, step)
        payload = _decision_to_jsonable(decision)
        for key, expected in step.get("expect", {}).items():
            actual = payload.get(key)
            if actual != expected:
                failures.append(f"{label}: expected {key}={expected!r}, got {actual!r}")

    return AdvancedScenarioResult(path=path, passed=not failures, failures=tuple(failures))


def _run_step(planner: AdvancedBehaviorPlanner, step: dict[str, Any]):
    action = str(step.get("action", "")).strip()
    snapshot = _snapshot_from_json(step.get("sensor", {}))

    if action == "assess_posture":
        return planner.assess_posture(snapshot)
    if action == "plan_self_righting":
        return planner.plan_self_righting(PostureState(str(step.get("posture", PostureState.NORMAL.value))))
    if action == "assess_terrain":
        return planner.assess_terrain(snapshot)
    if action == "plan_charging":
        return planner.plan_charging(snapshot)
    raise ValueError(f"unsupported advanced scenario action: {action}")


def _config_from_json(payload: dict[str, Any]) -> AdvancedFeatureConfig:
    mode = RuntimeMode(str(payload.get("runtimeMode", RuntimeMode.MOCK.value)))
    return AdvancedFeatureConfig(
        runtime_mode=mode,
        allow_self_righting=bool(payload.get("allowSelfRighting", False)),
        allow_auto_docking=bool(payload.get("allowAutoDocking", False)),
    )


def _snapshot_from_json(payload: dict[str, Any]) -> SensorSnapshot:
    return SensorSnapshot(
        front_distance_m=_optional_float(payload.get("frontDistanceM")),
        left_distance_m=_optional_float(payload.get("leftDistanceM")),
        right_distance_m=_optional_float(payload.get("rightDistanceM")),
        cliff_detected=bool(payload.get("cliffDetected", False)),
        collision_detected=bool(payload.get("collisionDetected", False)),
        imu_roll_deg=_optional_float(payload.get("imuRollDeg")),
        imu_pitch_deg=_optional_float(payload.get("imuPitchDeg")),
        battery_percent=_optional_int(payload.get("batteryPercent")),
    )


def _decision_to_jsonable(decision) -> dict[str, Any]:
    return {
        "feature": decision.feature.value,
        "state": decision.state,
        "command": decision.command,
        "reason": decision.reason,
        "requiresUserConfirmation": decision.requires_user_confirmation,
    }


def _optional_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _optional_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Sesame advanced behavior JSON scenarios")
    parser.add_argument("paths", nargs="*", type=Path, default=[Path(__file__).parent / "scenarios" / "advanced"])
    args = parser.parse_args()

    results = [run_advanced_scenario(path) for path in discover_advanced_scenarios(args.paths)]
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"{status} {result.path}")
        for failure in result.failures:
            print(f"  - {failure}")

    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
