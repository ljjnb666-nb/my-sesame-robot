# Sesame Robot Simulator

电脑模拟测试系统用于在不连接任何真实硬件的情况下验证机器人协议、AI 控制器、安全策略和场景流程。

## 长期目标

- 模拟服务器尽可能保持与真实 ESP32 相同或兼容的 HTTP/JSON 接口。
- AI 控制器通过配置选择 `mock`、`simulator` 或 `real_robot`。
- 上层控制代码不得因为模拟或真实环境不同而重写。
- 每个重要安全功能都必须有自动化场景测试。
- 普通软件模拟和测试可以自动执行。
- 涉及真实 ESP32、串口、舵机、摄像头或传感器时必须暂停询问用户。

## 阶段 1：Mock 机器人服务器

目标：

- 支持 `/api/command` 和 `/api/status`。
- 支持普通 `stop`、`emergency_stop`、`reset_emergency_stop` 和通信超时。
- 支持虚拟电量和虚拟传感器。
- 不连接任何真实硬件。

当前可复用 `ai-controller` 的 Mock 机器人服务器：

```powershell
powershell -ExecutionPolicy Bypass -File "..\ai-controller\run-mock.ps1"
```

后续会在 `simulator/` 下提供长期启动入口。

## 阶段 2：场景测试运行器

目标：

- 从 `simulator/scenarios/*.json` 读取事件序列。
- 自动执行命令。
- 检查机器人状态。
- 输出测试通过或失败。
- 覆盖正常行走、急停、解除、断联和障碍物场景。

启动命令：

```powershell
powershell -ExecutionPolicy Bypass -File ".\run-scenarios.ps1"
```

也可以只运行单个场景：

```powershell
powershell -ExecutionPolicy Bypass -File ".\run-scenarios.ps1" ".\scenarios\emergency_stop.json"
```

当前示例场景：

- `scenarios/normal_walk.json`
- `scenarios/emergency_stop.json`
- `scenarios/communication_timeout.json`
- `scenarios/obstacle.json`
- `scenarios/cliff_emergency.json`
- `scenarios/low_battery.json`

高级行为场景使用独立运行器，不连接 Mock HTTP 服务器，直接验证 AI 高级行为层输出：

```powershell
powershell -ExecutionPolicy Bypass -File ".\run-advanced-scenarios.ps1"
```

当前高级场景：

- `scenarios/advanced/fall_detection.json`
- `scenarios/advanced/real_self_righting_gate.json`
- `scenarios/advanced/terrain_unsafe.json`
- `scenarios/advanced/charging_gate.json`

组合场景使用独立运行器，将安全层、追踪层、高级行为、助手计划和 Arbiter 放在同一条链路中验证：

```powershell
powershell -ExecutionPolicy Bypass -File ".\run-integrated-scenarios.ps1"
```

当前组合场景：

- `scenarios/integrated/following_fall.json`
- `scenarios/integrated/following_low_battery.json`
- `scenarios/integrated/emergency_blocks_self_righting.json`
- `scenarios/integrated/real_self_righting_gate.json`
- `scenarios/integrated/target_distance_unknown.json`
- `scenarios/integrated/target_too_close.json`
- `scenarios/integrated/identity_lost_stops.json`
- `scenarios/integrated/communication_timeout_recovery.json`
- `scenarios/integrated/assistant_motion_blocked_by_obstacle.json`
- `scenarios/integrated/unknown_command_rejected.json`

场景步骤支持：

- `command`：发送机器人命令。
- `face`：设置 OLED 表情。
- `setSensor`：设置虚拟传感器。
- `setBatteryPercent`：设置虚拟电量。
- `waitMs`：等待指定毫秒数。
- `expect`：断言状态字段，支持 `virtualSensors.frontDistanceM` 这样的点路径。

高级场景步骤支持：

- `action`：执行 `assess_posture`、`plan_self_righting`、`assess_terrain` 或 `plan_charging`。
- `config`：设置 `runtimeMode`、`allowSelfRighting` 和 `allowAutoDocking`。
- `sensor`：设置 Mock IMU、电量、防跌落和碰撞输入。
- `posture`：为自动起身门槛提供姿态状态。
- `expect`：断言高级行为决策字段，例如 `state`、`command` 和 `requiresUserConfirmation`。

组合场景步骤支持：

- `config`：设置 `allowFollowing`、`runtimeMode`、`allowSelfRighting` 和 `allowAutoDocking`。
- `robotStatus`：设置急停、通信超时等机器人状态。
- `sensor`：设置 Mock 距离、IMU、电量、防跌落和碰撞输入。
- `target`：设置目标是否可见、画面中心位置和 `distanceM`。
- `identityConfirmed`：设置主人身份是否确认。
- `assistant`：设置助手提出的命令、表情或语音。
- `expect`：断言最终 Arbiter 输出和追踪状态。
- `expectBlockedActions`：断言被安全层或策略阻止的动作。

