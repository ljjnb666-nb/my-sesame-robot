import time
import unittest

from sesame_ai_robot.client import RobotClient
from sesame_ai_robot.config import ControllerConfig
from sesame_ai_robot.heartbeat import HeartbeatLoop
from sesame_ai_robot.mock_robot import MockRobotServer, MockRobotState


class HeartbeatLoopTest(unittest.TestCase):
    def setUp(self):
        self.server = MockRobotServer(port=0, state=MockRobotState(command_timeout_ms=200))
        self.server.start()
        self.client = RobotClient(ControllerConfig(robot_url=self.server.url, request_timeout_s=1.0))

    def tearDown(self):
        self.server.stop()

    def test_tick_refreshes_continuous_command(self):
        self.client.send_command("walk_forward")
        time.sleep(0.12)

        self.assertTrue(HeartbeatLoop(self.client, 0.05).tick())
        time.sleep(0.12)

        status = self.client.get_status()
        self.assertEqual(status.current_command, "forward")
        self.assertFalse(status.raw["communicationTimedOut"])

    def test_missing_heartbeat_times_out(self):
        self.client.send_command("walk_forward")
        time.sleep(0.25)

        status = self.client.get_status()
        self.assertEqual(status.current_command, "")
        self.assertTrue(status.raw["communicationTimedOut"])


if __name__ == "__main__":
    unittest.main()
