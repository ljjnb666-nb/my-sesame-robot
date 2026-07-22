from concurrent.futures import ThreadPoolExecutor
import unittest

from sesame_ai_robot.confirmation import ConfirmationErrorCode, ConfirmationStore, MAX_CONFIRMATION_TTL_SECONDS


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

        expired = store.consume(request.confirmation_id, "reset_emergency_stop", context, now=2.0)
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

    def test_invalid_ttl_values_are_rejected(self):
        for ttl in (0, -1, MAX_CONFIRMATION_TTL_SECONDS + 1):
            with self.subTest(ttl=ttl):
                with self.assertRaises(ValueError):
                    ConfirmationStore(ttl_seconds=ttl)

    def test_action_parameter_change_rejects_confirmation(self):
        store = ConfirmationStore(ttl_seconds=10)
        context = {
            "runtime_mode": "mock",
            "action": "charging_dock",
            "target_device": "dock-a",
            "proposed_command": "charging_dock:dock-a",
        }
        request = store.create("charging_dock", "dock", context, now=1.0)

        changed = dict(context, target_device="dock-b", proposed_command="charging_dock:dock-b")
        result = store.consume(request.confirmation_id, "charging_dock", changed, now=2.0)

        self.assertFalse(result.accepted)
        self.assertEqual(result.error, ConfirmationErrorCode.CONTEXT_CHANGED)

    def test_multiple_confirmations_do_not_interfere(self):
        store = ConfirmationStore(ttl_seconds=10)
        context_a = {"runtime_mode": "mock", "action": "reset_emergency_stop", "proposed_command": "reset_emergency_stop"}
        context_b = {"runtime_mode": "mock", "action": "self_righting", "proposed_command": "self_righting"}
        request_a = store.create("reset_emergency_stop", "reset", context_a, now=1.0)
        request_b = store.create("self_righting", "self right", context_b, now=1.0)

        result_a = store.consume(request_a.confirmation_id, "reset_emergency_stop", context_a, now=2.0)
        result_b = store.consume(request_b.confirmation_id, "self_righting", context_b, now=2.0)

        self.assertTrue(result_a.accepted)
        self.assertTrue(result_b.accepted)

    def test_concurrent_consume_accepts_at_most_once(self):
        store = ConfirmationStore(ttl_seconds=10)
        context = {"runtime_mode": "mock", "action": "reset_emergency_stop", "proposed_command": "reset_emergency_stop"}
        request = store.create("reset_emergency_stop", "reset", context, now=1.0)

        def consume_once():
            return store.consume(request.confirmation_id, "reset_emergency_stop", context, now=2.0)

        with ThreadPoolExecutor(max_workers=8) as executor:
            results = tuple(executor.map(lambda _: consume_once(), range(16)))

        self.assertEqual(sum(1 for result in results if result.accepted), 1)
        self.assertEqual(sum(1 for result in results if result.error == ConfirmationErrorCode.ALREADY_USED), 15)


if __name__ == "__main__":
    unittest.main()
