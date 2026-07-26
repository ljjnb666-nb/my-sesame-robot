import tempfile
import unittest

from sesame_ai_robot.confirmation import ConfirmationStore
from sesame_ai_robot.web.service import RobotSimulatorService


class WebConfirmationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.service = RobotSimulatorService(memory_storage_path=f"{self.tmp.name}/memory.json")

    def test_pending_metadata_is_created_without_grant(self):
        reply = self.service.chat("walk")
        pending = self.service._pending_confirmation
        self.assertIsNotNone(pending)
        self.assertEqual(pending.text, "walk")
        self.assertEqual(pending.action, "walk_forward")
        self.assertEqual(pending.fingerprint, reply["confirmationFingerprint"])
        self.assertFalse(hasattr(pending, "grant"))

    def test_confirmation_id_is_not_written_to_memory(self):
        reply = self.service.chat("walk")
        memory_text = str(self.service.loop.memory_manager.retrieve("short_term"))
        self.assertNotIn(reply["confirmationId"], memory_text)

    def test_confirmation_id_is_not_written_to_timeline(self):
        reply = self.service.chat("walk")
        encoded = str(self.service.timeline(20))
        self.assertNotIn(reply["confirmationId"], encoded)

    def test_service_does_not_directly_consume_confirmation_store(self):
        original = ConfirmationStore.consume

        def forbidden(*args, **kwargs):
            raise AssertionError("direct consume call")

        ConfirmationStore.consume = forbidden
        try:
            reply = self.service.chat("walk")
            self.assertEqual(reply["status"], "confirmation_required")
        finally:
            ConfirmationStore.consume = original

    def test_confirmation_consume_occurs_only_through_runtime_on_submit(self):
        requested = self.service.chat("walk")
        accepted = self.service.chat("walk", requested["confirmationId"])
        self.assertEqual(accepted["status"], "ok")

    def test_session_reset_clears_web_pending_metadata(self):
        self.service.chat("walk")
        self.assertIsNotNone(self.service._pending_confirmation)
        self.service.reset_session()
        self.assertIsNone(self.service._pending_confirmation)

    def test_session_reset_does_not_forge_confirmation_result(self):
        requested = self.service.chat("walk")
        self.service.reset_session()
        reply = self.service.chat("walk", requested["confirmationId"])
        self.assertIn(reply["status"], {"ok", "failed"})
        if reply["status"] == "failed":
            self.assertIn("runtime", reply["structured"])


if __name__ == "__main__":
    unittest.main()
