# AI Interaction Architecture

Sesame Robot now has a software-only AI interaction loop V0:

```text
user natural language
-> AIRequest
-> AIProvider
-> RobotIntent schema validator
-> ActionPlan validator
-> RobotRuntime
-> BehaviorArbiter
-> Runtime confirmation gate
-> VirtualHardwareRobotClient
-> simulator feedback
```

The AI provider only proposes structured intent. It cannot dispatch commands, create confirmation grants, lower safety severity, switch runtime mode, or access a hardware adapter.

## Components

- `AIProvider`: protocol implemented by `DeterministicMockProvider` and optional `OpenAICompatibleProvider`.
- `RobotIntent`: strict JSON contract parsed into dataclasses.
- `validate_ai_response`: rejects unknown fields, forbidden authority fields, invalid numbers, oversized strings, excessive nesting, unknown actions, and too many actions.
- `validate_plan`: checks action names, argument types, and V0 action limits.
- `AIInteractionLoop`: creates requests, calls the provider, validates intent, passes robot commands into `RobotRuntime`, and formats user feedback.
- `RobotRuntime`: remains the execution owner. It creates and consumes confirmation requests.
- `BehaviorArbiter`: remains the final safety arbiter before robot client dispatch.
- `VirtualHardwareRobotClient`: maps safe high-level commands to virtual hardware only.

## V0 Scope

V0 supports one action per AI turn. Multi-action provider output is validated and rejected unless future Runtime support can safely bind an immutable plan to confirmation.

Supported action namespaces:

- `query_status`
- `robot_command`
- `simulator.inject_fault`
- `simulator.clear_fault`
- `simulator.reset`
- `deny`

Default runtime mode is `simulator`. Real hardware mode is rejected by `AIInteractionLoop`.
