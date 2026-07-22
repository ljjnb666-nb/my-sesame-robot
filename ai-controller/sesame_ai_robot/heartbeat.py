from __future__ import annotations

import logging
import threading
import time

from .client import RobotClient, RobotClientError

LOGGER = logging.getLogger(__name__)


class HeartbeatLoop:
    def __init__(self, client: RobotClient, interval_s: float):
        self.client = client
        self.interval_s = interval_s
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="sesame-heartbeat", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=self.interval_s + 1.0)

    def tick(self) -> bool:
        try:
            self.client.heartbeat()
            return True
        except RobotClientError as exc:
            LOGGER.warning("heartbeat failed: %s", exc)
            return False

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self.tick()
            self._stop_event.wait(self.interval_s)
