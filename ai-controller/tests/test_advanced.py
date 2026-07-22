import unittest

from sesame_ai_robot.advanced import (
    AdvancedBehaviorPlanner,
    AdvancedFeatureConfig,
    ChargingIntent,
    EmotionState,
    MockMemoryStore,
    PostureState,
    RuntimeMode,
    TerrainState,
)
from sesame_ai_robot.safety import SensorSnapshot


class AdvancedBehaviorPlannerTest(unittest.TestCase):
    def test_fall_detection_requests_emergency_stop(self):
        decision = AdvancedBehaviorPlanner().assess_posture(SensorSnapshot(imu_roll_deg=72))

        self.assertEqual(decision.state, PostureState.FALLEN.value)
        self.assertEqual(decision.command, "emergency_stop")

    def test_tilt_requests_stop_before_fall_limit(self):
        decision = AdvancedBehaviorPlanner().assess_posture(SensorSnapshot(imu_pitch_deg=25))

        self.assertEqual(decision.state, PostureState.TILTED.value)
        self.assertEqual(decision.command, "stop")

    def test_mock_self_righting_can_request_high_level_stand(self):
        planner = AdvancedBehaviorPlanner(AdvancedFeatureConfig(allow_self_righting=True))

        decision = planner.plan_self_righting(PostureState.FALLEN)

        self.assertEqual(decision.command, "stand")
        self.assertFalse(decision.requires_user_confirmation)

    def test_real_robot_self_righting_waits_for_user(self):
        planner = AdvancedBehaviorPlanner(AdvancedFeatureConfig(
            runtime_mode=RuntimeMode.REAL_ROBOT,
            allow_self_righting=True,
        ))

        decision = planner.plan_self_righting(PostureState.FALLEN)

        self.assertIsNone(decision.command)
        self.assertTrue(decision.requires_user_confirmation)

    def test_terrain_cliff_requests_emergency_stop(self):
        decision = AdvancedBehaviorPlanner().assess_terrain(SensorSnapshot(cliff_detected=True))

        self.assertEqual(decision.state, TerrainState.UNSAFE.value)
        self.assertEqual(decision.command, "emergency_stop")

    def test_low_battery_mock_docking_is_policy_gated(self):
        decision = AdvancedBehaviorPlanner().plan_charging(SensorSnapshot(battery_percent=10))

        self.assertEqual(decision.state, ChargingIntent.WAIT_FOR_USER.value)
        self.assertIsNone(decision.command)

    def test_low_battery_real_docking_requires_confirmation(self):
        planner = AdvancedBehaviorPlanner(AdvancedFeatureConfig(
            runtime_mode=RuntimeMode.REAL_ROBOT,
            allow_auto_docking=True,
        ))

        decision = planner.plan_charging(SensorSnapshot(battery_percent=10))

        self.assertIsNone(decision.command)
        self.assertTrue(decision.requires_user_confirmation)

    def test_mock_auto_docking_does_not_emit_unsupported_command(self):
        planner = AdvancedBehaviorPlanner(AdvancedFeatureConfig(allow_auto_docking=True))

        decision = planner.plan_charging(SensorSnapshot(battery_percent=10))

        self.assertEqual(decision.state, ChargingIntent.SEEK_DOCK.value)
        self.assertIsNone(decision.command)

    def test_emotion_state_uses_context_without_persistence(self):
        emotion = EmotionState.from_context(owner_visible=True, battery_percent=80, emergency_stop_active=False)

        self.assertEqual(emotion.mood, "happy")

    def test_mock_memory_store_is_local_and_in_memory(self):
        store = MockMemoryStore()
        store.remember("owner.preference", "likes quiet voice", ("owner", "preference"))

        record = store.recall("owner.preference")

        self.assertIsNotNone(record)
        self.assertEqual(record.value, "likes quiet voice")


if __name__ == "__main__":
    unittest.main()
