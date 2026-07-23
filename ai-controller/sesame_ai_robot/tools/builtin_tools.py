from __future__ import annotations

from .models import ToolSpec
from .registry import ToolRegistry


READ_ONLY_TOOLS = (
    "get_battery_status",
    "get_robot_state",
    "get_pose",
    "get_communication_status",
    "get_actuator_status",
    "get_fault_status",
    "get_timeline",
    "get_charging_status",
)
ACTION_TOOLS = ("execute_action",)
BUILTIN_TOOL_NAMES = READ_ONLY_TOOLS + ACTION_TOOLS


def create_builtin_registry() -> ToolRegistry:
    registry = ToolRegistry()
    for name in READ_ONLY_TOOLS:
        registry.register(ToolSpec(
            name=name,
            description=f"Read-only robot tool: {name}",
            input_schema=_schema_for(name),
            category="query",
            read_only=True,
            version="1",
        ))
    registry.register(ToolSpec(
        name="execute_action",
        description="Execute an existing robot action through RobotRuntime safety arbitration.",
        input_schema={
            "type": "object",
            "properties": {"action": {"type": "string"}},
            "required": ["action"],
            "additionalProperties": False,
        },
        category="action",
        read_only=False,
        version="1",
    ))
    registry.freeze()
    return registry


def _schema_for(name: str) -> dict[str, object]:
    if name == "get_timeline":
        return {
            "type": "object",
            "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 50}},
            "required": [],
            "additionalProperties": False,
        }
    return {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    }
