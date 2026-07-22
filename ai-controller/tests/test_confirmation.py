import unittest

from sesame_ai_robot.confirmation import ConfirmationStore


class ConfirmationStoreTest(unittest.TestCase):
    def test_grant_is_action_bound_and_one_time(self):
        store = ConfirmationStore(ttl_seconds=10)
        context = {"runtime_mode": "mock", "emergency_stop_active": True, "target_action": "reset_emergency_stop"}
        request = store.create("reset_emergency_stop", "reset", context, now=1.0)

        self.assertIsNone(store.grant(request.confirmation_id, "stand", context, now=2.0))
        grant = store.grant(request.confirmation_id, "reset_emergency_stop", context, now=2.0)
        self.assertIsNotNone(grant)
        self.assertIsNone(store.grant(request.confirmation_id, "reset_emergency_stop", context, now=3.0))

    def test_expired_and_context_changed_confirmation_are_rejected(self):
        store = ConfirmationStore(ttl_seconds=1)
        context = {"runtime_mode": "mock", "emergency_stop_active": True, "target_action": "reset_emergency_stop"}
        request = store.create("reset_emergency_stop", "reset", context, now=1.0)

        self.assertIsNone(store.grant(request.confirmation_id, "reset_emergency_stop", context, now=3.0))

        request = store.create("self_righting", "stand", context, now=4.0)
        changed = dict(context, emergency_stop_active=False)
        self.assertIsNone(store.grant(request.confirmation_id, "self_righting", changed, now=4.5))


if __name__ == "__main__":
    unittest.main()
