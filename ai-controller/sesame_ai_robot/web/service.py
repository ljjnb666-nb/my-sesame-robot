from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import threading
import time
import uuid
from typing import Any

from ..advanced import RuntimeMode
from ..ai_interaction import AIInteractionLoop, reply_to_jsonable
from ..ai_provider import AIProvider, provider_from_env
from ..confirmation import ConfirmationStore
from ..memory import MemoryManager
from ..tools import create_builtin_registry
from ..tools.models import ToolResult
from ..virtual_hardware import FAULTS, SimulatorHardwareAdapter
from .security import (
    API_VERSION,
    DEFAULT_TIMELINE_LIMIT,
    MAX_CONFIRMATION_ID_CHARS,
    MAX_FAULT_CHARS,
    MAX_TIMELINE_LIMIT,
    ensure_json_safe,
    provider_label,
    sanitize_jsonable,
)


class WebServiceError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class PendingConfirmation:
    text: str
    action: str | None
    fingerprint: str | None
    created_at: float
    generation: int


class RobotSimulatorService:
    def __init__(
        self,
        *,
        provider: AIProvider | None = None,
        provider_name: str = "mock",
        memory_manager: MemoryManager | None = None,
        memory_storage_path: str | Path | None = None,
        confirmation_store_factory: Any | None = None,
    ) -> None:
        self._lock = threading.RLock()
        self._provider_name = provider_name
        self._provider = provider or provider_from_env(provider_name)
        self._external_memory_manager = memory_manager
        self._memory_storage_path = Path(memory_storage_path) if memory_storage_path is not None else None
        self._confirmation_store_factory = confirmation_store_factory or ConfirmationStore
        self._generation = 0
        self._pending_confirmation: PendingConfirmation | None = None
        self._build_session()

    def health(self) -> dict[str, Any]:
        with self._lock:
            return {
                "status": "ok",
                "version": API_VERSION,
                "runtimeMode": RuntimeMode.SIMULATOR.value,
                "simulatorOnly": True,
                "provider": provider_label(getattr(self._loop.provider, "name", self._provider_name)),
            }

    def chat(self, text: str, confirmation_id: str | None = None) -> dict[str, Any]:
        with self._lock:
            if confirmation_id is not None and len(confirmation_id) > MAX_CONFIRMATION_ID_CHARS:
                raise WebServiceError("invalid_request", "confirmationId is too long")
            if confirmation_id is not None:
                self._validate_pending_confirmation(text)
            reply = self._loop.handle_text(text, confirmation_id=confirmation_id)
            payload = reply_to_jsonable(reply, include_confirmation_id=True)
            if reply.requires_confirmation:
                self._pending_confirmation = PendingConfirmation(
                    text=text,
                    action=reply.action,
                    fingerprint=reply.confirmation_fingerprint,
                    created_at=time.monotonic(),
                    generation=self._generation,
                )
            elif confirmation_id is not None:
                self._pending_confirmation = None
            return ensure_json_safe(sanitize_jsonable(payload))

    def state(self) -> dict[str, Any]:
        with self._lock:
            result = self._execute_read_only("get_robot_state", {})
            state = dict(result.result or {})
            return ensure_json_safe(sanitize_jsonable({
                "runtimeMode": RuntimeMode.SIMULATOR.value,
                "motionState": state.get("motionState"),
                "currentCommand": state.get("currentCommand"),
                "currentFace": state.get("currentFace"),
                "emergencyStopActive": state.get("emergencyStopActive"),
                "communicationTimedOut": state.get("communicationTimedOut"),
                "batteryPercent": state.get("batteryPercent"),
                "robotPose": state.get("robotPose"),
                "chargingState": state.get("chargingState"),
                "faults": state.get("faults", []),
            }))

    def timeline(self, limit: int = DEFAULT_TIMELINE_LIMIT) -> dict[str, Any]:
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1 or limit > MAX_TIMELINE_LIMIT:
            raise WebServiceError("invalid_request", "timeline limit must be 1..50")
        with self._lock:
            result = self._execute_read_only("get_timeline", {"limit": limit})
            return ensure_json_safe(sanitize_jsonable(result.result or {"events": [], "limit": limit}))

    def inject_fault(self, fault: str) -> dict[str, Any]:
        with self._lock:
            self._validate_fault(fault, allow_all=False)
            self._loop.hardware.inject_fault(fault)
            return {"status": "ok", "fault": fault, "state": self.state()}

    def clear_fault(self, fault: str) -> dict[str, Any]:
        with self._lock:
            self._validate_fault(fault, allow_all=True)
            self._loop.hardware.clear_fault(fault)
            return {"status": "ok", "fault": fault, "state": self.state()}

    def reset_simulator(self) -> dict[str, Any]:
        with self._lock:
            old_memory = self._loop.memory_manager
            self._generation += 1
            self._pending_confirmation = None
            self._build_session(memory_manager=old_memory)
            return {"status": "ok", "generation": self._generation, "state": self.state()}

    def reset_session(self) -> dict[str, Any]:
        with self._lock:
            self._pending_confirmation = None
            self._loop.reset_session()
            return {
                "status": "ok",
                "sessionId": self._loop.memory.session_id,
                "runtimeConfirmationsRevoked": False,
            }

    def _testing_identity(self) -> dict[str, int]:
        with self._lock:
            return {
                "loop": id(self._loop),
                "runtime": id(self._loop.runtime),
                "confirmation_store": id(self._loop.confirmation_store),
                "hardware": id(self._loop.hardware),
                "facade": id(self._loop.read_only_facade),
                "executor": id(self._loop.tool_executor),
                "memory_manager": id(self._loop.memory_manager),
            }

    def _testing_snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "hardwareSnapshot": self._loop.hardware.state.snapshot(),
                "currentCommand": self._loop.client.current_command,
                "currentFace": self._loop.client.current_face,
                "runtimeMode": self._loop.runtime.config.runtime_mode.value,
                "allowRealRobot": self._loop.runtime.config.allow_real_robot,
                "confirmationRequestCount": len(self._loop.confirmation_store._requests),
                "hardwareEventCount": len(self._loop.hardware.events),
                "faults": sorted(self._loop.hardware.state.faults),
                "emergencyStop": self._loop.hardware.state.emergency_stop,
                "chargingState": self._loop.hardware.state.charging_state,
                "shortTermMemory": self._loop.memory_manager.retrieve("short_term"),
                "longTermMemory": self._loop.memory_manager.retrieve("long_term"),
                "memoryPath": str(self._loop.memory_manager.storage_path),
                "pendingConfirmation": self._pending_confirmation is not None,
            }

    def _testing_store_memory(self, scope: str, key: str, value: Any) -> None:
        with self._lock:
            self._loop.memory_manager.store(scope, key, value)

    def _testing_memory(self, scope: str, key: str | None = None) -> Any:
        with self._lock:
            return self._loop.memory_manager.retrieve(scope, key)

    def _testing_append_event(self, event: dict[str, Any]) -> None:
        with self._lock:
            self._loop.hardware.events.append(dict(event))

    def _build_session(self, memory_manager: MemoryManager | None = None) -> None:
        manager = memory_manager or self._external_memory_manager or MemoryManager(self._memory_storage_path)
        self._loop = AIInteractionLoop(
            provider=self._provider,
            runtime_mode=RuntimeMode.SIMULATOR,
            hardware=SimulatorHardwareAdapter(),
            confirmation_store=self._confirmation_store_factory(),
            memory_manager=manager,
            tool_registry=create_builtin_registry(),
        )

    def _execute_read_only(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
        result = self._loop.tool_executor.execute({
            "call_id": f"web_{uuid.uuid4().hex[:12]}",
            "tool_name": tool_name,
            "arguments": arguments,
        })
        if result.status != "ok":
            raise WebServiceError(result.error_code or "tool_failed", result.user_message or "tool execution failed")
        return result

    def _validate_pending_confirmation(self, text: str) -> None:
        pending = self._pending_confirmation
        if pending is None or pending.generation != self._generation:
            return
        if text != pending.text:
            raise WebServiceError("stale_confirmation", "confirmation text does not match the pending request")

    def _validate_fault(self, fault: str, *, allow_all: bool) -> None:
        if len(fault) > MAX_FAULT_CHARS:
            raise WebServiceError("invalid_request", "fault is too long")
        if allow_all and fault == "all":
            return
        if fault not in FAULTS:
            raise WebServiceError("unknown_fault", "unknown simulator fault")


def create_service(
    *,
    provider: AIProvider | None = None,
    provider_name: str = "mock",
    memory_manager: MemoryManager | None = None,
    memory_storage_path: str | Path | None = None,
    confirmation_store_factory: Any | None = None,
) -> RobotSimulatorService:
    return RobotSimulatorService(
        provider=provider,
        provider_name=provider_name,
        memory_manager=memory_manager,
        memory_storage_path=memory_storage_path,
        confirmation_store_factory=confirmation_store_factory,
    )
