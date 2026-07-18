from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .detection import DetectionResult
from .face_identity import FaceRecognitionResult


class TrackingState(str, Enum):
    IDLE = "idle"
    SEARCHING = "searching"
    TRACKING = "tracking"
    FOLLOWING = "following"
    TARGET_LOST = "target_lost"
    STOPPED = "stopped"
    EMERGENCY_STOP = "emergency_stop"


@dataclass(frozen=True)
class TrackingDecision:
    state: TrackingState
    command: str | None
    reason: str


@dataclass(frozen=True)
class TrackingConfig:
    allow_following: bool = False
    target_label: str = "person"
    center_deadband: float = 0.12
    safe_front_distance_m: float = 0.35


class TrackingController:
    def __init__(self, config: TrackingConfig | None = None):
        self.config = config or TrackingConfig()
        self.state = TrackingState.IDLE
        self._had_target = False

    def update(
        self,
        detections: DetectionResult,
        identity: FaceRecognitionResult,
        robot_status: dict[str, Any],
    ) -> TrackingDecision:
        if robot_status.get("emergencyStopActive", False):
            self.state = TrackingState.EMERGENCY_STOP
            return TrackingDecision(self.state, None, "robot emergency stop is active")

        if robot_status.get("communicationTimedOut", False):
            self.state = TrackingState.STOPPED
            return TrackingDecision(self.state, "stop", "robot communication timed out")

        if not identity.confirmed:
            self.state = TrackingState.SEARCHING if not self._had_target else TrackingState.TARGET_LOST
            return TrackingDecision(self.state, None, "owner identity is not confirmed")

        target = detections.best(self.config.target_label)
        if target is None:
            self.state = TrackingState.SEARCHING if not self._had_target else TrackingState.TARGET_LOST
            return TrackingDecision(self.state, None, "target is not visible")

        self._had_target = True
        sensors = robot_status.get("virtualSensors", {})
        front_distance = sensors.get("frontDistanceM")
        if isinstance(front_distance, (int, float)) and front_distance < self.config.safe_front_distance_m:
            self.state = TrackingState.STOPPED
            return TrackingDecision(self.state, "stop", "front obstacle is too close")

        if not self.config.allow_following:
            self.state = TrackingState.TRACKING
            return TrackingDecision(self.state, None, "following is disabled until safety layer is complete")

        normalized_center_x = target.center[0] / max(detections.frame_width, 1)
        if normalized_center_x < 0.5 - self.config.center_deadband:
            command = "turn_left"
        elif normalized_center_x > 0.5 + self.config.center_deadband:
            command = "turn_right"
        else:
            command = "walk_forward"

        self.state = TrackingState.FOLLOWING
        return TrackingDecision(self.state, command, "target confirmed and safety checks passed")
