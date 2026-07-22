# Sesame HTTP API Protocol

Last updated: 2026-07-22

## Scope

This document defines the shared firmware and mock-server `/api/command` protocol. The ESP32 firmware uses ArduinoJson for real JSON parsing, and the Python mock uses `sesame_ai_robot.protocol` for the same error names and status codes.

## Dependencies

- Firmware JSON parser: `ArduinoJson` `6.21.5`
- Request body limit: `512` bytes
- Build script: `scripts/firmware-build.ps1` checks for ArduinoJson and installs `ArduinoJson@6.21.5` when missing.

## Request Validation

`POST /api/command` accepts only a JSON object. The body must be non-empty and at most `512` bytes. At least one of `command` or `face` must be present.

`command`, when present, must be a non-empty string and must be one of the supported firmware commands. Arrays, numbers, booleans, null, and objects are rejected.

`face`, when present, must be a non-empty string and must be a known face name. Arrays, numbers, booleans, null, and objects are rejected.

The firmware does not print the full request body to serial logs.

## Error Response Shape

```json
{
  "status": "error",
  "error": "error_code",
  "message": "Human readable message"
}
```

## Error Codes

- `400 invalid_json`
- `400 invalid_payload`
- `400 missing_command`
- `400 invalid_command_type`
- `400 empty_command`
- `400 unknown_command`
- `400 invalid_face_type`
- `400 empty_face`
- `400 unknown_face`
- `409 emergency_stop_active`
- `413 payload_too_large`
- `405 method_not_allowed`

## Success Responses

Command:

```json
{
  "status": "ok",
  "message": "Command accepted",
  "command": "forward"
}
```

Face-only:

```json
{
  "status": "ok",
  "message": "Face updated",
  "face": "happy"
}
```

Heartbeat:

```json
{
  "status": "ok",
  "message": "Heartbeat accepted",
  "command": "heartbeat"
}
```

## Safety Notes

Software emergency stop is not the same as a physical power-disconnect emergency stop. `reset_emergency_stop` must go through the AI controller confirmation workflow before the AI controller sends it. Resetting does not restore an old movement command; tracking must reacquire the target and the assistant must provide a new command.

`stand` is a standing pose, not validated real self-righting. There is currently no real charging dock hardware, navigation, or docking command.

## 2026-07-22 Confirmation Trust Boundary Update

- `RobotRuntime` owns the long-lived `ConfirmationStore`.
- `BehaviorArbiter` does not create or persist confirmation requests.
- External callers cannot provide trusted `ConfirmationGrant` objects.
- Dangerous actions accept only a `confirmation_id` submitted back to `RobotRuntime`.
- Runtime validates and consumes the confirmation atomically before it asks Arbiter for an authorized final action.
- Confirmation IDs are action-bound, context-bound, expiring, and one-time use.
- Structured confirmation errors are: `unknown_id`, `expired`, `action_mismatch`, `context_changed`, and `already_used`.
- `user_confirmed_actions` is no longer an accepted Runtime or Arbiter input and cannot bypass confirmation.

Confirmation TTL uses the process monotonic clock. The default TTL is 60 seconds and stores reject zero, negative, or greater-than-300-second TTL values. A confirmation is expired when submitted at or after its `expiresAt` time.

Confirmation context includes canonical action identity, proposed command, runtime mode, emergency-stop state, safety severity, posture state, communication timeout state, robot motion state, battery percent, hardware availability, and experimental feature enablement. It excludes timestamps, raw sensor dumps, camera frames, microphone audio, personal media, debug logs, and other high-frequency or privacy-sensitive data.

The context fingerprint is SHA-256 over sorted `key=value` context pairs. Runtime JSON exposes the user-submittable `confirmationId` and a short context fingerprint for debugging, not the full internal context token. Runtime logs record only a short confirmation ID fingerprint, the action, lifecycle state, structured error, selected command, and real `safety_severity`.
