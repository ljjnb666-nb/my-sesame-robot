import math
import unittest
from dataclasses import FrozenInstanceError
from types import MappingProxyType

from sesame_ai_robot.tools import ToolCall, ToolResult, ToolSpec, create_builtin_registry
from sesame_ai_robot.tools.errors import ToolError, ToolErrorCode
from sesame_ai_robot.tools.schemas import validate_tool_call


class ToolModelsSchemaTest(unittest.TestCase):
    def setUp(self):
        self.registry = create_builtin_registry()

    def test_valid_tool_call(self):
        call = validate_tool_call({"call_id": "c1", "tool_name": "get_battery_status", "arguments": {}}, self.registry)
        self.assertEqual(call.tool_name, "get_battery_status")

    def test_missing_call_id_rejected(self):
        with self.assertRaises(ToolError):
            validate_tool_call({"tool_name": "get_battery_status", "arguments": {}}, self.registry)

    def test_missing_tool_name_rejected(self):
        with self.assertRaises(ToolError):
            validate_tool_call({"call_id": "c1", "arguments": {}}, self.registry)

    def test_missing_arguments_rejected(self):
        with self.assertRaises(ToolError):
            validate_tool_call({"call_id": "c1", "tool_name": "get_battery_status"}, self.registry)

    def test_extra_top_level_field_rejected(self):
        with self.assertRaises(ToolError):
            validate_tool_call({"call_id": "c1", "tool_name": "get_battery_status", "arguments": {}, "x": 1}, self.registry)

    def test_arguments_must_be_object(self):
        with self.assertRaises(ToolError):
            validate_tool_call({"call_id": "c1", "tool_name": "get_battery_status", "arguments": []}, self.registry)

    def test_tool_name_too_long_rejected(self):
        with self.assertRaises(ToolError):
            validate_tool_call({"call_id": "c1", "tool_name": "x" * 65, "arguments": {}}, self.registry)

    def test_string_too_long_rejected(self):
        with self.assertRaises(ToolError):
            validate_tool_call({"call_id": "c1", "tool_name": "execute_action", "arguments": {"action": "x" * 501}}, self.registry)

    def test_list_too_long_rejected(self):
        with self.assertRaises(ToolError):
            validate_tool_call({"call_id": "c1", "tool_name": "get_battery_status", "arguments": {"items": list(range(51))}}, self.registry)

    def test_nesting_too_deep_rejected(self):
        payload = {"call_id": "c1", "tool_name": "get_battery_status", "arguments": {"a": {"b": {"c": {"d": {"e": {"f": 1}}}}}}}
        with self.assertRaises(ToolError):
            validate_tool_call(payload, self.registry)

    def test_non_json_type_rejected(self):
        with self.assertRaises(ToolError):
            ToolCall("c1", "get_battery_status", {"bad": object()})

    def test_bool_is_not_integer(self):
        with self.assertRaises(ToolError):
            validate_tool_call({"call_id": "c1", "tool_name": "get_timeline", "arguments": {"limit": True}}, self.registry)

    def test_nan_and_infinity_rejected(self):
        for value in (math.nan, math.inf):
            with self.subTest(value=value):
                with self.assertRaises(ToolError):
                    validate_tool_call({"call_id": "c1", "tool_name": "get_timeline", "arguments": {"limit": value}}, self.registry)

    def test_forbidden_authority_field_rejected(self):
        with self.assertRaises(ToolError):
            validate_tool_call({"call_id": "c1", "tool_name": "execute_action", "arguments": {"action": "wave", "confirmation_id": "fake"}}, self.registry)

    def test_tool_spec_is_immutable(self):
        spec = ToolSpec("x", "desc", {"type": "object", "properties": {}, "required": []}, "query", True)
        with self.assertRaises(FrozenInstanceError):
            spec.name = "y"
        with self.assertRaises(TypeError):
            spec.input_schema["type"] = "array"

    def test_tool_call_arguments_are_deep_immutable(self):
        call = ToolCall("c1", "get_timeline", {"limit": 5, "nested": {"x": 1}, "items": [1]})
        self.assertIsInstance(call.arguments, MappingProxyType)
        with self.assertRaises(TypeError):
            call.arguments["limit"] = 10
        with self.assertRaises(TypeError):
            call.arguments["nested"]["x"] = 2
        with self.assertRaises(AttributeError):
            call.arguments["items"].append(2)

    def test_tool_call_to_jsonable_is_detached(self):
        call = ToolCall("c1", "get_timeline", {"limit": 5, "nested": {"x": 1}})
        payload = call.to_jsonable()
        payload["arguments"]["nested"]["x"] = 9
        self.assertEqual(call.arguments["nested"]["x"], 1)
        self.assertIsInstance(payload["arguments"], dict)

    def test_tool_result_status_allowlist(self):
        with self.assertRaises(ToolError):
            ToolResult("c1", "get_robot_state", "running", {}, None, "")

    def test_tool_result_failed_requires_error_code(self):
        with self.assertRaises(ToolError):
            ToolResult("c1", "get_robot_state", "failed", None, None, "")

    def test_tool_result_ok_rejects_error_code(self):
        with self.assertRaises(ToolError):
            ToolResult("c1", "get_robot_state", "ok", {}, "invalid_arguments", "")

    def test_tool_result_confirmation_requires_confirmation_id(self):
        with self.assertRaises(ToolError):
            ToolResult("c1", "execute_action", "confirmation_required", {"action": "walk_forward"}, "confirmation_required", "")

    def test_tool_result_user_message_is_bounded(self):
        with self.assertRaises(ToolError):
            ToolResult("c1", "get_robot_state", "ok", {}, None, "x" * 501)


if __name__ == "__main__":
    unittest.main()
