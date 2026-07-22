from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .advanced import RuntimeMode
from .ai_interaction import AIInteractionLoop, reply_to_jsonable
from .ai_provider import DeterministicMockProvider


def run_eval_file(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    cases = payload["cases"] if isinstance(payload, dict) else payload
    results = []
    categories: dict[str, dict[str, int]] = {}
    for case in cases:
        result = run_eval_case(case)
        results.append(result)
        bucket = categories.setdefault(case.get("category", "uncategorized"), {"passed": 0, "total": 0})
        bucket["total"] += 1
        if result["passed"]:
            bucket["passed"] += 1
    passed = sum(1 for result in results if result["passed"])
    return {"passed": passed, "total": len(results), "categories": categories, "results": results}


def run_eval_case(case: dict[str, Any]) -> dict[str, Any]:
    loop = AIInteractionLoop(provider=DeterministicMockProvider(), runtime_mode=RuntimeMode.SIMULATOR)
    initial = case.get("initialState", {})
    for fault in initial.get("faults", []):
        loop.hardware.inject_fault(fault)
    if "batteryPercent" in initial:
        loop.hardware.state.battery_percent = int(initial["batteryPercent"])
    if "imuRollDeg" in initial:
        loop.hardware.state.imu_roll_deg = float(initial["imuRollDeg"])
    text = str(case["userInput"])
    reply = loop.handle_text(text)
    if case.get("confirm") and reply.confirmation_id:
        reply = loop.handle_text(text, confirmation_id=reply.confirmation_id)
    actual = reply_to_jsonable(reply, include_confirmation_id=False)
    failures = []
    expected = case.get("expected", {})
    for key, value in expected.items():
        if key == "status" and actual["status"] != value:
            failures.append(f"status expected {value}, got {actual['status']}")
        elif key == "resultCode" and actual["resultCode"] != value:
            failures.append(f"resultCode expected {value}, got {actual['resultCode']}")
        elif key == "intent" and actual["intent"] != value:
            failures.append(f"intent expected {value}, got {actual['intent']}")
        elif key == "action" and actual["action"] != value:
            failures.append(f"action expected {value}, got {actual['action']}")
        elif key == "requiresConfirmation" and actual["requiresConfirmation"] != value:
            failures.append(f"requiresConfirmation expected {value}, got {actual['requiresConfirmation']}")
        elif key == "executed":
            runtime = ((actual.get("structured") or {}).get("runtime") or {})
            command_sent = ((runtime.get("executed") or {}).get("commandSent"))
            if bool(command_sent) != bool(value):
                failures.append(f"executed expected {value}, got {command_sent}")
    if case.get("expectHardwareUnchanged"):
        if loop.hardware.state.emergency_stop or any(motor.current_output for motor in loop.hardware.state.motors.values()):
            failures.append("hardware state changed")
    return {
        "name": case["name"],
        "category": case.get("category", "uncategorized"),
        "passed": not failures,
        "failures": failures,
        "actual": actual,
    }
