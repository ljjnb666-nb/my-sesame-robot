from __future__ import annotations

from dataclasses import dataclass
import json
import time
from typing import Any
from urllib import error, request

from .config import ControllerConfig


class RobotClientError(RuntimeError):
    pass


class UnsupportedCommandError(RobotClientError):
    pass


@dataclass(frozen=True)
class RobotStatus:
    raw: dict[str, Any]

    @property
    def emergency_stop_active(self) -> bool:
        return bool(self.raw.get("emergencyStopActive", False))

    @property
    def motion_state(self) -> str:
        return str(self.raw.get("motionState", "unknown"))

    @property
    def current_command(self) -> str:
        return str(self.raw.get("currentCommand", ""))


class RobotClient:
    COMMAND_ALIASES = {
        "walk_forward": "forward",
        "walk_backward": "backward",
        "turn_left": "left",
        "turn_right": "right",
        "emergency_stop": "emergency_stop",
        "reset_emergency_stop": "reset_emergency_stop",
        "stand": "stand",
        "rest": "rest",
        "stop": "stop",
        "wave": "wave",
        "dance": "dance",
        "swim": "swim",
        "point": "point",
        "pushup": "pushup",
        "bow": "bow",
        "cute": "cute",
        "freaky": "freaky",
        "worm": "worm",
        "shake": "shake",
        "shrug": "shrug",
        "dead": "dead",
        "crab": "crab",
        "heartbeat": "heartbeat",
    }

    def __init__(self, config: ControllerConfig):
        self.config = config
        self.base_url = config.robot_url.rstrip("/")

    def get_status(self) -> RobotStatus:
        return RobotStatus(self._request_json("GET", "/api/status"))

    def wait_until_available(self) -> RobotStatus:
        last_error: Exception | None = None
        for attempt in range(self.config.reconnect_attempts):
            try:
                return self.get_status()
            except RobotClientError as exc:
                last_error = exc
                if attempt + 1 < self.config.reconnect_attempts:
                    time.sleep(self.config.reconnect_delay_s)
        raise RobotClientError(f"robot unavailable after reconnect attempts: {last_error}") from last_error

    def send_command(self, command: str, face: str | None = None) -> dict[str, Any]:
        firmware_command = self._normalize_command(command)
        payload: dict[str, str] = {"command": firmware_command}
        if face:
            payload["face"] = face
        return self._request_json("POST", "/api/command", payload)

    def set_face(self, face: str) -> dict[str, Any]:
        return self._request_json("POST", "/api/command", {"face": face})

    def heartbeat(self) -> dict[str, Any]:
        return self.send_command("heartbeat")

    def emergency_stop(self) -> dict[str, Any]:
        return self.send_command("emergency_stop")

    def reset_emergency_stop(self) -> dict[str, Any]:
        return self.send_command("reset_emergency_stop")

    def _normalize_command(self, command: str) -> str:
        normalized = command.strip().lower()
        if normalized not in self.COMMAND_ALIASES:
            raise UnsupportedCommandError(f"unsupported robot command: {command}")
        return self.COMMAND_ALIASES[normalized]

    def _request_json(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        data = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        http_request = request.Request(
            f"{self.base_url}{path}",
            data=data,
            headers=headers,
            method=method,
        )

        try:
            with request.urlopen(http_request, timeout=self.config.request_timeout_s) as response:
                body = response.read().decode("utf-8")
                return json.loads(body)
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RobotClientError(f"HTTP {exc.code}: {body}") from exc
        except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RobotClientError(str(exc)) from exc
