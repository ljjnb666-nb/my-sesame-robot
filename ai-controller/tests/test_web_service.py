import tempfile
import unittest

from sesame_ai_robot.memory import MemoryManager
from sesame_ai_robot.web.service import RobotSimulatorService


class WebServiceLifecycleTest(unittest.TestCase):
    def make_service(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        return RobotSimulatorService(memory_storage_path=f"{self.tmp.name}/memory.json")

    def test_health_returns_local_simulator_metadata(self):
        service = self.make_service()
        self.assertEqual(service.health()["status"], "ok")
        self.assertEqual(service.health()["version"], "0.4")
        self.assertEqual(service.health()["runtimeMode"], "simulator")
        self.assertTrue(service.health()["simulatorOnly"])
        self.assertEqual(service.health()["provider"], "mock")

    def test_multiple_requests_reuse_loop_runtime_and_store(self):
        service = self.make_service()
        first = service.debug_identity()
        service.chat("battery")
        service.state()
        second = service.debug_identity()
        self.assertEqual(first["loop"], second["loop"])
        self.assertEqual(first["runtime"], second["runtime"])
        self.assertEqual(first["confirmation_store"], second["confirmation_store"])
        self.assertEqual(first["memory_manager"], second["memory_manager"])

    def test_simulator_reset_rebuilds_runtime_graph(self):
        service = self.make_service()
        before = service.debug_identity()
        service.reset_simulator()
        after = service.debug_identity()
        self.assertNotEqual(before["hardware"], after["hardware"])
        self.assertNotEqual(before["runtime"], after["runtime"])
        self.assertNotEqual(before["facade"], after["facade"])
        self.assertNotEqual(before["executor"], after["executor"])
        self.assertNotEqual(before["confirmation_store"], after["confirmation_store"])
        self.assertEqual(before["memory_manager"], after["memory_manager"])

    def test_simulator_reset_invalidates_old_confirmation(self):
        service = self.make_service()
        requested = service.chat("walk")
        confirmation_id = requested["confirmationId"]
        service.reset_simulator()
        reply = service.chat("walk", confirmation_id)
        self.assertEqual(reply["status"], "failed")
        self.assertEqual(reply["structured"]["runtime"]["confirmation"]["state"], "unknown_id")

    def test_simulator_reset_clears_fault_and_pending_metadata(self):
        service = self.make_service()
        service.inject_fault("servo_stuck")
        self.assertIn("servo_stuck", service.state()["faults"])
        service.chat("walk")
        service.reset_simulator()
        self.assertEqual(service.state()["faults"], [])
        self.assertIsNone(service._pending_confirmation)

    def test_session_reset_preserves_hardware_and_long_term_memory(self):
        service = self.make_service()
        service.inject_fault("servo_stuck")
        service.loop.memory_manager.store("long_term", "user_preferences", {"voice": "quiet"})
        service.loop.memory_manager.store("short_term", "task_context", {"tmp": "yes"})
        hardware_id = service.debug_identity()["hardware"]
        service.reset_session()
        self.assertEqual(service.debug_identity()["hardware"], hardware_id)
        self.assertIn("servo_stuck", service.state()["faults"])
        self.assertEqual(service.loop.memory_manager.retrieve("long_term", "user_preferences"), {"voice": "quiet"})
        self.assertEqual(service.loop.memory_manager.retrieve("short_term", "task_context"), {})

    def test_different_services_do_not_share_simulator_or_confirmation(self):
        one = self.make_service()
        two = self.make_service()
        one.inject_fault("servo_stuck")
        requested = one.chat("walk")
        self.assertIn("servo_stuck", one.state()["faults"])
        self.assertEqual(two.state()["faults"], [])
        reply = two.chat("walk", requested["confirmationId"])
        self.assertEqual(reply["structured"]["runtime"]["confirmation"]["state"], "unknown_id")

    def test_temporary_memory_path_is_used(self):
        service = self.make_service()
        self.assertIn(self.tmp.name, str(service.loop.memory_manager.storage_path))

    def test_injected_memory_manager_is_reused(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = MemoryManager(f"{tmp}/memory.json")
            service = RobotSimulatorService(memory_manager=manager)
            self.assertIs(service.loop.memory_manager, manager)


if __name__ == "__main__":
    unittest.main()
