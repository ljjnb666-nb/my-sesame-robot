import unittest

from sesame_ai_robot.assistant import AssistantAction, AssistantPolicy, MockAssistantPipeline


class AssistantPipelineTest(unittest.TestCase):
    def test_ignores_text_without_wake_word(self):
        plan = MockAssistantPipeline().handle_text("hello")

        self.assertEqual(plan.transcript, "")
        self.assertEqual(plan.steps, ())

    def test_emergency_stop_is_always_allowed(self):
        plan = MockAssistantPipeline().handle_text("sesame emergency stop")

        self.assertEqual(plan.steps[0].action, AssistantAction.ROBOT_COMMAND)
        self.assertEqual(plan.steps[0].value, "emergency_stop")

    def test_expression_request_sets_face(self):
        plan = MockAssistantPipeline().handle_text("sesame happy face")

        self.assertEqual(plan.steps[0].action, AssistantAction.SET_FACE)
        self.assertEqual(plan.steps[0].value, "happy")

    def test_expressive_action_is_allowed(self):
        plan = MockAssistantPipeline().handle_text("sesame wave")

        self.assertEqual(plan.steps[0].action, AssistantAction.ROBOT_COMMAND)
        self.assertEqual(plan.steps[0].value, "wave")

    def test_motion_is_blocked_by_default(self):
        plan = MockAssistantPipeline().handle_text("sesame follow me")

        self.assertEqual(plan.steps[0].action, AssistantAction.DENY)
        self.assertEqual(plan.steps[0].value, "walk_forward")

    def test_motion_can_be_enabled_for_simulation(self):
        pipeline = MockAssistantPipeline(policy=AssistantPolicy(allow_motion_commands=True))
        plan = pipeline.handle_text("sesame follow me")

        self.assertEqual(plan.steps[0].action, AssistantAction.ROBOT_COMMAND)
        self.assertEqual(plan.steps[0].value, "walk_forward")


if __name__ == "__main__":
    unittest.main()
