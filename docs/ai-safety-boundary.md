# AI Safety Boundary

The AI layer has no execution authority.

## Rules

- AI output must be JSON matching the `RobotIntent` schema.
- Unknown fields fail closed.
- Forbidden authority fields fail closed, including `confirmation_id`, `confirmation_grants`, `confirmed`, `bypass_arbiter`, `runtime_mode`, `safety_severity`, and `hardware_adapter`.
- Unknown actions fail closed.
- Out-of-range or invalid parameters fail closed.
- NaN, Infinity, oversized strings, and excessive nesting fail closed.
- AI cannot create or consume confirmation records.
- AI cannot switch into real hardware mode.
- AI cannot call serial ports, cameras, microphones, or firmware upload.

## Confirmation

High-risk AI-origin robot commands such as movement and stand are passed to `RobotRuntime`. Runtime asks `BehaviorArbiter` for a decision and creates a one-time, action-bound, context-bound confirmation request when required.

Confirmation IDs are only consumed by Runtime. Logs and AI memory store only short fingerprints, not complete IDs.

Covered states:

- request required
- accepted
- replay rejected
- wrong action rejected
- context changed rejected
- expired rejected
- runtime restart rejected
- AI-forged grant rejected by schema

## Hardware Status

The current AI loop is simulator-only. The real hardware adapter remains a stub and is not opened by this feature.
