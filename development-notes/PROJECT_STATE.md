# Sesame AI Robot Project State

最后更新：2026-07-18

## 当前分支

- 本地分支：`feat/ai-robot-v0`
- 上游跟踪：当前未配置本地分支上游跟踪。
- 远端：`origin` 指向 `https://github.com/ljjnb666-nb/my-sesame-robot.git`

## 最新提交

- `e98609a docs: add project roadmap and state tracking`
- 当前待提交阶段：`feat: add communication timeout soft stop`

## 已完成能力

- 原版固件可通过 Arduino CLI 编译脚本验证。
- 固件已模块化为主入口、动作序列、表情位图和网页资源。
- JSON API 已存在 `/api/status` 和 `/api/command`。
- 已加入软件锁存急停：
  - 支持 `emergency_stop`、`estop` 和串口短命令。
  - 支持 `reset_emergency_stop`。
  - 急停后清空当前命令。
  - 急停期间阻断普通动作命令。
  - 解除急停后保持无动作状态。
- 已实现通信超时自动软停止：
  - 连续运动命令需要重复命令或心跳刷新。
  - 超时只清空连续动作，不触发锁存急停。
  - 网页方向键按住期间自动发送续租请求。
  - JSON API 支持 `heartbeat` 命令。
  - `/api/status` 增加 `communicationTimedOut` 和 `commandTimeoutMs` 字段。

## 当前开发环境

- Arduino CLI：项目声明已验证版本为 1.5.1。
- ESP32 Arduino Core：项目声明已验证版本为 3.3.10。
- ESP32Servo：项目要求保持 3.0.9。
- Adafruit SSD1306：项目声明已验证版本为 2.5.17。
- Adafruit GFX Library：项目声明已验证版本为 1.12.6。
- 默认开发板：`esp32:esp32:lolin_s2_mini`

## 最近一次固件验证

命令：

```powershell
powershell -ExecutionPolicy Bypass -File ".\scripts\firmware-build.ps1"
```

结果：

- 编译状态：成功。
- 程序存储空间：1,132,122 bytes / 1,310,720 bytes，86%。
- 动态内存：79,456 bytes / 327,680 bytes，24%，剩余 248,224 bytes。
- 重要警告：本次输出未显示编译警告。
- 输出目录：`.build/output`

## 已知问题

- 本地 `feat/ai-robot-v0` 当前未配置上游跟踪分支。
- 2026-07-18 查询 `origin/feat/ai-robot-v0` 时 GitHub HTTPS 连接中断，未能确认远端状态。
- 真实硬件急停、解除急停、网页控制和串口路径尚未在实体机器人上验证。
- 通信超时软停止尚未在实体机器人连续运动中验证。
- 默认 AP 密码仍出现在上游固件文档和示例中；生产使用前应更改。

## 下一项任务

阶段 2：统一状态查询接口。

最小实现方向：

- 扩展 `/api/status` 的机器可读字段。
- 增加当前命令、动作状态、急停状态、延期解除状态、最后命令时间、通信超时状态、当前表情、固件版本和可用功能。
- 保持旧字段兼容。
- 更新固件 README 的状态 JSON 示例。

## 尚未完成的真实硬件验证

以下动作需要用户明确确认并手动执行，当前不会自动进行：

- 烧录真实 ESP32 开发板。
- 打开或操作真实串口。
- 驱动真实舵机。
- 控制机器人站立、行走或执行姿态动作。
- 验证软件急停在实体机器人运动中的制动效果。
- 验证解除急停后机器人保持无动作状态。
- 验证通信超时后连续运动自动停止且不锁存急停。
- 验证供电、电池、电机电流和舵机温度是否安全。