## 阶段 3：简单状态可视化

目标：

- 显示当前动作。
- 显示 8 个虚拟舵机角度。
- 显示急停和连接状态。
- 显示虚拟传感器数据。
- 显示 OLED 表情。

初期优先采用简单 2D 界面，不急于使用复杂三维物理引擎。

当前终端 2D 可视化启动命令：

```powershell
powershell -ExecutionPolicy Bypass -File ".\run-visualizer.ps1"
```

演示模式会循环虚拟命令：

```powershell
powershell -ExecutionPolicy Bypass -File ".\run-visualizer.ps1" --demo
```

单帧输出用于自动化检查：

```powershell
powershell -ExecutionPolicy Bypass -File ".\run-visualizer.ps1" --once --demo
```

## 阶段 4：视觉回放测试

目标：

- 支持读取真实摄像头。
- 支持读取视频文件。
- 支持读取测试图片目录。
- 支持 Mock 检测结果。
- 保证视觉模块和机器人控制模块解耦。

访问真实摄像头前必须等待用户明确确认。

当前启动命令：

```powershell
powershell -ExecutionPolicy Bypass -File ".\run-vision-replay.ps1" --source mock --frames 3
powershell -ExecutionPolicy Bypass -File ".\run-vision-replay.ps1" --source images --frames 3
```

用户明确确认允许访问真实摄像头后，可运行：

```powershell
powershell -ExecutionPolicy Bypass -File ".\run-vision-replay.ps1" --source camera --index 0 --frames 3
```

真实摄像头来源依赖本机 Python 安装 OpenCV（`cv2`）。如果缺少 OpenCV，Mock 和测试图片目录回放仍可正常运行。

当前视觉回放使用 Mock 检测器，只输出结构化检测结果，不发送机器人控制命令。

## 阶段 5：硬件在环测试

必须等待用户明确确认，并按顺序执行：

1. 先连接 ESP32，不连接舵机。
2. 再测试单个舵机。
3. 再进行架空的 8 舵机测试。
4. 最后才允许地面运动测试。

任一步骤失败都不得自动进入下一步。

## 2026-07-22 Scenario Update

- Integrated scenarios now cover protocol boundaries, emergency reset confirmation, self-righting confirmation, charging intent without hardware, confirmation replay/context rejection, rejected action semantics, and runtime CLI dry-run.
- `expectRejectedActions` is preferred for new scenarios. `expectBlockedActions` remains for compatibility.
- The selected final command must not appear in `rejectedActions`; communication-timeout `stop` is the selected command, not a rejected action.
- Protocol malformed JSON and oversized payload behavior is tested in `ai-controller/tests/test_mock_robot_protocol.py`; the integrated protocol scenario files document the coverage entry point.

## 2026-07-22 Confirmation Lifecycle Scenario Update

- Confirmation scenarios now use `RobotRuntime`, a persistent `ConfirmationStore`, and the mock robot server in one process.
- Scenario JSON no longer constructs `ConfirmationGrant`.
- Runtime-flow scenarios cover request, valid submit, replay, expired ID, wrong action, changed context, fake ID, emergency reset without motion resume, self-righting hardware block, and charging hardware block.
- `runtimeFlow: true` scenarios use `submitConfirmation: "last"` to submit the actual ID returned by the previous request step.

## 2026-07-22 Virtual Hardware Scenario Update

The virtual hardware layer lives in `ai-controller/sesame_ai_robot/virtual_hardware.py`. It defines the shared `RobotHardware` contract plus mock/simulator adapters and a real hardware adapter stub that does not open devices during import or initialization.

Run virtual hardware scenarios:

```powershell
powershell -ExecutionPolicy Bypass -File ".\run-hardware-scenarios.ps1"
```

Current virtual hardware scenarios:

- `scenarios/hardware/servo_safety.json`
- `scenarios/hardware/motor_safety.json`
- `scenarios/hardware/sensor_faults.json`

The scenarios validate software simulation only:

- Servo range, invalid id, offline, stuck, overheated, and emergency stop behavior.
- Motor power limit, duration limit, stall, overcurrent, auto-stop, and emergency stop behavior.
- Battery, pose, camera, microphone, charging-contact, and communication-loss faults.
- Failed dispatches keep actuator state unchanged unless the safety policy intentionally enters emergency stop.

CLI inspection commands are available through the AI controller and default to simulator-only state:

```powershell
powershell -ExecutionPolicy Bypass -File "..\ai-controller\run-cli.ps1" simulator-state
powershell -ExecutionPolicy Bypass -File "..\ai-controller\run-cli.ps1" simulator-inject-fault battery_low
powershell -ExecutionPolicy Bypass -File "..\ai-controller\run-cli.ps1" simulator-timeline
```

These commands do not open serial ports, cameras, microphones, GPIO, or actuator devices.
