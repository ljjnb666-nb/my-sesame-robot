import unittest

from sesame_ai_robot.confirmation import ConfirmationErrorCode, ConfirmationStore


class ConfirmationStoreTest(unittest.TestCase):
    def test_request_can_be_consumed_once(self):
        store = ConfirmationStore(ttl_seconds=10)
        context = {"runtime_mode": "mock", "emergency_stop_active": True, "target_action": "reset_emergency_stop"}
        request = store.create("reset_emergency_stop", "reset", context, now=1.0)

        result = store.consume(request.confirmation_id, "reset_emergency_stop", context, now=2.0)
        self.assertTrue(result.accepted)
        self.assertIsNotNone(result.grant)

        replay = store.consume(request.confirmation_id, "reset_emergency_stop", context, now=3.0)
        self.assertFalse(replay.accepted)
        self.assertEqual(replay.error, ConfirmationErrorCode.ALREADY_USED)

    def test_unknown_id_returns_error(self):
        result = ConfirmationStore().consume("missing", "reset_emergency_stop", {}, now=1.0)

        self.assertFalse(result.accepted)
        self.assertEqual(result.error, ConfirmationErrorCode.UNKNOWN_ID)

    def test_expired_and_context_changed_confirmation_are_rejected(self):
        store = ConfirmationStore(ttl_seconds=1)
        context = {"runtime_mode": "mock", "emergency_stop_active": True, "target_action": "reset_emergency_stop"}
        request = store.create("reset_emergency_stop", "reset", context, now=1.0)

        expired = store.consume(request.confirmation_id, "reset_emergency_stop", context, now=3.0)
        self.assertFalse(expired.accepted)
        self.assertEqual(expired.error, ConfirmationErrorCode.EXPIRED)

        request = store.create("self_righting", "stand", context, now=4.0)
        changed = dict(context, emergency_stop_active=False)
        changed_result = store.consume(request.confirmation_id, "self_righting", changed, now=4.5)
        self.assertFalse(changed_result.accepted)
        self.assertEqual(changed_result.error, ConfirmationErrorCode.CONTEXT_CHANGED)

    def test_action_mismatch_does_not_mark_used(self):
        store = ConfirmationStore(ttl_seconds=10)
        context = {"runtime_mode": "mock", "emergency_stop_active": True, "target_action": "reset_emergency_stop"}
        request = store.create("reset_emergency_stop", "reset", context, now=1.0)

        mismatch = store.consume(request.confirmation_id, "self_righting", context, now=2.0)
        self.assertFalse(mismatch.accepted)
        self.assertEqual(mismatch.error, ConfirmationErrorCode.ACTION_MISMATCH)

        accepted = store.consume(request.confirmation_id, "reset_emergency_stop", context, now=3.0)
        self.assertTrue(accepted.accepted)


if __name__ == "__main__":
    unittest.main()
