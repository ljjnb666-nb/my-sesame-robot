import unittest

from sesame_ai_robot.web.service import WebServiceError

from web_test_utils import make_service


class WebSimulatorTest(unittest.TestCase):
    def setUp(self):
        self.service, _tmp = make_service(self)

    def assert_read_only_call(self, fn, *args):
        before = self.service._testing_snapshot()
        result = fn(*args)
        after = self.service._testing_snapshot()
        for key in (
            "hardwareSnapshot",
            "currentCommand",
            "currentFace",
            "runtimeMode",
            "confirmationRequestCount",
            "hardwareEventCount",
            "faults",
            "emergencyStop",
            "chargingState",
        ):
            self.assertEqual(after[key], before[key], key)
        return result

    def test_state_returns_normalized_values_and_is_read_only(self):
        state = self.assert_read_only_call(self.service.state)
        self.assertEqual(state["runtimeMode"], "simulator")
        self.assertEqual(state["motionState"], "idle")
        self.assertEqual(state["currentCommand"], "")
        self.assertEqual(state["currentFace"], "default")
        self.assertEqual(state["batteryPercent"], 80)
        self.assertEqual(state["faults"], [])

    def test_timeline_default_and_max_are_read_only(self):
        self.service.inject_fault("servo_stuck")
        self.assertEqual(self.assert_read_only_call(self.service.timeline)["limit"], 20)
        self.assertEqual(self.assert_read_only_call(self.service.timeline, 50)["limit"], 50)

    def test_timeline_invalid_limits(self):
        for limit in (0, 51, True):
            with self.subTest(limit=limit):
                with self.assertRaises(WebServiceError) as ctx:
                    self.service.timeline(limit)
                self.assertEqual(ctx.exception.code, "invalid_request")

    def test_timeline_sanitizes_sensitive_text(self):
        self.service._testing_append_event({
            "eventType": "runtime",
            "reason": "confirmation_id=abc api_key=sk-secret C:\\Users\\name\\file.py",
            "result": {"memory": "private", "safe": "ok"},
        })
        encoded = str(self.service.timeline(1))
        self.assertNotIn("confirmation_id", encoded)
        self.assertNotIn("sk-secret", encoded)
        self.assertNotIn("C:\\Users", encoded)
        self.assertNotIn("private", encoded)

    def test_timeline_query_does_not_add_event(self):
        before = self.service._testing_snapshot()["hardwareEventCount"]
        self.service.timeline()
        self.assertEqual(self.service._testing_snapshot()["hardwareEventCount"], before)

    def test_inject_allowed_fault(self):
        reply = self.service.inject_fault("servo_stuck")
        self.assertEqual(reply["status"], "ok")
        self.assertIn("servo_stuck", self.service.state()["faults"])

    def test_reject_unknown_and_long_faults(self):
        for fault in ("unknown_fault", "x" * 81, "../secret", "http://example.com", "servo_stuck; rm -rf ."):
            with self.subTest(fault=fault):
                with self.assertRaises(WebServiceError):
                    self.service.inject_fault(fault)

    def test_fault_length_boundary_uses_canonical_limit(self):
        allowed_length_unknown = "x" * 80
        with self.assertRaises(WebServiceError) as unknown:
            self.service.inject_fault(allowed_length_unknown)
        self.assertEqual(unknown.exception.code, "unknown_fault")
        with self.assertRaises(WebServiceError) as too_long:
            self.service.inject_fault("x" * 81)
        self.assertEqual(too_long.exception.code, "invalid_request")

    def test_all_injection_rejected_but_clear_allowed(self):
        with self.assertRaises(WebServiceError) as ctx:
            self.service.inject_fault("all")
        self.assertEqual(ctx.exception.code, "unknown_fault")
        self.service.inject_fault("motor_stall")
        self.assertEqual(self.service.clear_fault("all")["status"], "ok")
        self.assertEqual(self.service.state()["faults"], [])

    def test_clear_fault_and_reject_unknown(self):
        self.service.inject_fault("servo_stuck")
        self.assertEqual(self.service.clear_fault("servo_stuck")["status"], "ok")
        self.assertNotIn("servo_stuck", self.service.state()["faults"])
        with self.assertRaises(WebServiceError) as ctx:
            self.service.clear_fault("unknown_fault")
        self.assertEqual(ctx.exception.code, "unknown_fault")

    def test_fault_api_does_not_change_runtime_mode_or_real_hardware(self):
        before = self.service._testing_snapshot()
        self.service.inject_fault("battery_low")
        after = self.service._testing_snapshot()
        self.assertEqual(after["runtimeMode"], before["runtimeMode"])
        self.assertFalse(after["allowRealRobot"])


if __name__ == "__main__":
    unittest.main()
