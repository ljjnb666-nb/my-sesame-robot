from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol
import math
import time


class HardwareDispatchError(RuntimeError):
    pass


class HardwareSafetyError(HardwareDispatchError):
    pass


class ManualClock:
    def __init__(self, now: float = 0.0):
        self.now = now

    def monotonic(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("clock cannot advance by a negative duration")
        self.now += seconds


class RobotHardware(Protocol):
    def read_battery(self) -> dict[str, Any]:
        ...

    def read_pose(self) -> dict[str, Any]:
        ...

    def set_servo(self, servo_id: int, angle: float, speed: float = 90.0) -> dict[str, Any]:
        ...

    def set_motor(self, motor_id: int, power: float, duration: float) -> dict[str, Any]:
        ...

    def stop_all_actuators(self) -> None:
        ...

    def capture_camera_frame(self) -> dict[str, Any]:
        ...

    def capture_audio(self, duration: float) -> dict[str, Any]:
        ...

    def read_charging_state(self) -> dict[str, Any]:
        ...


@dataclass
class VirtualServo:
    servo_id: int
    current_angle: float = 90.0
    target_angle: float = 90.0
    min_angle: float = 0.0
    max_angle: float = 180.0
    speed: float = 90.0
    motion_started_at: float | None = None
    motion_ends_at: float | None = None
    stuck: bool = False
    overheated: bool = False
    offline: bool = False
    safety_limit_exceeded: bool = False

    def snapshot(self) -> dict[str, Any]:
        return {
            "servoId": self.servo_id,
            "currentAngle": self.current_angle,
            "targetAngle": self.target_angle,
            "minAngle": self.min_angle,
            "maxAngle": self.max_angle,
            "speed": self.speed,
            "motionStartedAt": self.motion_started_at,
            "motionEndsAt": self.motion_ends_at,
            "stuck": self.stuck,
            "overheated": self.overheated,
            "offline": self.offline,
            "safetyLimitExceeded": self.safety_limit_exceeded,
        }


@dataclass
class VirtualMotor:
    motor_id: int
    direction: str = "stop"
    power: float = 0.0
    duration: float = 0.0
    current_output: float = 0.0
    stalled: bool = False
    overcurrent: bool = False
    offline: bool = False
    auto_stop_at: float | None = None
    emergency_stopped: bool = False

    def snapshot(self) -> dict[str, Any]:
        return {
            "motorId": self.motor_id,
            "direction": self.direction,
            "power": self.power,
            "duration": self.duration,
            "currentOutput": self.current_output,
            "stalled": self.stalled,
            "overcurrent": self.overcurrent,
            "offline": self.offline,
            "autoStopAt": self.auto_stop_at,
            "emergencyStopped": self.emergency_stopped,
        }


@dataclass
class VirtualRobotState:
    runtime_mode: str = "simulator"
    robot_pose: str = "standing"
    battery_percent: int | None = 80
    battery_voltage: float | None = 7.4
    charging_state: str = "not_charging"
    communication_state: str = "connected"
    camera_state: str = "ok"
    microphone_state: str = "ok"
    hardware_enabled: bool = True
    experiment_enabled: bool = False
    emergency_stop: bool = False
    temperature_state: str = "normal"
    imu_roll_deg: float | None = 0.0
    imu_pitch_deg: float | None = 0.0
    faults: set[str] = field(default_factory=set)
    servos: dict[int, VirtualServo] = field(default_factory=lambda: {i: VirtualServo(i) for i in range(8)})
    motors: dict[int, VirtualMotor] = field(default_factory=lambda: {i: VirtualMotor(i) for i in range(2)})

    def snapshot(self) -> dict[str, Any]:
        return {
            "runtimeMode": self.runtime_mode,
            "robotPose": self.robot_pose,
            "battery": {"percent": self.battery_percent, "voltage": self.battery_voltage},
            "chargingState": self.charging_state,
            "communicationState": self.communication_state,
            "cameraState": self.camera_state,
            "microphoneState": self.microphone_state,
            "hardwareEnabled": self.hardware_enabled,
            "experimentEnabled": self.experiment_enabled,
            "emergencyStop": self.emergency_stop,
            "temperatureState": self.temperature_state,
            "pose": {"rollDeg": self.imu_roll_deg, "pitchDeg": self.imu_pitch_deg},
            "faults": sorted(self.faults),
            "servos": {str(k): servo.snapshot() for k, servo in self.servos.items()},
            "motors": {str(k): motor.snapshot() for k, motor in self.motors.items()},
        }


FAULTS = {
    "servo_stuck",
    "servo_offline",
    "servo_overheated",
    "motor_stall",
    "motor_overcurrent",
    "motor_offline",
    "battery_low",
    "battery_sensor_missing",
    "battery_voltage_invalid",
    "pose_sensor_missing",
    "pose_sensor_invalid",
    "pose_sensor_frozen",
    "camera_timeout",
    "camera_unavailable",
    "camera_black_frame",
    "microphone_unavailable",
    "microphone_timeout",
    "microphone_clipping",
    "communication_lost",
    "runtime_restart",
    "charging_contact_failed",
    "dispatch_failed",
}


class VirtualRobotHardware:
    def __init__(self, state: VirtualRobotState | None = None, clock: Any | None = None):
        self.state = state or VirtualRobotState()
        self._clock = clock.monotonic if hasattr(clock, "monotonic") else clock or time.monotonic
        self.events: list[dict[str, Any]] = []

    def read_battery(self) -> dict[str, Any]:
        self._apply_faults()
        if "battery_sensor_missing" in self.state.faults:
            return {"available": False, "percent": None, "voltage": None, "state": "missing"}
        return {
            "available": True,
            "percent": self.state.battery_percent,
            "voltage": self.state.battery_voltage,
            "state": self.state.charging_state,
        }

    def read_pose(self) -> dict[str, Any]:
        self._apply_faults()
        if "pose_sensor_missing" in self.state.faults:
            return {"available": False, "rollDeg": None, "pitchDeg": None, "state": "missing"}
        if "pose_sensor_invalid" in self.state.faults:
            return {"available": True, "rollDeg": math.nan, "pitchDeg": math.nan, "state": "invalid"}
        return {
            "available": True,
            "rollDeg": self.state.imu_roll_deg,
            "pitchDeg": self.state.imu_pitch_deg,
            "state": self.state.robot_pose,
        }

    def set_servo(self, servo_id: int, angle: float, speed: float = 90.0) -> dict[str, Any]:
        before = self.state.snapshot()
        try:
            self._ensure_dispatch_allowed("set_servo")
            servo = self._servo(servo_id)
            if servo.offline:
                raise HardwareSafetyError("servo is offline")
            if servo.stuck:
                raise HardwareSafetyError("servo is stuck")
            if servo.overheated:
                raise HardwareSafetyError("servo is overheated")
            if not servo.min_angle <= angle <= servo.max_angle:
                servo.safety_limit_exceeded = True
                raise HardwareSafetyError("servo angle is outside safe limits")
            if speed <= 0:
                raise HardwareSafetyError("servo speed must be greater than zero")
            now = self._now()
            travel = abs(angle - servo.current_angle)
            servo.target_angle = float(angle)
            servo.speed = float(speed)
            servo.motion_started_at = now
            servo.motion_ends_at = now + travel / speed
            servo.current_angle = float(angle)
            self._event("servo_motion_completed", "set_servo", "ok", servo_id=servo_id)
            return {"status": "ok", "servoId": servo_id, "angle": angle}
        except Exception as exc:
            if "communication is not connected" not in str(exc):
                self._restore_actuators(before)
            self._event("action_rejected", "set_servo", "rejected", reason=str(exc), servo_id=servo_id)
            raise

    def set_motor(self, motor_id: int, power: float, duration: float) -> dict[str, Any]:
        before = self.state.snapshot()
        try:
            self._ensure_dispatch_allowed("set_motor")
            motor = self._motor(motor_id)
            if motor.offline:
                raise HardwareSafetyError("motor is offline")
            if motor.stalled:
                raise HardwareSafetyError("motor is stalled")
            if motor.overcurrent:
                raise HardwareSafetyError("motor overcurrent")
            if not -1.0 <= power <= 1.0:
                raise HardwareSafetyError("motor power is outside safe limits")
            if duration < 0:
                raise HardwareSafetyError("motor duration must be non-negative")
            if duration > 5.0:
                raise HardwareSafetyError("motor duration exceeds simulator safety limit")
            now = self._now()
            motor.power = float(power)
            motor.duration = float(duration)
            motor.current_output = float(power)
            motor.direction = "forward" if power > 0 else "reverse" if power < 0 else "stop"
            motor.auto_stop_at = now + duration
            motor.emergency_stopped = False
            self._event("action_dispatched", "set_motor", "ok", motor_id=motor_id)
            if duration == 0:
                self._stop_motor(motor)
            return {"status": "ok", "motorId": motor_id, "power": power, "duration": duration}
        except Exception as exc:
            if "communication is not connected" not in str(exc):
                self._restore_actuators(before)
            self._event("action_rejected", "set_motor", "rejected", reason=str(exc), motor_id=motor_id)
            raise

    def stop_all_actuators(self) -> None:
        for motor in self.state.motors.values():
            self._stop_motor(motor)
            motor.emergency_stopped = True
        for servo in self.state.servos.values():
            servo.target_angle = servo.current_angle
            servo.motion_ends_at = self._now()
        self.state.emergency_stop = True
        self._event("emergency_stop", "stop_all_actuators", "ok")

    def capture_camera_frame(self) -> dict[str, Any]:
        self._apply_faults()
        if self.state.camera_state != "ok":
            raise HardwareSafetyError(f"camera {self.state.camera_state}")
        return {"kind": "virtual_frame", "width": 64, "height": 48, "blackFrame": False}

    def capture_audio(self, duration: float) -> dict[str, Any]:
        self._apply_faults()
        if duration < 0:
            raise HardwareSafetyError("audio duration must be non-negative")
        if self.state.microphone_state != "ok":
            raise HardwareSafetyError(f"microphone {self.state.microphone_state}")
        return {"kind": "virtual_audio", "duration": duration, "sampleRate": 16000, "clipped": False}

    def read_charging_state(self) -> dict[str, Any]:
        self._apply_faults()
        return {"state": self.state.charging_state, "contactSafe": self.state.charging_state != "contact_failed"}

    def inject_fault(self, fault: str) -> None:
        if fault not in FAULTS:
            raise ValueError(f"unknown fault: {fault}")
        self.state.faults.add(fault)
        self._apply_faults()
        self._event("fault_injected", None, "ok", fault=fault)

    def clear_fault(self, fault: str | None = None) -> None:
        if fault is None or fault == "all":
            self.state.faults.clear()
        else:
            self.state.faults.discard(fault)
        self._reset_fault_surfaces()
        self._apply_faults()
        self._event("fault_cleared", None, "ok", fault=fault or "all")

    def tick(self) -> None:
        now = self._now()
        for motor in self.state.motors.values():
            if motor.auto_stop_at is not None and now >= motor.auto_stop_at:
                self._stop_motor(motor)
                self._event("motor_auto_stopped", "set_motor", "ok", motor_id=motor.motor_id)

    def _ensure_dispatch_allowed(self, action: str) -> None:
        self._apply_faults()
        if self.state.emergency_stop:
            raise HardwareSafetyError("emergency stop is active")
        if not self.state.hardware_enabled:
            raise HardwareSafetyError("hardware switch is disabled")
        if self.state.communication_state != "connected":
            self.stop_all_actuators()
            raise HardwareSafetyError("communication is not connected")
        if "dispatch_failed" in self.state.faults:
            raise HardwareDispatchError("dispatch failed")
        if self.state.battery_percent is None:
            raise HardwareSafetyError("battery data is missing")
        if self.state.battery_percent < 10 and action == "set_motor":
            raise HardwareSafetyError("battery is too low for motor output")
        if self.state.imu_roll_deg is None or self.state.imu_pitch_deg is None:
            raise HardwareSafetyError("pose data is missing")
        if not _finite(self.state.imu_roll_deg) or not _finite(self.state.imu_pitch_deg):
            raise HardwareSafetyError("pose data is invalid")

    def _servo(self, servo_id: int) -> VirtualServo:
        if servo_id not in self.state.servos:
            raise HardwareSafetyError(f"unknown servo id: {servo_id}")
        return self.state.servos[servo_id]

    def _motor(self, motor_id: int) -> VirtualMotor:
        if motor_id not in self.state.motors:
            raise HardwareSafetyError(f"unknown motor id: {motor_id}")
        return self.state.motors[motor_id]

    def _apply_faults(self) -> None:
        if "communication_lost" in self.state.faults:
            self.state.communication_state = "lost"
        if "battery_low" in self.state.faults:
            self.state.battery_percent = 5
        if "battery_sensor_missing" in self.state.faults:
            self.state.battery_percent = None
            self.state.battery_voltage = None
        if "battery_voltage_invalid" in self.state.faults:
            self.state.battery_voltage = None
        if "pose_sensor_missing" in self.state.faults:
            self.state.imu_roll_deg = None
            self.state.imu_pitch_deg = None
        if "pose_sensor_invalid" in self.state.faults:
            self.state.imu_roll_deg = math.nan
            self.state.imu_pitch_deg = math.nan
        if "camera_timeout" in self.state.faults:
            self.state.camera_state = "timeout"
        if "camera_unavailable" in self.state.faults:
            self.state.camera_state = "unavailable"
        if "camera_black_frame" in self.state.faults:
            self.state.camera_state = "black_frame"
        if "microphone_unavailable" in self.state.faults:
            self.state.microphone_state = "unavailable"
        if "microphone_timeout" in self.state.faults:
            self.state.microphone_state = "timeout"
        if "microphone_clipping" in self.state.faults:
            self.state.microphone_state = "clipping"
        if "charging_contact_failed" in self.state.faults:
            self.state.charging_state = "contact_failed"
        for servo in self.state.servos.values():
            servo.offline = "servo_offline" in self.state.faults
            servo.stuck = "servo_stuck" in self.state.faults
            servo.overheated = "servo_overheated" in self.state.faults
        for motor in self.state.motors.values():
            motor.offline = "motor_offline" in self.state.faults
            motor.stalled = "motor_stall" in self.state.faults
            motor.overcurrent = "motor_overcurrent" in self.state.faults

    def _reset_fault_surfaces(self) -> None:
        self.state.communication_state = "connected"
        self.state.camera_state = "ok"
        self.state.microphone_state = "ok"
        self.state.charging_state = "not_charging"
        if "battery_low" not in self.state.faults:
            self.state.battery_percent = 80
        if self.state.battery_percent is None:
            self.state.battery_percent = 80
        if self.state.battery_voltage is None:
            self.state.battery_voltage = 7.4
        if self.state.imu_roll_deg is None or not _finite(self.state.imu_roll_deg):
            self.state.imu_roll_deg = 0.0
        if self.state.imu_pitch_deg is None or not _finite(self.state.imu_pitch_deg):
            self.state.imu_pitch_deg = 0.0
        for servo in self.state.servos.values():
            servo.offline = False
            servo.stuck = False
            servo.overheated = False
        for motor in self.state.motors.values():
            motor.offline = False
            motor.stalled = False
            motor.overcurrent = False

    def _restore_actuators(self, snapshot: dict[str, Any]) -> None:
        for key, servo_snapshot in snapshot["servos"].items():
            servo = self.state.servos[int(key)]
            servo.current_angle = servo_snapshot["currentAngle"]
            servo.target_angle = servo_snapshot["targetAngle"]
            servo.speed = servo_snapshot["speed"]
            servo.motion_started_at = servo_snapshot["motionStartedAt"]
            servo.motion_ends_at = servo_snapshot["motionEndsAt"]
        for key, motor_snapshot in snapshot["motors"].items():
            motor = self.state.motors[int(key)]
            motor.direction = motor_snapshot["direction"]
            motor.power = motor_snapshot["power"]
            motor.duration = motor_snapshot["duration"]
            motor.current_output = motor_snapshot["currentOutput"]
            motor.auto_stop_at = motor_snapshot["autoStopAt"]
            motor.emergency_stopped = motor_snapshot["emergencyStopped"]

    def _stop_motor(self, motor: VirtualMotor) -> None:
        motor.direction = "stop"
        motor.power = 0.0
        motor.duration = 0.0
        motor.current_output = 0.0
        motor.auto_stop_at = None

    def _event(self, event_type: str, action: str | None, result: str, **extra: Any) -> None:
        self.events.append({
            "time": self._now(),
            "eventType": event_type,
            "action": action,
            "safetySeverity": "emergency_stop" if self.state.emergency_stop else "ok",
            "runtimeMode": self.state.runtime_mode,
            "result": result,
            **extra,
        })

    def _now(self) -> float:
        return float(self._clock())


class MockHardwareAdapter(VirtualRobotHardware):
    pass


class SimulatorHardwareAdapter(VirtualRobotHardware):
    pass


class HardwareAdapter:
    def __init__(self, *, device: str | None = None, baud: int = 115200, allow_open: bool = False):
        self.device = device
        self.baud = baud
        self.allow_open = allow_open
        self.connected = False

    def open(self) -> None:
        if not self.allow_open:
            raise HardwareSafetyError("hardware adapter requires explicit allow_open=True")
        raise NotImplementedError("real hardware transport is pending real hardware selection")


def _finite(value: float | None) -> bool:
    return value is not None and math.isfinite(value)


class VirtualHardwareRobotClient:
    def __init__(self, hardware: VirtualRobotHardware):
        self.hardware = hardware
        self.current_command = ""
        self.current_face = "default"

    def get_status(self):
        from .client import RobotStatus

        state = self.hardware.state
        return RobotStatus({
            "firmwareVersion": "virtual-hardware-simulator",
            "currentCommand": self.current_command,
            "currentFace": self.current_face,
            "motionState": "emergency_stop" if state.emergency_stop else "moving" if self.current_command else "idle",
            "motionInProgress": bool(self.current_command),
            "emergencyStopActive": state.emergency_stop,
            "communicationTimedOut": state.communication_state != "connected",
            "virtualBatteryPercent": state.battery_percent,
            "virtualSensors": {
                "frontDistanceM": 1.0,
                "leftDistanceM": 1.0,
                "rightDistanceM": 1.0,
                "cliffDetected": False,
                "collisionDetected": False,
                "imuRollDeg": state.imu_roll_deg,
                "imuPitchDeg": state.imu_pitch_deg,
            },
            "capabilities": ["virtual_hardware", "fault_injection", "safe_stop"],
        })

    def send_command(self, command: str, face: str | None = None) -> dict[str, Any]:
        if face is not None:
            self.current_face = face
        normalized = command.strip().lower()
        if normalized == "emergency_stop":
            self.hardware.stop_all_actuators()
            self.current_command = ""
            return {"status": "ok", "command": normalized}
        if normalized == "reset_emergency_stop":
            self.hardware.state.emergency_stop = False
            self.current_command = ""
            return {"status": "ok", "command": normalized}
        if normalized == "stop":
            for motor in self.hardware.state.motors.values():
                self.hardware._stop_motor(motor)
            self.current_command = ""
            return {"status": "ok", "command": normalized}
        if normalized in {"walk_forward", "walk_backward", "turn_left", "turn_right"}:
            power = 0.25
            if normalized in {"walk_backward", "turn_right"}:
                power = -0.25
            self.hardware.set_motor(0, power, 0.5)
            self.current_command = normalized
            return {"status": "ok", "command": normalized}
        if normalized == "stand":
            for servo_id in self.hardware.state.servos:
                self.hardware.set_servo(servo_id, 90.0, 180.0)
            self.current_command = normalized
            return {"status": "ok", "command": normalized}
        if normalized == "rest":
            for servo_id, angle in enumerate((45.0, 135.0, 45.0, 135.0, 45.0, 135.0, 45.0, 135.0)):
                self.hardware.set_servo(servo_id, angle, 180.0)
            self.current_command = normalized
            return {"status": "ok", "command": normalized}
        if normalized in {"heartbeat", "wave"}:
            self.current_command = normalized if normalized == "wave" else self.current_command
            return {"status": "ok", "command": normalized}
        raise HardwareSafetyError(f"unsupported virtual command: {command}")

    def set_face(self, face: str) -> dict[str, Any]:
        self.current_face = face
        return {"status": "ok", "face": face}
