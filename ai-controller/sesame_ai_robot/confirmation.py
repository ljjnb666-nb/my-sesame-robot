from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import time
import uuid
from typing import Any


DEFAULT_CONFIRMATION_TTL_SECONDS = 60.0


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


@dataclass
class ConfirmationStore:
    ttl_seconds: float = DEFAULT_CONFIRMATION_TTL_SECONDS
    _requests: dict[str, ConfirmationRequest] = field(default_factory=dict)
    _used: set[str] = field(default_factory=set)

    def create(self, action: str, reason: str, context: dict[str, Any], now: float | None = None) -> ConfirmationRequest:
        created_at = time.monotonic() if now is None else now
        request = ConfirmationRequest(
            confirmation_id=uuid.uuid4().hex,
            action=action,
            reason=reason,
            created_at=created_at,
            expires_at=created_at + self.ttl_seconds,
            context_token=context_token(context),
        )
        self._requests[request.confirmation_id] = request
        return request

    def grant(
        self,
        confirmation_id: str,
        action: str,
        context: dict[str, Any],
        now: float | None = None,
    ) -> ConfirmationGrant | None:
        granted_at = time.monotonic() if now is None else now
        request = self._requests.get(confirmation_id)
        token = context_token(context)
        if request is None:
            return None
        if confirmation_id in self._used:
            return None
        if request.action != action:
            return None
        if request.expires_at < granted_at:
            return None
        if request.context_token != token:
            return None
        self._used.add(confirmation_id)
        return ConfirmationGrant(confirmation_id, action, granted_at, token)


def context_token(context: dict[str, Any]) -> str:
    parts = [
        str(context.get("runtime_mode", "")),
        str(context.get("emergency_stop_active", "")),
        str(context.get("posture", "")),
        str(context.get("target_action", "")),
        str(context.get("safety_summary", "")),
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
