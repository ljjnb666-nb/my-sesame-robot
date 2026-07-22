from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .detection import DetectionResult
from .face_identity import FaceRecognitionResult
from .safety import SafetyAssessment, SafetyMonitor, SensorSnapshot


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
    follow_start_distance_m: float = 1.2
    follow_stop_distance_m: float = 0.7


class TrackingController:
    def __init__(self, config: TrackingConfig | None = None, safety_monitor: SafetyMonitor | None = None):
        self.config = config or TrackingConfig()
        self.safety_monitor = safety_monitor or SafetyMonitor()
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
            command = "stop" if self._had_target else None
            return TrackingDecision(self.state, command, "owner identity is not confirmed")

        target = detections.best(self.config.target_label)
        if target is None:
            self.state = TrackingState.SEARCHING if not self._had_target else TrackingState.TARGET_LOST
            command = "stop" if self._had_target else None
            return TrackingDecision(self.state, command, "target is not visible")

        self._had_target = True
        safety = self.safety_monitor.assess(SensorSnapshot.from_robot_status(robot_status))
        if not safety.allows_motion:
            self.state = TrackingState.STOPPED
            return TrackingDecision(self.state, safety.command, safety.reason)

        if not self.config.allow_following:
            self.state = TrackingState.TRACKING
            return TrackingDecision(self.state, None, "following is disabled until safety layer is complete")

        normalized_center_x = target.center[0] / max(detections.frame_width, 1)
        if normalized_center_x < 0.5 - self.config.center_deadband:
            command = "turn_left"
        elif normalized_center_x > 0.5 + self.config.center_deadband:
            command = "turn_right"
        elif target.distance_m is None:
            self.state = TrackingState.TRACKING
            return TrackingDecision(self.state, None, "target distance is unknown")
        elif target.distance_m <= self.config.follow_stop_distance_m:
            self.state = TrackingState.STOPPED
            return TrackingDecision(self.state, "stop", "target is too close")
        elif target.distance_m < self.config.follow_start_distance_m:
            self.state = TrackingState.TRACKING
            return TrackingDecision(self.state, None, "target is within follow hold distance")
        else:
            command = "walk_forward"

        self.state = TrackingState.FOLLOWING
        return TrackingDecision(self.state, command, "target confirmed and safety checks passed")
