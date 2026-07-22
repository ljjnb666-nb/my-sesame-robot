from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Protocol

from .camera import CameraFrame


@dataclass(frozen=True)
class BoundingBox:
    x: float
    y: float
    width: float
    height: float

    @property
    def center_x(self) -> float:
        return self.x + self.width / 2

    @property
    def center_y(self) -> float:
        return self.y + self.height / 2

    def normalized(self, frame_width: int, frame_height: int) -> "BoundingBox":
        if frame_width <= 0 or frame_height <= 0:
            raise ValueError("frame dimensions must be greater than zero")
        return BoundingBox(
            x=self.x / frame_width,
            y=self.y / frame_height,
            width=self.width / frame_width,
            height=self.height / frame_height,
        )


@dataclass(frozen=True)
class Detection:
    label: str
    confidence: float
    box: BoundingBox
    distance_m: float | None = None

    @property
    def center(self) -> tuple[float, float]:
        return (self.box.center_x, self.box.center_y)


@dataclass(frozen=True)
class DetectionResult:
    source: str
    captured_at: float
    processed_at: float
    frame_width: int
    frame_height: int
    detections: tuple[Detection, ...]

    @property
    def latency_ms(self) -> float:
        return (self.processed_at - self.captured_at) * 1000

    def best(self, label: str | None = None) -> Detection | None:
        candidates = self.detections
        if label is not None:
            candidates = tuple(item for item in candidates if item.label == label)
        if not candidates:
            return None
        return max(candidates, key=lambda item: item.confidence)


class ObjectDetector(Protocol):
    name: str

    def detect(self, frame: CameraFrame) -> DetectionResult:
        ...


class MockObjectDetector:
    name = "mock-object-detector"

    def __init__(self, detections: tuple[Detection, ...] | None = None):
        self._detections = detections

    def detect(self, frame: CameraFrame) -> DetectionResult:
        detections = self._detections or (
            Detection(
                label="person",
                confidence=0.91,
                box=BoundingBox(
                    x=frame.width * 0.35,
                    y=frame.height * 0.15,
                    width=frame.width * 0.3,
                    height=frame.height * 0.7,
                ),
                distance_m=0.8,
            ),
            Detection(
                label="object",
                confidence=0.64,
                box=BoundingBox(
                    x=frame.width * 0.68,
                    y=frame.height * 0.55,
                    width=frame.width * 0.16,
                    height=frame.height * 0.18,
                ),
                distance_m=1.2,
            ),
        )
        return DetectionResult(
            source=frame.source,
            captured_at=frame.captured_at,
            processed_at=time.monotonic(),
            frame_width=frame.width,
            frame_height=frame.height,
            detections=detections,
        )


def result_to_jsonable(result: DetectionResult) -> dict[str, object]:
    return {
        "source": result.source,
        "capturedAt": result.captured_at,
        "processedAt": result.processed_at,
        "latencyMs": result.latency_ms,
        "frame": {
            "width": result.frame_width,
            "height": result.frame_height,
        },
        "detections": [
            {
                "label": detection.label,
                "confidence": detection.confidence,
                "center": {
                    "x": detection.center[0],
                    "y": detection.center[1],
                },
                "box": {
                    "x": detection.box.x,
                    "y": detection.box.y,
                    "width": detection.box.width,
                    "height": detection.box.height,
                },
                "distanceM": detection.distance_m,
            }
            for detection in result.detections
        ],
    }
