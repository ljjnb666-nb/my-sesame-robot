from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .advanced import AdvancedDecision, RuntimeMode
from .assistant import AssistantAction, AssistantPlan
from .client import RobotClient
from .confirmation import ConfirmationContext, ConfirmationRequest
from .safety import SafetyAssessment, SafetySeverity
from .tracking import TrackingDecision


@dataclass(frozen=True)
class RejectedAction:
    command: str
    source: str
    reason: str


@dataclass(frozen=True)
class ConfirmationRequirement:
    action: str
    reason: str
    context: ConfirmationContext


@dataclass(frozen=True)
class RobotActionPlan:
    command: str | None
    face: str | None
    speech: str | None
    source: str
    reason: str
    requires_user_confirmation: bool = False
    confirmation_requirement: ConfirmationRequirement | None = None
    confirmation_request: ConfirmationRequest | None = None
    rejected_actions: tuple[RejectedAction, ...] = ()

    @property
    def blocked_actions(self) -> tuple[str, ...]:
        return tuple(action.command for action in self.rejected_actions)


@dataclass(frozen=True)
class ArbiterInput:
    robot_status: dict[str, Any]
    safety: SafetyAssessment
    tracking: TrackingDecision | None = None
    advanced: tuple[AdvancedDecision, ...] = ()
    assistant: AssistantPlan | None = None
    runtime_mode: RuntimeMode = RuntimeMode.MOCK
    runtime_authorized_actions: tuple[str, ...] = ()


