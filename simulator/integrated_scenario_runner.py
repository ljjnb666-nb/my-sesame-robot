from __future__ import annotations

from dataclasses import dataclass
import argparse
import json
from pathlib import Path
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AI_CONTROLLER = ROOT / "ai-controller"
if str(AI_CONTROLLER) not in sys.path:
    sys.path.insert(0, str(AI_CONTROLLER))

from sesame_ai_robot.advanced import AdvancedBehaviorPlanner, AdvancedFeatureConfig, PostureState, RuntimeMode
from sesame_ai_robot.arbiter import ArbiterInput, BehaviorArbiter
from sesame_ai_robot.assistant import AssistantAction, AssistantPlan, AssistantStep
from sesame_ai_robot.detection import BoundingBox, Detection, DetectionResult
from sesame_ai_robot.face_identity import FaceIdentity, FaceRecognitionResult
from sesame_ai_robot.safety import SafetyMonitor, SensorSnapshot
from sesame_ai_robot.tracking import TrackingConfig, TrackingController


@dataclass(frozen=True)
class IntegratedScenarioResult:
    path: Path
    passed: bool
    failures: tuple[str, ...]


def discover_integrated_scenarios(paths: list[Path]) -> list[Path]:
    scenarios: list[Path] = []
    for path in paths:
        if path.is_dir():
            scenarios.extend(sorted(path.glob("*.json")))
        else:
            scenarios.append(path)
    return scenarios


def run_integrated_scenario(path: Path) -> IntegratedScenarioResult:
    scenario = json.loads(path.read_text(encoding="utf-8"))
    config = scenario.get("config", {})
    runtime_mode = RuntimeMode(str(config.get("runtimeMode", RuntimeMode.MOCK.value)))
    tracking = TrackingController(TrackingConfig(allow_following=bool(config.get("allowFollowing", False))))
    safety_monitor = SafetyMonitor()
    advanced_planner = AdvancedBehaviorPlanner(AdvancedFeatureConfig(
        runtime_mode=runtime_mode,
        allow_self_righting=bool(config.get("allowSelfRighting", False)),
        allow_auto_docking=bool(config.get("allowAutoDocking", False)),
    ))
    arbiter = BehaviorArbiter()
    failures: list[str] = []

    for index, step in enumerate(scenario.get("steps", []), start=1):
        label = step.get("name", f"step {index}")
        status = _robot_status(step.get("robotStatus", {}), step.get("sensor", {}))
        detections = _detections(step.get("target", {}))
        identity = _identity(bool(step.get("identityConfirmed", False)))
        tracking_decision = tracking.update(detections, identity, status)
        snapshot = SensorSnapshot.from_robot_status(status)
        posture = advanced_planner.assess_posture(snapshot)
        posture_state = PostureState(str(step.get("posture", posture.state)))
        advanced = (
            posture,
            advanced_planner.assess_terrain(snapshot),
            advanced_planner.plan_self_righting(posture_state),
            advanced_planner.plan_charging(snapshot),
        )
        assistant = _assistant_plan(step.get("assistant", {}))
        plan = arbiter.decide(ArbiterInput(
            robot_status=status,
            safety=safety_monitor.assess(snapshot),
            tracking=tracking_decision,
            advanced=advanced,
            assistant=assistant,
            runtime_mode=runtime_mode,
        ))
        payload = {
            "command": plan.command,
            "face": plan.face,
            "speech": plan.speech,
            "source": plan.source,
            "reason": plan.reason,
            "requiresUserConfirmation": plan.requires_user_confirmation,
            "blockedActions": list(plan.blocked_actions),
            "trackingState": tracking_decision.state.value,
            "trackingCommand": tracking_decision.command,
        }
        for key, expected in step.get("expect", {}).items():
            actual = payload.get(key)
            if actual != expected:
                failures.append(f"{label}: expected {key}={expected!r}, got {actual!r}")
        for blocked in step.get("expectBlockedActions", []):
            if blocked not in payload["blockedActions"]:
                failures.append(f"{label}: expected blocked action {blocked!r}, got {payload['blockedActions']!r}")

    return IntegratedScenarioResult(path, not failures, tuple(failures))


def _robot_status(base: dict[str, Any], sensor: dict[str, Any]) -> dict[str, Any]:
    status = {
        "emergencyStopActive": bool(base.get("emergencyStopActive", False)),
        "communicationTimedOut": bool(base.get("communicationTimedOut", False)),
        "virtualBatteryPercent": int(sensor.get("batteryPercent", base.get("virtualBatteryPercent", 80))),
        "virtualSensors": {
            "frontDistanceM": float(sensor.get("frontDistanceM", 1.0)),
            "leftDistanceM": float(sensor.get("leftDistanceM", 1.0)),
            "rightDistanceM": float(sensor.get("rightDistanceM", 1.0)),
            "cliffDetected": bool(sensor.get("cliffDetected", False)),
            "collisionDetected": bool(sensor.get("collisionDetected", False)),
            "imuRollDeg": float(sensor.get("imuRollDeg", 0.0)),
            "imuPitchDeg": float(sensor.get("imuPitchDeg", 0.0)),
        },
    }
    status.update(base)
    return status


def _detections(target: dict[str, Any]) -> DetectionResult:
    detections: tuple[Detection, ...] = ()
    if bool(target.get("visible", False)):
        center_x = float(target.get("centerX", 0.5)) * 100
        detections = (
            Detection(
                "person",
                float(target.get("confidence", 0.9)),
                BoundingBox(center_x - 5, 20, 10, 40),
                _optional_float(target.get("distanceM")),
            ),
        )
    now = time.monotonic()
    return DetectionResult("integrated-scenario", now, now, 100, 100, detections)


def _identity(confirmed: bool) -> FaceRecognitionResult:
    identity = FaceIdentity("owner", "Owner", 0.0) if confirmed else None
    return FaceRecognitionResult(identity, 0.9 if confirmed else 0.0, 0.75)


def _assistant_plan(payload: dict[str, Any]) -> AssistantPlan | None:
    steps: list[AssistantStep] = []
    for command in payload.get("commands", []):
        steps.append(AssistantStep(AssistantAction.ROBOT_COMMAND, str(command), "scenario assistant command"))
    if "face" in payload:
        steps.append(AssistantStep(AssistantAction.SET_FACE, str(payload["face"]), "scenario face"))
    if "speech" in payload:
        steps.append(AssistantStep(AssistantAction.SAY, str(payload["speech"]), "scenario speech"))
    if not steps:
        return None
    return AssistantPlan(str(payload.get("transcript", "")), tuple(steps))


def _optional_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Sesame integrated behavior scenarios")
    parser.add_argument("paths", nargs="*", type=Path, default=[Path(__file__).parent / "scenarios" / "integrated"])
    args = parser.parse_args()

    results = [run_integrated_scenario(path) for path in discover_integrated_scenarios(args.paths)]
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"{status} {result.path}")
        for failure in result.failures:
            print(f"  - {failure}")
    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
