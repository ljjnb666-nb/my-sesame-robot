# Sesame AI Robot Project State

最后更新：2026-07-22

## 当前分支

- 本地分支：`feat/ai-robot-v0`
- 上游跟踪：`origin/feat/ai-robot-v0`
- 远端：`origin` 指向 `https://github.com/ljjnb666-nb/my-sesame-robot.git`

## 最新提交

- `28e5830 test: add integrated safety scenarios`
- 当前待提交阶段：`docs: sync ai robot project state`

## 已完成能力

- 原版固件可通过 Arduino CLI 编译脚本验证。
- 固件已模块化为主入口、动作序列、表情位图和网页资源。
- JSON API 已存在 `/api/status` 和 `/api/command`。
- 已修复固件和 Mock 服务器未知命令协议：
  - 未知命令返回 HTTP 400 和结构化 JSON 错误 `unknown_command`。
  - 空命令返回 `empty_command`。
  - 缺少 `command` 且不是 face-only 请求时返回 `missing_command`。
  - 非法 JSON 返回 `invalid_json`。
  - 急停期间普通动作返回 `emergency_stop_active`，不会污染 `currentCommand`。
  - 未知命令不会让 `motionState` 进入 `moving`。
- 已加入软件锁存急停：
  - 支持 `emergency_stop`、`estop` 和串口短命令。
  - 支持 `reset_emergency_stop`。
  - 急停后清空当前命令。
  - 急停期间阻断普通动作命令。
  - 解除急停后保持无动作状态。
  - 软件急停不等于物理断电急停，不能替代电源级安全开关。
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
- 已建立主人人脸注册和识别基础：
  - 提供本地身份存储接口和 Mock 人脸识别器。
  - `ai-controller/data/` 已加入忽略规则，用于未来本地私有人脸数据。
  - Mock 识别必须达到阈值才确认身份，无法确认时不会默认当作主人。
  - 当前未采集真实照片，未生成真实人脸特征。
- 已决定将电脑模拟测试系统纳入长期开发流程：
  - AI 控制器后续通过配置选择 `mock`、`simulator` 或 `real_robot`。
  - 上层控制代码不得因为模拟或真实环境不同而重写。
  - 模拟服务器必须尽可能兼容真实 ESP32 HTTP/JSON 协议。
  - 每个重要安全功能都必须有自动化场景测试。
  - 涉及真实 ESP32、串口、舵机、摄像头或传感器时必须暂停询问用户。
- 已建立电脑模拟测试系统最小版本：
  - `simulator/run-scenarios.ps1` 可运行 JSON 场景。
  - 示例场景覆盖正常行走、急停、解除急停、通信超时和障碍物传感器状态。
  - Mock 机器人状态包含虚拟电量和虚拟传感器。
  - 场景运行器自动启动本地 Mock 服务器，不连接真实硬件。
- 已建立视觉追踪和安全跟随最小状态机：
  - 支持 `idle`、`searching`、`tracking`、`following`、`target_lost`、`stopped`、`emergency_stop`。
  - 急停和通信超时优先于追踪。
  - 身份未确认时不进入跟随。
  - 默认不允许真实跟随，只输出 tracking 状态。
  - 障碍物过近时输出高级 `stop` 命令。
  - 距离未知时不默认前进，目标过近时只停止，不自动后退。
  - 已跟随目标丢失或身份丢失时输出 `stop`，避免连续运动延续。
- 已建立传感器安全层最小版本：
  - 支持前方距离、左右距离、防跌落、IMU 姿态、碰撞和电池状态评估。
  - 普通障碍物和低电量输出高级 `stop`。
  - 防跌落、碰撞和过大倾角输出高级 `emergency_stop`。
  - 安全层已接入追踪状态机和 Mock 状态。
  - `SensorSnapshot.from_robot_status()` 优先读取真实 `sensors` 和 `battery` 字段，虚拟字段作为回退。
- 已建立模拟系统简单状态可视化：
  - `simulator/run-visualizer.ps1` 启动终端 2D 状态面板。
  - 显示当前动作、8 个虚拟舵机角度、急停状态、连接状态、虚拟传感器、电量和 OLED 表情。
  - Mock 机器人状态提供 `virtualServoAngles`。
- 已建立视觉回放测试最小版本：
  - `simulator/run-vision-replay.ps1` 支持 Mock、测试图片目录和真实摄像头来源。
  - `simulator/test-images/` 提供可提交 PGM 测试图片。
  - 视觉回放使用 Mock 检测器输出结构化结果，不发送机器人控制命令。
- 已建立 Mock 语音与大模型助手最小版本：
  - 本地 Mock 唤醒词、Mock 语音识别、Mock 语言模型、Mock TTS 和命令权限策略。
  - 不调用真实麦克风、不录音、不访问云端服务、不需要 API Key。
  - 运动命令默认被拒绝，急停命令始终允许。
