# Simulation Capability Matrix

This matrix is based on repository code and automated scenario coverage. It does not describe real hardware test results.

| 能力 | 已模拟 | 模拟精度 | 是否有故障注入 | 是否进入 CI |
| --- | --- | --- | --- | --- |
| 舵机 | 是 | Structured virtual state: current/target angle, range, speed, motion timing, offline/stuck/overheat flags | 是: `servo_stuck`, `servo_offline`, `servo_overheated` | 是: unit tests and `run-hardware-scenarios.ps1` |
| 电机 | 是 | Structured virtual state: direction, power, duration, output, auto-stop deadline, stall/overcurrent/offline flags | 是: `motor_stall`, `motor_overcurrent`, `motor_offline` | 是: unit tests and `run-hardware-scenarios.ps1` |
| 姿态传感器 | 是 | Roll/pitch and pose state with missing/invalid/frozen fault surfaces | 是: `pose_sensor_missing`, `pose_sensor_invalid`, `pose_sensor_frozen` | 是: unit tests and hardware scenarios |
| 电池 | 是 | Percent, voltage, charging state, missing/low/invalid voltage markers | 是: `battery_low`, `battery_sensor_missing`, `battery_voltage_invalid` | 是: unit tests and hardware scenarios |
| 摄像头 | 部分 | Structured virtual frame and explicit timeout/unavailable/black-frame errors; no real image capture in CI | 是: `camera_timeout`, `camera_unavailable`, `camera_black_frame` | 是: unit tests and hardware scenarios |
| 麦克风 | 部分 | Structured virtual audio and explicit timeout/unavailable/clipping errors; no real audio capture in CI | 是: `microphone_unavailable`, `microphone_timeout`, `microphone_clipping` | 是: unit tests and hardware scenarios |
| 串口通信 | 部分 | HTTP/JSON mock protocol and virtual communication-loss fault; no real serial scan/open | 是: `communication_lost`, malformed/oversized JSON protocol tests | 是: existing protocol tests and hardware scenarios |
| 充电底座 | 部分 | Charging/contact state and contact failure marker; no physical docking simulation | 是: `charging_contact_failed` | 是: hardware scenarios and integrated charging gate scenarios |
| Confirmation | 是 | One-time, TTL-bound, action-bound, context-bound in Runtime | 是: replay, expired, wrong action, context changed, runtime restart, dispatch failure | 是: AI tests, CLI demo, integrated scenarios |
| Runtime 重启 | 是 | New Runtime session cannot consume old in-memory confirmations | 是: `runtime_restart` listed; session restart tested through ConfirmationStore separation | 是: AI tests and integrated scenarios |

## Verified By Software Automation

- Runtime and Arbiter behavior.
- Confirmation lifecycle and rejection states.
- Mock robot HTTP/JSON protocol.
- Virtual actuator state transitions.
- Virtual sensor fault surfaces.
- Fault injection and clearing.
- Simulator scenario replay.
- Firmware compilation.
- GitHub Actions CI when run on PR/main.

## Not Verified Without Real Hardware

- Firmware upload to an ESP32 board.
- ESP32 physical boot.
- Real serial communication.
- Real servo direction, current, heat, and mechanical limits.
- Real motor direction, current, and driver behavior.
- Real camera and microphone compatibility.
- Real battery and charging system behavior.
- Physical self-righting, walking, docking, and full AI-to-hardware chain.
