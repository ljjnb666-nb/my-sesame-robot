import unittest

from sesame_ai_robot.advanced import AdvancedDecision, AdvancedFeature, RuntimeMode
from sesame_ai_robot.arbiter import ArbiterInput, BehaviorArbiter
from sesame_ai_robot.assistant import AssistantAction, AssistantPlan, AssistantStep
from sesame_ai_robot.safety import SafetyAssessment, SafetySeverity
from sesame_ai_robot.tracking import TrackingDecision, TrackingState


def ok_safety():
    return SafetyAssessment(SafetySeverity.OK, None, "ok")


class BehaviorArbiterTest(unittest.TestCase):
    def test_active_emergency_stop_blocks_all_actions(self):
        plan = BehaviorArbiter().decide(ArbiterInput(
            robot_status={"emergencyStopActive": True},
            safety=ok_safety(),
            advanced=(AdvancedDecision(AdvancedFeature.SELF_RIGHTING, "fallen", "stand", "mock self-righting"),),
            tracking=TrackingDecision(TrackingState.FOLLOWING, "walk_forward", "tracking"),
        ))

        self.assertIsNone(plan.command)
        self.assertIn("stand", plan.blocked_actions)
        self.assertIn("walk_forward", plan.blocked_actions)

    def test_safety_emergency_stop_overrides_tracking(self):
        plan = BehaviorArbiter().decide(ArbiterInput(
            robot_status={"emergencyStopActive": False},
            safety=SafetyAssessment(SafetySeverity.EMERGENCY_STOP, "emergency_stop", "fall detected"),
            tracking=TrackingDecision(TrackingState.FOLLOWING, "walk_forward", "tracking"),
        ))

        self.assertEqual(plan.command, "emergency_stop")
        self.assertEqual(plan.source, "safety")
        self.assertIn("walk_forward", plan.blocked_actions)

    def test_safety_stop_overrides_assistant_motion(self):
        assistant = AssistantPlan("go", (
            AssistantStep(AssistantAction.ROBOT_COMMAND, "walk_forward", "user requested movement"),
        ))

        plan = BehaviorArbiter().decide(ArbiterInput(
            robot_status={"emergencyStopActive": False},
            safety=SafetyAssessment(SafetySeverity.STOP, "stop", "front obstacle is too close"),
            assistant=assistant,
        ))

        self.assertEqual(plan.command, "stop")
        self.assertIn("walk_forward", plan.blocked_actions)

    def test_real_robot_advanced_action_requires_confirmation(self):
        plan = BehaviorArbiter().decide(ArbiterInput(
            robot_status={"emergencyStopActive": False},
            safety=ok_safety(),
            runtime_mode=RuntimeMode.REAL_ROBOT,
            advanced=(AdvancedDecision(
                AdvancedFeature.SELF_RIGHTING,
                "fallen",
                None,
                "real robot self-righting requires explicit user confirmation",
                requires_user_confirmation=True,
            ),),
        ))

        self.assertIsNone(plan.command)
        self.assertTrue(plan.requires_user_confirmation)

    def test_tracking_wins_before_assistant_motion(self):
        assistant = AssistantPlan("go", (
            AssistantStep(AssistantAction.ROBOT_COMMAND, "walk_forward", "assistant movement"),
        ))

        plan = BehaviorArbiter().decide(ArbiterInput(
            robot_status={"emergencyStopActive": False},
            safety=ok_safety(),
            tracking=TrackingDecision(TrackingState.FOLLOWING, "turn_left", "target is left"),
            assistant=assistant,
        ))

        self.assertEqual(plan.command, "turn_left")
        self.assertEqual(plan.source, "tracking")

    def test_unknown_assistant_command_is_rejected_before_client(self):
        assistant = AssistantPlan("fly", (
            AssistantStep(AssistantAction.ROBOT_COMMAND, "fly", "assistant hallucinated command"),
        ))

        plan = BehaviorArbiter().decide(ArbiterInput(
            robot_status={"emergencyStopActive": False},
            safety=ok_safety(),
            assistant=assistant,
        ))

        self.assertIsNone(plan.command)
        self.assertEqual(plan.source, "arbiter")
        self.assertEqual(plan.blocked_actions, ("fly",))

    def test_assistant_face_and_speech_without_motion(self):
        assistant = AssistantPlan("happy", (
            AssistantStep(AssistantAction.SET_FACE, "happy", "expression"),
            AssistantStep(AssistantAction.SAY, "I changed the face.", "confirm"),
        ))

        plan = BehaviorArbiter().decide(ArbiterInput(
            robot_status={"emergencyStopActive": False},
            safety=ok_safety(),
            assistant=assistant,
        ))

        self.assertIsNone(plan.command)
        self.assertEqual(plan.face, "happy")
        self.assertEqual(plan.speech, "I changed the face.")


if __name__ == "__main__":
    unittest.main()
