# AI Controller

这里存放电脑端或单板计算机端的视觉、语音、大模型和机器人高层控制程序。

当前阶段只建立电脑端控制基础工程，并通过 Mock 机器人验证；不会自动连接、烧录或控制真实机器人。

## 功能范围

- 配置管理：通过环境变量配置机器人 URL、请求超时、心跳间隔和日志级别。
- 日志：统一 Python logging 初始化。
- HTTP/JSON 客户端：调用固件 `/api/status` 和 `/api/command`。
- 状态查询：读取机器可读状态。
- 命令发送：只发送固件当前支持的高级命令，不直接控制单个舵机。
- 心跳：刷新连续运动超时窗口。
- 自动重连：状态查询支持有限次数重试。
- 急停接口：支持 `emergency_stop` 和 `reset_emergency_stop`。
- Mock 机器人：本地 HTTP 服务模拟固件 JSON API。
- 摄像头原型：提供 Mock 帧源、可选 OpenCV 摄像头源、帧率和延迟统计。
- 检测原型：提供检测结果数据结构、Mock 人体/物体检测器和 JSON 输出。
- 人脸身份原型：提供本地身份目录规范、注册/删除接口和 Mock 识别阈值逻辑。
- 传感器安全层：评估距离、防跌落、碰撞、IMU 姿态和电池状态。
- 追踪状态机：消费检测、身份和机器人状态，默认不发送真实跟随命令。
- Mock 语音与大模型助手：提供本地唤醒词、语音识别、语言模型、TTS 和命令权限流水线。
- 高级功能 Mock 层：提供跌倒检测、自动起身门槛、地形状态、情绪状态、内存 Mock 和回充意图。
- 统一决策仲裁器：统一安全层、追踪层、高级行为和助手计划，输出最终 `RobotActionPlan`。
- 最小运行时：支持单步、固定次数、dry-run、mock/simulator 模式；`real_robot` 默认禁止。
- 单元测试：覆盖状态查询、命令别名、急停、心跳、通信超时、Mock 协议、摄像头 Mock、检测 Mock、人脸身份 Mock、传感器安全层、追踪状态机、助手策略、高级功能安全边界、Arbiter 和 Runtime。

## 支持的命令

客户端当前支持：

- `stand`
- `rest`
- `walk_forward`
- `walk_backward`
- `turn_left`
- `turn_right`
- `stop`
- `wave`
- `dance`
- `swim`
- `point`
- `pushup`
- `bow`
- `cute`
- `freaky`
- `worm`
- `shake`
- `shrug`
- `dead`
- `crab`
- `emergency_stop`
- `reset_emergency_stop`
- `heartbeat`

`follow_owner`、`stop_following` 等未来高级行为暂不直接下发到固件，避免把未知命令写入机器人状态。

机器人 HTTP 客户端会绕过系统代理直连目标地址，避免本地 Mock 或局域网机器人请求被代理服务改写。

固件和 Mock 服务器会拒绝未知命令、空命令、缺失命令和非法 JSON。客户端白名单只是前置保护，不能替代固件本地验证。

## 运行测试

```powershell
powershell -ExecutionPolicy Bypass -File ".\run-tests.ps1"
```

## 启动 Mock 机器人

```powershell
powershell -ExecutionPolicy Bypass -File ".\run-mock.ps1"
```

默认地址是 `http://127.0.0.1:8765`。

## 使用 CLI

