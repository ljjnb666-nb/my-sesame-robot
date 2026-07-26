import unittest

from sesame_ai_robot.ai_models import AIErrorCode
from sesame_ai_robot.arbiter import RobotActionPlan
from sesame_ai_robot.ai_interaction import ALLOWED_COMMANDS
from sesame_ai_robot.confirmation import ConfirmationRequest, ConfirmationStore
from sesame_ai_robot.robot_actions import SUPPORTED_ROBOT_ACTIONS
from sesame_ai_robot.runtime import RobotRuntime, RobotRuntimeConfig, RuntimeStepResult
from sesame_ai_robot.tools import RobotReadOnlyFacade, ToolCall, ToolExecutor, create_builtin_registry
from sesame_ai_robot.virtual_hardware import SimulatorHardwareAdapter, VirtualHardwareRobotClient


def call(tool_name, arguments=None):
    return {"call_id": "c1", "tool_name": tool_name, "arguments": arguments or {}}


class ToolExecutorTest(unittest.TestCase):
    def setUp(self):
        self.hardware = SimulatorHardwareAdapter()
        self.client = VirtualHardwareRobotClient(self.hardware)
        self.store = ConfirmationStore()
        self.runtime = RobotRuntime(self.client, RobotRuntimeConfig(dry_run=False), confirmation_store=self.store)
        self.executor = ToolExecutor(
            registry=create_builtin_registry(),
            read_only=RobotReadOnlyFacade(client=self.client, hardware=self.hardware),
            runtime=self.runtime,
        )

    def test_wave_executes(self):
        result = self.executor.execute(call("execute_action", {"action": "wave"}))
        self.assertEqual(result.status, "ok")
        self.assertEqual(self.client.current_command, "wave")

    def test_stop_executes(self):
        self.executor.execute(call("execute_action", {"action": "wave"}))
        result = self.executor.execute(call("execute_action", {"action": "stop"}))
        self.assertEqual(result.status, "ok")
        self.assertEqual(self.client.current_command, "")

    def test_emergency_stop_executes_current_semantics(self):
        result = self.executor.execute(call("execute_action", {"action": "emergency_stop"}))
        self.assertEqual(result.status, "ok")
        self.assertTrue(self.hardware.state.emergency_stop)

    def test_walk_forward_requires_confirmation(self):
        result = self.executor.execute(call("execute_action", {"action": "walk_forward"}))
        self.assertEqual(result.status, "confirmation_required")
        self.assertTrue(result.result["confirmation_id"])

    def test_correct_confirmation_executes(self):
        requested = self.executor.execute(call("execute_action", {"action": "walk_forward"}))
        accepted = self.executor.execute(call("execute_action", {"action": "walk_forward"}), confirmation_id=requested.result["confirmation_id"])
        self.assertEqual(accepted.status, "ok")
        self.assertEqual(self.hardware.state.motors[0].direction, "forward")

    def test_replay_rejected(self):
        requested = self.executor.execute(call("execute_action", {"action": "walk_forward"}))
        self.executor.execute(call("execute_action", {"action": "walk_forward"}), confirmation_id=requested.result["confirmation_id"])
        replay = self.executor.execute(call("execute_action", {"action": "walk_forward"}), confirmation_id=requested.result["confirmation_id"])
        self.assertEqual(replay.error_code, "already_used")

    def test_wrong_action_rejected(self):
        requested = self.executor.execute(call("execute_action", {"action": "walk_forward"}))
        wrong = self.executor.execute(call("execute_action", {"action": "stand"}), confirmation_id=requested.result["confirmation_id"])
        self.assertEqual(wrong.error_code, "action_mismatch")

    def test_extra_parameters_rejected(self):
        result = self.executor.execute(call("execute_action", {"action": "walk_forward", "parameters": {}}))
        self.assertEqual(result.error_code, "invalid_arguments")

    def test_context_changed_rejected(self):
        requested = self.executor.execute(call("execute_action", {"action": "walk_forward"}))
        self.hardware.state.battery_percent = 79
        changed = self.executor.execute(call("execute_action", {"action": "walk_forward"}), confirmation_id=requested.result["confirmation_id"])
        self.assertEqual(changed.error_code, "context_changed")

    def test_expired_rejected(self):
        clock = {"now": 10.0}
        store = ConfirmationStore(ttl_seconds=1, _clock=lambda: clock["now"])
        runtime = RobotRuntime(self.client, RobotRuntimeConfig(dry_run=False), confirmation_store=store)
        executor = ToolExecutor(registry=create_builtin_registry(), read_only=RobotReadOnlyFacade(client=self.client, hardware=self.hardware), runtime=runtime)
        requested = executor.execute(call("execute_action", {"action": "walk_forward"}))
        clock["now"] = 11.0
        expired = executor.execute(call("execute_action", {"action": "walk_forward"}), confirmation_id=requested.result["confirmation_id"])
        self.assertEqual(expired.error_code, "expired")

    def test_runtime_restart_unknown_id(self):
        requested = self.executor.execute(call("execute_action", {"action": "walk_forward"}))
        new_runtime = RobotRuntime(self.client, RobotRuntimeConfig(dry_run=False))
        executor = ToolExecutor(registry=create_builtin_registry(), read_only=RobotReadOnlyFacade(client=self.client, hardware=self.hardware), runtime=new_runtime)
        result = executor.execute(call("execute_action", {"action": "walk_forward"}), confirmation_id=requested.result["confirmation_id"])
        self.assertEqual(result.error_code, "unknown_id")

    def test_executor_does_not_hold_direct_hardware_or_client(self):
        self.assertFalse(hasattr(self.executor, "hardware"))
        self.assertFalse(hasattr(self.executor, "client"))

    def test_tool_call_object_valid_query_executes(self):
        result = self.executor.execute(ToolCall("c1", "get_battery_status", {}))
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.result["percent"], 80)

    def test_tool_call_object_extra_action_argument_rejected(self):
        result = self.executor.execute(ToolCall("c1", "execute_action", {"action": "wave", "extra": True}))
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error_code, "invalid_arguments")

    def test_tool_call_object_invalid_timeline_limit_rejected(self):
        result = self.executor.execute(ToolCall("c1", "get_timeline", {"limit": 51}))
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error_code, "invalid_arguments")

    def test_tool_call_object_overlong_call_id_rejected_before_execution(self):
        with self.assertRaises(Exception):
            ToolCall("x" * 129, "get_robot_state", {})

    def test_tool_call_object_overlong_tool_name_rejected_before_execution(self):
        with self.assertRaises(Exception):
            ToolCall("c1", "x" * 65, {})

    def test_tool_call_object_nested_confirmation_id_rejected(self):
        result = self.executor.execute(ToolCall("c1", "get_timeline", {"limit": 1, "nested": {"confirmation_id": "x"}}))
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error_code, "invalid_tool_call_schema")

    def test_tool_call_validation_rechecks_mutated_jsonable_payload(self):
        call_obj = ToolCall("c1", "get_timeline", {"limit": 1})
        payload = call_obj.to_jsonable()
        payload["arguments"]["limit"] = 100
        result = self.executor.execute(payload)
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error_code, "invalid_arguments")

    def test_tool_call_object_and_dict_paths_return_same_error_code(self):
        dict_result = self.executor.execute(call("get_timeline", {"limit": 0}))
        object_result = self.executor.execute(ToolCall("c1", "get_timeline", {"limit": 0}))
        self.assertEqual(dict_result.error_code, "invalid_arguments")
        self.assertEqual(object_result.error_code, dict_result.error_code)

    def test_supported_robot_actions_are_canonical(self):
        execute_schema = create_builtin_registry().get("execute_action").to_jsonable()["input_schema"]
        self.assertEqual(ALLOWED_COMMANDS, SUPPORTED_ROBOT_ACTIONS)
        self.assertEqual(set(execute_schema["properties"]["action"]["enum"]), SUPPORTED_ROBOT_ACTIONS)

    def test_execute_action_calls_runtime_once_with_assistant_plan(self):
        fake_runtime = FakeRuntime(RuntimeStepResult(
            {"motionState": "idle"},
            RobotActionPlan("wave", None, None, "assistant", "fake allowed"),
            True,
            False,
            confirmation_state="none",
        ))
        executor = ToolExecutor(
            registry=create_builtin_registry(),
            read_only=RobotReadOnlyFacade(client=self.client, hardware=self.hardware),
            runtime=fake_runtime,
        )
        result = executor.execute(call("execute_action", {"action": "wave"}))
        self.assertEqual(result.status, "ok")
        self.assertEqual(fake_runtime.step_calls, 1)
        self.assertEqual(fake_runtime.assistant.steps[0].value, "wave")
        self.assertEqual(fake_runtime.assistant.steps[0].reason, "AI structured intent")
        self.assertIsNone(fake_runtime.confirmation_id)

    def test_action_result_size_does_not_turn_success_into_failure(self):
        fake_runtime = FakeRuntime(RuntimeStepResult(
            {"motionState": "idle"},
            RobotActionPlan("wave", None, None, "assistant", "x" * 10000),
            True,
            False,
            confirmation_state="none",
        ))
        executor = ToolExecutor(
            registry=create_builtin_registry(),
            read_only=RobotReadOnlyFacade(client=self.client, hardware=self.hardware),
            runtime=fake_runtime,
        )
        result = executor.execute(call("execute_action", {"action": "wave"}))
        self.assertEqual(result.status, "ok")
        self.assertTrue(result.result["runtime"]["executed"]["commandSent"])
        self.assertNotEqual(result.error_code, "tool_result_too_large")

    def test_confirmation_required_keeps_confirmation_id_when_reason_is_huge(self):
        confirmation_request = ConfirmationRequest("confirm123", "walk_forward", "reason", 1.0, 2.0, "ctx")
        fake_runtime = FakeRuntime(RuntimeStepResult(
            {"motionState": "idle"},
            RobotActionPlan(
                None,
                None,
                None,
                "assistant",
                "x" * 10000,
                requires_user_confirmation=True,
                confirmation_request=confirmation_request,
            ),
            False,
            False,
            confirmation_state="requested",
        ))
        executor = ToolExecutor(
            registry=create_builtin_registry(),
            read_only=RobotReadOnlyFacade(client=self.client, hardware=self.hardware),
            runtime=fake_runtime,
        )
        result = executor.execute(call("execute_action", {"action": "walk_forward"}))
        self.assertEqual(result.status, "confirmation_required")
        self.assertEqual(result.result["confirmation_id"], "confirm123")
        self.assertNotEqual(result.error_code, "tool_result_too_large")

    def test_runtime_rejection_preserves_runtime_error_code(self):
        fake_runtime = FakeRuntime(RuntimeStepResult(
            {"motionState": "idle"},
            RobotActionPlan(None, None, None, "runtime", "already used"),
            False,
            False,
            confirmation_state="already_used",
            confirmation_error="already_used",
        ))
        executor = ToolExecutor(
            registry=create_builtin_registry(),
            read_only=RobotReadOnlyFacade(client=self.client, hardware=self.hardware),
            runtime=fake_runtime,
        )
        result = executor.execute(call("execute_action", {"action": "walk_forward"}))
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error_code, "already_used")


class FakeRuntime:
    def __init__(self, result):
        self.result = result
        self.config = RobotRuntimeConfig(dry_run=False)
        self.step_calls = 0
        self.assistant = None
        self.confirmation_id = None

    def step(self, *, assistant=None, confirmation_id=None):
        self.step_calls += 1
        self.assistant = assistant
        self.confirmation_id = confirmation_id
        return self.result


if __name__ == "__main__":
    unittest.main()
