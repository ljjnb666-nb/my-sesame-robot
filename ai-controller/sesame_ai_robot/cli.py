from __future__ import annotations

import argparse
import json

from .client import RobotClient
from .config import ControllerConfig
from .camera import CameraMonitor, MockCameraSource, OpenCVCameraSource, enumerate_opencv_cameras
from .logging_config import configure_logging
from .mock_robot import MockRobotServer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sesame AI Robot controller")
    parser.add_argument("--robot-url", default=None, help="Robot base URL, default from SESAME_ROBOT_URL or mock URL")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="Read robot status")

    command_parser = subparsers.add_parser("command", help="Send a supported robot command")
    command_parser.add_argument("robot_command")
    command_parser.add_argument("--face", default=None)

    face_parser = subparsers.add_parser("face", help="Set face without moving")
    face_parser.add_argument("face")

    subparsers.add_parser("emergency-stop", help="Latch software emergency stop")
    subparsers.add_parser("reset-emergency-stop", help="Clear software emergency stop")
    subparsers.add_parser("heartbeat", help="Refresh active continuous movement")

    mock_parser = subparsers.add_parser("mock-server", help="Run local mock robot server")
    mock_parser.add_argument("--host", default="127.0.0.1")
    mock_parser.add_argument("--port", type=int, default=8765)

    camera_parser = subparsers.add_parser("camera-smoke", help="Read camera frames and print FPS/latency stats")
    camera_parser.add_argument("--mock", action="store_true", help="Use generated frames instead of a real camera")
    camera_parser.add_argument("--index", type=int, default=0)
    camera_parser.add_argument("--frames", type=int, default=30)

    camera_list_parser = subparsers.add_parser("camera-list", help="List OpenCV camera indexes")
    camera_list_parser.add_argument("--max-index", type=int, default=5)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = ControllerConfig.from_env()
    configure_logging(config.log_level)

    if args.command == "mock-server":
        server = MockRobotServer(args.host, args.port)
        print(f"Mock robot listening at {server.url}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            return 0

    if args.command == "camera-list":
        print(json.dumps({"cameras": enumerate_opencv_cameras(args.max_index)}, ensure_ascii=False, indent=2))
        return 0

    if args.command == "camera-smoke":
        source = MockCameraSource() if args.mock else OpenCVCameraSource(args.index)
        try:
            stats = CameraMonitor(source).collect(args.frames)
        finally:
            source.close()
        print(json.dumps(stats.__dict__, ensure_ascii=False, indent=2))
        return 0

    if args.robot_url:
        config = ControllerConfig(
            robot_url=args.robot_url,
            request_timeout_s=config.request_timeout_s,
            heartbeat_interval_s=config.heartbeat_interval_s,
            reconnect_attempts=config.reconnect_attempts,
            reconnect_delay_s=config.reconnect_delay_s,
            log_level=config.log_level,
        )
    client = RobotClient(config)

    if args.command == "status":
        print(json.dumps(client.get_status().raw, ensure_ascii=False, indent=2))
    elif args.command == "command":
        print(json.dumps(client.send_command(args.robot_command, args.face), ensure_ascii=False, indent=2))
    elif args.command == "face":
        print(json.dumps(client.set_face(args.face), ensure_ascii=False, indent=2))
    elif args.command == "emergency-stop":
        print(json.dumps(client.emergency_stop(), ensure_ascii=False, indent=2))
    elif args.command == "reset-emergency-stop":
        print(json.dumps(client.reset_emergency_stop(), ensure_ascii=False, indent=2))
    elif args.command == "heartbeat":
        print(json.dumps(client.heartbeat(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