class BehaviorArbiter:
    ALWAYS_ALLOWED = {"stop", "emergency_stop", "reset_emergency_stop", "heartbeat"}
    EXPRESSIVE_COMMANDS = {"wave"}
    MOTION_COMMANDS = {"walk_forward", "walk_backward", "turn_left", "turn_right"}
    CONFIRMATION_ACTIONS = {"reset_emergency_stop", "self_righting", "charging_dock"}

    def decide(self, inputs: ArbiterInput) -> RobotActionPlan:
        candidates = self._candidate_actions(inputs)

        if inputs.robot_status.get("emergencyStopActive", False):
            allowed = self._emergency_allowed_plan(inputs)
            if allowed is not None:
                return allowed
            return RobotActionPlan(
                None,
                None,
                None,
                "safety",
                "robot emergency stop is active",
                rejected_actions=self._reject(candidates, "emergency stop is active"),
            )

        if inputs.safety.severity == SafetySeverity.EMERGENCY_STOP:
            return RobotActionPlan(
                inputs.safety.command,
                None,
                None,
                "safety",
                inputs.safety.reason,
                rejected_actions=self._reject(candidates, "safety emergency stop overrides action", inputs.safety.command),
            )

        for decision in inputs.advanced:
            if decision.command == "emergency_stop":
                return RobotActionPlan(
                    "emergency_stop",
                    None,
                    None,
                    "advanced",
                    decision.reason,
                    rejected_actions=self._reject(candidates, "advanced emergency stop overrides action", "emergency_stop"),
                )

        if inputs.robot_status.get("communicationTimedOut", False):
            return RobotActionPlan(
                "stop",
                None,
                None,
                "safety",
                "robot communication timed out",
                rejected_actions=self._reject(candidates, "communication timeout forced stop", "stop"),
            )

        if inputs.safety.severity == SafetySeverity.STOP:
            return RobotActionPlan(
                inputs.safety.command,
                None,
                None,
                "safety",
                inputs.safety.reason,
                rejected_actions=self._reject(candidates, "safety stop overrides action", inputs.safety.command),
            )

        assistant_stop = self._assistant_user_stop(inputs.assistant)
        if assistant_stop is not None:
            return RobotActionPlan(
                assistant_stop,
                None,
                None,
                "assistant",
                "user requested stop",
                rejected_actions=self._reject(candidates, "user stop overrides action", assistant_stop),
            )

        advanced_plan = self._advanced_plan(inputs)
        if advanced_plan is not None:
            return advanced_plan

        if inputs.tracking is not None and inputs.tracking.command:
            return self._validated_command(inputs.tracking.command, "tracking", inputs.tracking.reason, candidates)

        assistant_plan = self._assistant_plan(inputs.assistant, candidates)
        if assistant_plan is not None:
            return assistant_plan

        face = self._assistant_face(inputs.assistant)
        speech = self._assistant_speech(inputs.assistant)
        if face or speech:
            return RobotActionPlan(None, face, speech, "assistant", "assistant expression or speech")

        return RobotActionPlan(None, None, None, "idle", "no action selected")

    def _advanced_plan(self, inputs: ArbiterInput) -> RobotActionPlan | None:
        for decision in inputs.advanced:
            action = decision.feature.value
            proposed = decision.proposed_command or decision.command
            if decision.requires_user_confirmation and not self._has_confirmation(inputs, action):
                context = self._confirmation_context(inputs, action, proposed, decision.state)
                return RobotActionPlan(
                    None,
                    None,
                    None,
                    "advanced",
                    decision.reason,
                    requires_user_confirmation=True,
                    confirmation_requirement=ConfirmationRequirement(
                        action,
                        decision.reason,
                        context,
                    ),
                )
            if decision.requires_user_confirmation and not decision.command:
                return RobotActionPlan(None, None, None, "advanced", decision.reason)
            if decision.command:
                return self._validated_command(decision.command, "advanced", decision.reason, self._candidate_actions(inputs))
        return None

    def _assistant_plan(self, assistant: AssistantPlan | None, candidates: tuple[RejectedAction, ...]) -> RobotActionPlan | None:
        if assistant is None:
            return None
        for step in assistant.steps:
            if step.action != AssistantAction.ROBOT_COMMAND:
                continue
            if step.value in self.ALWAYS_ALLOWED:
                continue
            if step.value in self.MOTION_COMMANDS:
                return self._validated_command(step.value, "assistant", step.reason, candidates)
            if step.value in self.EXPRESSIVE_COMMANDS:
                return self._validated_command(step.value, "assistant", step.reason, candidates)
            return RobotActionPlan(
                None,
                None,
                None,
                "arbiter",
                f"unsupported assistant command: {step.value}",
                rejected_actions=(RejectedAction(step.value, "assistant", step.reason),),
            )
        return None

    def _assistant_user_stop(self, assistant: AssistantPlan | None) -> str | None:
        if assistant is None:
            return None
        for step in assistant.steps:
            if step.action == AssistantAction.ROBOT_COMMAND and step.value in self.ALWAYS_ALLOWED:
                return step.value
        return None

    def _assistant_face(self, assistant: AssistantPlan | None) -> str | None:
        if assistant is None:
            return None
        for step in assistant.steps:
            if step.action == AssistantAction.SET_FACE:
                return step.value
        return None

    def _assistant_speech(self, assistant: AssistantPlan | None) -> str | None:
        if assistant is None:
            return None
        for step in assistant.steps:
            if step.action == AssistantAction.SAY:
                return step.value
        return None

    def _candidate_actions(self, inputs: ArbiterInput) -> tuple[RejectedAction, ...]:
        commands: list[RejectedAction] = []
        for decision in inputs.advanced:
            if decision.command:
                commands.append(RejectedAction(decision.command, "advanced", decision.reason))
            elif decision.proposed_command:
                commands.append(RejectedAction(decision.proposed_command, "advanced", decision.reason))
        if inputs.tracking is not None and inputs.tracking.command:
            commands.append(RejectedAction(inputs.tracking.command, "tracking", inputs.tracking.reason))
        if inputs.assistant is not None:
            commands.extend(
                RejectedAction(step.value, "assistant", step.reason)
                for step in inputs.assistant.steps
                if step.action == AssistantAction.ROBOT_COMMAND
            )
        return tuple(action for action in commands if action.command)

    def _reject(
        self,
        candidates: tuple[RejectedAction, ...],
        reason: str,
        selected_command: str | None = None,
    ) -> tuple[RejectedAction, ...]:
        return tuple(
            RejectedAction(action.command, action.source, reason)
            for action in candidates
            if action.command and action.command != selected_command
        )

    def _validated_command(
        self,
        command: str,
        source: str,
        reason: str,
        candidates: tuple[RejectedAction, ...],
    ) -> RobotActionPlan:
        if command not in RobotClient.COMMAND_ALIASES:
            return RobotActionPlan(
                None,
                None,
                None,
                "arbiter",
                f"unsupported robot command before client: {command}",
                rejected_actions=(RejectedAction(command, source, reason),),
            )
        return RobotActionPlan(command, None, None, source, reason, rejected_actions=self._reject(candidates, "lower priority action not selected", command))

    def _emergency_allowed_plan(self, inputs: ArbiterInput) -> RobotActionPlan | None:
        assistant_command = self._assistant_user_stop(inputs.assistant)
        if assistant_command in {"stop", "emergency_stop", "heartbeat"}:
            return RobotActionPlan(assistant_command, None, None, "assistant", "allowed while emergency stop is active")
        if assistant_command == "reset_emergency_stop":
            if inputs.safety.severity == SafetySeverity.EMERGENCY_STOP:
                return RobotActionPlan(None, None, None, "safety", "sensor safety still requires emergency stop")
            if self._has_confirmation(inputs, "reset_emergency_stop"):
                return RobotActionPlan("reset_emergency_stop", None, None, "assistant", "confirmed emergency stop reset")
            context = self._confirmation_context(inputs, "reset_emergency_stop", "reset_emergency_stop", "")
            return RobotActionPlan(
                None,
                None,
                None,
                "assistant",
                "emergency stop reset requires user confirmation",
                requires_user_confirmation=True,
                confirmation_requirement=ConfirmationRequirement(
                    "reset_emergency_stop",
                    "emergency stop reset requires user confirmation",
                    context,
                ),
            )
        return None

    def _has_confirmation(self, inputs: ArbiterInput, action: str) -> bool:
        return action in inputs.runtime_authorized_actions

    def _confirmation_context(
        self,
        inputs: ArbiterInput,
        action: str,
        proposed_command: str | None,
        posture_state: str,
    ) -> ConfirmationContext:
        return ConfirmationContext(
            runtime_mode=inputs.runtime_mode.value,
            action=action,
            emergency_stop_active=bool(inputs.robot_status.get("emergencyStopActive", False)),
            safety_severity=inputs.safety.severity.value,
            posture_state=posture_state or str(inputs.robot_status.get("motionState", "")),
            communication_timed_out=bool(inputs.robot_status.get("communicationTimedOut", False)),
            robot_motion_state=str(inputs.robot_status.get("motionState", "")),
            proposed_command=proposed_command,
            battery_percent=_battery_percent(inputs.robot_status),
            hardware_available=False,
            experimental_enabled=False,
        )


def _battery_percent(status: dict[str, Any]) -> int | None:
    battery = status.get("battery") if isinstance(status.get("battery"), dict) else {}
    value = battery.get("percent", status.get("virtualBatteryPercent"))
    return value if isinstance(value, int) else None
