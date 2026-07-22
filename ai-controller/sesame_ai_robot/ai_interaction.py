from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import math
import time
import uuid
from typing import Any

from .advanced import RuntimeMode
from .ai_models import (
    AIErrorCode,
    AIProviderError,
    AIProviderRefusal,
    AIProviderTimeout,
    AIRequest,
    AIResponse,
    ActionPlan,
    ConversationTurn,
    ExecutionResult,
    MAX_ACTIONS_DEFAULT,
    MAX_ACTIONS_HARD_LIMIT,
    MAX_NESTING_DEPTH,
    MAX_PROVIDER_OUTPUT_CHARS,
    MAX_STRING_CHARS,
    MAX_TEXT_CHARS,
    PlanValidationResult,
    ProposedAction,
    RobotIntent,
    RobotReply,
)
from .ai_provider import AIProvider, provider_from_env
from .assistant import AssistantAction, AssistantPlan, AssistantStep
from .confirmation import ConfirmationStore
from .runtime import RobotRuntime, RobotRuntimeConfig, result_to_jsonable
from .virtual_hardware import HardwareDispatchError, HardwareSafetyError, SimulatorHardwareAdapter, VirtualHardwareRobotClient


ALLOWED_TOP_LEVEL_FIELDS = {
    "request_id",
    "intent",
    "confidence",
    "requires_clarification",
    "clarification_question",
    "actions",
    "user_message",
    "reason_code",
}
FORBIDDEN_FIELDS = {
    "confirmation_id",
    "confirmation_grant",
    "confirmation_grants",
    "user_confirmed",
    "user_confirmed_actions",
    "confirmed",
    "bypass_arbiter",
    "skip_arbiter",
    "hardware_adapter",
    "runtime_mode",
    "safety_severity",
}
ALLOWED_ACTIONS = {
    "query_status",
    "robot_command",
    "deny",
    "simulator.inject_fault",
    "simulator.clear_fault",
    "simulator.reset",
}
ALLOWED_QUERIES = {"summary", "battery", "pose", "communication", "actuators", "faults", "timeline", "charging"}
ALLOWED_COMMANDS = {
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


@dataclass
class ConversationMemory:
    session_id: str
    max_turns: int = 8
    turns: list[ConversationTurn] = field(default_factory=list)
    last_clarification: str | None = None
    last_execution: ExecutionResult | None = None
    pending_confirmation_fingerprint: str | None = None

    def add(self, turn: ConversationTurn) -> None:
        self.turns.append(turn)
        if len(self.turns) > self.max_turns:
            self.turns = self.turns[-self.max_turns :]

    def clear(self) -> None:
        self.turns.clear()
        self.last_clarification = None
        self.last_execution = None
        self.pending_confirmation_fingerprint = None

    def model_safe_summary(self) -> tuple[str, ...]:
        return tuple(
            f"user={turn.user_text[:80]} reply={turn.robot_reply[:80]} code={turn.result_code}"
            for turn in self.turns[-3:]
        )


class AIIntentValidationError(ValueError):
    def __init__(self, message: str, code: AIErrorCode = AIErrorCode.SCHEMA_VALIDATION_FAILED):
        super().__init__(message)
        self.code = code


class AIInteractionLoop:
    def __init__(
        self,
        provider: AIProvider | None = None,
        runtime_mode: RuntimeMode = RuntimeMode.SIMULATOR,
        hardware: SimulatorHardwareAdapter | None = None,
        confirmation_store: ConfirmationStore | None = None,
        max_actions: int = MAX_ACTIONS_DEFAULT,
    ) -> None:
        if runtime_mode == RuntimeMode.REAL_ROBOT:
            raise ValueError("AI interaction loop does not allow real_robot mode")
        if max_actions <= 0 or max_actions > MAX_ACTIONS_HARD_LIMIT:
            raise ValueError(f"max_actions must be 1..{MAX_ACTIONS_HARD_LIMIT}")
        self.provider = provider or provider_from_env("mock")
        self.runtime_mode = runtime_mode
        self.hardware = hardware or SimulatorHardwareAdapter()
        self.client = VirtualHardwareRobotClient(self.hardware)
        self.confirmation_store = confirmation_store or ConfirmationStore()
        self.runtime = RobotRuntime(
            self.client,
            RobotRuntimeConfig(runtime_mode=runtime_mode, dry_run=False),
            confirmation_store=self.confirmation_store,
        )
        self.max_actions = max_actions
        self.memory = ConversationMemory(session_id=f"session_{uuid.uuid4().hex[:12]}")
        self.events: list[dict[str, Any]] = []

    def reset_session(self) -> None:
        self.memory.clear()
        self._event("ai_session_reset", None, None, "ok")

    def handle_text(self, text: str, confirmation_id: str | None = None) -> RobotReply:
        started = time.monotonic()
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        if len(text) > MAX_TEXT_CHARS:
            return self._reply(request_id, "failed", "命令过长，未执行任何模拟器动作。", AIErrorCode.PLAN_REJECTED.value)
        request_data = self._build_request(request_id, text)
        self._event("ai_request_received", request_id, None, "ok")
        try:
            self._event("provider_request_started", request_id, None, "ok")
            response = self.provider.generate_intent(request_data)
            self._event("provider_response_received", request_id, None, "ok", provider=response.provider, model=response.model)
            intent = validate_ai_response(response, request_data)
            self._event("intent_validated", request_id, intent.intent, "ok")
            validation = validate_plan(intent, self.max_actions)
            if not validation.accepted or validation.plan is None:
                self._event("plan_rejected", request_id, intent.intent, validation.error_code.value if validation.error_code else "rejected")
                return self._finish(request_id, text, self._reply(
                    request_id,
                    "failed",
                    f"动作未执行：{validation.reason}",
                    (validation.error_code or AIErrorCode.PLAN_REJECTED).value,
                    intent=intent.intent,
                ))
            self._event("plan_created", request_id, intent.intent, "ok")
            if intent.requires_clarification:
                self.memory.last_clarification = intent.clarification_question
                return self._finish(request_id, text, self._reply(
                    request_id,
                    "clarification_required",
                    intent.clarification_question or "请补充更明确的动作参数。",
                    AIErrorCode.CLARIFICATION_REQUIRED.value,
                    intent=intent.intent,
                ))
            result = self._execute_plan(validation.plan, confirmation_id)
            duration_ms = int((time.monotonic() - started) * 1000)
            reply = self._reply(
                request_id,
                result.status,
                result.user_message,
                (result.error_code or AIErrorCode.OK).value,
                intent=intent.intent,
                action=result.action,
                requires_confirmation=result.confirmation_state == "requested",
                confirmation_id=(result.diagnostics or {}).get("confirmation_id"),
                structured={**(result.diagnostics or {}), "durationMs": duration_ms},
            )
            return self._finish(request_id, text, reply, result)
        except AIProviderTimeout:
            self._event("provider_response_received", request_id, None, AIErrorCode.PROVIDER_TIMEOUT.value)
            return self._finish(request_id, text, self._reply(
                request_id,
                "failed",
                "AI provider 超时，未执行任何模拟器动作。",
                AIErrorCode.PROVIDER_TIMEOUT.value,
            ))
        except AIProviderRefusal:
            return self._finish(request_id, text, self._reply(
                request_id,
                "failed",
                "AI provider 拒绝生成意图，未执行任何模拟器动作。",
                AIErrorCode.PROVIDER_REFUSED.value,
            ))
        except AIProviderError:
            return self._finish(request_id, text, self._reply(
                request_id,
                "failed",
                "AI provider 出错，未执行任何模拟器动作。",
                AIErrorCode.PROVIDER_ERROR.value,
            ))
        except AIIntentValidationError as exc:
            self._event("intent_validation_failed", request_id, None, exc.code.value)
            return self._finish(request_id, text, self._reply(
                request_id,
                "failed",
                f"AI 输出未通过结构化校验：{exc}",
                exc.code.value,
            ))

    def _execute_plan(self, plan: ActionPlan, confirmation_id: str | None) -> ExecutionResult:
        if len(plan.actions) != 1:
            return ExecutionResult(None, "failed", AIErrorCode.PLAN_REJECTED, "V0 only executes one action", user_message="动作未执行：V0 只支持单动作计划。")
        action = plan.actions[0]
        if action.action == "deny":
            return ExecutionResult(action.action, "failed", AIErrorCode.PLAN_REJECTED, "denied", user_message="动作未执行：该请求会绕过安全边界或使用不存在的能力。")
        if action.action == "query_status":
            self._event("action_dispatched", None, action.action, "ok")
            message, details = self._query_status(str(action.arguments.get("query", "summary")))
            self._event("action_completed", None, action.action, "ok")
            return ExecutionResult(action.action, "ok", None, None, user_message=message, diagnostics=details)
        if action.action == "robot_command":
            command = str(action.arguments["command"])
            assistant = AssistantPlan(
                transcript=command,
                steps=(AssistantStep(AssistantAction.ROBOT_COMMAND, command, "AI structured intent"),),
            )
            result = self.runtime.step(assistant=assistant, confirmation_id=confirmation_id)
            payload = result_to_jsonable(result, self.runtime.config)
            if result.confirmation_state == "requested":
                request_obj = result.plan.confirmation_request
                self.memory.pending_confirmation_fingerprint = _fingerprint(request_obj.confirmation_id if request_obj else None)
                self._event("confirmation_required", None, command, "confirmation_required", confirmation_fingerprint=self.memory.pending_confirmation_fingerprint)
                return ExecutionResult(
                    command,
                    "confirmation_required",
                    AIErrorCode.CONFIRMATION_REQUIRED,
                    result.plan.reason,
                    confirmation_state="requested",
                    user_message=f"该虚拟机器人动作需要确认。原因：{result.plan.reason}",
                    diagnostics={"runtime": payload, "confirmation_id": request_obj.confirmation_id if request_obj else None},
                )
            if result.confirmation_state not in {"none", "accepted"}:
                self._event("action_failed", None, command, result.confirmation_state)
                return ExecutionResult(
                    command,
                    "failed",
                    AIErrorCode.EXECUTION_FAILED,
                    result.confirmation_error,
                    confirmation_state=result.confirmation_state,
                    user_message=f"动作未执行：confirmation 状态为 {result.confirmation_state}。",
                    diagnostics={"runtime": payload},
                )
            if result.sent_command:
                if result.plan.command != command:
                    self._event("action_failed", None, command, result.plan.source)
                    return ExecutionResult(
                        command,
                        "failed",
                        AIErrorCode.EXECUTION_FAILED,
                        result.plan.reason,
                        confirmation_state=result.confirmation_state,
                        user_message=f"动作未执行：安全层选择了 {result.plan.command}，原因：{result.plan.reason}",
                        diagnostics={"runtime": payload, "hardware": self.hardware.state.snapshot()},
                    )
                self._event("action_dispatched", None, command, "ok")
                self._event("action_completed", None, command, "ok")
                return ExecutionResult(
                    command,
                    "ok",
                    None,
                    None,
                    confirmation_state=result.confirmation_state,
                    user_message=f"模拟器已执行虚拟机器人动作：{command}。",
                    diagnostics={"runtime": payload, "hardware": self.hardware.state.snapshot()},
                )
            return ExecutionResult(
                command,
                "failed",
                AIErrorCode.EXECUTION_FAILED,
                result.plan.reason,
                confirmation_state=result.confirmation_state,
                user_message=f"动作未执行：{result.plan.reason}",
                diagnostics={"runtime": payload},
            )
        try:
            if action.action == "simulator.inject_fault":
                fault = str(action.arguments["fault"])
                self.hardware.inject_fault(fault)
                return ExecutionResult(action.action, "ok", None, None, user_message=f"已在模拟器注入故障：{fault}。", diagnostics={"hardware": self.hardware.state.snapshot()})
            if action.action == "simulator.clear_fault":
                fault = str(action.arguments.get("fault", "all"))
                self.hardware.clear_fault(fault)
                return ExecutionResult(action.action, "ok", None, None, user_message=f"已清除模拟器故障：{fault}。", diagnostics={"hardware": self.hardware.state.snapshot()})
            if action.action == "simulator.reset":
                self.hardware = SimulatorHardwareAdapter()
                self.client = VirtualHardwareRobotClient(self.hardware)
                self.runtime = RobotRuntime(
                    self.client,
                    RobotRuntimeConfig(runtime_mode=self.runtime_mode, dry_run=False),
                    confirmation_store=self.confirmation_store,
                )
                return ExecutionResult(action.action, "ok", None, None, user_message="模拟器状态已重置。", diagnostics={"hardware": self.hardware.state.snapshot()})
        except (ValueError, HardwareDispatchError, HardwareSafetyError) as exc:
            return ExecutionResult(action.action, "failed", AIErrorCode.EXECUTION_FAILED, str(exc), user_message=f"模拟器操作未执行：{exc}")
        return ExecutionResult(action.action, "failed", AIErrorCode.UNSUPPORTED_ACTION, "unsupported action", user_message="动作未执行：不支持的 action。")

    def _build_request(self, request_id: str, text: str) -> AIRequest:
        status = self.client.get_status().raw
        return AIRequest(
            request_id=request_id,
            session_id=self.memory.session_id,
            user_text=text,
            runtime_mode=self.runtime_mode.value,
            capabilities=tuple(status.get("capabilities", ())) + ("ai_structured_intent",),
            robot_state=_status_summary(status),
            safety_context={
                "mode": self.runtime_mode.value,
                "history": self.memory.model_safe_summary(),
                "maxActions": self.max_actions,
            },
            max_actions=self.max_actions,
        )

    def _query_status(self, query: str) -> tuple[str, dict[str, Any]]:
        snapshot = self.hardware.state.snapshot()
        if query == "battery":
            battery = snapshot["battery"]
            return f"已读取虚拟机器人电量：当前为 {battery['percent']}%。", {"battery": battery}
        if query == "pose":
            return f"已读取虚拟机器人姿态：{snapshot['robotPose']}，IMU={snapshot['pose']}。", {"pose": snapshot["pose"], "robotPose": snapshot["robotPose"]}
        if query == "faults":
            return f"已读取模拟器故障状态：{', '.join(snapshot['faults']) if snapshot['faults'] else '无故障'}。", {"faults": snapshot["faults"]}
        if query == "actuators":
            return "已读取虚拟执行器状态。", {"servos": snapshot["servos"], "motors": snapshot["motors"]}
        if query == "charging":
            return f"已读取模拟器充电状态：{snapshot['chargingState']}。", {"chargingState": snapshot["chargingState"]}
        if query == "communication":
            return f"已读取虚拟机器人通信状态：{snapshot['communicationState']}。", {"communicationState": snapshot["communicationState"]}
        if query == "timeline":
            return "已读取模拟器事件时间线。", {"events": list(self.hardware.events)}
        return (
            f"已读取虚拟机器人状态：电量 {snapshot['battery']['percent']}%，姿态 {snapshot['robotPose']}，通信 {snapshot['communicationState']}。",
            {"state": snapshot},
        )

    def _reply(
        self,
        request_id: str,
        status: str,
        message: str,
        result_code: str,
        intent: str | None = None,
        action: str | None = None,
        requires_confirmation: bool = False,
        confirmation_id: str | None = None,
        structured: dict[str, Any] | None = None,
    ) -> RobotReply:
        return RobotReply(
            request_id=request_id,
            session_id=self.memory.session_id,
            status=status,
            user_message=message,
            result_code=result_code,
            intent=intent,
            action=action,
            requires_confirmation=requires_confirmation,
            confirmation_id=confirmation_id,
            confirmation_fingerprint=_fingerprint(confirmation_id),
            structured=structured,
        )

    def _finish(
        self,
        request_id: str,
        text: str,
        reply: RobotReply,
        result: ExecutionResult | None = None,
    ) -> RobotReply:
        if result is not None:
            self.memory.last_execution = result
        self.memory.add(ConversationTurn(request_id, text[:MAX_STRING_CHARS], reply.user_message, reply.result_code))
        self._event("robot_reply_created", request_id, reply.action, reply.result_code, confirmation_fingerprint=reply.confirmation_fingerprint)
        return reply

    def _event(self, event_type: str, request_id: str | None, action: str | None, result: str, **extra: Any) -> None:
        self.events.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "eventType": event_type,
            "requestId": request_id,
            "sessionFingerprint": _fingerprint(self.memory.session_id),
            "provider": getattr(self.provider, "name", "unknown"),
            "runtimeMode": self.runtime_mode.value,
            "action": action,
            "resultCode": result,
            **{key: value for key, value in extra.items() if key != "confirmation_id"},
        })


