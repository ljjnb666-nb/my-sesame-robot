from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .safety import SensorSnapshot


class RuntimeMode(str, Enum):
    MOCK = "mock"
    SIMULATOR = "simulator"
    REAL_ROBOT = "real_robot"


class AdvancedFeature(str, Enum):
    FALL_DETECTION = "fall_detection"
    SELF_RIGHTING = "self_righting"
    TERRAIN_ADAPTATION = "terrain_adaptation"
    EMOTION_STATE = "emotion_state"
    MEMORY = "memory"
    CHARGING_DOCK = "charging_dock"


class PostureState(str, Enum):
    NORMAL = "normal"
    TILTED = "tilted"
    FALLEN = "fallen"


class TerrainState(str, Enum):
    LEVEL = "level"
    UNEVEN = "uneven"
    UNSAFE = "unsafe"


class ChargingIntent(str, Enum):
    NONE = "none"
    SEEK_DOCK = "seek_dock"
    WAIT_FOR_USER = "wait_for_user"


@dataclass(frozen=True)
class AdvancedFeatureConfig:
    runtime_mode: RuntimeMode = RuntimeMode.MOCK
    allow_self_righting: bool = False
    allow_auto_docking: bool = False
    tilted_deg: float = 18.0
    fallen_deg: float = 60.0
    low_battery_dock_percent: int = 25


@dataclass(frozen=True)
class AdvancedDecision:
    feature: AdvancedFeature
    state: str
    command: str | None
    reason: str
    requires_user_confirmation: bool = False


@dataclass(frozen=True)
class EmotionState:
    mood: str = "neutral"
    arousal: float = 0.2
    confidence: float = 0.5

    @classmethod
    def from_context(cls, owner_visible: bool, battery_percent: int | None, emergency_stop_active: bool) -> "EmotionState":
        if emergency_stop_active:
            return cls("alarmed", 0.9, 0.8)
        if battery_percent is not None and battery_percent < 20:
            return cls("tired", 0.4, 0.7)
        if owner_visible:
            return cls("happy", 0.5, 0.7)
        return cls()


@dataclass(frozen=True)
class MemoryRecord:
    key: str
    value: str
    tags: tuple[str, ...] = ()


@dataclass
class MockMemoryStore:
    records: dict[str, MemoryRecord] = field(default_factory=dict)

    def remember(self, key: str, value: str, tags: tuple[str, ...] = ()) -> MemoryRecord:
        record = MemoryRecord(key.strip(), value.strip(), tags)
        self.records[record.key] = record
        return record

    def recall(self, key: str) -> MemoryRecord | None:
        return self.records.get(key.strip())


class AdvancedBehaviorPlanner:
    def __init__(self, config: AdvancedFeatureConfig | None = None):
        self.config = config or AdvancedFeatureConfig()

    def assess_posture(self, snapshot: SensorSnapshot) -> AdvancedDecision:
        tilt = _max_abs(snapshot.imu_roll_deg, snapshot.imu_pitch_deg)
        if tilt >= self.config.fallen_deg:
            return AdvancedDecision(
                AdvancedFeature.FALL_DETECTION,
                PostureState.FALLEN.value,
                "emergency_stop",
                "fall detected from IMU tilt",
            )
        if tilt >= self.config.tilted_deg:
            return AdvancedDecision(
                AdvancedFeature.FALL_DETECTION,
                PostureState.TILTED.value,
                "stop",
                "large tilt detected",
            )
        return AdvancedDecision(
            AdvancedFeature.FALL_DETECTION,
            PostureState.NORMAL.value,
            None,
            "posture is within mock limits",
        )

    def plan_self_righting(self, posture: PostureState) -> AdvancedDecision:
        if posture != PostureState.FALLEN:
            return AdvancedDecision(
                AdvancedFeature.SELF_RIGHTING,
                posture.value,
                None,
                "self-righting is only considered after a fall",
            )

        if self.config.runtime_mode == RuntimeMode.REAL_ROBOT:
            return AdvancedDecision(
                AdvancedFeature.SELF_RIGHTING,
                posture.value,
                None,
                "real robot self-righting requires explicit user confirmation",
                requires_user_confirmation=True,
            )

        if not self.config.allow_self_righting:
            return AdvancedDecision(
                AdvancedFeature.SELF_RIGHTING,
                posture.value,
                None,
                "mock self-righting is disabled by policy",
            )

        return AdvancedDecision(
            AdvancedFeature.SELF_RIGHTING,
            posture.value,
            "stand",
            "mock self-righting can request a high-level stand command",
        )

    def assess_terrain(self, snapshot: SensorSnapshot) -> AdvancedDecision:
        tilt = _max_abs(snapshot.imu_roll_deg, snapshot.imu_pitch_deg)
        if snapshot.cliff_detected or snapshot.collision_detected:
            return AdvancedDecision(
                AdvancedFeature.TERRAIN_ADAPTATION,
                TerrainState.UNSAFE.value,
                "emergency_stop",
                "terrain sensor indicates unsafe condition",
            )
        if tilt >= self.config.tilted_deg:
            return AdvancedDecision(
                AdvancedFeature.TERRAIN_ADAPTATION,
                TerrainState.UNEVEN.value,
                "stop",
                "terrain appears uneven in mock IMU data",
            )
        return AdvancedDecision(
            AdvancedFeature.TERRAIN_ADAPTATION,
            TerrainState.LEVEL.value,
            None,
            "terrain appears level",
        )

    def plan_charging(self, snapshot: SensorSnapshot) -> AdvancedDecision:
        battery = snapshot.battery_percent
        if battery is None or battery >= self.config.low_battery_dock_percent:
            return AdvancedDecision(
                AdvancedFeature.CHARGING_DOCK,
                ChargingIntent.NONE.value,
                None,
                "battery does not require docking",
            )

        if self.config.runtime_mode == RuntimeMode.REAL_ROBOT:
            return AdvancedDecision(
                AdvancedFeature.CHARGING_DOCK,
                ChargingIntent.WAIT_FOR_USER.value,
                "stop",
                "real docking requires explicit user confirmation",
                requires_user_confirmation=True,
            )

        if not self.config.allow_auto_docking:
            return AdvancedDecision(
                AdvancedFeature.CHARGING_DOCK,
                ChargingIntent.WAIT_FOR_USER.value,
                "stop",
                "auto docking is disabled by policy",
            )

        return AdvancedDecision(
            AdvancedFeature.CHARGING_DOCK,
            ChargingIntent.SEEK_DOCK.value,
            None,
            "mock docking intent is available but not wired to a robot command",
        )


def _max_abs(*values: float | None) -> float:
    numeric = [abs(value) for value in values if value is not None]
    return max(numeric, default=0.0)
