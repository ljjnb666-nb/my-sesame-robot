import unittest

from sesame_ai_robot.client import RobotClient, UnsupportedCommandError
from sesame_ai_robot.config import ControllerConfig
from sesame_ai_robot.mock_robot import MockRobotServer


class RobotClientTest(unittest.TestCase):
    def setUp(self):
        self.server = MockRobotServer(port=0)
        self.server.start()
        self.client = RobotClient(ControllerConfig(robot_url=self.server.url, request_timeout_s=1.0))

    def tearDown(self):
        self.server.stop()

    def test_get_status(self):
        status = self.client.get_status()

        self.assertEqual(status.motion_state, "idle")
        self.assertFalse(status.emergency_stop_active)
        self.assertIn("availableCommands", status.raw)

    def test_send_alias_command(self):
        response = self.client.send_command("walk_forward")

        self.assertEqual(response["status"], "ok")
        self.assertEqual(self.client.get_status().current_command, "forward")

    def test_emergency_stop_latches_and_reset_clears(self):
        self.client.send_command("walk_forward")
        self.client.emergency_stop()

        status = self.client.get_status()
        self.assertTrue(status.emergency_stop_active)
        self.assertEqual(status.current_command, "")

        self.client.reset_emergency_stop()
        self.assertFalse(self.client.get_status().emergency_stop_active)

    def test_rejects_unsupported_command(self):
        with self.assertRaises(UnsupportedCommandError):
            self.client.send_command("follow_owner")


if __name__ == "__main__":
    unittest.main()
