from __future__ import annotations

from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import time
from typing import Any

from .protocol import AVAILABLE_COMMANDS, AVAILABLE_FACES, ERRORS, MAX_API_BODY_BYTES, validate_api_payload

CONTINUOUS_COMMANDS = {"forward", "backward", "left", "right"}


@dataclass(frozen=True)
class MockRobotResponse:
    status_code: int
    payload: dict[str, Any]


def api_error(status_code: int, error: str, message: str) -> MockRobotResponse:
    return MockRobotResponse(status_code, {
        "status": "error",
        "error": error,
        "message": message,
    })


def protocol_error(code: str) -> MockRobotResponse:
    error = ERRORS[code]
    return MockRobotResponse(error.status_code, error.payload())


@dataclass
class MockRobotState:
    command_timeout_ms: int = 1200
    started_at: float = field(default_factory=time.monotonic)
    current_command: str = ""
    current_face: str = "default"
    emergency_stop_active: bool = False
    pending_emergency_reset: bool = False
    communication_timed_out: bool = False
    last_command_at: float = 0.0
    virtual_battery_percent: int = 100
    virtual_servo_angles: list[int] = field(default_factory=lambda: [90, 90, 90, 90, 90, 90, 90, 90])
    virtual_sensors: dict[str, float | bool] = field(default_factory=lambda: {
        "frontDistanceM": 1.0,
        "leftDistanceM": 1.0,
        "rightDistanceM": 1.0,
        "cliffDetected": False,
        "collisionDetected": False,
        "imuRollDeg": 0.0,
        "imuPitchDeg": 0.0,
    })

    def as_status(self) -> dict[str, Any]:
        self.apply_timeout()
        now = time.monotonic()
        motion_state = "emergency_stop" if self.emergency_stop_active else "moving" if self.current_command else "idle"
        if self.communication_timed_out:
            motion_state = "communication_timeout"

        last_command_ms = int((self.last_command_at - self.started_at) * 1000) if self.last_command_at else 0
        last_command_age_ms = int((now - self.last_command_at) * 1000) if self.last_command_at else 0
        return {
            "firmwareVersion": "mock-ai-controller",
            "uptimeMs": int((now - self.started_at) * 1000),
            "currentCommand": self.current_command,
            "currentFace": self.current_face,
            "motionState": motion_state,
            "motionInProgress": bool(self.current_command),
            "emergencyStopActive": self.emergency_stop_active,
            "pendingEmergencyReset": self.pending_emergency_reset,
            "communicationTimedOut": self.communication_timed_out,
            "commandTimeoutMs": self.command_timeout_ms,
            "lastCommandMs": last_command_ms,
            "lastCommandAgeMs": last_command_age_ms,
            "availableCommands": sorted(AVAILABLE_COMMANDS),
            "capabilities": ["json_api", "face_control", "latched_emergency_stop", "communication_timeout_soft_stop", "mock_robot"],
            "virtualBatteryPercent": self.virtual_battery_percent,
            "virtualServoAngles": self.virtual_servo_angles,
            "virtualSensors": self.virtual_sensors,
            "networkConnected": False,
            "apIP": "127.0.0.1",
        }

    def apply_command(self, payload: dict[str, Any]) -> MockRobotResponse:
        command, face, error = validate_api_payload(payload)
        if error is not None:
            return MockRobotResponse(error.status_code, error.payload())
        now = time.monotonic()

        if face is not None:
            self.current_face = face

        if command is None and face is not None:
            self.last_command_at = now
            return MockRobotResponse(200, {"status": "ok", "message": "Face updated", "face": face})

        if (
            self.emergency_stop_active
            and command not in {"emergency_stop", "reset_emergency_stop", "stop", "heartbeat"}
        ):
            return protocol_error("emergency_stop_active")

        if command == "emergency_stop":
            self.emergency_stop_active = True
            self.current_command = ""
            self.communication_timed_out = False
        elif command == "reset_emergency_stop":
            self.emergency_stop_active = False
            self.current_command = ""
            self.communication_timed_out = False
        elif command == "stop":
            self.current_command = ""
            self.communication_timed_out = False
        elif command == "heartbeat":
            if self.current_command in CONTINUOUS_COMMANDS:
                self.last_command_at = now
                self.communication_timed_out = False
            return MockRobotResponse(200, {"status": "ok", "message": "Heartbeat accepted", "command": "heartbeat"})
        elif command in AVAILABLE_COMMANDS:
            self.current_command = command
            self._apply_virtual_pose(command)
            self.communication_timed_out = False

        self.last_command_at = now
        if command == "stop":
            message = "Command stopped"
        elif command == "emergency_stop":
            message = "Emergency stop activated"
        elif command == "reset_emergency_stop":
            message = "Emergency stop reset"
        else:
            message = "Command accepted"
        return MockRobotResponse(200, {"status": "ok", "message": message, "command": command})

    def _apply_virtual_pose(self, command: str) -> None:
        poses = {
            "stand": [90, 90, 90, 90, 90, 90, 90, 90],
            "rest": [45, 135, 45, 135, 45, 135, 45, 135],
            "forward": [105, 75, 110, 70, 80, 100, 85, 95],
            "backward": [75, 105, 70, 110, 100, 80, 95, 85],
            "left": [120, 95, 120, 95, 60, 85, 60, 85],
            "right": [60, 85, 60, 85, 120, 95, 120, 95],
        }
        self.virtual_servo_angles = poses.get(command, self.virtual_servo_angles)

    def apply_timeout(self) -> None:
        if self.current_command not in CONTINUOUS_COMMANDS or not self.last_command_at:
            return
        age_ms = int((time.monotonic() - self.last_command_at) * 1000)
        if age_ms > self.command_timeout_ms:
            self.current_command = ""
            self.communication_timed_out = True


class MockRobotServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8765, state: MockRobotState | None = None):
        self.state = state or MockRobotState()
        self._server = ThreadingHTTPServer((host, port), self._make_handler())
        self.url = f"http://{self._server.server_address[0]}:{self._server.server_address[1]}"
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._server.serve_forever, name="sesame-mock-robot", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        if self._thread:
            self._thread.join(timeout=2.0)

    def serve_forever(self) -> None:
        self._server.serve_forever()

    def _make_handler(self) -> type[BaseHTTPRequestHandler]:
        state = self.state

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                if self.path != "/api/status":
                    self.send_error(404)
                    return
                self._send_json(state.as_status())

            def do_POST(self) -> None:
                if self.path != "/api/command":
                    self.send_error(404)
                    return
                length = int(self.headers.get("Content-Length", "0"))
                if length > MAX_API_BODY_BYTES:
                    self.rfile.read(length)
                    response = protocol_error("payload_too_large")
                    self._send_json(response.payload, response.status_code)
                    return
                if length == 0:
                    response = protocol_error("invalid_json")
                    self._send_json(response.payload, response.status_code)
                    return
                body = self.rfile.read(length).decode("utf-8")
                try:
                    payload = json.loads(body)
                except json.JSONDecodeError:
                    response = protocol_error("invalid_json")
                    self._send_json(response.payload, response.status_code)
                    return
                if not isinstance(payload, dict):
                    response = protocol_error("invalid_payload")
                    self._send_json(response.payload, response.status_code)
                    return
                response = state.apply_command(payload)
                self._send_json(response.payload, response.status_code)

            def log_message(self, format: str, *args: object) -> None:
                return

            def _send_json(self, payload: dict[str, Any], status_code: int = 200) -> None:
                body = json.dumps(payload).encode("utf-8")
                self.send_response(status_code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        return Handler
