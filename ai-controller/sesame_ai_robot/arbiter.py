from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .advanced import AdvancedDecision, RuntimeMode
from .assistant import AssistantAction, AssistantPlan
from .client import RobotClient
from .safety import SafetyAssessment, SafetySeverity
from .tracking import TrackingDecision


@dataclass(frozen=True)
class RobotActionPlan:
    command: str | None
    face: str | None
    speech: str | None
    source: str
    reason: str
    requires_user_confirmation: bool = False
    blocked_actions: tuple[str, ...] = ()


@dataclass(frozen=True)
class ArbiterInput:
    robot_status: dict[str, Any]
    safety: SafetyAssessment
    tracking: TrackingDecision | None = None
    advanced: tuple[AdvancedDecision, ...] = ()
    assistant: AssistantPlan | None = None
    runtime_mode: RuntimeMode = RuntimeMode.MOCK
    user_confirmed_actions: tuple[str, ...] = ()


class BehaviorArbiter:
    ALWAYS_ALLOWED = {"stop", "emergency_stop", "reset_emergency_stop"}
    EXPRESSIVE_COMMANDS = {"wave"}
    MOTION_COMMANDS = {"walk_forward", "walk_backward", "turn_left", "turn_right"}

    def decide(self, inputs: ArbiterInput) -> RobotActionPlan:
        blocked = self._candidate_commands(inputs)

        if inputs.robot_status.get("emergencyStopActive", False):
            return RobotActionPlan(None, None, None, "safety", "robot emergency stop is active", blocked_actions=blocked)

        if inputs.safety.severity == SafetySeverity.EMERGENCY_STOP:
            return RobotActionPlan(
                inputs.safety.command,
                None,
                None,
                "safety",
                inputs.safety.reason,
                blocked_actions=blocked,
            )

        for decision in inputs.advanced:
            if decision.command == "emergency_stop":
                return RobotActionPlan(
                    "emergency_stop",
                    None,
                    None,
                    "advanced",
                    decision.reason,
                    blocked_actions=blocked,
                )

        if inputs.robot_status.get("communicationTimedOut", False):
            return RobotActionPlan("stop", None, None, "safety", "robot communication timed out", blocked_actions=blocked)

        if inputs.safety.severity == SafetySeverity.STOP:
            return RobotActionPlan(inputs.safety.command, None, None, "safety", inputs.safety.reason, blocked_actions=blocked)

        assistant_stop = self._assistant_user_stop(inputs.assistant)
        if assistant_stop is not None:
            return RobotActionPlan(assistant_stop, None, None, "assistant", "user requested stop", blocked_actions=blocked)

        advanced_plan = self._advanced_plan(inputs)
        if advanced_plan is not None:
            return advanced_plan

        if inputs.tracking is not None and inputs.tracking.command:
            return self._validated_command(inputs.tracking.command, "tracking", inputs.tracking.reason, blocked)

        assistant_plan = self._assistant_plan(inputs.assistant, blocked)
        if assistant_plan is not None:
            return assistant_plan

        face = self._assistant_face(inputs.assistant)
        speech = self._assistant_speech(inputs.assistant)
        if face or speech:
            return RobotActionPlan(None, face, speech, "assistant", "assistant expression or speech", blocked_actions=blocked)

        return RobotActionPlan(None, None, None, "idle", "no action selected", blocked_actions=blocked)

    def _advanced_plan(self, inputs: ArbiterInput) -> RobotActionPlan | None:
        for decision in inputs.advanced:
            if decision.requires_user_confirmation and decision.feature.value not in inputs.user_confirmed_actions:
                blocked = tuple(item for item in (decision.command,) if item)
                return RobotActionPlan(
                    None,
                    None,
                    None,
                    "advanced",
                    decision.reason,
                    requires_user_confirmation=True,
                    blocked_actions=blocked,
                )
            if decision.command:
                return self._validated_command(decision.command, "advanced", decision.reason, ())
        return None

    def _assistant_plan(self, assistant: AssistantPlan | None, blocked: tuple[str, ...]) -> RobotActionPlan | None:
        if assistant is None:
            return None
        for step in assistant.steps:
            if step.action != AssistantAction.ROBOT_COMMAND:
                continue
            if step.value in self.ALWAYS_ALLOWED:
                continue
            if step.value in self.MOTION_COMMANDS:
                return self._validated_command(step.value, "assistant", step.reason, blocked)
            if step.value in self.EXPRESSIVE_COMMANDS:
                return self._validated_command(step.value, "assistant", step.reason, blocked)
            return RobotActionPlan(
                None,
                None,
                None,
                "arbiter",
                f"unsupported assistant command: {step.value}",
                blocked_actions=(step.value,),
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

    def _candidate_commands(self, inputs: ArbiterInput) -> tuple[str, ...]:
        commands: list[str] = []
        for decision in inputs.advanced:
            if decision.command:
                commands.append(decision.command)
        if inputs.tracking is not None and inputs.tracking.command:
            commands.append(inputs.tracking.command)
        if inputs.assistant is not None:
            commands.extend(
                step.value
                for step in inputs.assistant.steps
                if step.action == AssistantAction.ROBOT_COMMAND
            )
        return tuple(command for command in commands if command)

    def _validated_command(
        self,
        command: str,
        source: str,
        reason: str,
        blocked: tuple[str, ...],
    ) -> RobotActionPlan:
        if command not in RobotClient.COMMAND_ALIASES:
            return RobotActionPlan(
                None,
                None,
                None,
                "arbiter",
                f"unsupported robot command before client: {command}",
                blocked_actions=(command,),
            )
        return RobotActionPlan(command, None, None, source, reason, blocked_actions=blocked)
