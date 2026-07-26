from __future__ import annotations

from enum import Enum


class ToolErrorCode(str, Enum):
    INVALID_TOOL_CALL_SCHEMA = "invalid_tool_call_schema"
    UNKNOWN_TOOL = "unknown_tool"
    INVALID_ARGUMENTS = "invalid_arguments"
    FORBIDDEN_TOOL = "forbidden_tool"
    TOOL_LIMIT_EXCEEDED = "tool_limit_exceeded"
    RECURSIVE_TOOL_CALL = "recursive_tool_call"
    TOOL_RESULT_TOO_LARGE = "tool_result_too_large"
    TOOL_EXECUTION_FAILED = "tool_execution_failed"


class ToolError(ValueError):
    def __init__(self, message: str, code: ToolErrorCode = ToolErrorCode.INVALID_TOOL_CALL_SCHEMA):
        super().__init__(message)
        self.code = code
