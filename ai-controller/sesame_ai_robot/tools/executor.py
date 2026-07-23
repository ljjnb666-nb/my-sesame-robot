from __future__ import annotations

import json
from typing import Any

from ..ai_models import AIErrorCode
from ..assistant import AssistantAction, AssistantPlan, AssistantStep
from ..runtime import RobotRuntime, result_to_jsonable
from .builtin_tools import BUILTIN_TOOL_NAMES
from .errors import ToolError, ToolErrorCode
from .models import ToolCall, ToolResult
from .read_only import RobotReadOnlyFacade
from .registry import ToolRegistry
from .schemas import validate_tool_call


MAX_TOOL_CALLS_PER_REQUEST = 3
MAX_TOOL_RESULT_BYTES = 4096
ALLOWED_EXECUTE_ACTIONS = {
    "stop",
    "emergency_stop",
    "wave",
    "walk_forward",
    "walk_backward",
    "turn_left",
    "turn_right",
    "stand",
    "rest",
}


class ToolExecutor:
    def __init__(
        self,
        *,
        registry: ToolRegistry,
        read_only: RobotReadOnlyFacade,
        runtime: RobotRuntime,
    ) -> None:
        self.registry = registry
        self.read_only = read_only
        self.runtime = runtime
        self._executing = False

    def execute_many(
        self,
        payloads: list[dict[str, Any] | ToolCall],
        *,
        confirmation_id: str | None = None,
    ) -> tuple[ToolResult, ...]:
        if len(payloads) > MAX_TOOL_CALLS_PER_REQUEST:
            return (self._error_result("limit", "", ToolErrorCode.TOOL_LIMIT_EXCEEDED, "tool call limit exceeded"),)
        results: list[ToolResult] = []
        for payload in payloads:
            results.append(self.execute(payload, confirmation_id=confirmation_id))
        return tuple(results)

    def execute(self, payload: dict[str, Any] | ToolCall, *, confirmation_id: str | None = None) -> ToolResult:
        if self._executing:
            return self._error_result(_call_id(payload), _tool_name(payload), ToolErrorCode.RECURSIVE_TOOL_CALL, "recursive tool call rejected")
        self._executing = True
        try:
            try:
                call = payload if isinstance(payload, ToolCall) else validate_tool_call(payload, self.registry)
                self.registry.get(call.tool_name)
                if call.tool_name not in BUILTIN_TOOL_NAMES:
                    raise ToolError("forbidden tool", ToolErrorCode.FORBIDDEN_TOOL)
                result = self._execute_call(call, confirmation_id=confirmation_id)
                return self._enforce_result_size(result)
            except ToolError as exc:
                return self._error_result(_call_id(payload), _tool_name(payload), exc.code, str(exc))
            except Exception:
                return self._error_result(_call_id(payload), _tool_name(payload), ToolErrorCode.TOOL_EXECUTION_FAILED, "tool execution failed")
        finally:
            self._executing = False

    def _execute_call(self, call: ToolCall, *, confirmation_id: str | None) -> ToolResult:
        if call.tool_name == "get_battery_status":
            return self._ok(call, self.read_only.get_battery_status(), "已读取虚拟机器人电量。")
        if call.tool_name == "get_robot_state":
            return self._ok(call, self.read_only.get_robot_state(), "已读取虚拟机器人状态。")
        if call.tool_name == "get_pose":
            return self._ok(call, self.read_only.get_pose(), "已读取虚拟机器人姿态。")
        if call.tool_name == "get_communication_status":
            return self._ok(call, self.read_only.get_communication_status(), "已读取虚拟机器人通信状态。")
        if call.tool_name == "get_actuator_status":
            return self._ok(call, self.read_only.get_actuator_status(), "已读取虚拟执行器状态。")
        if call.tool_name == "get_fault_status":
            return self._ok(call, self.read_only.get_fault_status(), "已读取模拟器故障状态。")
        if call.tool_name == "get_charging_status":
            return self._ok(call, self.read_only.get_charging_status(), "已读取模拟器充电状态。")
        if call.tool_name == "get_timeline":
            return self._ok(call, self.read_only.get_timeline(int(call.arguments.get("limit", 20))), "已读取模拟器事件时间线。")
        if call.tool_name == "execute_action":
            return self._execute_action(call, confirmation_id=confirmation_id)
        raise ToolError("unknown tool", ToolErrorCode.UNKNOWN_TOOL)

    def _execute_action(self, call: ToolCall, *, confirmation_id: str | None) -> ToolResult:
        action = call.arguments.get("action")
        if not isinstance(action, str) or action not in ALLOWED_EXECUTE_ACTIONS:
            return self._error_result(call.call_id, call.tool_name, ToolErrorCode.INVALID_ARGUMENTS, "unsupported robot action")
        assistant = AssistantPlan(
            transcript=action,
            steps=(AssistantStep(AssistantAction.ROBOT_COMMAND, action, "AI structured intent"),),
        )
        runtime_result = self.runtime.step(assistant=assistant, confirmation_id=confirmation_id)
        payload = result_to_jsonable(runtime_result, self.runtime.config)
        if runtime_result.confirmation_state == "requested":
            return ToolResult(
                call.call_id,
                call.tool_name,
                "confirmation_required",
                {"action": action, "runtime": payload, "confirmation_id": runtime_result.plan.confirmation_request.confirmation_id},
                AIErrorCode.CONFIRMATION_REQUIRED.value,
                f"该虚拟机器人动作需要确认。原因：{runtime_result.plan.reason}",
            )
        if runtime_result.confirmation_state not in {"none", "accepted"}:
            return ToolResult(
                call.call_id,
                call.tool_name,
                "failed",
                {"action": action, "runtime": payload},
                runtime_result.confirmation_state,
                f"动作未执行：confirmation 状态为 {runtime_result.confirmation_state}。",
            )
        if runtime_result.sent_command:
            if runtime_result.plan.command != action:
                return ToolResult(
                    call.call_id,
                    call.tool_name,
                    "failed",
                    {"action": action, "runtime": payload},
                    ToolErrorCode.TOOL_EXECUTION_FAILED.value,
                    f"动作未执行：安全层选择了 {runtime_result.plan.command}，原因：{runtime_result.plan.reason}",
                )
            return ToolResult(
                call.call_id,
                call.tool_name,
                "ok",
                {"action": action, "runtime": payload},
                None,
                f"模拟器已执行虚拟机器人动作：{action}。",
            )
        return ToolResult(
            call.call_id,
            call.tool_name,
            "failed",
            {"action": action, "runtime": payload},
            ToolErrorCode.TOOL_EXECUTION_FAILED.value,
            f"动作未执行：{runtime_result.plan.reason}",
        )

    def _ok(self, call: ToolCall, result: dict[str, Any], message: str) -> ToolResult:
        return ToolResult(call.call_id, call.tool_name, "ok", result, None, message)

    def _enforce_result_size(self, result: ToolResult) -> ToolResult:
        encoded = json.dumps(result.to_jsonable(), ensure_ascii=False, allow_nan=False)
        if len(encoded.encode("utf-8")) <= MAX_TOOL_RESULT_BYTES:
            return result
        return ToolResult(
            result.call_id,
            result.tool_name,
            "failed",
            None,
            ToolErrorCode.TOOL_RESULT_TOO_LARGE.value,
            "tool result exceeded size limit",
        )

    def _error_result(self, call_id: str, tool_name: str, code: ToolErrorCode, message: str) -> ToolResult:
        return ToolResult(call_id or "invalid", tool_name or "unknown", "failed", None, code.value, message)


def _call_id(payload: dict[str, Any] | ToolCall) -> str:
    if isinstance(payload, ToolCall):
        return payload.call_id
    value = payload.get("call_id") if isinstance(payload, dict) else None
    return value if isinstance(value, str) and len(value) <= 128 else "invalid"


def _tool_name(payload: dict[str, Any] | ToolCall) -> str:
    if isinstance(payload, ToolCall):
        return payload.tool_name
    value = payload.get("tool_name") if isinstance(payload, dict) else None
    return value if isinstance(value, str) and len(value) <= 64 else "unknown"
