# Hardware Validation Plan

This plan is for real Sesame Robot hardware acceptance after software, mock, simulator, and firmware-build validation have passed. Do not run these steps from Codex automation. A human operator must perform them with the robot physically present.

## 1. Pre-Test Safety Preparation

- Emergency stop: verify the software emergency stop command, physical power switch, and manual disconnect path before any actuator test.
- Power cutoff: keep a reachable battery disconnect or bench-supply cutoff available during every powered stage.
- Servo limits: confirm firmware angle limits are enabled and have not been widened for the test.
- Mechanical inspection: check leg linkages, horn screws, cable routing, and printed parts for binding or cracks.
- Battery voltage: verify pack voltage is within the safe operating range before load tests.
- Charging dock: inspect polarity, contacts, insulation, alignment guides, and any exposed conductors before dock tests.
- Test area: clear the surface around the robot and use a low-friction fallback area for first motion.
- Two-person watch: use one operator at the console and one spotter near the cutoff for first actuator, standing, walking, self-righting, and dock-contact tests.
- First-run power: use low-power or current-limited supply where possible before battery-only motion.
- Logging and video: record command logs, firmware serial logs if intentionally opened by the human operator, and a clear video angle for post-test review.

## 2. Staged Test Order

Run stages from lower risk to higher risk. Do not advance after a failed stage until the cause is understood and fixed.

| Stage | Scope | Preconditions | Steps | Expected Result | Stop Conditions | Pass Criteria | May Advance |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Power only, no actuators | Robot on stable surface, servos mechanically unloaded if possible | Apply power, observe boot, do not send movement commands | Firmware boots, no overheating, no unexpected servo drive | Heat, smoke, repeated reset, unexpected motion | Stable boot for 2 minutes | Yes, if stable |
| 2 | Serial and logs | Stage 1 passed, human explicitly chooses to open serial | Observe logs only; do not upload firmware | Logs show normal boot and no crash loop | Brownout, watchdog loop, malformed status | Status output is readable and stable | Yes |
| 3 | Camera | Stage 1 passed, privacy area cleared | Start camera smoke test under human control | Frames are readable, no upload of private media | Wrong camera, privacy concern, high latency spike | Expected camera selected and frames stable | Yes |
| 4 | Microphone | Stage 1 passed, quiet local area, privacy consent | Start microphone smoke test under human control | Audio capture works locally | Wrong input, privacy concern, clipping | Expected input selected and local capture stable | Yes |
| 5 | Single servo small angle | Stage 2 passed, current limit active | Move one servo by a small angle within firmware limits | Servo moves smoothly and stops | Binding, overcurrent, excessive heat, angle overshoot | Motion stays within limits and returns neutral | Yes |
| 6 | Multi-servo coordination | Stage 5 passed for all servos | Run a small coordinated pose change, not walking | Legs move together without collision | Linkage interference, tipping, overcurrent | Pose is repeatable and stable | Yes |
| 7 | Standing posture | Stage 6 passed, spotter ready | Command stand, then rest | Robot stands without falling or oscillation | Tip-over, servo chatter, unstable current | Stand/rest repeat 3 times safely | Yes |
| 8 | Self-righting | Stage 7 passed, soft test surface | Request self-righting with confirmation flow | No action without confirmation; one confirmed attempt executes | High current, collision, unsafe posture | Attempt stays within mechanical limits | Yes |
| 9 | Walking or movement | Stage 7 passed, clear area | Test stop, then short forward/turn commands | Robot moves predictably and stop works | Drifting off table, missed stop, obstacle contact | Stop interrupts motion and gait is stable | Yes |
| 10 | Charging dock recognition | Stage 3 passed, dock unpowered or protected | Detect dock target without contact | Dock is identified without motion into contact | False target, unstable detection | Recognition is repeatable | Yes |
| 11 | Charging contact | Stage 10 passed, electrical checks complete | Approach/contact under close supervision | Contacts align without short or mechanical jam | Spark, wrong polarity, collision, excessive force | Contact is mechanically and electrically safe | Yes |
| 12 | AI command full path | Prior stages passed | Send high-level AI commands through Runtime only | Runtime sends only high-level commands; firmware safety remains final gate | Any bypass of confirmation, safety, or timeout | Logs and behavior match expected safety policy | Complete |

## 3. Confirmation Hardware Acceptance

- No confirmation: high-risk actions such as `reset_emergency_stop`, `self_righting`, and `charging_dock` must not execute without a Runtime-issued confirmation ID.
- One-time use: a valid confirmation ID may execute at most once. Replaying the same ID must be rejected before any servo or motor command is sent.
- Expired confirmation: a confirmation submitted at or after `expiresAt` must be rejected before hardware command dispatch.
- Wrong action: a confirmation requested for one action must not authorize another action.
- Context changed: changes to relevant action context must invalidate the confirmation before command dispatch.
- Runtime restart: old in-memory confirmations must be invalid after creating a new Runtime session.
- Severity logs: logs must record the actual safety severity (`ok`, `stop`, or `emergency_stop`) for the step.
- Rejection point: every confirmation rejection must occur before servo, motor, self-righting, charging, or movement command dispatch.

## 4. Confirmation Context Contract

The confirmation context includes only fields needed to determine whether a dangerous action is still the same decision:

- Action identity: canonical action name and proposed command.
- Runtime session mode: mock, simulator, or real robot.
- Safety prerequisites: emergency-stop active flag, safety severity, communication timeout, posture state, and robot motion state.
- Hardware gating inputs: battery percent, hardware availability flag, and experimental feature flag.

The confirmation context intentionally excludes frequent or unrelated data such as timestamps, raw camera frames, microphone audio, personal identity media, full sensor dumps, debug logs, and complete confirmation IDs. Excluding noisy data prevents confirmations from expiring for irrelevant reasons; including safety and action fields prevents reuse after the target decision changes.

The context fingerprint is generated by sorting the context keys, formatting each `key=value` pair, joining them with `|`, and hashing the result with SHA-256. Logs and CLI JSON may show short fingerprints for audit correlation, but must not log complete internal context tokens.

## 5. Firmware Capacity Gate Recommendation

Current observed build size is 1,138,226 bytes of 1,310,720 bytes flash, or about 86%. Remaining flash is 172,494 bytes. Current dynamic memory use is 79,456 bytes of 327,680 bytes, or about 24%.

Recommended CI warning threshold: 88% flash.

Recommended CI failure threshold: 92% flash.

These thresholds leave room for normal compiler variation while flagging meaningful regressions before the partition is exhausted. Do not fail CI on small byte-level fluctuations below the warning threshold.
