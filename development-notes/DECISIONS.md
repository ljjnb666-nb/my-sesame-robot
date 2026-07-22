# Architecture Decisions

本文档记录 Sesame AI Robot 的重要架构决策和原因。

## ADR-001：采用 ESP32 + AI 主控制器双控制器架构

状态：已接受。

决策：

- ESP32 负责实时舵机控制、步态执行、OLED、传感器、安全保护和通信超时。
- AI 主控制器负责摄像头、视觉检测、人脸识别、语音、大语言模型、高层行为和状态估计。
- AI 主控制器只发送高级动作请求，不直接连续控制单个舵机角度。

原因：

- ESP32 更适合本地实时控制和硬件安全闭环。
- 视觉模型、语音模型和大语言模型计算量大，不适合放入 ESP32 固件。
- 双控制器架构可以让 AI 行为失败时仍由 ESP32 保留最终安全决策权。

影响：

- 所有运动相关功能必须经过 ESP32 安全层。
- AI 控制器接口必须以 `stand`、`rest`、`walk_forward`、`turn_left`、`turn_right`、`stop`、`wave`、`follow_owner`、`stop_following`、`set_face`、`emergency_stop` 等高级命令为主。
- 固件状态接口必须足够机器可读，便于 AI 控制器判断安全状态。

## ADR-002：锁存急停优先于所有普通命令

状态：已接受。

决策：

- 软件急停使用锁存状态。
- 急停激活后清空当前命令并阻断普通动作。
- 解除急停只解除锁存，不恢复旧动作。

原因：

- 急停后自动恢复旧动作可能导致机器人在用户未预期时再次运动。
- 锁存语义更适合实体机器人安全控制。

影响：

- API、网页和串口路径都必须遵守急停状态。
- AI 控制器在急停后必须重新发出明确的新动作命令。

## ADR-003：通信超时使用软停止，不等同于急停

状态：已接受，待实现。

决策：

- 通信超时停止连续运动。
- 通信超时不触发锁存急停。
- 通信恢复后仍需要新的有效命令或心跳维持连续运动。

原因：

- 网络抖动和客户端关闭是常见情况，应停止运动但不一定进入需要人工解除的急停。
- 急停保留给明确危险或用户主动触发的最高优先级事件。

影响：

- 固件需要记录最后命令或心跳时间。
- 状态接口需要暴露通信是否超时。
- 连续运动命令和一次性姿态命令需要区分。

## ADR-004：依赖版本保持已验证组合

状态：已接受。

决策：

- Arduino CLI、ESP32 Arduino Core、ESP32Servo、Adafruit SSD1306 和 Adafruit GFX Library 按项目已验证版本维护。
- `ESP32Servo` 保持 3.0.9，升级前必须做兼容性测试。

原因：

- 舵机控制依赖 PWM 行为，依赖升级可能改变硬件行为。
- `ESP32Servo` 新版本存在已知多通道影响风险。

影响：

- 除非任务明确要求，不升级关键依赖。
- 任何依赖升级都必须独立提交并记录测试结果。

## ADR-005：真实硬件动作必须人工确认

状态：已接受。

决策：

- 不自动烧录开发板。
- 不自动打开真实串口。
- 不自动驱动舵机或让机器人行走。
- 不自动更改接线、电源、PCB 或舵机角度限制。

原因：

- 软件代理无法直接确认实体机器人的供电、接线、机械干涉和周边安全。
- 错误动作可能损坏舵机、开发板、电池或机械结构。

影响：

- 软件阶段以编译、单元测试和 Mock 测试为主。
- 需要真实硬件验证时，必须暂停并给用户具体步骤、预期结果和风险说明。

## ADR-006: Strict JSON API and Action-Bound Confirmation

Status: accepted.

Decision:
- Firmware `/api/command` uses ArduinoJson with a 512-byte body limit.
- Firmware and Mock use the same error names and response shape.
- Dangerous AI-controller actions use action-bound, expiring, one-time confirmation grants.
- `reset_emergency_stop`, `self_righting`, and `charging_dock` require confirmation before execution planning.
- `stand` is not treated as validated real self-righting.
- Charging remains an intent because no real dock hardware or navigation stack exists.

Reason:
- String-search JSON parsing cannot safely reject malformed objects or wrong field types.
- Tuple-based confirmations can be replayed or reused across actions.
- Real hardware recovery actions need an explicit, auditable gate.

Impact:
- Mock protocol tests now validate types, oversize bodies, non-object JSON, and stable error payloads.
- Runtime CLI supports mock/simulator dry-run JSON output.
- `real_robot` remains blocked by default.

## ADR-007: Runtime Owns Confirmation Grants

Status: accepted.

Decision:
- `RobotRuntime` is the owner of `ConfirmationStore`.
- `BehaviorArbiter` may report that an action requires confirmation, but it does not create a store, persist a request, or accept public grants.
- Callers submit only `confirmation_id`; Runtime computes the current context and calls `ConfirmationStore.consume()` to validate and consume in one operation.
- `user_confirmed_actions` and externally supplied `ConfirmationGrant` inputs are removed.
- `ConfirmationStore.consume()` uses an internal lock and marks an accepted confirmation as used before Runtime dispatches the selected command.
- Confirmation TTL uses monotonic time, rejects zero or negative values, rejects values above 300 seconds, and expires when `now >= expiresAt`.
- Runtime logs store confirmation ID fingerprints instead of complete confirmation IDs.

Reason:
- A temporary store in Arbiter cannot validate a later user confirmation.
- Action strings and caller-constructed grants can bypass safety.
- Confirmation validation and consumption must be atomic to prevent replay.
- Command dispatch failure must not make a previously accepted confirmation reusable.

Impact:
- Confirmation lifecycle tests now assert `unknown_id`, `expired`, `action_mismatch`, `context_changed`, and `already_used`.
- Runtime logs record real safety severity and confirmation state.
- Concurrent consume tests assert that only one caller can accept a confirmation ID.
- Action parameter changes are represented in the context fingerprint and invalidate the confirmation.
