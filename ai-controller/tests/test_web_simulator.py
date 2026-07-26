import tempfile
import unittest

from sesame_ai_robot.web.service import RobotSimulatorService


class WebSimulatorTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.service = RobotSimulatorService(memory_storage_path=f"{self.tmp.name}/memory.json")

    def assert_read_only_call(self, fn, *args):
        loop = self.service.loop
        before = loop.hardware.state.snapshot()
        command = loop.client.current_command
        face = loop.client.current_face
        events = len(loop.hardware.events)
        confirmations = len(loop.confirmation_store._requests)
        runtime_mode = loop.runtime.config.runtime_mode
        result = fn(*args)
        self.assertEqual(loop.hardware.state.snapshot(), before)
        self.assertEqual(loop.client.current_command, command)
        self.assertEqual(loop.client.current_face, face)
        self.assertEqual(len(loop.hardware.events), events)
        self.assertEqual(len(loop.confirmation_store._requests), confirmations)
        self.assertEqual(loop.runtime.config.runtime_mode, runtime_mode)
        return result

    def test_state_returns_normalized_fields(self):
        state = self.assert_read_only_call(self.service.state)
        self.assertEqual(state["runtimeMode"], "simulator")
        self.assertIn("motionState", state)
        self.assertIn("currentCommand", state)
        self.assertIn("currentFace", state)
        self.assertIn("batteryPercent", state)
        self.assertIn("faults", state)

    def test_timeline_default_and_max(self):
        self.service.inject_fault("servo_stuck")
        self.assertEqual(self.assert_read_only_call(self.service.timeline)["limit"], 20)
        self.assertEqual(self.assert_read_only_call(self.service.timeline, 50)["limit"], 50)

    def test_timeline_invalid_limits(self):
        for limit in (0, 51, True):
            with self.assertRaises(ValueError):
                self.service.timeline(limit)

    def test_timeline_sanitizes_sensitive_text(self):
        self.service.loop.hardware.events.append({
            "eventType": "runtime",
            "reason": "confirmation_id=abc api_key=sk-secret C:\\Users\\name\\file.py",
            "result": "ok",
        })
        encoded = str(self.service.timeline(1))
        self.assertNotIn("confirmation_id", encoded)
        self.assertNotIn("sk-secret", encoded)
        self.assertNotIn("C:\\Users", encoded)

    def test_timeline_query_does_not_add_event(self):
        before = len(self.service.loop.hardware.events)
        self.service.timeline()
        self.assertEqual(len(self.service.loop.hardware.events), before)

    def test_inject_allowed_fault(self):
        reply = self.service.inject_fault("servo_stuck")
        self.assertEqual(reply["status"], "ok")
        self.assertIn("servo_stuck", self.service.state()["faults"])

    def test_reject_unknown_and_long_fault(self):
        for fault in ("unknown_fault", "x" * 121):
            with self.assertRaises(ValueError):
                self.service.inject_fault(fault)

    def test_clear_fault_and_all(self):
        self.service.inject_fault("servo_stuck")
        self.service.clear_fault("servo_stuck")
        self.assertNotIn("servo_stuck", self.service.state()["faults"])
        self.service.inject_fault("motor_stall")
        self.service.clear_fault("all")
        self.assertEqual(self.service.state()["faults"], [])

    def test_clear_unknown_fault_rejected(self):
        with self.assertRaises(ValueError):
            self.service.clear_fault("unknown_fault")

    def test_fault_api_does_not_change_runtime_mode_or_real_hardware(self):
        before_mode = self.service.loop.runtime.config.runtime_mode
        self.service.inject_fault("battery_low")
        self.assertEqual(self.service.loop.runtime.config.runtime_mode, before_mode)
        self.assertFalse(self.service.loop.runtime.config.allow_real_robot)


if __name__ == "__main__":
    unittest.main()
