from __future__ import annotations

from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import time
from typing import Any


CONTINUOUS_COMMANDS = {"forward", "backward", "left", "right"}
AVAILABLE_COMMANDS = [
    "stand", "rest", "forward", "backward", "left", "right", "stop",
    "wave", "dance", "swim", "point", "pushup", "bow", "cute", "freaky",
    "worm", "shake", "shrug", "dead", "crab", "emergency_stop",
    "reset_emergency_stop", "heartbeat",
]


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
    virtual_sensors: dict[str, float | bool] = field(default_factory=lambda: {
        "frontDistanceM": 1.0,
        "leftDistanceM": 1.0,
        "rightDistanceM": 1.0,
        "cliffDetected": False,
        "collisionDetected": False,
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
            "availableCommands": AVAILABLE_COMMANDS,
            "capabilities": ["json_api", "face_control", "latched_emergency_stop", "communication_timeout_soft_stop", "mock_robot"],
            "virtualBatteryPercent": self.virtual_battery_percent,
            "virtualSensors": self.virtual_sensors,
            "networkConnected": False,
            "apIP": "127.0.0.1",
        }

    def apply_command(self, payload: dict[str, Any]) -> dict[str, str]:
        command = str(payload.get("command", "")).strip().lower()
        face = payload.get("face")
        now = time.monotonic()

        if face:
            self.current_face = str(face)

        if not command:
            self.last_command_at = now
            return {"status": "ok", "message": "Face updated"}

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
            return {"status": "ok", "message": "Heartbeat accepted"}
        elif command in AVAILABLE_COMMANDS and not self.emergency_stop_active:
            self.current_command = command
            self.communication_timed_out = False

        self.last_command_at = now
        return {"status": "ok", "message": "Command executed"}

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
                body = self.rfile.read(length).decode("utf-8") if length else "{}"
                payload = json.loads(body)
                self._send_json(state.apply_command(payload))

            def log_message(self, format: str, *args: object) -> None:
                return

            def _send_json(self, payload: dict[str, Any]) -> None:
                body = json.dumps(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        return Handler
