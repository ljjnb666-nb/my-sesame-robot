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

from sesame_ai_robot.client import RobotClient
from sesame_ai_robot.config import ControllerConfig
from sesame_ai_robot.mock_robot import MockRobotServer


@dataclass(frozen=True)
class ScenarioResult:
    path: Path
    passed: bool
    failures: tuple[str, ...]


def load_scenario(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def get_path(payload: dict[str, Any], dotted_path: str) -> Any:
    current: Any = payload
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(dotted_path)
        current = current[part]
    return current


def run_scenario(path: Path) -> ScenarioResult:
    scenario = load_scenario(path)
    failures: list[str] = []
    server = MockRobotServer(port=0)
    server.start()
    client = RobotClient(ControllerConfig(robot_url=server.url, request_timeout_s=1.0))

    try:
        for index, step in enumerate(scenario.get("steps", []), start=1):
            label = step.get("name", f"step {index}")

            if "command" in step:
                client.send_command(step["command"])

            if "face" in step:
                client.set_face(step["face"])

            if "setSensor" in step:
                server.state.virtual_sensors.update(step["setSensor"])

            if "setBatteryPercent" in step:
                server.state.virtual_battery_percent = int(step["setBatteryPercent"])

            if "waitMs" in step:
                time.sleep(float(step["waitMs"]) / 1000)

            if "expect" in step:
                status = client.get_status().raw
                for key, expected in step["expect"].items():
                    try:
                        actual = get_path(status, key)
                    except KeyError:
                        failures.append(f"{label}: missing status field {key}")
                        continue
                    if actual != expected:
                        failures.append(f"{label}: expected {key}={expected!r}, got {actual!r}")
    finally:
        server.stop()

    return ScenarioResult(path=path, passed=not failures, failures=tuple(failures))


def discover_scenarios(paths: list[Path]) -> list[Path]:
    scenarios: list[Path] = []
    for path in paths:
        if path.is_dir():
            scenarios.extend(sorted(path.glob("*.json")))
        else:
            scenarios.append(path)
    return scenarios


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Sesame simulator JSON scenarios")
    parser.add_argument("paths", nargs="*", type=Path, default=[Path(__file__).parent / "scenarios"])
    args = parser.parse_args()

    results = [run_scenario(path) for path in discover_scenarios(args.paths)]
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"{status} {result.path}")
        for failure in result.failures:
            print(f"  - {failure}")

    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
