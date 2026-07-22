from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class ControllerConfig:
    robot_url: str = "http://127.0.0.1:8765"
    request_timeout_s: float = 2.0
    heartbeat_interval_s: float = 0.4
    reconnect_attempts: int = 3
    reconnect_delay_s: float = 0.5
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "ControllerConfig":
        return cls(
            robot_url=os.getenv("SESAME_ROBOT_URL", cls.robot_url).rstrip("/"),
            request_timeout_s=float(os.getenv("SESAME_REQUEST_TIMEOUT_S", cls.request_timeout_s)),
            heartbeat_interval_s=float(os.getenv("SESAME_HEARTBEAT_INTERVAL_S", cls.heartbeat_interval_s)),
            reconnect_attempts=int(os.getenv("SESAME_RECONNECT_ATTEMPTS", cls.reconnect_attempts)),
            reconnect_delay_s=float(os.getenv("SESAME_RECONNECT_DELAY_S", cls.reconnect_delay_s)),
            log_level=os.getenv("SESAME_LOG_LEVEL", cls.log_level),
        )
