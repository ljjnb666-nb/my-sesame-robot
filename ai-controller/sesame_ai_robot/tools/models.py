from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import json
from types import MappingProxyType
from typing import Any

from .errors import ToolError, ToolErrorCode


FORBIDDEN_TOOL_CALL_FIELDS = {
    "confirmation_id",
    "confirmation_grant",
    "confirmation_grants",
    "safety_severity",
    "runtime_mode",
    "allow_real_robot",
    "arbiter_override",
    "hardware_backend",
    "callable",
    "function",
    "python_callable",
}


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    category: str
    read_only: bool
    version: str = "1"
    _schema_view: MappingProxyType = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        _ensure_json_safe(self.input_schema)
        frozen_schema = _deep_freeze(self.input_schema)
        object.__setattr__(self, "input_schema", frozen_schema)
        object.__setattr__(self, "_schema_view", frozen_schema)

    def schema(self) -> MappingProxyType:
        return self._schema_view

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": _deep_thaw(self.input_schema),
            "category": self.category,
            "read_only": self.read_only,
            "version": self.version,
        }


@dataclass(frozen=True)
class ToolCall:
    call_id: str
    tool_name: str
    arguments: dict[str, Any]

    def __post_init__(self) -> None:
        for key in self.arguments:
            if _normalized(key) in {_normalized(field) for field in FORBIDDEN_TOOL_CALL_FIELDS}:
                raise ToolError(f"forbidden tool argument field: {key}", ToolErrorCode.INVALID_TOOL_CALL_SCHEMA)
        _ensure_json_safe(self.arguments)
        object.__setattr__(self, "arguments", deepcopy(self.arguments))

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "call_id": self.call_id,
            "tool_name": self.tool_name,
            "arguments": deepcopy(self.arguments),
        }


@dataclass(frozen=True)
class ToolResult:
    call_id: str
    tool_name: str
    status: str
    result: dict[str, Any] | None = None
    error_code: str | None = None
    user_message: str = ""

    def __post_init__(self) -> None:
        if self.result is not None:
            _ensure_json_safe(self.result)

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "call_id": self.call_id,
            "tool_name": self.tool_name,
            "status": self.status,
            "result": deepcopy(self.result),
            "error_code": self.error_code,
            "user_message": self.user_message,
        }


def _ensure_json_safe(value: Any) -> None:
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ToolError("tool model contains non JSON-safe data") from exc


def _deep_freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({str(key): _deep_freeze(child) for key, child in value.items()})
    if isinstance(value, list):
        return tuple(_deep_freeze(child) for child in value)
    return value


def _deep_thaw(value: Any) -> Any:
    if isinstance(value, MappingProxyType):
        return {key: _deep_thaw(child) for key, child in value.items()}
    if isinstance(value, tuple):
        return [_deep_thaw(child) for child in value]
    return deepcopy(value)


def _normalized(value: str) -> str:
    return "".join(char for char in value.lower() if char.isalnum())
