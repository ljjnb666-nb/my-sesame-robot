import json
import unittest

from sesame_ai_robot.ai_models import AIResponse
from sesame_ai_robot.confirmation import ConfirmationStore
from sesame_ai_robot.web.service import WebServiceError

from web_test_utils import make_service


class DriftProvider:
    name = "mock"

    def __init__(self):
        self.calls = 0

    def generate_intent(self, request):
        self.calls += 1
        command = "walk_forward" if self.calls == 1 else "stand"
        payload = {
            "request_id": request.request_id,
            "intent": "robot_command",
            "confidence": 0.9,
            "requires_clarification": False,
            "clarification_question": None,
            "actions": [{"action": "robot_command", "arguments": {"command": command}}],
            "user_message": "mock",
            "reason_code": "mock_rule",
        }
        return AIResponse(request.request_id, json.dumps(payload), provider=self.name)


class WebConfirmationTest(unittest.TestCase):
    def setUp(self):
        self.service, _tmp = make_service(self)

    def test_pending_metadata_is_created_without_grant(self):
        reply = self.service.chat("walk")
        snapshot = self.service._testing_snapshot()
        self.assertTrue(snapshot["pendingConfirmation"])
        self.assertEqual(reply["action"], "walk_forward")
        self.assertIsNotNone(reply["confirmationFingerprint"])

    def test_confirmation_id_is_not_written_to_memory(self):
        reply = self.service.chat("walk")
        memory_text = str(self.service._testing_memory("short_term"))
        self.assertNotIn(reply["confirmationId"], memory_text)

    def test_confirmation_id_is_not_written_to_timeline(self):
        reply = self.service.chat("walk")
        encoded = str(self.service.timeline(20))
        self.assertNotIn(reply["confirmationId"], encoded)

    def test_service_does_not_directly_consume_confirmation_store_on_request(self):
        original = ConfirmationStore.consume

        def forbidden(*args, **kwargs):
            raise AssertionError("direct consume call")

        ConfirmationStore.consume = forbidden
        try:
            reply = self.service.chat("walk")
            self.assertEqual(reply["status"], "confirmation_required")
        finally:
            ConfirmationStore.consume = original

    def test_correct_confirmation_consumes_through_runtime(self):
        requested = self.service.chat("walk")
        accepted = self.service.chat("walk", requested["confirmationId"])
        self.assertEqual(accepted["status"], "ok")
        self.assertEqual(accepted["structured"]["runtime"]["confirmation"]["state"], "accepted")

    def test_session_reset_clears_web_pending_metadata(self):
        self.service.chat("walk")
        self.assertTrue(self.service._testing_snapshot()["pendingConfirmation"])
        result = self.service.reset_session()
        self.assertFalse(result["runtimeConfirmationsRevoked"])
        self.assertFalse(self.service._testing_snapshot()["pendingConfirmation"])

    def test_provider_drift_returns_action_mismatch(self):
        service, _tmp = make_service(self, provider=DriftProvider())
        requested = service.chat("walk")
        reply = service.chat("walk", requested["confirmationId"])
        self.assertEqual(reply["status"], "failed")
        self.assertEqual(reply["structured"]["runtime"]["confirmation"]["state"], "action_mismatch")

    def test_expired_confirmation_is_deterministic(self):
        clock = {"now": 100.0}

        def store_factory():
            return ConfirmationStore(ttl_seconds=1.0, _clock=lambda: clock["now"])

        service, _tmp = make_service(self, confirmation_store_factory=store_factory)
        requested = service.chat("walk")
        clock["now"] = 101.0
        reply = service.chat("walk", requested["confirmationId"])
        self.assertEqual(reply["status"], "failed")
        self.assertEqual(reply["structured"]["runtime"]["confirmation"]["state"], "expired")

    def test_text_mismatch_does_not_reach_runtime(self):
        requested = self.service.chat("walk")
        with self.assertRaises(WebServiceError) as ctx:
            self.service.chat("stand", requested["confirmationId"])
        self.assertEqual(ctx.exception.code, "stale_confirmation")


if __name__ == "__main__":
    unittest.main()
