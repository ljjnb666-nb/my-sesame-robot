import unittest

from sesame_ai_robot.memory import MemoryManager
from sesame_ai_robot.web.service import RobotSimulatorService

from web_test_utils import make_service


class WebServiceLifecycleTest(unittest.TestCase):
    def test_health_returns_local_simulator_metadata(self):
        service, _tmp = make_service(self)
        self.assertEqual(service.health(), {
            "status": "ok",
            "version": "0.4",
            "runtimeMode": "simulator",
            "simulatorOnly": True,
            "provider": "mock",
        })

    def test_multiple_requests_reuse_loop_runtime_and_store(self):
        service, _tmp = make_service(self)
        first = service._testing_identity()
        service.chat("battery")
        service.state()
        second = service._testing_identity()
        self.assertEqual(first["loop"], second["loop"])
        self.assertEqual(first["runtime"], second["runtime"])
        self.assertEqual(first["confirmation_store"], second["confirmation_store"])
        self.assertEqual(first["memory_manager"], second["memory_manager"])

    def test_simulator_reset_rebuilds_runtime_graph(self):
        service, _tmp = make_service(self)
        before = service._testing_identity()
        service.reset_simulator()
        after = service._testing_identity()
        self.assertNotEqual(before["hardware"], after["hardware"])
        self.assertNotEqual(before["runtime"], after["runtime"])
        self.assertNotEqual(before["facade"], after["facade"])
        self.assertNotEqual(before["executor"], after["executor"])
        self.assertNotEqual(before["confirmation_store"], after["confirmation_store"])
        self.assertEqual(before["memory_manager"], after["memory_manager"])

    def test_simulator_reset_invalidates_old_confirmation_as_unknown_id(self):
        service, _tmp = make_service(self)
        requested = service.chat("walk")
        service.reset_simulator()
        reply = service.chat("walk", requested["confirmationId"])
        self.assertEqual(reply["status"], "failed")
        self.assertEqual(reply["structured"]["runtime"]["confirmation"]["state"], "unknown_id")

    def test_simulator_reset_clears_fault_and_pending_metadata(self):
        service, _tmp = make_service(self)
        service.inject_fault("servo_stuck")
        service.chat("walk")
        self.assertTrue(service._testing_snapshot()["pendingConfirmation"])
        service.reset_simulator()
        snapshot = service._testing_snapshot()
        self.assertEqual(snapshot["faults"], [])
        self.assertFalse(snapshot["pendingConfirmation"])

    def test_session_reset_preserves_hardware_and_long_term_memory(self):
        service, _tmp = make_service(self)
        service.inject_fault("servo_stuck")
        service._testing_store_memory("long_term", "user_preferences", {"voice": "quiet"})
        service._testing_store_memory("short_term", "task_context", {"tmp": "yes"})
        hardware_id = service._testing_identity()["hardware"]
        result = service.reset_session()
        self.assertFalse(result["runtimeConfirmationsRevoked"])
        self.assertEqual(service._testing_identity()["hardware"], hardware_id)
        self.assertIn("servo_stuck", service.state()["faults"])
        self.assertEqual(service._testing_memory("long_term", "user_preferences"), {"voice": "quiet"})
        self.assertEqual(service._testing_memory("short_term", "task_context"), {})

    def test_session_reset_keeps_runtime_confirmation_semantics(self):
        service, _tmp = make_service(self)
        requested = service.chat("walk")
        service.reset_session()
        accepted = service.chat("walk", requested["confirmationId"])
        self.assertEqual(accepted["status"], "ok")
        self.assertEqual(accepted["action"], "walk_forward")

    def test_different_services_do_not_share_simulator_or_confirmation(self):
        one, _tmp_one = make_service(self)
        two, _tmp_two = make_service(self)
        one.inject_fault("servo_stuck")
        requested = one.chat("walk")
        self.assertIn("servo_stuck", one.state()["faults"])
        self.assertEqual(two.state()["faults"], [])
        reply = two.chat("walk", requested["confirmationId"])
        self.assertEqual(reply["structured"]["runtime"]["confirmation"]["state"], "unknown_id")

    def test_temporary_memory_path_is_used(self):
        service, tmp = make_service(self)
        self.assertIn(tmp.name, service._testing_snapshot()["memoryPath"])

    def test_injected_memory_manager_is_reused(self):
        with self.subTest("injected manager"):
            import tempfile
            with tempfile.TemporaryDirectory() as tmp:
                manager = MemoryManager(f"{tmp}/memory.json")
                service = RobotSimulatorService(memory_manager=manager)
                self.assertEqual(service._testing_identity()["memory_manager"], id(manager))

    def test_service_does_not_publicly_expose_control_objects(self):
        service, _tmp = make_service(self)
        for name in (
            "loop",
            "hardware",
            "client",
            "runtime",
            "confirmation_store",
            "tool_executor",
            "read_only_facade",
        ):
            self.assertFalse(hasattr(service, name), name)

    def test_state_uses_tool_executor_read_only_tool(self):
        service, _tmp = make_service(self)
        calls = []
        original = service._loop.tool_executor.execute

        def spy(payload, *, confirmation_id=None):
            calls.append(payload["tool_name"])
            return original(payload, confirmation_id=confirmation_id)

        service._loop.tool_executor.execute = spy
        state = service.state()
        self.assertEqual(state["batteryPercent"], 80)
        self.assertEqual(calls, ["get_robot_state"])

    def test_timeline_uses_tool_executor_read_only_tool(self):
        service, _tmp = make_service(self)
        calls = []
        original = service._loop.tool_executor.execute

        def spy(payload, *, confirmation_id=None):
            calls.append((payload["tool_name"], payload["arguments"]))
            return original(payload, confirmation_id=confirmation_id)

        service._loop.tool_executor.execute = spy
        result = service.timeline(3)
        self.assertEqual(result["limit"], 3)
        self.assertEqual(calls, [("get_timeline", {"limit": 3})])

    def test_fault_api_does_not_use_execute_action(self):
        service, _tmp = make_service(self)
        calls = []
        original = service._loop.tool_executor.execute

        def spy(payload, *, confirmation_id=None):
            calls.append(payload["tool_name"])
            return original(payload, confirmation_id=confirmation_id)

        service._loop.tool_executor.execute = spy
        service.inject_fault("servo_stuck")
        self.assertNotIn("execute_action", calls)
        self.assertEqual(calls, ["get_robot_state"])


if __name__ == "__main__":
    unittest.main()
