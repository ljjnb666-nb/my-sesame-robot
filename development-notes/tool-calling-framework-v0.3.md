# Tool Calling Framework v0.3

## Architecture

Tool calling is an internal execution boundary. Providers still return the existing `RobotIntent` schema. `AIInteractionLoop` maps validated `RobotIntent` actions to internal `ToolCall` objects, validates them again against the frozen `ToolRegistry`, and executes them through `ToolExecutor`.

Action flow:

`RobotIntent -> ToolCall(execute_action) -> ToolExecutor -> RobotRuntime.step() -> BehaviorArbiter -> ConfirmationStore -> VirtualHardwareRobotClient`

Query flow:

`RobotIntent -> ToolCall(read-only tool) -> ToolExecutor -> RobotReadOnlyFacade`

## Built-in Tools

Read-only tools:

- `get_battery_status`
- `get_robot_state`
- `get_pose`
- `get_communication_status`
- `get_actuator_status`
- `get_fault_status`
- `get_timeline`
- `get_charging_status`

Action tool:

- `execute_action`

`execute_action` only adapts existing robot actions into the existing Runtime safety chain. It does not directly command hardware.

## Safety Boundary

The registry is statically populated, frozen after setup, and does not load tools from Memory, Robot Profile, YAML, JSON, environment variables, plugins, Python paths, network sources, or provider output. Dynamic code execution and reflection-based tool dispatch are not part of this framework.

`ToolExecutor` does not hold direct hardware or client handles. Read-only operations use `RobotReadOnlyFacade`; action operations construct an `AssistantPlan` and call `RobotRuntime.step()`.

Confirmation semantics remain owned by `RobotRuntime` and `ConfirmationStore`. Tool calls cannot create grants, consume confirmations directly, or treat `call_id` as authorization.

Memory remains `UNTRUSTED_CONTEXT`. Robot Profile capabilities are descriptive only and do not authorize tools or actions.

## Limits

- Max tool calls per user request: 3
- No parallel tool execution
- No recursive tool execution
- No tool-calls-tool behavior
- No repeat, while, wait, background tasks, timers, or autonomous task planning
- Tool result limit: 4096 bytes
- Timeline default limit: 20 entries
- Timeline hard limit: 50 entries