另开一个终端，在 `ai-controller/` 目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File ".\run-cli.ps1" status
powershell -ExecutionPolicy Bypass -File ".\run-cli.ps1" command walk_forward
powershell -ExecutionPolicy Bypass -File ".\run-cli.ps1" heartbeat
powershell -ExecutionPolicy Bypass -File ".\run-cli.ps1" emergency-stop
powershell -ExecutionPolicy Bypass -File ".\run-cli.ps1" reset-emergency-stop
```

## 摄像头原型

默认建议先使用 Mock 帧源，不打开真实摄像头：

```powershell
powershell -ExecutionPolicy Bypass -File ".\run-cli.ps1" camera-smoke --mock --frames 30
```

如果用户已经明确确认允许访问电脑摄像头，并且本地安装了 OpenCV，可枚举和读取真实摄像头：

```powershell
powershell -ExecutionPolicy Bypass -File ".\run-cli.ps1" camera-list
powershell -ExecutionPolicy Bypass -File ".\run-cli.ps1" camera-smoke --index 0 --frames 30
```

真实摄像头路径需要本机 Python 可导入 `cv2`。

视觉模块当前只统计帧率和延迟，不会发送机器人运动命令。

## 检测原型

使用 Mock 帧源和 Mock 检测器执行一次检测：

```powershell
powershell -ExecutionPolicy Bypass -File ".\run-cli.ps1" detect-smoke --mock
```

检测输出包含：

- `label`：目标类别，例如 `person` 或 `object`。
- `confidence`：置信度。
- `center`：目标中心点。
- `box`：目标边界框。
- `distanceM`：初步距离估计接口，可为空。

检测模块只生成结构化感知结果，不会直接调用机器人动作接口。

## 人脸身份原型

本阶段只实现本地身份数据结构和 Mock 识别，不采集真实照片，不生成真实人脸特征。

```powershell
powershell -ExecutionPolicy Bypass -File ".\run-cli.ps1" face-id-smoke
powershell -ExecutionPolicy Bypass -File ".\run-cli.ps1" face-id-smoke --confidence 0.6 --threshold 0.75
```

隐私规则：

- 私有人脸数据默认放在 `ai-controller/data/`。
- `ai-controller/data/` 已加入仓库忽略规则。
- 未确认身份时，识别结果不会默认当作主人。

## 追踪状态机

`TrackingController` 建立高层状态：

- `idle`
- `searching`
- `tracking`
- `following`
- `target_lost`
- `stopped`
- `emergency_stop`

安全规则：

- 急停状态优先于所有追踪行为。
- 身份未确认时不进入跟随。
- 默认 `allow_following=false`，只输出 `tracking` 状态，不发送运动命令。
- 距离、电池、防跌落、碰撞和 IMU 姿态由 `SafetyMonitor` 统一评估。
- 普通障碍物和低电量输出 `stop`，防跌落、碰撞和过大倾角输出 `emergency_stop`。
- 距离未知时不前进；距离过近时输出 `stop`，本轮不自动后退。
- 已跟随目标丢失或身份丢失时输出 `stop`，防止旧连续运动延续。
- 即使允许跟随，也只输出 `walk_forward`、`turn_left`、`turn_right` 等高级命令，不直接控制舵机。

## 统一 Arbiter 和 Runtime

`BehaviorArbiter` 是唯一的最终计划仲裁入口。它消费机器人状态、安全评估、追踪决策、高级行为决策和助手计划，输出：

- `command`
- `face`
- `speech`
- `source`
- `reason`
- `requires_user_confirmation`
- `blocked_actions`

优先级以安全为先：急停激活、跌落/碰撞/悬崖/严重倾斜、通信超时、低电量和障碍物都会覆盖追踪、助手和高级行为。未知命令会在进入 `RobotClient` 前被拒绝。

`RobotRuntime` 当前是最小软件运行时，只用于 mock/simulator 和 dry-run 集成；真实机器人模式默认被阻断，必须等待用户明确确认。软件急停只是软件锁存保护，不等于物理断电急停。

## Mock 语音与大模型助手

当前只使用本地 Mock，不调用麦克风、录音、云端语音服务或大模型 API。

```powershell
powershell -ExecutionPolicy Bypass -File ".\run-cli.ps1" assistant-smoke "sesame happy face"
powershell -ExecutionPolicy Bypass -File ".\run-cli.ps1" assistant-smoke "sesame emergency stop"
powershell -ExecutionPolicy Bypass -File ".\run-cli.ps1" assistant-smoke "sesame follow me"
```

默认策略：

- `emergency_stop`、`stop`、`reset_emergency_stop` 始终允许。
- `wave` 等表达动作允许。
- `walk_forward`、`turn_left`、`turn_right` 等运动命令默认拒绝。
- 模拟测试可用 `--allow-motion` 显式开启运动命令计划，但仍只输出计划，不直接控制真实机器人。

## 高级功能 Mock 层

`AdvancedBehaviorPlanner` 当前只提供可测试的高级行为决策，不执行真实动作序列：

- 跌倒检测：IMU 姿态超过 Mock 阈值时输出 `stop` 或 `emergency_stop`。
- 自动起身：只在 `mock` 或 `simulator` 模式、且策略允许时输出高层 `stand` 建议；`real_robot` 模式必须等待用户确认。
- 地形自适应：根据 Mock IMU、防跌落和碰撞状态输出地形状态与安全命令。
- 情绪状态：根据主人可见、电量和急停上下文生成本地状态，不调用云端服务。
- 长期记忆：当前为进程内 Mock 存储，不写入私人人脸、录音或云端数据。
- 自动回充：默认只输出 `stop` 或等待确认；真实机器人回充必须单独确认硬件条件。

连接真实机器人前必须由用户明确确认，并设置：

```powershell
$env:SESAME_ROBOT_URL = "http://sesame-robot.local"
```

## 环境变量

- `SESAME_ROBOT_URL`：机器人 URL，默认 `http://127.0.0.1:8765`。
- `SESAME_REQUEST_TIMEOUT_S`：单次请求超时秒数，默认 `2.0`。
- `SESAME_HEARTBEAT_INTERVAL_S`：心跳间隔秒数，默认 `0.4`。
- `SESAME_RECONNECT_ATTEMPTS`：自动重连尝试次数，默认 `3`。
- `SESAME_RECONNECT_DELAY_S`：重连间隔秒数，默认 `0.5`。
- `SESAME_LOG_LEVEL`：日志级别，默认 `INFO`。
