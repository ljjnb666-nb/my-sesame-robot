# Sesame AI Robot Project State

最后更新：2026-07-18

## 当前分支

- 本地分支：`feat/ai-robot-v0`
- 上游跟踪：`origin/feat/ai-robot-v0`
- 远端：`origin` 指向 `https://github.com/ljjnb666-nb/my-sesame-robot.git`

## 最新提交

- `02eac9b feat: add camera prototype foundation`
- 当前待提交阶段：`feat: add mock object detection pipeline`

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
- 已扩展统一状态查询接口：
  - `/api/status` 保留旧字段。
  - 新增固件版本、运行时间、运动状态、动作执行状态、急停状态、延期解除状态、最后输入时间、可用命令和能力列表。
  - 对状态中的字符串字段进行 JSON 转义。
- 已建立 ai-controller 基础工程：
  - Python 标准库实现，无第三方运行依赖。
  - 包含配置、日志、HTTP/JSON 客户端、状态查询、命令发送、心跳、急停接口、有限重连和 Mock 机器人。
  - 提供 `run-tests.ps1`、`run-mock.ps1` 和 `run-cli.ps1`。
  - 单元测试覆盖 Mock 状态、命令别名、急停、拒绝未知命令、心跳刷新和通信超时。
- 已建立电脑端摄像头原型基础：
  - 提供摄像头源抽象、Mock 帧源、可选 OpenCV 真实摄像头源和摄像头枚举函数。
  - 支持 `camera-smoke --mock` 统计 FPS 和延迟。
  - 视觉模块当前不发送运动命令。
- 已建立人体和物体检测基础：
  - 提供检测输出数据结构和检测器协议。
  - Mock 检测器默认输出 `person` 和 `object`。
  - 检测结果包含类别、置信度、中心点、边界框和初步距离估计字段。
  - 检测模块与机器人控制客户端分离，不发送动作命令。

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
- 程序存储空间：1,133,894 bytes / 1,310,720 bytes，86%。
- 动态内存：79,456 bytes / 327,680 bytes，24%，剩余 248,224 bytes。
- 重要警告：本次输出未显示编译警告。
- 输出目录：`.build/output`

## 最近一次 AI 控制器验证

命令：

```powershell
powershell -ExecutionPolicy Bypass -File ".\run-tests.ps1"
```

执行目录：`ai-controller/`

结果：

- 单元测试状态：成功。
- 测试数量：12。
- CLI 冒烟测试：Mock 服务启动后，`run-cli.ps1 status` 成功返回状态 JSON。
- 摄像头冒烟测试：`run-cli.ps1 camera-smoke --mock --frames 10` 成功返回 FPS 和延迟统计。
- 检测冒烟测试：`run-cli.ps1 detect-smoke --mock` 成功返回 Mock 人体和物体检测 JSON。
- 真实机器人连接：未进行。
- 真实摄像头访问：未进行。

## 已知问题

- 真实硬件急停、解除急停、网页控制和串口路径尚未在实体机器人上验证。
- 通信超时软停止尚未在实体机器人连续运动中验证。
- 默认 AP 密码仍出现在上游固件文档和示例中；生产使用前应更改。

## 下一项任务

阶段 6：主人人脸注册和识别。

最小实现方向：

- 建立本地人脸身份数据目录规范。
- 默认不提交照片和人脸特征。
- 建立人脸注册、删除和识别接口。
- 支持 Mock 人脸识别数据和置信度阈值。
- 无法确认身份时不得默认当作主人。

## 尚未完成的真实硬件验证

以下动作需要用户明确确认并手动执行，当前不会自动进行：

- 烧录真实 ESP32 开发板。
- 打开或操作真实串口。
- 驱动真实舵机。
- 控制机器人站立、行走或执行姿态动作。
- 验证软件急停在实体机器人运动中的制动效果。
- 验证解除急停后机器人保持无动作状态。
- 验证通信超时后连续运动自动停止且不锁存急停。
- 验证真实摄像头枚举、读取、预览关闭和帧率延迟统计。
- 验证供电、电池、电机电流和舵机温度是否安全。
