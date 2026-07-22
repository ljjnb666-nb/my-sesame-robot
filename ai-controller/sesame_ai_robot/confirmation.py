from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import threading
import time
import uuid
from typing import Any, Callable


DEFAULT_CONFIRMATION_TTL_SECONDS = 60.0
MAX_CONFIRMATION_TTL_SECONDS = 300.0


@dataclass(frozen=True)
class ConfirmationRequest:
    confirmation_id: str
    action: str
    reason: str
    created_at: float
    expires_at: float
    context_token: str


@dataclass(frozen=True)
class ConfirmationGrant:
    confirmation_id: str
    action: str
    granted_at: float
    context_token: str


class ConfirmationErrorCode(str, Enum):
    UNKNOWN_ID = "unknown_id"
    EXPIRED = "expired"
    ACTION_MISMATCH = "action_mismatch"
    CONTEXT_CHANGED = "context_changed"
    ALREADY_USED = "already_used"


@dataclass(frozen=True)
class ConfirmationContext:
    runtime_mode: str
    action: str
    emergency_stop_active: bool
    safety_severity: str
    posture_state: str
    communication_timed_out: bool
    robot_motion_state: str
    proposed_command: str | None = None
    battery_percent: int | None = None
    hardware_available: bool = False
    experimental_enabled: bool = False

    def as_token_payload(self) -> dict[str, Any]:
        return {
            "runtime_mode": self.runtime_mode,
            "action": self.action,
            "emergency_stop_active": self.emergency_stop_active,
            "safety_severity": self.safety_severity,
            "posture_state": self.posture_state,
            "communication_timed_out": self.communication_timed_out,
            "robot_motion_state": self.robot_motion_state,
            "proposed_command": self.proposed_command or "",
            "battery_percent": self.battery_percent,
            "hardware_available": self.hardware_available,
            "experimental_enabled": self.experimental_enabled,
        }


@dataclass(frozen=True)
class ConfirmationResult:
    accepted: bool
    grant: ConfirmationGrant | None
    error: ConfirmationErrorCode | None
    reason: str


@dataclass
class ConfirmationStore:
    ttl_seconds: float = DEFAULT_CONFIRMATION_TTL_SECONDS
    _requests: dict[str, ConfirmationRequest] = field(default_factory=dict)
    _used: set[str] = field(default_factory=set)
    _clock: Callable[[], float] = time.monotonic
    _lock: threading.RLock = field(default_factory=threading.RLock)

    def __post_init__(self) -> None:
        if self.ttl_seconds <= 0:
            raise ValueError("confirmation ttl_seconds must be greater than zero")
        if self.ttl_seconds > MAX_CONFIRMATION_TTL_SECONDS:
            raise ValueError(f"confirmation ttl_seconds must be <= {MAX_CONFIRMATION_TTL_SECONDS}")

    def create(
        self,
        action: str,
        reason: str,
        context: dict[str, Any] | ConfirmationContext,
        now: float | None = None,
    ) -> ConfirmationRequest:
        created_at = self._clock() if now is None else now
        payload = _context_payload(context)
        request = ConfirmationRequest(
            confirmation_id=uuid.uuid4().hex,
            action=action,
            reason=reason,
            created_at=created_at,
            expires_at=created_at + self.ttl_seconds,
            context_token=context_token(payload),
        )
        with self._lock:
            self._requests[request.confirmation_id] = request
        return request

    def get_request(self, confirmation_id: str) -> ConfirmationRequest | None:
        with self._lock:
            return self._requests.get(confirmation_id)

    def consume(
        self,
        confirmation_id: str,
        expected_action: str,
        context: dict[str, Any] | ConfirmationContext,
        now: float | None = None,
    ) -> ConfirmationResult:
        granted_at = self._clock() if now is None else now
        token = context_token(_context_payload(context))
        with self._lock:
            request = self._requests.get(confirmation_id)
            if request is None:
                return ConfirmationResult(False, None, ConfirmationErrorCode.UNKNOWN_ID, "confirmation id is unknown")
            if confirmation_id in self._used:
                return ConfirmationResult(False, None, ConfirmationErrorCode.ALREADY_USED, "confirmation was already used")
            if request.action != expected_action:
                return ConfirmationResult(False, None, ConfirmationErrorCode.ACTION_MISMATCH, "confirmation action does not match")
            if granted_at >= request.expires_at:
                return ConfirmationResult(False, None, ConfirmationErrorCode.EXPIRED, "confirmation has expired")
            if request.context_token != token:
                return ConfirmationResult(False, None, ConfirmationErrorCode.CONTEXT_CHANGED, "confirmation context changed")
            self._used.add(confirmation_id)
        grant = ConfirmationGrant(confirmation_id, request.action, granted_at, token)
        return ConfirmationResult(True, grant, None, "confirmation accepted")


def _context_payload(context: dict[str, Any] | ConfirmationContext) -> dict[str, Any]:
    if isinstance(context, ConfirmationContext):
        return context.as_token_payload()
    return context


def context_token(context: dict[str, Any]) -> str:
    parts = [f"{key}={context.get(key)!r}" for key in sorted(context)]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
