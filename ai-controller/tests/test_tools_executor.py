import unittest

from sesame_ai_robot.confirmation import ConfirmationStore
from sesame_ai_robot.runtime import RobotRuntime, RobotRuntimeConfig
from sesame_ai_robot.tools import RobotReadOnlyFacade, ToolExecutor, create_builtin_registry
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
        self.hardware.inject_fault("communication_lost")
        changed = self.executor.execute(call("execute_action", {"action": "walk_forward"}), confirmation_id=requested.result["confirmation_id"])
        self.assertIn(changed.error_code, {"context_changed", "action_mismatch"})

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


if __name__ == "__main__":
    unittest.main()
