import unittest

from sesame_ai_robot.assistant import AssistantAction, AssistantPlan, AssistantStep
from sesame_ai_robot.client import RobotClient
from sesame_ai_robot.confirmation import ConfirmationStore
from sesame_ai_robot.config import ControllerConfig
from sesame_ai_robot.mock_robot import MockRobotServer, MockRobotState
from sesame_ai_robot.runtime import RobotRuntime, RobotRuntimeConfig
from sesame_ai_robot.advanced import RuntimeMode
from sesame_ai_robot.tracking import TrackingDecision, TrackingState


def assistant_command(command: str) -> AssistantPlan:
    return AssistantPlan(command, (AssistantStep(AssistantAction.ROBOT_COMMAND, command, "test command"),))


class RobotRuntimeTest(unittest.TestCase):
    def setUp(self):
        self.server = MockRobotServer(port=0)
        self.server.start()
        self.client = RobotClient(ControllerConfig(robot_url=self.server.url, request_timeout_s=1.0))

    def tearDown(self):
        self.server.stop()

    def test_dry_run_does_not_send_tracking_command(self):
        runtime = RobotRuntime(self.client, RobotRuntimeConfig(dry_run=True))

        result = runtime.step(tracking=TrackingDecision(TrackingState.FOLLOWING, "walk_forward", "tracking"))

        self.assertEqual(result.plan.command, "walk_forward")
        self.assertFalse(result.sent_command)
        self.assertEqual(self.client.get_status().current_command, "")

    def test_mock_runtime_can_send_final_plan(self):
        runtime = RobotRuntime(self.client, RobotRuntimeConfig(dry_run=False))

        result = runtime.step(tracking=TrackingDecision(TrackingState.FOLLOWING, "turn_left", "tracking"))

        self.assertEqual(result.plan.command, "turn_left")
        self.assertTrue(result.sent_command)
        self.assertEqual(self.client.get_status().current_command, "left")

    def test_real_robot_mode_is_blocked_without_confirmation(self):
        runtime = RobotRuntime(self.client, RobotRuntimeConfig(
            runtime_mode=RuntimeMode.REAL_ROBOT,
            dry_run=False,
            allow_real_robot=False,
        ))

        result = runtime.step()

        self.assertIsNone(result.plan.command)
        self.assertTrue(result.plan.requires_user_confirmation)
        self.assertEqual(result.plan.source, "runtime")

    def test_runtime_safety_overrides_tracking(self):
        self.server.stop()
        self.server = MockRobotServer(port=0, state=MockRobotState(
            virtual_sensors={
                "frontDistanceM": 0.2,
                "leftDistanceM": 1.0,
                "rightDistanceM": 1.0,
                "cliffDetected": False,
                "collisionDetected": False,
                "imuRollDeg": 0.0,
                "imuPitchDeg": 0.0,
            },
        ))
        self.server.start()
        self.client = RobotClient(ControllerConfig(robot_url=self.server.url, request_timeout_s=1.0))
        runtime = RobotRuntime(self.client, RobotRuntimeConfig(dry_run=True))

        result = runtime.step(tracking=TrackingDecision(TrackingState.FOLLOWING, "walk_forward", "tracking"))

        self.assertEqual(result.plan.command, "stop")
        self.assertEqual(result.plan.source, "safety")
        self.assertIn("walk_forward", result.plan.blocked_actions)

    def test_runtime_creates_and_consumes_emergency_reset_confirmation_once(self):
        self.server.state.emergency_stop_active = True
        runtime = RobotRuntime(self.client, RobotRuntimeConfig(dry_run=False))
        assistant = assistant_command("reset_emergency_stop")

        requested = runtime.step(assistant=assistant)
        request = requested.plan.confirmation_request
        self.assertIsNotNone(request)
        self.assertTrue(requested.plan.requires_user_confirmation)
        self.assertFalse(requested.sent_command)

        accepted = runtime.step(assistant=assistant, confirmation_id=request.confirmation_id)
        self.assertEqual(accepted.plan.command, "reset_emergency_stop")
        self.assertEqual(accepted.confirmation_state, "accepted")
        self.assertTrue(accepted.sent_command)
        self.assertEqual(self.client.get_status().current_command, "")

        replay = runtime.step(assistant=assistant, confirmation_id=request.confirmation_id)
        self.assertIsNone(replay.plan.command)
        self.assertEqual(replay.confirmation_state, "already_used")
        self.assertFalse(replay.sent_command)

    def test_runtime_rejects_unknown_expired_and_wrong_action_confirmation_ids(self):
        self.server.state.emergency_stop_active = True
        assistant = assistant_command("reset_emergency_stop")

        runtime = RobotRuntime(self.client, RobotRuntimeConfig(dry_run=True))
        unknown = runtime.step(assistant=assistant, confirmation_id="fake-id")
        self.assertEqual(unknown.confirmation_state, "unknown_id")
        self.assertIsNone(unknown.plan.command)

        clock = {"now": 10.0}
        runtime = RobotRuntime(
            self.client,
            RobotRuntimeConfig(dry_run=True),
            confirmation_store=ConfirmationStore(ttl_seconds=1.0, _clock=lambda: clock["now"]),
        )
        request = runtime.step(assistant=assistant).plan.confirmation_request
        clock["now"] = 11.0
        expired = runtime.step(assistant=assistant, confirmation_id=request.confirmation_id)
        self.assertEqual(expired.confirmation_state, "expired")
        self.assertIsNone(expired.plan.command)

        runtime = RobotRuntime(self.client, RobotRuntimeConfig(dry_run=True))
        request = runtime.step(assistant=assistant).plan.confirmation_request
        mismatch = runtime.step(
            assistant=assistant,
            confirmation_id=request.confirmation_id,
            confirmation_action="self_righting",
        )
        self.assertEqual(mismatch.confirmation_state, "action_mismatch")
        self.assertIsNone(mismatch.plan.command)

    def test_runtime_rejects_context_changed_confirmation(self):
        self.server.state.emergency_stop_active = True
        runtime = RobotRuntime(self.client, RobotRuntimeConfig(dry_run=True))
        assistant = assistant_command("reset_emergency_stop")
        request = runtime.step(assistant=assistant).plan.confirmation_request

        self.server.state.virtual_sensors["cliffDetected"] = True
        changed = runtime.step(assistant=assistant, confirmation_id=request.confirmation_id)

        self.assertIn(changed.confirmation_state, {"context_changed", "action_mismatch"})
        self.assertIsNone(changed.plan.command)
        self.assertFalse(changed.sent_command)

    def test_confirmation_id_cannot_cross_runtime_sessions(self):
        self.server.state.emergency_stop_active = True
        assistant = assistant_command("reset_emergency_stop")
        first_runtime = RobotRuntime(self.client, RobotRuntimeConfig(dry_run=True))
        second_runtime = RobotRuntime(self.client, RobotRuntimeConfig(dry_run=True))
        request = first_runtime.step(assistant=assistant).plan.confirmation_request

        result = second_runtime.step(assistant=assistant, confirmation_id=request.confirmation_id)

        self.assertEqual(result.confirmation_state, "unknown_id")
        self.assertFalse(result.sent_command)

    def test_confirmation_stays_consumed_when_command_send_fails(self):
        self.server.state.emergency_stop_active = True
        assistant = assistant_command("reset_emergency_stop")
        runtime = RobotRuntime(self.client, RobotRuntimeConfig(dry_run=True))
        request = runtime.step(assistant=assistant).plan.confirmation_request

        failing_runtime = RobotRuntime(
            FailingCommandClient(self.client),
            RobotRuntimeConfig(dry_run=False),
            confirmation_store=runtime.confirmation_store,
        )

        with self.assertRaises(RuntimeError):
            failing_runtime.step(assistant=assistant, confirmation_id=request.confirmation_id)

        replay = runtime.step(assistant=assistant, confirmation_id=request.confirmation_id)
        self.assertEqual(replay.confirmation_state, "already_used")
        self.assertFalse(replay.sent_command)

    def test_runtime_log_records_real_safety_severity(self):
        runtime = RobotRuntime(self.client, RobotRuntimeConfig(dry_run=True))

        runtime.step()

        self.assertEqual(runtime.logs[-1]["safety_severity"], "ok")

    def test_runtime_log_redacts_confirmation_id(self):
        self.server.state.emergency_stop_active = True
        runtime = RobotRuntime(self.client, RobotRuntimeConfig(dry_run=True))
        request = runtime.step(assistant=assistant_command("reset_emergency_stop")).plan.confirmation_request

        log_entry = runtime.logs[-1]

        self.assertNotIn("confirmation_id", log_entry)
        self.assertEqual(log_entry["confirmation_id_fingerprint"], request.confirmation_id[:12])
        self.assertNotEqual(log_entry["confirmation_id_fingerprint"], request.confirmation_id)


class FailingCommandClient:
    def __init__(self, wrapped: RobotClient):
        self.wrapped = wrapped

    def get_status(self):
        return self.wrapped.get_status()

    def send_command(self, command: str, face: str | None = None):
        raise RuntimeError("simulated command send failure")

    def set_face(self, face: str):
        return self.wrapped.set_face(face)


if __name__ == "__main__":
    unittest.main()
