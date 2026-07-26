import tempfile
import unittest

from sesame_ai_robot.ai_models import RobotReply
from sesame_ai_robot.web.service import RobotSimulatorService


class WebChatTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.service = RobotSimulatorService(memory_storage_path=f"{self.tmp.name}/memory.json")

    def test_query_battery(self):
        reply = self.service.chat("battery")
        self.assertEqual(reply["status"], "ok")
        self.assertEqual(reply["structured"]["battery"]["percent"], 80)

    def test_query_state(self):
        reply = self.service.chat("status")
        self.assertEqual(reply["status"], "ok")
        self.assertIn("state", reply["structured"])

    def test_low_risk_wave_executes(self):
        reply = self.service.chat("wave")
        self.assertEqual(reply["status"], "ok")
        self.assertEqual(reply["action"], "wave")
        self.assertFalse(reply["requiresConfirmation"])

    def test_stop_executes_without_confirmation(self):
        reply = self.service.chat("stop")
        self.assertEqual(reply["status"], "ok")
        self.assertEqual(reply["action"], "stop")

    def test_motion_requires_confirmation(self):
        reply = self.service.chat("walk")
        self.assertEqual(reply["status"], "confirmation_required")
        self.assertTrue(reply["requiresConfirmation"])
        self.assertIn("confirmationId", reply)
        self.assertIsNotNone(reply["confirmationFingerprint"])

    def test_correct_confirmation(self):
        requested = self.service.chat("walk")
        accepted = self.service.chat("walk", requested["confirmationId"])
        self.assertEqual(accepted["status"], "ok")
        self.assertEqual(accepted["action"], "walk_forward")

    def test_replay_rejected_by_runtime(self):
        requested = self.service.chat("walk")
        self.service.chat("walk", requested["confirmationId"])
        replay = self.service.chat("walk", requested["confirmationId"])
        self.assertEqual(replay["status"], "failed")
        self.assertEqual(replay["structured"]["runtime"]["confirmation"]["state"], "already_used")

    def test_wrong_action_text_rejected_as_stale_web_confirmation(self):
        requested = self.service.chat("walk")
        with self.assertRaises(ValueError):
            self.service.chat("stand", requested["confirmationId"])

    def test_context_changed_reaches_runtime(self):
        requested = self.service.chat("walk")
        self.service.inject_fault("communication_lost")
        reply = self.service.chat("walk", requested["confirmationId"])
        self.assertEqual(reply["status"], "failed")
        self.assertIn(reply["structured"]["runtime"]["confirmation"]["state"], {"context_changed", "action_mismatch"})

    def test_unknown_confirmation_reaches_runtime(self):
        reply = self.service.chat("walk", "unknown-confirmation-id")
        self.assertEqual(reply["status"], "failed")
        self.assertEqual(reply["structured"]["runtime"]["confirmation"]["state"], "unknown_id")

    def test_confirmation_id_length_rejected(self):
        with self.assertRaises(ValueError):
            self.service.chat("walk", "x" * 129)

    def test_chat_calls_ai_interaction_loop_handle_text(self):
        calls = []

        def fake_handle_text(text, confirmation_id=None):
            calls.append((text, confirmation_id))
            return RobotReply("req", "session", "ok", "ok", "ok")

        self.service.loop.handle_text = fake_handle_text
        reply = self.service.chat("battery", "confirm")
        self.assertEqual(calls, [("battery", "confirm")])
        self.assertEqual(reply["status"], "ok")


if __name__ == "__main__":
    unittest.main()
