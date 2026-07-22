from __future__ import annotations

import argparse
import json

from .client import RobotClient
from .config import ControllerConfig
from .camera import CameraMonitor, MockCameraSource, OpenCVCameraSource, enumerate_opencv_cameras
from .logging_config import configure_logging
from .mock_robot import MockRobotServer, MockRobotState
from .detection import MockObjectDetector, result_to_jsonable as detection_result_to_jsonable
from .face_identity import FaceIdentity, MockFaceRecognizer, recognition_to_jsonable
from .assistant import AssistantPolicy, MockAssistantPipeline, plan_to_jsonable
from .advanced import RuntimeMode
from .runtime import RobotRuntime, RobotRuntimeConfig, result_to_jsonable as runtime_result_to_jsonable
from .tracking import TrackingDecision, TrackingState


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

    detect_parser = subparsers.add_parser("detect-smoke", help="Run one object detection pass")
    detect_parser.add_argument("--mock", action="store_true", help="Use generated frames and mock detections")
    detect_parser.add_argument("--index", type=int, default=0)

    face_parser = subparsers.add_parser("face-id-smoke", help="Run one face identity pass with mock data")
    face_parser.add_argument("--confidence", type=float, default=0.82)
    face_parser.add_argument("--threshold", type=float, default=0.75)

    assistant_parser = subparsers.add_parser("assistant-smoke", help="Run the local mock assistant pipeline")
    assistant_parser.add_argument("text")
    assistant_parser.add_argument("--allow-motion", action="store_true")

    for name in ("runtime-step", "runtime-run"):
        runtime_parser = subparsers.add_parser(name, help="Run RobotRuntime without hardware by default")
        runtime_parser.add_argument("--mode", choices=[mode.value for mode in RuntimeMode], default=RuntimeMode.MOCK.value)
        runtime_parser.add_argument("--dry-run", action="store_true", default=False)
        runtime_parser.add_argument("--steps", type=int, default=1)
        runtime_parser.add_argument("--assistant-command", default=None)
        runtime_parser.add_argument("--identity-confirmed", action="store_true")
        runtime_parser.add_argument("--target-visible", action="store_true")
        runtime_parser.add_argument("--target-distance", type=float, default=None)
        runtime_parser.add_argument("--imu-roll", type=float, default=0.0)
        runtime_parser.add_argument("--imu-pitch", type=float, default=0.0)
        runtime_parser.add_argument("--battery-percent", type=int, default=100)
        runtime_parser.add_argument("--cliff-detected", action="store_true")
        runtime_parser.add_argument("--collision-detected", action="store_true")
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
        try:
            print(json.dumps({"cameras": enumerate_opencv_cameras(args.max_index)}, ensure_ascii=False, indent=2))
        except RuntimeError as exc:
            print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2))
            return 1
        return 0

    if args.command == "camera-smoke":
        try:
            source = MockCameraSource() if args.mock else OpenCVCameraSource(args.index)
        except RuntimeError as exc:
            print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2))
            return 1
        try:
            stats = CameraMonitor(source).collect(args.frames)
        finally:
            source.close()
        print(json.dumps(stats.__dict__, ensure_ascii=False, indent=2))
        return 0

    if args.command == "detect-smoke":
        source = MockCameraSource() if args.mock else OpenCVCameraSource(args.index)
        try:
            frame = source.read()
            result = MockObjectDetector().detect(frame)
        finally:
            source.close()
        print(json.dumps(detection_result_to_jsonable(result), ensure_ascii=False, indent=2))
        return 0

    if args.command == "face-id-smoke":
        identity = FaceIdentity(identity_id="owner-local", display_name="Owner", created_at=0.0)
        result = MockFaceRecognizer(identity, args.confidence, args.threshold).identify(MockCameraSource().read())
        print(json.dumps(recognition_to_jsonable(result), ensure_ascii=False, indent=2))
        return 0

    if args.command == "assistant-smoke":
        pipeline = MockAssistantPipeline(policy=AssistantPolicy(allow_motion_commands=args.allow_motion))
        print(json.dumps(plan_to_jsonable(pipeline.handle_text(args.text)), ensure_ascii=False, indent=2))
        return 0

    if args.command in {"runtime-step", "runtime-run"}:
        mode = RuntimeMode(args.mode)
        config = RobotRuntimeConfig(runtime_mode=mode, dry_run=True if args.dry_run else mode != RuntimeMode.MOCK)
        state = MockRobotState(
            virtual_battery_percent=args.battery_percent,
            virtual_sensors={
                "frontDistanceM": 1.0,
                "leftDistanceM": 1.0,
                "rightDistanceM": 1.0,
                "cliffDetected": args.cliff_detected,
                "collisionDetected": args.collision_detected,
                "imuRollDeg": args.imu_roll,
                "imuPitchDeg": args.imu_pitch,
            },
        )
        server = MockRobotServer(port=0, state=state)
        server.start()
        try:
            runtime_client = RobotClient(ControllerConfig(robot_url=server.url, request_timeout_s=1.0))
            runtime = RobotRuntime(runtime_client, config)
            tracking = None
            if args.target_visible:
                tracking = TrackingDecision(
                    TrackingState.FOLLOWING,
                    "walk_forward" if args.target_distance is None or args.target_distance > 0.45 else "stop",
                    "runtime cli dry-run target",
                )
            assistant = None
            if args.assistant_command:
                assistant = MockAssistantPipeline(
                    policy=AssistantPolicy(allow_motion_commands=True)
                ).handle_text(f"sesame {args.assistant_command}")
            count = 1 if args.command == "runtime-step" else args.steps
            results = tuple(runtime.step(tracking=tracking, assistant=assistant) for _ in range(count))
            payload = runtime_result_to_jsonable(results[-1], config)
            if args.command == "runtime-run":
                payload["steps"] = [runtime_result_to_jsonable(result, config) for result in results]
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        finally:
            server.stop()
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
