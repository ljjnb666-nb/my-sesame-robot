# Tool Calling Framework v0.3

## Architecture

Tool calling is an internal execution boundary. Providers still return the existing `RobotIntent` schema. `AIInteractionLoop` maps validated `RobotIntent` actions to internal `ToolCall` payloads, validates them again against the frozen `ToolRegistry`, and executes them through `ToolExecutor`.

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

The supported robot action allowlist is canonicalized in `sesame_ai_robot.robot_actions.SUPPORTED_ROBOT_ACTIONS` and is shared by AI `ActionPlan` validation and the `execute_action` tool schema. This PR does not add, remove, or redefine robot actions.

## Safety Boundary

The registry is statically populated, frozen after setup, and does not load tools from Memory, Robot Profile, YAML, JSON, environment variables, plugins, Python paths, network sources, or provider output. Dynamic code execution and reflection-based tool dispatch are not part of this framework.

`ToolExecutor` requires a frozen registry at construction time. It does not auto-freeze mutable registries, register tools from configuration, or accept late tool mutation.

`ToolExecutor` does not hold direct hardware or client handles. Read-only operations use `RobotReadOnlyFacade`; action operations construct an `AssistantPlan` and call `RobotRuntime.step()`.

All inputs are revalidated at execution time. Passing an already constructed `ToolCall` object does not bypass schema validation; the executor converts it back to JSON and runs the same validation path used for dict payloads.

`ToolCall.arguments` is deeply immutable after construction. Nested dicts are converted to read-only mappings, lists are converted to tuples, and `to_jsonable()` returns a detached plain JSON structure.

Action results use a bounded Runtime summary. Result size enforcement must not rewrite a completed Runtime action or confirmation request into an unrelated `tool_result_too_large` failure. Query tools remain side-effect free and may return a bounded or truncated read result.

Unknown `query_status` mappings fail closed. There is no legacy `_query_status` fallback path; query execution goes through `ToolExecutor -> RobotReadOnlyFacade`.

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
- Tool result statuses: `ok`, `failed`, `confirmation_required`
