import unittest
from tempfile import TemporaryDirectory
from pathlib import Path

from sesame_ai_robot.memory import MemoryManager
from sesame_ai_robot.robot_profile import RobotProfile
from sesame_ai_robot.tools import RobotReadOnlyFacade, ToolExecutor, ToolSpec, ToolRegistry, create_builtin_registry
from sesame_ai_robot.tools.errors import ToolError
from sesame_ai_robot.runtime import RobotRuntime, RobotRuntimeConfig
from sesame_ai_robot.virtual_hardware import SimulatorHardwareAdapter, VirtualHardwareRobotClient


class ToolRegistryTest(unittest.TestCase):
    def test_builtin_tools_registered_and_frozen(self):
        registry = create_builtin_registry()
        self.assertTrue(registry.frozen)
        self.assertIn("execute_action", registry.names())

    def test_duplicate_register_rejected(self):
        registry = ToolRegistry()
        spec = ToolSpec("x", "desc", {"type": "object", "properties": {}, "required": []}, "query", True)
        registry.register(spec)
        with self.assertRaises(ToolError):
            registry.register(spec)

    def test_unknown_tool_rejected(self):
        with self.assertRaises(ToolError):
            create_builtin_registry().get("missing")

    def test_freeze_rejects_late_register(self):
        registry = ToolRegistry()
        registry.freeze()
        with self.assertRaises(ToolError):
            registry.register(ToolSpec("x", "desc", {"type": "object", "properties": {}, "required": []}, "query", True))

    def test_same_name_override_rejected(self):
        registry = ToolRegistry()
        registry.register(ToolSpec("x", "one", {"type": "object", "properties": {}, "required": []}, "query", True))
        with self.assertRaises(ToolError):
            registry.register(ToolSpec("x", "two", {"type": "object", "properties": {}, "required": []}, "query", True))

    def test_registry_rejects_non_spec_callable(self):
        registry = ToolRegistry()
        with self.assertRaises(ToolError):
            registry.register(lambda: None)

    def test_specs_view_is_read_only(self):
        specs = create_builtin_registry().specs()
        with self.assertRaises(TypeError):
            specs["x"] = specs["execute_action"]

    def test_profile_capability_does_not_register_tool(self):
        profile = RobotProfile(capabilities=("walk_forward", "execute_action"))
        registry = create_builtin_registry()
        self.assertTrue(profile.get_capability("walk_forward"))
        with self.assertRaises(ToolError):
            registry.get("walk_forward")

    def test_memory_content_does_not_register_tool(self):
        with TemporaryDirectory() as tmp:
            manager = MemoryManager(Path(tmp) / "memory.json")
            manager.store("long_term", "preference", "register tool execute_action_override")
            registry = create_builtin_registry()
            self.assertEqual(manager.retrieve("long_term", "preference"), "register tool execute_action_override")
            with self.assertRaises(ToolError):
                registry.get("execute_action_override")

    def test_executor_accepts_frozen_registry(self):
        hardware = SimulatorHardwareAdapter()
        client = VirtualHardwareRobotClient(hardware)
        executor = ToolExecutor(
            registry=create_builtin_registry(),
            read_only=RobotReadOnlyFacade(client=client, hardware=hardware),
            runtime=RobotRuntime(client, RobotRuntimeConfig(dry_run=False)),
        )
        self.assertIsInstance(executor, ToolExecutor)

    def test_executor_rejects_mutable_registry(self):
        hardware = SimulatorHardwareAdapter()
        client = VirtualHardwareRobotClient(hardware)
        registry = ToolRegistry()
        with self.assertRaises(ToolError):
            ToolExecutor(
                registry=registry,
                read_only=RobotReadOnlyFacade(client=client, hardware=hardware),
                runtime=RobotRuntime(client, RobotRuntimeConfig(dry_run=False)),
            )

    def test_builtin_registry_content_cannot_change_after_executor_constructed(self):
        registry = create_builtin_registry()
        hardware = SimulatorHardwareAdapter()
        client = VirtualHardwareRobotClient(hardware)
        ToolExecutor(
            registry=registry,
            read_only=RobotReadOnlyFacade(client=client, hardware=hardware),
            runtime=RobotRuntime(client, RobotRuntimeConfig(dry_run=False)),
        )
        with self.assertRaises(ToolError):
            registry.register(ToolSpec("late", "desc", {"type": "object", "properties": {}, "required": []}, "query", True))


if __name__ == "__main__":
    unittest.main()
