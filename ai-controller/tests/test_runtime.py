import unittest

from sesame_ai_robot.client import RobotClient
from sesame_ai_robot.config import ControllerConfig
from sesame_ai_robot.mock_robot import MockRobotServer, MockRobotState
from sesame_ai_robot.runtime import RobotRuntime, RobotRuntimeConfig
from sesame_ai_robot.advanced import RuntimeMode
from sesame_ai_robot.tracking import TrackingDecision, TrackingState


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


if __name__ == "__main__":
    unittest.main()
