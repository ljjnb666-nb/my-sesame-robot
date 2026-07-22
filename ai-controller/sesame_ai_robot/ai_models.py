from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


MAX_ACTIONS_DEFAULT = 3
MAX_ACTIONS_HARD_LIMIT = 5
MAX_TEXT_CHARS = 500
MAX_PROVIDER_OUTPUT_CHARS = 6000
MAX_STRING_CHARS = 300
MAX_NESTING_DEPTH = 5


class AIErrorCode(str, Enum):
    OK = "ok"
    CLARIFICATION_REQUIRED = "clarification_required"
    PROVIDER_TIMEOUT = "provider_timeout"
    PROVIDER_ERROR = "provider_error"
    PROVIDER_REFUSED = "provider_refused"
    INVALID_JSON = "invalid_json"
    SCHEMA_VALIDATION_FAILED = "schema_validation_failed"
    PLAN_REJECTED = "plan_rejected"
    UNSUPPORTED_ACTION = "unsupported_action"
    PARAMETER_OUT_OF_RANGE = "parameter_out_of_range"
    CONFIRMATION_REQUIRED = "confirmation_required"
    EXECUTION_FAILED = "execution_failed"


class AIProviderError(RuntimeError):
    code = AIErrorCode.PROVIDER_ERROR


class AIProviderTimeout(AIProviderError):
    code = AIErrorCode.PROVIDER_TIMEOUT


class AIProviderRefusal(AIProviderError):
    code = AIErrorCode.PROVIDER_REFUSED


@dataclass(frozen=True)
class AIRequest:
    request_id: str
    session_id: str
    user_text: str
    runtime_mode: str
    capabilities: tuple[str, ...]
    robot_state: dict[str, Any]
    safety_context: dict[str, Any]
    max_actions: int = MAX_ACTIONS_DEFAULT


@dataclass(frozen=True)
class ProposedAction:
    action: str
    arguments: dict[str, Any]
    target: str | None = None
    source: str = "ai_provider"
    risk: str = "unknown"


@dataclass(frozen=True)
class RobotIntent:
    request_id: str
    intent: str
    confidence: float
    requires_clarification: bool
    clarification_question: str | None
    actions: tuple[ProposedAction, ...]
    user_message: str
    reason_code: str


@dataclass(frozen=True)
class AIResponse:
    request_id: str
    raw_content: str
    intent: RobotIntent | None = None
    provider: str = "mock"
    model: str | None = None


@dataclass(frozen=True)
class ActionPlan:
    actions: tuple[ProposedAction, ...]
    max_steps: int = MAX_ACTIONS_DEFAULT
    failure_policy: str = "stop_on_failure"
    allow_partial_execution: bool = False
    timeout_seconds: float = 5.0


@dataclass(frozen=True)
class PlanValidationResult:
    accepted: bool
    plan: ActionPlan | None
    error_code: AIErrorCode | None = None
    reason: str = ""


@dataclass(frozen=True)
class ExecutionResult:
    action: str | None
    status: str
    error_code: AIErrorCode | None
    rejection_reason: str | None
    confirmation_state: str = "none"
    hardware_change: dict[str, Any] | None = None
    user_message: str = ""
    diagnostics: dict[str, Any] | None = None


@dataclass(frozen=True)
class ConversationTurn:
    request_id: str
    user_text: str
    robot_reply: str
    result_code: str


@dataclass(frozen=True)
class RobotReply:
    request_id: str
    session_id: str
    status: str
    user_message: str
    result_code: str
    intent: str | None = None
    action: str | None = None
    requires_confirmation: bool = False
    confirmation_id: str | None = None
    confirmation_fingerprint: str | None = None
    structured: dict[str, Any] | None = None