def validate_ai_response(response: AIResponse, request_data: AIRequest) -> RobotIntent:
    raw = response.raw_content
    if not raw.strip():
        raise AIIntentValidationError("empty provider content", AIErrorCode.SCHEMA_VALIDATION_FAILED)
    if len(raw) > MAX_PROVIDER_OUTPUT_CHARS:
        raise AIIntentValidationError("provider output is too large", AIErrorCode.SCHEMA_VALIDATION_FAILED)
    try:
        payload = json.loads(raw, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    except (json.JSONDecodeError, ValueError) as exc:
        raise AIIntentValidationError("provider did not return valid JSON", AIErrorCode.INVALID_JSON) from exc
    _validate_value(payload, 0)
    if not isinstance(payload, dict):
        raise AIIntentValidationError("top-level response must be an object")
    extra = set(payload) - ALLOWED_TOP_LEVEL_FIELDS
    forbidden = set(payload) & FORBIDDEN_FIELDS
    if extra or forbidden:
        raise AIIntentValidationError(f"unknown or forbidden top-level fields: {sorted(extra | forbidden)}")
    required = ALLOWED_TOP_LEVEL_FIELDS - {"clarification_question"}
    missing = required - set(payload)
    if missing:
        raise AIIntentValidationError(f"missing fields: {sorted(missing)}")
    if payload["request_id"] != request_data.request_id:
        raise AIIntentValidationError("provider request_id does not match")
    intent_name = _string(payload["intent"], "intent")
    confidence = payload["confidence"]
    if not isinstance(confidence, (int, float)) or not math.isfinite(float(confidence)) or not 0 <= float(confidence) <= 1:
        raise AIIntentValidationError("confidence must be a finite number between 0 and 1")
    requires_clarification = payload["requires_clarification"]
    if not isinstance(requires_clarification, bool):
        raise AIIntentValidationError("requires_clarification must be boolean")
    clarification = payload.get("clarification_question")
    if clarification is not None:
        clarification = _string(clarification, "clarification_question")
    user_message = _string(payload["user_message"], "user_message")
    reason_code = _string(payload["reason_code"], "reason_code")
    actions_payload = payload["actions"]
    if not isinstance(actions_payload, list):
        raise AIIntentValidationError("actions must be a list")
    if len(actions_payload) > request_data.max_actions:
        raise AIIntentValidationError("too many actions", AIErrorCode.PLAN_REJECTED)
    actions: list[ProposedAction] = []
    for item in actions_payload:
        if not isinstance(item, dict):
            raise AIIntentValidationError("action must be an object")
        forbidden_action_fields = set(item) & FORBIDDEN_FIELDS
        extra_action_fields = set(item) - {"action", "arguments", "target", "source", "risk"}
        if forbidden_action_fields or extra_action_fields:
            raise AIIntentValidationError(f"unknown or forbidden action fields: {sorted(forbidden_action_fields | extra_action_fields)}")
        action_name = _string(item.get("action"), "action")
        if action_name not in ALLOWED_ACTIONS:
            raise AIIntentValidationError(f"unsupported action: {action_name}", AIErrorCode.UNSUPPORTED_ACTION)
        arguments = item.get("arguments")
        if not isinstance(arguments, dict):
            raise AIIntentValidationError("action arguments must be an object")
        actions.append(ProposedAction(action_name, arguments, item.get("target"), item.get("source", "ai_provider"), item.get("risk", "unknown")))
    return RobotIntent(
        request_id=request_data.request_id,
        intent=intent_name,
        confidence=float(confidence),
        requires_clarification=requires_clarification,
        clarification_question=clarification,
        actions=tuple(actions),
        user_message=user_message,
        reason_code=reason_code,
    )


def validate_plan(intent: RobotIntent, max_actions: int) -> PlanValidationResult:
    if intent.requires_clarification:
        if intent.actions:
            return PlanValidationResult(False, None, AIErrorCode.PLAN_REJECTED, "clarification cannot include actions")
        return PlanValidationResult(True, ActionPlan(()))
    if not intent.actions:
        return PlanValidationResult(False, None, AIErrorCode.PLAN_REJECTED, "no action proposed")
    if len(intent.actions) > max_actions or len(intent.actions) > MAX_ACTIONS_HARD_LIMIT:
        return PlanValidationResult(False, None, AIErrorCode.PLAN_REJECTED, "too many actions")
    for action in intent.actions:
        error = _validate_action_arguments(action)
        if error is not None:
            return error
    return PlanValidationResult(True, ActionPlan(intent.actions, max_steps=max_actions))


def reply_to_jsonable(reply: RobotReply, *, include_confirmation_id: bool = False) -> dict[str, Any]:
    payload = {
        "requestId": reply.request_id,
        "sessionId": reply.session_id,
        "status": reply.status,
        "resultCode": reply.result_code,
        "intent": reply.intent,
        "action": reply.action,
        "requiresConfirmation": reply.requires_confirmation,
        "confirmationFingerprint": reply.confirmation_fingerprint,
        "message": reply.user_message,
        "structured": reply.structured,
    }
    if include_confirmation_id:
        payload["confirmationId"] = reply.confirmation_id
    return payload


def _validate_action_arguments(action: ProposedAction) -> PlanValidationResult | None:
    args = action.arguments
    if action.action == "query_status":
        query = args.get("query", "summary")
        if not isinstance(query, str) or query not in ALLOWED_QUERIES:
            return PlanValidationResult(False, None, AIErrorCode.PLAN_REJECTED, "unsupported status query")
    elif action.action == "robot_command":
        command = args.get("command")
        if not isinstance(command, str) or command not in ALLOWED_COMMANDS:
            return PlanValidationResult(False, None, AIErrorCode.UNSUPPORTED_ACTION, "unsupported robot command")
    elif action.action in {"simulator.inject_fault", "simulator.clear_fault"}:
        fault = args.get("fault", "all")
        if not isinstance(fault, str) or len(fault) > 80:
            return PlanValidationResult(False, None, AIErrorCode.PLAN_REJECTED, "invalid simulator fault")
    elif action.action == "simulator.reset":
        if args:
            return PlanValidationResult(False, None, AIErrorCode.PLAN_REJECTED, "simulator reset takes no arguments")
    elif action.action == "deny":
        reason = args.get("reason", "")
        if not isinstance(reason, str):
            return PlanValidationResult(False, None, AIErrorCode.PLAN_REJECTED, "deny reason must be a string")
    else:
        return PlanValidationResult(False, None, AIErrorCode.UNSUPPORTED_ACTION, "unsupported action")
    return None


def _validate_value(value: Any, depth: int) -> None:
    if depth > MAX_NESTING_DEPTH:
        raise AIIntentValidationError("response nesting is too deep")
    if isinstance(value, dict):
        if set(value) & FORBIDDEN_FIELDS:
            raise AIIntentValidationError("response contains forbidden authority fields")
        for key, child in value.items():
            if not isinstance(key, str) or len(key) > MAX_STRING_CHARS:
                raise AIIntentValidationError("object key is invalid")
            _validate_value(child, depth + 1)
    elif isinstance(value, list):
        if len(value) > MAX_ACTIONS_HARD_LIMIT + 2:
            raise AIIntentValidationError("list is too large")
        for child in value:
            _validate_value(child, depth + 1)
    elif isinstance(value, str):
        if len(value) > MAX_STRING_CHARS:
            raise AIIntentValidationError("string is too long")
    elif isinstance(value, (int, float)):
        if not math.isfinite(float(value)):
            raise AIIntentValidationError("number must be finite")
    elif value is None or isinstance(value, bool):
        return
    else:
        raise AIIntentValidationError("unsupported JSON value type")


def _string(value: Any, field: str) -> str:
    if not isinstance(value, str) or len(value) > MAX_STRING_CHARS:
        raise AIIntentValidationError(f"{field} must be a bounded string")
    return value


def _status_summary(status: dict[str, Any]) -> dict[str, Any]:
    return {
        "motionState": status.get("motionState"),
        "emergencyStopActive": status.get("emergencyStopActive"),
        "communicationTimedOut": status.get("communicationTimedOut"),
        "virtualBatteryPercent": status.get("virtualBatteryPercent"),
    }


def _fingerprint(value: str | None) -> str | None:
    if not value:
        return None
    return value[:12]
