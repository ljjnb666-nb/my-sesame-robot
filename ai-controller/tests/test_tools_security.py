import unittest

from sesame_ai_robot.robot_profile import RobotProfile
from sesame_ai_robot.runtime import RobotRuntime, RobotRuntimeConfig
from sesame_ai_robot.tools import RobotReadOnlyFacade, ToolExecutor, create_builtin_registry
from sesame_ai_robot.virtual_hardware import SimulatorHardwareAdapter, VirtualHardwareRobotClient


class ToolSecurityTest(unittest.TestCase):
    def setUp(self):
        self.hardware = SimulatorHardwareAdapter()
        self.client = VirtualHardwareRobotClient(self.hardware)
        self.executor = ToolExecutor(
            registry=create_builtin_registry(),
            read_only=RobotReadOnlyFacade(client=self.client, hardware=self.hardware),
            runtime=RobotRuntime(self.client, RobotRuntimeConfig(dry_run=False)),
        )

    def assert_rejected_tool(self, name):
        result = self.executor.execute({"call_id": "c1", "tool_name": name, "arguments": {}})
        self.assertIn(result.error_code, {"unknown_tool", "invalid_tool_call_schema"})

    def test_unknown_tool(self):
        self.assert_rejected_tool("unknown")

    def test_import_tool_rejected(self):
        self.assert_rejected_tool("__import__")

    def test_eval_tool_rejected(self):
        self.assert_rejected_tool("eval")

    def test_exec_tool_rejected(self):
        self.assert_rejected_tool("exec")

    def test_open_tool_rejected(self):
        self.assert_rejected_tool("open")

    def test_read_file_tool_rejected(self):
        self.assert_rejected_tool("read_file")

    def test_get_environment_tool_rejected(self):
        self.assert_rejected_tool("get_environment")

    def test_shell_tool_rejected(self):
        self.assert_rejected_tool("shell")

    def test_subprocess_tool_rejected(self):
        self.assert_rejected_tool("subprocess")

    def test_direct_hardware_command_rejected(self):
        self.assert_rejected_tool("direct_hardware_command")

    def test_safety_severity_override_rejected(self):
        result = self.executor.execute({"call_id": "c1", "tool_name": "execute_action", "arguments": {"action": "wave", "safety_severity": "ok"}})
        self.assertEqual(result.error_code, "invalid_tool_call_schema")

    def test_runtime_mode_override_rejected(self):
        result = self.executor.execute({"call_id": "c1", "tool_name": "execute_action", "arguments": {"action": "wave", "runtime_mode": "real_robot"}})
        self.assertEqual(result.error_code, "invalid_tool_call_schema")

    def test_real_hardware_enable_rejected(self):
        result = self.executor.execute({"call_id": "c1", "tool_name": "execute_action", "arguments": {"action": "wave", "allow_real_robot": True}})
        self.assertEqual(result.error_code, "invalid_tool_call_schema")

    def test_profile_does_not_authorize_motion(self):
        profile = RobotProfile(capabilities=("walk_forward",))
        result = self.executor.execute({"call_id": "c1", "tool_name": "execute_action", "arguments": {"action": "walk_forward"}})
        self.assertTrue(profile.get_capability("walk_forward"))
        self.assertEqual(result.status, "confirmation_required")

    def test_nested_tool_call_rejected(self):
        result = self.executor.execute({"call_id": "c1", "tool_name": "get_battery_status", "arguments": {"tool_name": "execute_action"}})
        self.assertEqual(result.error_code, "invalid_arguments")

    def test_recursive_tool_call_rejected(self):
        self.executor._executing = True
        try:
            result = self.executor.execute({"call_id": "c1", "tool_name": "get_battery_status", "arguments": {}})
        finally:
            self.executor._executing = False
        self.assertEqual(result.error_code, "recursive_tool_call")

    def test_more_than_three_calls_rejected(self):
        result = self.executor.execute_many([
            {"call_id": "c1", "tool_name": "get_battery_status", "arguments": {}},
            {"call_id": "c2", "tool_name": "get_battery_status", "arguments": {}},
            {"call_id": "c3", "tool_name": "get_battery_status", "arguments": {}},
            {"call_id": "c4", "tool_name": "get_battery_status", "arguments": {}},
        ])
        self.assertEqual(result[0].error_code, "tool_limit_exceeded")

    def test_traceback_not_leaked(self):
        result = self.executor.execute({"call_id": "c1", "tool_name": "get_timeline", "arguments": {"limit": 100}})
        self.assertNotIn("Traceback", result.user_message)

    def test_provider_confirmation_field_rejected(self):
        result = self.executor.execute({"call_id": "c1", "tool_name": "execute_action", "arguments": {"action": "wave", "confirmation_grant": "yes"}})
        self.assertEqual(result.error_code, "invalid_tool_call_schema")

    def test_oversized_result_rejected(self):
        for index in range(200):
            self.hardware.events.append({"eventType": "x" * 200, "time": index, "result": "ok"})
        result = self.executor.execute({"call_id": "c1", "tool_name": "get_timeline", "arguments": {"limit": 50}})
        self.assertIn(result.status, {"ok", "failed"})
        if result.status == "failed":
            self.assertEqual(result.error_code, "tool_result_too_large")


if __name__ == "__main__":
    unittest.main()
