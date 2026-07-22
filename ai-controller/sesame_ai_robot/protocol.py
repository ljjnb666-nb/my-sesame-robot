from __future__ import annotations

from dataclasses import dataclass
from typing import Any


MAX_API_BODY_BYTES = 512

AVAILABLE_COMMANDS = {
    "stand", "rest", "forward", "backward", "left", "right", "stop",
    "wave", "dance", "swim", "point", "pushup", "bow", "cute", "freaky",
    "worm", "shake", "shrug", "dead", "crab", "emergency_stop",
    "reset_emergency_stop", "heartbeat",
}

AVAILABLE_FACES = {
    "walk", "rest", "swim", "dance", "wave", "point", "stand", "cute",
    "pushup", "freaky", "bow", "worm", "shake", "shrug", "dead", "crab",
    "idle", "idle_blink", "default", "happy", "talk_happy", "sad",
    "talk_sad", "angry", "talk_angry", "surprised", "talk_surprised",
    "sleepy", "talk_sleepy", "love", "talk_love", "excited",
    "talk_excited", "confused", "talk_confused", "thinking",
    "talk_thinking",
}


@dataclass(frozen=True)
class ProtocolError:
    status_code: int
    error: str
    message: str

    def payload(self) -> dict[str, str]:
        return {"status": "error", "error": self.error, "message": self.message}


ERRORS = {
    "invalid_json": ProtocolError(400, "invalid_json", "Invalid JSON body"),
    "invalid_payload": ProtocolError(400, "invalid_payload", "Request body must be a JSON object"),
    "missing_command": ProtocolError(400, "missing_command", "Missing command or face field"),
    "invalid_command_type": ProtocolError(400, "invalid_command_type", "Command must be a string"),
    "empty_command": ProtocolError(400, "empty_command", "Command must not be empty"),
    "unknown_command": ProtocolError(400, "unknown_command", "Unsupported robot command"),
    "invalid_face_type": ProtocolError(400, "invalid_face_type", "Face must be a string"),
    "empty_face": ProtocolError(400, "empty_face", "Face must not be empty"),
    "unknown_face": ProtocolError(400, "unknown_face", "Unsupported face"),
    "emergency_stop_active": ProtocolError(409, "emergency_stop_active", "Emergency stop is active"),
    "payload_too_large": ProtocolError(413, "payload_too_large", "Request body is too large"),
    "method_not_allowed": ProtocolError(405, "method_not_allowed", "Method not allowed"),
}


def validate_api_payload(payload: Any) -> tuple[str | None, str | None, ProtocolError | None]:
    if not isinstance(payload, dict):
        return None, None, ERRORS["invalid_payload"]

    has_command = "command" in payload
    has_face = "face" in payload
    if not has_command and not has_face:
        return None, None, ERRORS["missing_command"]

    command: str | None = None
    face: str | None = None
    if has_command:
        if not isinstance(payload["command"], str):
            return None, None, ERRORS["invalid_command_type"]
        command = payload["command"].strip().lower()
        if not command:
            return None, None, ERRORS["empty_command"]
        if command not in AVAILABLE_COMMANDS:
            return None, None, ERRORS["unknown_command"]

    if has_face:
        if not isinstance(payload["face"], str):
            return None, None, ERRORS["invalid_face_type"]
        face = payload["face"].strip().lower()
        if not face:
            return None, None, ERRORS["empty_face"]
        if face not in AVAILABLE_FACES:
            return None, None, ERRORS["unknown_face"]

    return command, face, None
