# Hardware BOM Draft

This is a planning draft, not a final purchase decision. Unknown models and electrical values are intentionally marked as `待真实硬件选型后确定`.

## Minimum Runnable Version

| 项目 | 必要性 | 软件接口要求 | 关键参数 | 是否已确定 | 备注 |
| -- | --- | ------ | ---- | ----- | -- |
| 主控板 | 必需 | ESP32 firmware build target | Lolin S2 Mini compatible, FQBN `esp32:esp32:lolin_s2_mini` | 部分确定 | Use current verified firmware target |
| 舵机 | 必需 | 8 servo channels, angle limits | Safe angle range and current draw待确认 | 否 | Do not assume direction or limits before bench test |
| 电机及驱动 | 可选 | `set_motor` high-level power/duration | Driver voltage/current待确认 | 否 | Only needed for future non-servo drive additions |
| 电池 | 可选 | Battery percent/voltage status | Chemistry, capacity, protection待确认 | 否 | USB-only bring-up can precede battery work |
| 电源管理 | 必需 | Low-battery and voltage fault reporting | Regulator current and thermal headroom待确认 | 否 | Keep actuator power budget conservative |
| USB 数据线 | 必需 | Firmware build/flash by human operator | Data-capable USB cable | 否 | No automated upload in Codex tasks |
| 调试工具 | 推荐 | Human-controlled logs only | Serial adapter if needed待确认 | 否 | Do not open serial from automation |
| 万用表 | 必需 | None | Voltage, continuity, resistance | 否 | Required before first power |
| 保险丝和开关 | 必需 | Hardware emergency cutoff | Rating待选型确认 | 否 | Must be reachable during actuator tests |
| 螺丝和固定件 | 必需 | None | Mechanical fit待确认 | 否 | Match printed parts |

## Recommended Development Version

| 项目 | 必要性 | 软件接口要求 | 关键参数 | 是否已确定 | 备注 |
| -- | --- | ------ | ---- | ----- | -- |
| 摄像头 | 推荐 | `capture_camera_frame` with timeout/error states | Resolution, FPS, mounting, privacy workflow待确认 | 否 | Start with mock/images before real camera |
| 麦克风 | 推荐 | `capture_audio` with unavailable/timeout/clipping states | Sample rate, gain, noise floor待确认 | 否 | Local-only by default |
| 姿态传感器 | 推荐 | Roll/pitch, missing/invalid/frozen states | IMU bus, orientation, calibration待确认 | 否 | Needed before movement safety claims |
| 线材和接插件 | 必需 | None | Current rating, polarity marking待确认 | 否 | Label actuator power separately |
| 舵机独立供电 | 推荐 | Low-voltage fault visibility | Voltage/current待确认 | 否 | Avoid powering servos from USB |
| 电机驱动隔离 | 可选 | Fault states for stall/overcurrent/offline | Driver protection待确认 | 否 | Only if motors are added |

## Complete Robot Version

| 项目 | 必要性 | 软件接口要求 | 关键参数 | 是否已确定 | 备注 |
| -- | --- | ------ | ---- | ----- | -- |
| 充电模块 | 可选 | Charging state and fault reporting | Charge IC, cell chemistry, cutoff behavior待确认 | 否 | Do not test until power path is verified |
| 充电底座材料 | 可选 | Dock detection/contact result | Alignment, polarity protection, contact material待确认 | 否 | Contact tests require staged hardware validation |
| 机械结构 | 必需 | Pose and actuator limits feed safety policy | Print material, tolerances, binding points待确认 | 部分确定 | Existing CAD/STL available, actual print未验证 |
| 电源管理扩展 | 推荐 | Battery, voltage fault, charging states | Fuse, switch, regulator, connector ratings待确认 | 否 | Must pass wiring checklist |

Avoid buying the complete robot bill at the start. Bring up controller, firmware build, mock/simulator validation, and power checks first; then add actuators and sensors in staged tests.
