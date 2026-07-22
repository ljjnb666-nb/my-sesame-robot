from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any

from .advanced import AdvancedBehaviorPlanner, AdvancedFeatureConfig, PostureState, RuntimeMode
from .arbiter import ArbiterInput, BehaviorArbiter, RobotActionPlan
from .assistant import AssistantPlan
from .client import RobotClient
from .confirmation import ConfirmationErrorCode, ConfirmationResult, ConfirmationStore
from .safety import SafetyAssessment, SafetyMonitor, SensorSnapshot
from .tracking import TrackingDecision


@dataclass(frozen=True)
class RobotRuntimeConfig:
    runtime_mode: RuntimeMode = RuntimeMode.MOCK
    dry_run: bool = True
    allow_real_robot: bool = False
    max_steps: int = 1


@dataclass(frozen=True)
class RuntimeStepResult:
    status: dict[str, Any]
    plan: RobotActionPlan
    sent_command: bool
    sent_face: bool
    safety_assessment: SafetyAssessment | None = None
    confirmation_result: ConfirmationResult | None = None
    confirmation_state: str = "none"
    confirmation_error: str | None = None


class RobotRuntime:
    def __init__(
        self,
        client: RobotClient,
        config: RobotRuntimeConfig | None = None,
        safety_monitor: SafetyMonitor | None = None,
        advanced_planner: AdvancedBehaviorPlanner | None = None,
        arbiter: BehaviorArbiter | None = None,
        confirmation_store: ConfirmationStore | None = None,
    ):
        self.client = client
        self.config = config or RobotRuntimeConfig()
        self.safety_monitor = safety_monitor or SafetyMonitor()
        self.advanced_planner = advanced_planner or AdvancedBehaviorPlanner(AdvancedFeatureConfig(
            runtime_mode=self.config.runtime_mode,
        ))
        self.arbiter = arbiter or BehaviorArbiter()
        self.confirmation_store = confirmation_store or ConfirmationStore()
        self.logs: list[dict[str, Any]] = []

    def step(
        self,
        tracking: TrackingDecision | None = None,
        assistant: AssistantPlan | None = None,
        confirmation_id: str | None = None,
        confirmation_action: str | None = None,
    ) -> RuntimeStepResult:
        if self.config.runtime_mode == RuntimeMode.REAL_ROBOT and not self.config.allow_real_robot:
            plan = RobotActionPlan(
                None,
                None,
                None,
                "runtime",
                "real_robot mode is disabled until explicit user confirmation",
                requires_user_confirmation=True,
            )
            result = RuntimeStepResult({}, plan, False, False, None, None, "blocked", None)
            self._log(result)
            return result

        status = self.client.get_status().raw
        snapshot = SensorSnapshot.from_robot_status(status)
        safety = self.safety_monitor.assess(snapshot)
        advanced = self._advanced_decisions(snapshot)
        base_input = ArbiterInput(
            robot_status=status,
            safety=safety,
            tracking=tracking,
            advanced=advanced,
            assistant=assistant,
            runtime_mode=self.config.runtime_mode,
        )
        plan = self.arbiter.decide(base_input)
        confirmation_result: ConfirmationResult | None = None
        confirmation_state = "none"
        confirmation_error: str | None = None

        if confirmation_id is not None:
            if plan.confirmation_requirement is None:
                stored_request = self.confirmation_store.get_request(confirmation_id)
                if stored_request is None:
                    confirmation_result = ConfirmationResult(
                        False,
                        None,
                        ConfirmationErrorCode.UNKNOWN_ID,
                        "confirmation id is unknown",
                    )
                else:
                    confirmation_result = self.confirmation_store.consume(
                        confirmation_id,
                        confirmation_action or stored_request.action,
                        {},
                    )
            else:
                expected_action = confirmation_action or plan.confirmation_requirement.action
                confirmation_result = self.confirmation_store.consume(
                    confirmation_id,
                    expected_action,
                    plan.confirmation_requirement.context,
                )
            if confirmation_result.accepted and confirmation_result.grant is not None:
                authorized_input = replace(
                    base_input,
                    runtime_authorized_actions=(confirmation_result.grant.action,),
                )
                plan = self.arbiter.decide(authorized_input)
                confirmation_state = self._accepted_confirmation_state(confirmation_result.grant.action, plan)
            else:
                confirmation_state = confirmation_result.error.value if confirmation_result.error else "rejected"
                confirmation_error = confirmation_state
                plan = RobotActionPlan(
                    None,
                    None,
                    None,
                    "runtime",
                    confirmation_result.reason,
                )
        elif plan.confirmation_requirement is not None:
            request = self.confirmation_store.create(
                plan.confirmation_requirement.action,
                plan.confirmation_requirement.reason,
                plan.confirmation_requirement.context,
            )
            plan = replace(plan, confirmation_request=request)
            confirmation_state = "requested"

        sent_command = False
        sent_face = False
        if not self.config.dry_run:
            if plan.command:
                self.client.send_command(plan.command)
                sent_command = True
            if plan.face:
                self.client.set_face(plan.face)
                sent_face = True

        result = RuntimeStepResult(
            status,
            plan,
            sent_command,
            sent_face,
            safety,
            confirmation_result,
            confirmation_state,
            confirmation_error,
        )
        self._log(result)
        return result

    def run(self, steps: int | None = None) -> tuple[RuntimeStepResult, ...]:
        count = steps if steps is not None else self.config.max_steps
        return tuple(self.step() for _ in range(count))

    def _advanced_decisions(self, snapshot: SensorSnapshot):
        posture = self.advanced_planner.assess_posture(snapshot)
        posture_state = PostureState(posture.state)
        return (
            posture,
            self.advanced_planner.assess_terrain(snapshot),
            self.advanced_planner.plan_self_righting(posture_state),
            self.advanced_planner.plan_charging(snapshot),
        )

    def _accepted_confirmation_state(self, action: str, plan: RobotActionPlan) -> str:
        if action in {"self_righting", "charging_dock"} and plan.command is None:
            return "hardware_blocked"
        return "accepted"

    def _log(self, result: RuntimeStepResult) -> None:
        status = result.status
        confirmation_id = (
            result.plan.confirmation_request.confirmation_id
            if result.plan.confirmation_request is not None
            else result.confirmation_result.grant.confirmation_id
            if result.confirmation_result is not None and result.confirmation_result.grant is not None
            else None
        )
        rejected_actions = [
            {"command": action.command, "source": action.source, "reason": action.reason}
            for action in result.plan.rejected_actions
        ]
        self.logs.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "runtime_mode": self.config.runtime_mode.value,
            "dry_run": self.config.dry_run,
            "robot_status_summary": {
                "motionState": status.get("motionState"),
                "emergencyStopActive": status.get("emergencyStopActive"),
                "communicationTimedOut": status.get("communicationTimedOut"),
            },
            "safety_severity": (
                result.safety_assessment.severity.value
                if result.safety_assessment is not None
                else None
            ),
            "selected_command": result.plan.command,
            "selected_source": result.plan.source,
            "reason": result.plan.reason,
            "confirmation_id_fingerprint": _fingerprint(confirmation_id),
            "confirmation_action": (
                result.plan.confirmation_request.action
                if result.plan.confirmation_request is not None
                else result.confirmation_result.grant.action
                if result.confirmation_result is not None and result.confirmation_result.grant is not None
                else result.plan.confirmation_requirement.action
                if result.plan.confirmation_requirement is not None
                else None
            ),
            "confirmation_state": result.confirmation_state,
            "confirmation_error": result.confirmation_error,
            "rejected_actions": rejected_actions,
            "sent_command": result.sent_command,
            "sent_face": result.sent_face,
            "error": None,
        })