- 已完成板载 AI 主控制器迁移评估准备：
  - 新增 `development-notes/ONBOARD_AI_EVALUATION.md`。
  - 记录 Raspberry Pi、CM 系列和其他单板计算机评估方向。
  - 记录摄像头、麦克风、扬声器、电源和电池需求。
  - 明确硬件在环测试顺序，当前不采购、不连接真实硬件。
- 已建立高级功能 Mock 层：
  - 新增 `AdvancedBehaviorPlanner`。
  - 支持跌倒检测、自动起身门槛、地形状态、情绪状态、Mock 记忆和回充意图。
  - `real_robot` 模式下自动起身和自动回充必须等待用户明确确认。
  - 当前只输出高层命令建议，不执行真实动作序列。
- 已建立高级功能 Mock 场景测试：
  - 新增 `simulator/advanced_scenario_runner.py`。
  - 新增 `run-advanced-scenarios.ps1`。
  - 覆盖跌倒急停、真实模式自动起身确认门槛、地形危险和真实模式回充确认门槛。
  - 高级场景直接验证 AI 行为层，不连接真实硬件。
- 已建立统一决策仲裁器和最小运行时：
  - 新增 `BehaviorArbiter`、`ArbiterInput` 和 `RobotActionPlan`。
  - 统一仲裁安全层、追踪层、高级行为和助手计划。
  - 安全决策优先覆盖追踪、助手和高级行为。
  - 未知命令在进入 `RobotClient` 前被拒绝。
  - 新增 `RobotRuntime`，支持单步、固定次数循环、dry-run、mock/simulator 模式。
  - `real_robot` 模式默认禁止，必须显式确认后才允许进入。
- 已建立组合场景测试：
  - 新增 `simulator/integrated_scenario_runner.py`。
  - 新增 `run-integrated-scenarios.ps1`。
  - 覆盖跟随中跌倒、跟随中低电量、急停后自动起身请求、真实模式自动起身门槛、目标距离未知、目标过近、身份丢失、通信超时恢复、AI 动作被安全层否决和未知命令拒绝。

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
- 程序存储空间：1,134,938 bytes / 1,310,720 bytes，86%。
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
- 测试数量：66。
- 模拟器测试数量：14。
- CLI 冒烟测试：Mock 服务启动后，`run-cli.ps1 status` 成功返回状态 JSON。
- 摄像头冒烟测试：`run-cli.ps1 camera-smoke --mock --frames 10` 成功返回 FPS 和延迟统计。
- 检测冒烟测试：`run-cli.ps1 detect-smoke --mock` 成功返回 Mock 人体和物体检测 JSON。
- 人脸识别冒烟测试：`run-cli.ps1 face-id-smoke` 成功返回 Mock 身份确认 JSON。
- 模拟场景测试：`simulator/run-scenarios.ps1` 成功运行 6 个示例场景。
- 高级行为场景测试：`simulator/run-advanced-scenarios.ps1` 成功运行 4 个场景。
- 组合场景测试：`simulator/run-integrated-scenarios.ps1` 成功运行 10 个场景。
- 追踪状态机测试：覆盖急停、身份未确认、默认不跟随、障碍物停止和目标偏右转向。
- 传感器安全层测试：覆盖安全状态、障碍物、碰撞、防跌落、倾角、低电量和状态解析。
- 可视化冒烟测试：`simulator/run-visualizer.ps1 --once --demo` 成功输出一帧模拟状态。
- 视觉回放测试：Mock 来源和测试图片目录来源均通过自动化测试。
- 真实摄像头测试：本轮未执行。
- 助手流水线测试：覆盖无唤醒词忽略、急停允许、表情设置、表达动作、默认拒绝运动和模拟允许运动。
- 真实机器人连接：未进行。
- 真实摄像头访问：未进行。

## 已知问题

- 真实硬件急停、解除急停、网页控制和串口路径尚未在实体机器人上验证。
- 通信超时软停止尚未在实体机器人连续运动中验证。
- 默认 AP 密码仍出现在上游固件文档和示例中；生产使用前应更改。
- 真实摄像头读取依赖 OpenCV；当前环境 `ModuleNotFoundError: No module named 'cv2'`。

## 下一项任务

优先任务：阶段 11 运行时 CLI 和更多 dry-run 集成。

最小实现方向：

- 为 `RobotRuntime` 增加 CLI dry-run 入口。
- 扩展组合场景输出为更完整的结构化日志。
- 不进入真实起身、真实回充或地面运动测试。

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
- 验证真实传感器字段来自实体 ESP32 的完整状态。
- 验证真实人脸注册、删除和识别流程；不得提交照片或特征数据。
- 验证供电、电池、电机电流和舵机温度是否安全。
