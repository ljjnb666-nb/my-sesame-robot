import json
import unittest

from sesame_ai_robot.tools import RobotReadOnlyFacade
from sesame_ai_robot.virtual_hardware import SimulatorHardwareAdapter, VirtualHardwareRobotClient
from sesame_ai_robot.runtime import RobotRuntime, RobotRuntimeConfig


class ToolReadOnlyTest(unittest.TestCase):
    def setUp(self):
        self.hardware = SimulatorHardwareAdapter()
        self.client = VirtualHardwareRobotClient(self.hardware)
        self.runtime = RobotRuntime(self.client, RobotRuntimeConfig(dry_run=False))
        self.facade = RobotReadOnlyFacade(client=self.client, hardware=self.hardware)

    def assert_read_only(self, fn, *args):
        before = self.hardware.state.snapshot()
        command = self.client.current_command
        face = self.client.current_face
        event_count = len(self.hardware.events)
        confirmation_count = len(self.runtime.confirmation_store._requests)
        runtime_mode = self.runtime.config.runtime_mode
        emergency_stop = self.hardware.state.emergency_stop
        charging_state = self.hardware.state.charging_state
        faults = set(self.hardware.state.faults)
        result = fn(*args)
        self.assertEqual(self.hardware.state.snapshot(), before)
        self.assertEqual(self.client.current_command, command)
        self.assertEqual(self.client.current_face, face)
        self.assertEqual(len(self.hardware.events), event_count)
        self.assertEqual(len(self.runtime.confirmation_store._requests), confirmation_count)
        self.assertEqual(self.runtime.config.runtime_mode, runtime_mode)
        self.assertEqual(self.hardware.state.emergency_stop, emergency_stop)
        self.assertEqual(self.hardware.state.charging_state, charging_state)
        self.assertEqual(self.hardware.state.faults, faults)
        json.dumps(result, allow_nan=False)
        return result

    def test_battery_status(self):
        self.assertEqual(self.assert_read_only(self.facade.get_battery_status)["percent"], 80)

    def test_robot_state(self):
        self.assertIn("motionState", self.assert_read_only(self.facade.get_robot_state))

    def test_pose(self):
        self.assertIn("pose", self.assert_read_only(self.facade.get_pose))

    def test_communication(self):
        self.assertTrue(self.assert_read_only(self.facade.get_communication_status)["connected"])

    def test_actuator(self):
        result = self.assert_read_only(self.facade.get_actuator_status)
        self.assertIn("servos", result)
        self.assertIn("motors", result)

    def test_fault(self):
        self.hardware.inject_fault("servo_stuck")
        result = self.assert_read_only(self.facade.get_fault_status)
        self.assertIn("servo_stuck", result["faults"])

    def test_timeline_default_limit(self):
        for _ in range(30):
            self.hardware.inject_fault("servo_stuck")
            self.hardware.clear_fault("servo_stuck")
        self.assertLessEqual(len(self.assert_read_only(self.facade.get_timeline)["events"]), 20)

    def test_timeline_max_limit(self):
        self.assertEqual(self.assert_read_only(self.facade.get_timeline, 50)["limit"], 50)

    def test_timeline_invalid_limit(self):
        with self.assertRaises(ValueError):
            self.facade.get_timeline(0)

    def test_charging(self):
        self.assertEqual(self.assert_read_only(self.facade.get_charging_status)["chargingState"], "not_charging")

    def test_result_size_is_bounded(self):
        result = self.assert_read_only(self.facade.get_actuator_status)
        self.assertLessEqual(len(json.dumps(result, allow_nan=False).encode("utf-8")), 4096)

    def test_query_does_not_change_motion_state(self):
        before = self.client.get_status().raw["motionState"]
        self.facade.get_robot_state()
        self.assertEqual(self.client.get_status().raw["motionState"], before)

    def test_timeline_event_fields_are_allowlisted_and_sanitized(self):
        self.hardware.events.append({
            "eventType": "runtime",
            "reason": "confirmation_id=abc token=secret C:\\Users\\x",
            "callable": lambda: None,
            "api_key": "sk-test",
            "object": object(),
            "result": {"password": "hidden", "safe": "ok"},
        })
        result = self.assert_read_only(self.facade.get_timeline, 1)
        event = result["events"][0]
        self.assertEqual(set(event), {"eventType", "reason", "result"})
        self.assertEqual(event["reason"], "[filtered]")
        self.assertEqual(event["result"], {"safe": "ok"})
        encoded = json.dumps(event, ensure_ascii=False)
        self.assertNotIn("confirmation_id", encoded)
        self.assertNotIn("token", encoded)
        self.assertNotIn("api_key", encoded)
        self.assertNotIn("C:\\Users", encoded)


if __name__ == "__main__":
    unittest.main()
