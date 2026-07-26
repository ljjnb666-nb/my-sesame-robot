from __future__ import annotations

import math
from typing import Any

from .errors import ToolError, ToolErrorCode
from .models import FORBIDDEN_TOOL_CALL_FIELDS, MAX_CALL_ID_CHARS, MAX_TOOL_NAME_CHARS, ToolCall
from .registry import ToolRegistry


MAX_STRING_CHARS = 500
MAX_LIST_ITEMS = 50
MAX_OBJECT_FIELDS = 50
MAX_NESTING_DEPTH = 5


def validate_tool_call(payload: Any, registry: ToolRegistry) -> ToolCall:
    _validate_json_value(payload, 0)
    if not isinstance(payload, dict):
        raise ToolError("tool call must be an object", ToolErrorCode.INVALID_TOOL_CALL_SCHEMA)
    allowed = {"call_id", "tool_name", "arguments"}
    extra = set(payload) - allowed
    missing = allowed - set(payload)
    forbidden = {_normalized(key) for key in payload} & {_normalized(key) for key in FORBIDDEN_TOOL_CALL_FIELDS}
    if extra or missing or forbidden:
        raise ToolError("tool call fields are invalid", ToolErrorCode.INVALID_TOOL_CALL_SCHEMA)
    call_id = _bounded_string(payload["call_id"], "call_id", MAX_CALL_ID_CHARS)
    tool_name = _bounded_string(payload["tool_name"], "tool_name", MAX_TOOL_NAME_CHARS)
    try:
        spec = registry.get(tool_name)
    except ToolError as exc:
        raise ToolError(str(exc), ToolErrorCode.UNKNOWN_TOOL) from exc
    arguments = payload["arguments"]
    if not isinstance(arguments, dict):
        raise ToolError("tool arguments must be an object", ToolErrorCode.INVALID_ARGUMENTS)
    _validate_arguments(arguments, spec.input_schema)
    return ToolCall(call_id, tool_name, arguments)


def _validate_arguments(arguments: dict[str, Any], schema: dict[str, Any]) -> None:
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))
    extra = set(arguments) - set(properties)
    missing = required - set(arguments)
    if extra or missing:
        raise ToolError("tool arguments do not match schema", ToolErrorCode.INVALID_ARGUMENTS)
    for key, value in arguments.items():
        spec = properties[key]
        expected = spec.get("type")
        if expected == "string":
            _bounded_string(value, key, MAX_STRING_CHARS)
            allowed_values = spec.get("enum")
            if allowed_values is not None and value not in allowed_values:
                raise ToolError(f"{key} is not supported", ToolErrorCode.INVALID_ARGUMENTS)
        elif expected == "integer":
            if isinstance(value, bool) or not isinstance(value, int):
                raise ToolError(f"{key} must be an integer", ToolErrorCode.INVALID_ARGUMENTS)
            minimum = spec.get("minimum")
            maximum = spec.get("maximum")
            if minimum is not None and value < minimum:
                raise ToolError(f"{key} is below minimum", ToolErrorCode.INVALID_ARGUMENTS)
            if maximum is not None and value > maximum:
                raise ToolError(f"{key} is above maximum", ToolErrorCode.INVALID_ARGUMENTS)
        elif expected == "object":
            if not isinstance(value, dict):
                raise ToolError(f"{key} must be an object", ToolErrorCode.INVALID_ARGUMENTS)
        else:
            raise ToolError(f"unsupported argument schema for {key}", ToolErrorCode.INVALID_ARGUMENTS)


def _validate_json_value(value: Any, depth: int) -> None:
    if depth > MAX_NESTING_DEPTH:
        raise ToolError("tool call nesting is too deep", ToolErrorCode.INVALID_TOOL_CALL_SCHEMA)
    if isinstance(value, dict):
        if len(value) > MAX_OBJECT_FIELDS:
            raise ToolError("tool call object has too many fields", ToolErrorCode.INVALID_TOOL_CALL_SCHEMA)
        for key, child in value.items():
            if not isinstance(key, str) or len(key) > MAX_STRING_CHARS:
                raise ToolError("tool call object key is invalid", ToolErrorCode.INVALID_TOOL_CALL_SCHEMA)
            if _normalized(key) in {_normalized(field) for field in FORBIDDEN_TOOL_CALL_FIELDS}:
                raise ToolError("tool call contains forbidden authority field", ToolErrorCode.INVALID_TOOL_CALL_SCHEMA)
            _validate_json_value(child, depth + 1)
    elif isinstance(value, list):
        if len(value) > MAX_LIST_ITEMS:
            raise ToolError("tool call list is too large", ToolErrorCode.INVALID_TOOL_CALL_SCHEMA)
        for child in value:
            _validate_json_value(child, depth + 1)
    elif isinstance(value, str):
        if len(value) > MAX_STRING_CHARS:
            raise ToolError("tool call string is too long", ToolErrorCode.INVALID_TOOL_CALL_SCHEMA)
    elif isinstance(value, bool) or value is None:
        return
    elif isinstance(value, int):
        return
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise ToolError("tool call number must be finite", ToolErrorCode.INVALID_TOOL_CALL_SCHEMA)
    else:
        raise ToolError("tool call contains non JSON value", ToolErrorCode.INVALID_TOOL_CALL_SCHEMA)


def _bounded_string(value: Any, field: str, limit: int) -> str:
    if not isinstance(value, str) or len(value) > limit:
        raise ToolError(f"{field} must be a bounded string", ToolErrorCode.INVALID_TOOL_CALL_SCHEMA)
    return value


def _normalized(value: str) -> str:
    return "".join(char for char in value.lower() if char.isalnum())
