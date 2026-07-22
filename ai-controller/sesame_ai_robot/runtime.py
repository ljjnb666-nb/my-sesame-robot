from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .advanced import AdvancedBehaviorPlanner, AdvancedFeatureConfig, PostureState, RuntimeMode
from .arbiter import ArbiterInput, BehaviorArbiter, RobotActionPlan
from .assistant import AssistantPlan
from .client import RobotClient
from .confirmation import ConfirmationGrant
from .safety import SafetyMonitor, SensorSnapshot
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


class RobotRuntime:
    def __init__(
        self,
        client: RobotClient,
        config: RobotRuntimeConfig | None = None,
        safety_monitor: SafetyMonitor | None = None,
        advanced_planner: AdvancedBehaviorPlanner | None = None,
        arbiter: BehaviorArbiter | None = None,
    ):
        self.client = client
        self.config = config or RobotRuntimeConfig()
        self.safety_monitor = safety_monitor or SafetyMonitor()
        self.advanced_planner = advanced_planner or AdvancedBehaviorPlanner(AdvancedFeatureConfig(
            runtime_mode=self.config.runtime_mode,
        ))
        self.arbiter = arbiter or BehaviorArbiter()
        self.logs: list[dict[str, Any]] = []

    def step(
        self,
        tracking: TrackingDecision | None = None,
        assistant: AssistantPlan | None = None,
        user_confirmed_actions: tuple[str, ...] = (),
        confirmation_grants: tuple[ConfirmationGrant, ...] = (),
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
            result = RuntimeStepResult({}, plan, False, False)
            self._log(result)
            return result

        status = self.client.get_status().raw
        snapshot = SensorSnapshot.from_robot_status(status)
        safety = self.safety_monitor.assess(snapshot)
        posture = self.advanced_planner.assess_posture(snapshot)
        posture_state = PostureState(posture.state)
        advanced = (
            posture,
            self.advanced_planner.assess_terrain(snapshot),
            self.advanced_planner.plan_self_righting(posture_state),
            self.advanced_planner.plan_charging(snapshot),
        )
        plan = self.arbiter.decide(ArbiterInput(
            robot_status=status,
            safety=safety,
            tracking=tracking,
            advanced=advanced,
            assistant=assistant,
            runtime_mode=self.config.runtime_mode,
            user_confirmed_actions=user_confirmed_actions,
            confirmation_grants=confirmation_grants,
        ))

        sent_command = False
        sent_face = False
        if not self.config.dry_run:
            if plan.command:
                self.client.send_command(plan.command)
                sent_command = True
            if plan.face:
                self.client.set_face(plan.face)
                sent_face = True

        result = RuntimeStepResult(status, plan, sent_command, sent_face)
        self._log(result)
        return result

    def run(self, steps: int | None = None) -> tuple[RuntimeStepResult, ...]:
        count = steps if steps is not None else self.config.max_steps
        return tuple(self.step() for _ in range(count))

    def _log(self, result: RuntimeStepResult) -> None:
        status = result.status
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
            "safety_severity": result.plan.source if result.plan.source == "safety" else None,
            "selected_command": result.plan.command,
            "selected_source": result.plan.source,
            "reason": result.plan.reason,
            "confirmation_id": (
                result.plan.confirmation_request.confirmation_id
                if result.plan.confirmation_request is not None
                else None
            ),
            "confirmation_state": "requested" if result.plan.requires_user_confirmation else "none",
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
                "contextToken": plan.confirmation_request.context_token,
            }
            if plan.confirmation_request is not None
            else None
        ),
        "rejectedActions": [
            {"command": action.command, "source": action.source, "reason": action.reason}
            for action in plan.rejected_actions
        ],
    }


def result_to_jsonable(result: RuntimeStepResult, config: RobotRuntimeConfig) -> dict[str, Any]:
    return {
        "runtimeMode": config.runtime_mode.value,
        "dryRun": config.dry_run,
        "status": result.status,
        "plan": plan_to_jsonable(result.plan),
        "executed": {
            "commandSent": result.sent_command,
            "faceSent": result.sent_face,
        },
    }
