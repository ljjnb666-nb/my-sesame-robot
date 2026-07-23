from __future__ import annotations

from copy import deepcopy
import json
from typing import Any


MAX_TIMELINE_LIMIT = 50
DEFAULT_TIMELINE_LIMIT = 20
MAX_READ_RESULT_BYTES = 4096


class RobotReadOnlyFacade:
    def __init__(self, *, client: Any, hardware: Any) -> None:
        self._client = client
        self._hardware = hardware

    def get_robot_state(self) -> dict[str, Any]:
        status = self._status()
        snapshot = self._snapshot()
        return _bounded_json({
            "motionState": status.get("motionState"),
            "currentCommand": status.get("currentCommand"),
            "currentFace": status.get("currentFace"),
            "emergencyStopActive": status.get("emergencyStopActive"),
            "communicationTimedOut": status.get("communicationTimedOut"),
            "batteryPercent": status.get("virtualBatteryPercent"),
            "robotPose": snapshot.get("robotPose"),
            "chargingState": snapshot.get("chargingState"),
            "faults": list(snapshot.get("faults", [])),
        })

    def get_battery_status(self) -> dict[str, Any]:
        snapshot = self._snapshot()
        battery = snapshot.get("battery", {})
        return _bounded_json({
            "available": battery.get("percent") is not None,
            "percent": battery.get("percent"),
            "voltage": battery.get("voltage"),
            "chargingState": snapshot.get("chargingState"),
        })

    def get_pose(self) -> dict[str, Any]:
        snapshot = self._snapshot()
        return _bounded_json({
            "robotPose": snapshot.get("robotPose"),
            "pose": deepcopy(snapshot.get("pose", {})),
        })

    def get_communication_status(self) -> dict[str, Any]:
        status = self._status()
        snapshot = self._snapshot()
        return _bounded_json({
            "connected": snapshot.get("communicationState") == "connected",
            "timedOut": bool(status.get("communicationTimedOut")),
            "communicationState": snapshot.get("communicationState"),
        })

    def get_actuator_status(self) -> dict[str, Any]:
        snapshot = self._snapshot()
        return _bounded_json({
            "servos": deepcopy(snapshot.get("servos", {})),
            "motors": deepcopy(snapshot.get("motors", {})),
        })

    def get_fault_status(self) -> dict[str, Any]:
        snapshot = self._snapshot()
        return _bounded_json({
            "faults": list(snapshot.get("faults", [])),
            "hasFaults": bool(snapshot.get("faults", [])),
        })

    def get_charging_status(self) -> dict[str, Any]:
        snapshot = self._snapshot()
        battery = snapshot.get("battery", {})
        return _bounded_json({
            "chargingState": snapshot.get("chargingState"),
            "batteryPercent": battery.get("percent"),
            "dockState": snapshot.get("chargingState"),
        })

    def get_timeline(self, limit: int = DEFAULT_TIMELINE_LIMIT) -> dict[str, Any]:
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1 or limit > MAX_TIMELINE_LIMIT:
            raise ValueError("timeline limit must be 1..50")
        events = []
        for event in list(getattr(self._hardware, "events", []))[-limit:]:
            if isinstance(event, dict):
                events.append(_sanitize_event(event))
        return _bounded_json({"events": events, "limit": limit})

    def _status(self) -> dict[str, Any]:
        return deepcopy(self._client.get_status().raw)

    def _snapshot(self) -> dict[str, Any]:
        return deepcopy(self._hardware.state.snapshot())


def _sanitize_event(event: dict[str, Any]) -> dict[str, Any]:
    allowed = {"time", "eventType", "action", "safetySeverity", "runtimeMode", "result", "reason", "fault", "servo_id", "motor_id"}
    return {str(key): deepcopy(value) for key, value in event.items() if key in allowed}


def _bounded_json(payload: dict[str, Any]) -> dict[str, Any]:
    encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False)
    if len(encoded.encode("utf-8")) <= MAX_READ_RESULT_BYTES:
        return payload
    return {"truncated": True, "reason": "read result exceeded size limit"}
