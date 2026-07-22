# Hardware Interface Contract

This document defines the software contract for future Sesame Robot hardware. It is not a record of completed real-hardware validation. Values not already established by the repository are marked as `待真实硬件选型后确定`.

## Controller

| Item | Contract |
| --- | --- |
| Expected ESP32 board | Lolin S2 Mini by default |
| FQBN | `esp32:esp32:lolin_s2_mini` |
| Firmware build | `powershell -ExecutionPolicy Bypass -File .\scripts\firmware-build.ps1` |
| Arduino CLI | 1.5.1 |
| ESP32 Arduino Core | 3.3.10 |
| Flash | Derived from firmware build output |
| RAM | Derived from firmware build output |
| Serial baud rate | `待真实硬件选型后确定` |
| USB connection | `待真实硬件选型后确定` |

## Runtime Modes

The AI controller must default to non-hardware operation. Valid modes are:

| Mode | Hardware access | Purpose |
| --- | --- | --- |
| `mock` | No | HTTP mock robot and Runtime tests |
| `simulator` | No | Virtual actuators, sensors, faults, and scenario replay |
| `real_robot` | Only after explicit user approval | Future real hardware operation |

Importing a hardware adapter must not open serial, GPIO, cameras, microphones, or actuators. Real transport opening must be an explicit operation.

## Unified Hardware Interface

The software boundary is represented by `RobotHardware` in `ai-controller/sesame_ai_robot/virtual_hardware.py`.

Required methods:

| Method | Contract |
| --- | --- |
| `read_battery()` | Return structured battery availability, percent, voltage, and charging state |
| `read_pose()` | Return structured pose availability, roll, pitch, and state |
| `set_servo(servo_id, angle, speed)` | Validate id, range, speed, faults, battery, pose, communication, and emergency state before mutation |
| `set_motor(motor_id, power, duration)` | Validate id, power range, duration, faults, battery, pose, communication, and emergency state before mutation |
| `stop_all_actuators()` | Put motors and in-progress servo targets into safe state |
| `capture_camera_frame()` | Return structured virtual frame or explicit error |
| `capture_audio(duration)` | Return structured virtual audio or explicit error |
| `read_charging_state()` | Return charging/contact state |

## Actuators

| Area | Contract |
| --- | --- |
| Servo ids | Simulator supports ids `0..7`; real mapping is `待真实硬件选型后确定` |
| Servo angle range | Simulator default `0..180` degrees; real safe limits are `待真实硬件选型后确定` |
| Servo faults | `servo_stuck`, `servo_offline`, `servo_overheated` |
| Motor ids | Simulator supports ids `0..1`; real mapping is `待真实硬件选型后确定` |
| Motor power range | Simulator `-1.0..1.0` |
| Motor duration limit | Simulator maximum 5 seconds per dispatch |
| Motor faults | `motor_stall`, `motor_overcurrent`, `motor_offline` |
| Emergency stop | All motor outputs become zero; servo targets hold current angle |
| Disconnect behavior | Communication loss stops actuators and fails closed |

## Sensors

| Sensor | Simulator states | Real hardware status |
| --- | --- | --- |
| Pose / IMU | normal, tilted, fallen, missing, invalid, frozen marker | `待真实硬件选型后确定` |
| Battery | normal, low, missing, invalid voltage, charging markers | `待真实硬件选型后确定` |
| Camera | virtual frame, unavailable, timeout, black-frame marker | `待真实硬件选型后确定` |
| Microphone | virtual audio, unavailable, timeout, clipping marker | `待真实硬件选型后确定` |
| Charging detection | not charging, contact failed, charging markers | `待真实硬件选型后确定` |

## Communication Protocol

Current firmware-facing HTTP/JSON protocol remains `/api/status` and `/api/command` in the mock robot.

| Area | Contract |
| --- | --- |
| Message format | JSON object |
| Required command field | `command` for motion/control requests |
| Optional face field | `face` |
| Error format | Structured JSON with `status`, `error`, and `message` |
| Payload limit | Enforced by protocol validator |
| Timeout | Communication timeout must result in stop/fail-closed behavior |
| Retry | `待真实硬件选型后确定` |
| Idempotency | Replayed high-risk confirmations must not dispatch a second action |
| Invalid messages | Reject and fail closed; do not infer dangerous commands from malformed data |

## Safety Constraints

- Default state is non-hardware and stopped.
- Runtime `real_robot` mode is blocked unless explicitly allowed.
- High-risk actions continue to require Runtime Confirmation.
- Confirmation IDs are one-time, TTL-limited, action-bound, and context-bound.
- Low battery, missing battery data, invalid pose data, emergency stop, disabled hardware switch, and communication loss block actuator dispatch.
- Simulator faults must be injectable and clearable through public APIs or scenario files.
- Software simulation results must not be reported as real hardware test results.