def plan_to_jsonable(plan: RobotActionPlan) -> dict[str, Any]:
    return {
        "command": plan.command,
        "face": plan.face,
        "speech": plan.speech,
        "source": plan.source,
        "reason": plan.reason,
        "requiresUserConfirmation": plan.requires_user_confirmation,
        "confirmationRequest": (
            {
                "confirmationId": plan.confirmation_request.confirmation_id,
                "action": plan.confirmation_request.action,
                "reason": plan.confirmation_request.reason,
                "createdAt": plan.confirmation_request.created_at,
                "expiresAt": plan.confirmation_request.expires_at,
                "contextFingerprint": _fingerprint(plan.confirmation_request.context_token),
            }
            if plan.confirmation_request is not None
            else None
        ),
        "rejectedActions": [
            {"command": action.command, "source": action.source, "reason": action.reason}
            for action in plan.rejected_actions
        ],
    }


def _fingerprint(value: str | None) -> str | None:
    if not value:
        return None
    return value[:12]


def result_to_jsonable(result: RuntimeStepResult, config: RobotRuntimeConfig) -> dict[str, Any]:
    return {
        "runtimeMode": config.runtime_mode.value,
        "dryRun": config.dry_run,
        "status": result.status,
        "plan": plan_to_jsonable(result.plan),
        "confirmation": {
            "state": result.confirmation_state,
            "error": result.confirmation_error,
            "reason": result.confirmation_result.reason if result.confirmation_result is not None else None,
        },
        "executed": {
            "commandSent": result.sent_command,
            "faceSent": result.sent_face,
        },
    }
