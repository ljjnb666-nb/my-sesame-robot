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
- 单元测试：覆盖状态查询、命令别名、急停、心跳和通信超时。

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

视觉模块当前只统计帧率和延迟，不会发送机器人运动命令。

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
