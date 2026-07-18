from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class SafetySeverity(str, Enum):
    OK = "ok"
    STOP = "stop"
    EMERGENCY_STOP = "emergency_stop"


@dataclass(frozen=True)
class SensorSnapshot:
    front_distance_m: float | None = None
    left_distance_m: float | None = None
    right_distance_m: float | None = None
    cliff_detected: bool = False
    collision_detected: bool = False
    imu_roll_deg: float | None = None
    imu_pitch_deg: float | None = None
    battery_percent: int | None = None

    @classmethod
    def from_robot_status(cls, status: dict[str, Any]) -> "SensorSnapshot":
        sensors = status.get("virtualSensors", {})
        return cls(
            front_distance_m=_optional_float(sensors.get("frontDistanceM")),
            left_distance_m=_optional_float(sensors.get("leftDistanceM")),
            right_distance_m=_optional_float(sensors.get("rightDistanceM")),
            cliff_detected=bool(sensors.get("cliffDetected", False)),
            collision_detected=bool(sensors.get("collisionDetected", False)),
            imu_roll_deg=_optional_float(sensors.get("imuRollDeg")),
            imu_pitch_deg=_optional_float(sensors.get("imuPitchDeg")),
            battery_percent=_optional_int(status.get("virtualBatteryPercent")),
        )


@dataclass(frozen=True)
class SafetyConfig:
    min_front_distance_m: float = 0.35
    min_side_distance_m: float = 0.18
    low_battery_percent: int = 15
    max_tilt_deg: float = 35.0


@dataclass(frozen=True)
class SafetyAssessment:
    severity: SafetySeverity
    command: str | None
    reason: str

    @property
    def allows_motion(self) -> bool:
        return self.severity == SafetySeverity.OK


class SafetyMonitor:
    def __init__(self, config: SafetyConfig | None = None):
        self.config = config or SafetyConfig()

    def assess(self, snapshot: SensorSnapshot) -> SafetyAssessment:
        if snapshot.collision_detected:
            return SafetyAssessment(SafetySeverity.EMERGENCY_STOP, "emergency_stop", "collision detected")
        if snapshot.cliff_detected:
            return SafetyAssessment(SafetySeverity.EMERGENCY_STOP, "emergency_stop", "cliff detected")

        if _abs_exceeds(snapshot.imu_roll_deg, self.config.max_tilt_deg):
            return SafetyAssessment(SafetySeverity.EMERGENCY_STOP, "emergency_stop", "roll angle exceeds safe limit")
        if _abs_exceeds(snapshot.imu_pitch_deg, self.config.max_tilt_deg):
            return SafetyAssessment(SafetySeverity.EMERGENCY_STOP, "emergency_stop", "pitch angle exceeds safe limit")

        if snapshot.front_distance_m is not None and snapshot.front_distance_m < self.config.min_front_distance_m:
            return SafetyAssessment(SafetySeverity.STOP, "stop", "front obstacle is too close")
        if snapshot.left_distance_m is not None and snapshot.left_distance_m < self.config.min_side_distance_m:
            return SafetyAssessment(SafetySeverity.STOP, "stop", "left obstacle is too close")
        if snapshot.right_distance_m is not None and snapshot.right_distance_m < self.config.min_side_distance_m:
            return SafetyAssessment(SafetySeverity.STOP, "stop", "right obstacle is too close")

        if snapshot.battery_percent is not None and snapshot.battery_percent < self.config.low_battery_percent:
            return SafetyAssessment(SafetySeverity.STOP, "stop", "battery is low")

        return SafetyAssessment(SafetySeverity.OK, None, "sensors are within safe limits")


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    return None


def _abs_exceeds(value: float | None, limit: float) -> bool:
    return value is not None and abs(value) > limit
