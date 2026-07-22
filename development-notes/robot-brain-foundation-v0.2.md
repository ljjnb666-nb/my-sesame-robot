# Robot Brain Foundation v0.2

## Memory Trust Boundary

The local JSON memory backend stores sanitized conversation/task context and non-sensitive long-term preferences. Memory content is always untrusted context. It cannot grant action permissions, create confirmation grants, change Runtime mode, enable real hardware, override BehaviorArbiter rules, or modify safety severity.

The sanitizer reduces accidental persistence of secrets and safety-bypass text, but it is not a complete secret scanner or complete prompt-injection defense.

If `memory.json` is missing, the controller starts with empty memory. If it is invalid JSON, has a non-object root, or uses an incompatible version, the file is quarantined as `memory.json.corrupt` or `memory.json.corrupt.N`, empty memory is used, and the load error remains available on `MemoryManager.last_load_error`.

## Local JSON Backend Limits

The JSON backend is intended for single-process or controlled single-writer use. It writes through a temporary file and replace operation, but it does not implement cross-process locking. A future backend should add file locks or move to a small database if multiple writers are needed.

## Robot Profile Boundary

`robot_profile.yaml` is descriptive configuration only. The profile loader accepts `name`, `personality`, `capabilities`, and non-safety `limits`; it rejects fields that attempt to change Arbiter rules, confirmation requirements, Runtime authorization, real-robot gates, Runtime mode, or safety severity.
