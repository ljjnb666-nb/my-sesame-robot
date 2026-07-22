from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .advanced import AdvancedBehaviorPlanner, AdvancedFeatureConfig, PostureState, RuntimeMode
from .arbiter import ArbiterInput, BehaviorArbiter, RobotActionPlan
from .assistant import AssistantPlan
from .client import RobotClient
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
        self.logs.append({
            "source": result.plan.source,
            "command": result.plan.command,
            "face": result.plan.face,
            "reason": result.plan.reason,
            "requiresUserConfirmation": result.plan.requires_user_confirmation,
            "sentCommand": result.sent_command,
            "sentFace": result.sent_face,
        })
