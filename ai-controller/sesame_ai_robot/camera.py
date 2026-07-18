from __future__ import annotations

from dataclasses import dataclass
import statistics
import time
from typing import Protocol


@dataclass(frozen=True)
class CameraFrame:
    width: int
    height: int
    captured_at: float
    source: str
    data: bytes


@dataclass(frozen=True)
class CameraStats:
    frames: int
    fps: float
    average_latency_ms: float
    max_latency_ms: float


class CameraSource(Protocol):
    name: str

    def read(self) -> CameraFrame:
        ...

    def close(self) -> None:
        ...


class MockCameraSource:
    name = "mock-camera"

    def __init__(self, width: int = 320, height: int = 240):
        self.width = width
        self.height = height
        self._frame_index = 0

    def read(self) -> CameraFrame:
        captured_at = time.monotonic()
        value = self._frame_index % 256
        self._frame_index += 1
        return CameraFrame(
            width=self.width,
            height=self.height,
            captured_at=captured_at,
            source=self.name,
            data=bytes([value]) * (self.width * self.height),
        )

    def close(self) -> None:
        return None


class OpenCVCameraSource:
    def __init__(self, index: int = 0):
        import cv2  # type: ignore[import-not-found]

        self.name = f"opencv-camera-{index}"
        self._cv2 = cv2
        self._capture = cv2.VideoCapture(index)
        if not self._capture.isOpened():
            raise RuntimeError(f"camera index {index} is not available")

    def read(self) -> CameraFrame:
        ok, frame = self._capture.read()
        captured_at = time.monotonic()
        if not ok:
            raise RuntimeError("failed to read camera frame")
        height, width = frame.shape[:2]
        return CameraFrame(
            width=int(width),
            height=int(height),
            captured_at=captured_at,
            source=self.name,
            data=frame.tobytes(),
        )

    def close(self) -> None:
        self._capture.release()


def enumerate_opencv_cameras(max_index: int = 5) -> list[int]:
    import cv2  # type: ignore[import-not-found]

    found: list[int] = []
    for index in range(max_index + 1):
        capture = cv2.VideoCapture(index)
        try:
            if capture.isOpened():
                found.append(index)
        finally:
            capture.release()
    return found


class CameraMonitor:
    def __init__(self, source: CameraSource):
        self.source = source

    def collect(self, frames: int = 30) -> CameraStats:
        if frames <= 0:
            raise ValueError("frames must be greater than zero")

        latencies: list[float] = []
        started_at = time.monotonic()
        for _ in range(frames):
            frame = self.source.read()
            latencies.append((time.monotonic() - frame.captured_at) * 1000)
        elapsed = max(time.monotonic() - started_at, 0.000001)
        return CameraStats(
            frames=frames,
            fps=frames / elapsed,
            average_latency_ms=statistics.fmean(latencies),
            max_latency_ms=max(latencies),
        )
