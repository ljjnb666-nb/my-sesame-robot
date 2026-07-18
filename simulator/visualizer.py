from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AI_CONTROLLER = ROOT / "ai-controller"
if str(AI_CONTROLLER) not in sys.path:
    sys.path.insert(0, str(AI_CONTROLLER))

from sesame_ai_robot.client import RobotClient
from sesame_ai_robot.config import ControllerConfig
from sesame_ai_robot.mock_robot import MockRobotServer


DEMO_COMMANDS = ("stand", "walk_forward", "turn_left", "turn_right", "stop")


def render_status(status: dict[str, Any]) -> str:
    servos = status.get("virtualServoAngles", [90] * 8)
    sensors = status.get("virtualSensors", {})
    lines = [
        "Sesame Robot Simulator",
        "=" * 48,
        f"Connected: yes   E-Stop: {status.get('emergencyStopActive')}   Timeout: {status.get('communicationTimedOut')}",
        f"Action: {status.get('currentCommand') or 'idle'}   Motion: {status.get('motionState')}   Face: {status.get('currentFace')}",
        f"Battery: {status.get('virtualBatteryPercent', 'n/a')}%",
        "",
        "Virtual servos",
    ]
    for index, angle in enumerate(servos, start=1):
        lines.append(f"  S{index}: {angle:>3} deg {servo_bar(int(angle))}")
    lines.extend([
        "",
        "Virtual sensors",
        f"  Front: {sensors.get('frontDistanceM', 'n/a')} m",
        f"  Left : {sensors.get('leftDistanceM', 'n/a')} m",
        f"  Right: {sensors.get('rightDistanceM', 'n/a')} m",
        f"  Cliff: {sensors.get('cliffDetected', False)}",
        f"  Collision: {sensors.get('collisionDetected', False)}",
        f"  IMU roll/pitch: {sensors.get('imuRollDeg', 'n/a')} / {sensors.get('imuPitchDeg', 'n/a')} deg",
        "",
        "OLED",
        oled_face(str(status.get("currentFace", "default"))),
    ])
    return "\n".join(lines)


def servo_bar(angle: int) -> str:
    clamped = max(0, min(180, angle))
    filled = round(clamped / 180 * 18)
    return "[" + "#" * filled + "." * (18 - filled) + "]"


def oled_face(face: str) -> str:
    faces = {
        "default": "( ._.)",
        "stand": "( ^_^)",
        "walk": "( o_o)",
        "rest": "(-_- ) zZ",
        "happy": "( ^o^)",
    }
    return f"  {faces.get(face, faces['default'])}"


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def run_visualizer(refresh_s: float, once: bool, demo: bool) -> None:
    server = MockRobotServer(port=0)
    server.start()
    client = RobotClient(ControllerConfig(robot_url=server.url, request_timeout_s=1.0))
    demo_index = 0
    last_demo_at = 0.0

    try:
        while True:
            now = time.monotonic()
            if demo and now - last_demo_at >= 1.0:
                client.send_command(DEMO_COMMANDS[demo_index % len(DEMO_COMMANDS)])
                demo_index += 1
                last_demo_at = now

            status = client.get_status().raw
            if not once:
                clear_screen()
            print(render_status(status))
            if once:
                return
            time.sleep(refresh_s)
    finally:
        server.stop()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a simple Sesame simulator state visualizer")
    parser.add_argument("--refresh-s", type=float, default=0.5)
    parser.add_argument("--once", action="store_true", help="Render one frame and exit")
    parser.add_argument("--demo", action="store_true", help="Cycle through virtual commands")
    args = parser.parse_args()

    run_visualizer(args.refresh_s, args.once, args.demo)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
