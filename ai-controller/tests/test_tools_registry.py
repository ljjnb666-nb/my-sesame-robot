import unittest

from sesame_ai_robot.robot_profile import RobotProfile
from sesame_ai_robot.tools import ToolSpec, ToolRegistry, create_builtin_registry
from sesame_ai_robot.tools.errors import ToolError


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


if __name__ == "__main__":
    unittest.main()
