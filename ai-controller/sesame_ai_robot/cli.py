from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys

from .client import RobotClient
from .config import ControllerConfig
from .camera import CameraMonitor, MockCameraSource, OpenCVCameraSource, enumerate_opencv_cameras
from .logging_config import configure_logging
from .mock_robot import MockRobotServer, MockRobotState
from .detection import MockObjectDetector, result_to_jsonable as detection_result_to_jsonable
from .face_identity import FaceIdentity, MockFaceRecognizer, recognition_to_jsonable
from .assistant import AssistantAction, AssistantPlan, AssistantPolicy, AssistantStep, MockAssistantPipeline, plan_to_jsonable
from .advanced import RuntimeMode
from .ai_interaction import AIInteractionLoop, reply_to_jsonable
from .ai_provider import provider_from_env
from .confirmation import ConfirmationStore
from .runtime import RobotRuntime, RobotRuntimeConfig, result_to_jsonable as runtime_result_to_jsonable
from .tracking import TrackingDecision, TrackingState
from .virtual_hardware import HardwareDispatchError, HardwareSafetyError, ManualClock, SimulatorHardwareAdapter


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

    for name in ("runtime-step", "runtime-run", "runtime-confirmation-demo"):
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

    simulator_state = subparsers.add_parser("simulator-state", help="Print virtual hardware state as JSON")
    simulator_state.add_argument("--fault", action="append", default=[])
    simulator_state.add_argument("--dry-run", action="store_true")

    simulator_fault = subparsers.add_parser("simulator-inject-fault", help="Inject a virtual hardware fault and print state")
    simulator_fault.add_argument("fault")
    simulator_fault.add_argument("--dry-run", action="store_true")

    simulator_reset = subparsers.add_parser("simulator-reset", help="Reset virtual hardware state")
    simulator_reset.add_argument("--dry-run", action="store_true")

    simulator_timeline = subparsers.add_parser("simulator-timeline", help="Run a small virtual hardware timeline")
    simulator_timeline.add_argument("--dry-run", action="store_true")

    simulator_run = subparsers.add_parser("simulator-run-scenario", help="Run virtual hardware simulator scenarios")
    simulator_run.add_argument("paths", nargs="*")

    ai_command = subparsers.add_parser("ai-command", help="Run one natural-language AI interaction loop turn")
    ai_command.add_argument("--mode", choices=[RuntimeMode.MOCK.value, RuntimeMode.SIMULATOR.value], default=RuntimeMode.SIMULATOR.value)
    ai_command.add_argument("--provider", default="mock")
    ai_command.add_argument("--text", required=True)
    ai_command.add_argument("--confirmation-id", default=None)
    ai_command.add_argument("--json", action="store_true")

    ai_chat = subparsers.add_parser("ai-chat", help="Run a bounded non-hardware AI chat loop")
    ai_chat.add_argument("--mode", choices=[RuntimeMode.MOCK.value, RuntimeMode.SIMULATOR.value], default=RuntimeMode.SIMULATOR.value)
    ai_chat.add_argument("--provider", default="mock")
    ai_chat.add_argument("--turns", type=int, default=5)

    ai_eval = subparsers.add_parser("ai-eval", help="Run deterministic AI interaction eval cases")
    ai_eval.add_argument("--cases", default=None)
    ai_eval.add_argument("--json", action="store_true")

    ai_run_scenario = subparsers.add_parser("ai-run-scenario", help="Run deterministic AI eval cases from a file")
    ai_run_scenario.add_argument("--cases", default=None)
    ai_run_scenario.add_argument("--json", action="store_true")

    subparsers.add_parser("ai-session-reset", help="Reset an in-memory AI session")
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

    if args.command == "ai-session-reset":
        loop = AIInteractionLoop()
        loop.reset_session()
        print(json.dumps({"status": "ok", "message": "AI session reset in memory"}, ensure_ascii=False, indent=2))
        return 0

    if args.command == "ai-command":
        try:
            loop = AIInteractionLoop(
                provider=provider_from_env(args.provider),
                runtime_mode=RuntimeMode(args.mode),
            )
            reply = loop.handle_text(args.text, confirmation_id=args.confirmation_id)
        except Exception as exc:
            print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False, indent=2))
            return 2
        payload = reply_to_jsonable(reply, include_confirmation_id=True)
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(reply.user_message)
            if reply.requires_confirmation and reply.confirmation_id:
                print(f"confirmation_required {reply.confirmation_id}")
        return 0 if reply.status in {"ok", "confirmation_required", "clarification_required"} else 1

    if args.command in {"ai-eval", "ai-run-scenario"}:
        repo = Path(__file__).resolve().parents[2]
        cases_path = Path(args.cases) if args.cases else repo / "ai-controller" / "evals" / "ai_interaction_cases.json"
        try:
            from .ai_eval import run_eval_file

            summary = run_eval_file(cases_path)
        except Exception as exc:
            print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False, indent=2))
            return 2
        if args.json:
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        else:
            print(f"AI eval: {summary['passed']}/{summary['total']} PASS")
        return 0 if summary["passed"] == summary["total"] else 1

    if args.command == "ai-chat":
        loop = AIInteractionLoop(
            provider=provider_from_env(args.provider),
            runtime_mode=RuntimeMode(args.mode),
        )
        for _ in range(max(1, min(args.turns, 10))):
            try:
                text = input("> ").strip()
            except EOFError:
                break
            if text in {"exit", "quit"}:
                break
            reply = loop.handle_text(text)
            print(reply.user_message)
        return 0

    if args.command == "simulator-run-scenario":
        repo = Path(__file__).resolve().parents[2]
        runner_path = repo / "simulator" / "hardware_scenario_runner.py"
        spec = importlib.util.spec_from_file_location("sesame_hardware_scenario_runner", runner_path)
        if spec is None or spec.loader is None:
            print(json.dumps({"error": "hardware scenario runner is unavailable"}, ensure_ascii=False, indent=2))
            return 1
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        scenario_paths = [Path(path) for path in args.paths] if args.paths else [repo / "simulator" / "scenarios" / "hardware"]
        results = [module.run_hardware_scenario(path) for path in module.discover_scenarios(scenario_paths)]
        print(json.dumps({
            "results": [
                {"path": str(result.path), "passed": result.passed, "failures": list(result.failures)}
                for result in results
            ]
        }, ensure_ascii=False, indent=2))
        return 0 if all(result.passed for result in results) else 1

    if args.command in {"simulator-state", "simulator-inject-fault", "simulator-reset", "simulator-timeline"}:
        clock = ManualClock(100.0)
        hardware = SimulatorHardwareAdapter(clock=clock)
        try:
            if args.command == "simulator-state":
                for fault in args.fault:
                    hardware.inject_fault(fault)
                payload = {"dryRun": bool(args.dry_run), "state": hardware.state.snapshot(), "events": hardware.events}
            elif args.command == "simulator-inject-fault":
                hardware.inject_fault(args.fault)
                payload = {"dryRun": bool(args.dry_run), "state": hardware.state.snapshot(), "events": hardware.events}
            elif args.command == "simulator-reset":
                payload = {"dryRun": bool(args.dry_run), "state": hardware.state.snapshot(), "events": hardware.events}
            else:
                if not args.dry_run:
                    hardware.set_servo(0, 100, 100)
                    hardware.set_motor(0, 0.25, 0.5)
                    clock.advance(0.5)
                    hardware.tick()
                payload = {"dryRun": bool(args.dry_run), "state": hardware.state.snapshot(), "events": hardware.events}
        except (ValueError, HardwareDispatchError, HardwareSafetyError) as exc:
            print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2))
            return 1
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if args.command in {"runtime-step", "runtime-run", "runtime-confirmation-demo"}:
        mode = RuntimeMode(args.mode)
        config = RobotRuntimeConfig(runtime_mode=mode, dry_run=True if args.dry_run else mode != RuntimeMode.MOCK)
        state = MockRobotState(
            emergency_stop_active=args.assistant_command == "reset_emergency_stop" or args.command == "runtime-confirmation-demo",
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
                assistant = _assistant_command_plan(args.assistant_command)
            if args.command == "runtime-confirmation-demo":
                assistant = _assistant_command_plan("reset_emergency_stop")
                requested = runtime.step(tracking=tracking, assistant=assistant)
                confirmation_id = requested.plan.confirmation_request.confirmation_id
                accepted = runtime.step(tracking=tracking, assistant=assistant, confirmation_id=confirmation_id)
                replay = runtime.step(tracking=tracking, assistant=assistant, confirmation_id=confirmation_id)
                wrong_action_request = runtime.step(tracking=tracking, assistant=assistant)
                wrong_action = runtime.step(
                    tracking=tracking,
                    assistant=assistant,
                    confirmation_id=wrong_action_request.plan.confirmation_request.confirmation_id,
                    confirmation_action="self_righting",
                )
                context_request = runtime.step(tracking=tracking, assistant=assistant)
                server.state.virtual_sensors["cliffDetected"] = True
                context_changed = runtime.step(
                    tracking=tracking,
                    assistant=assistant,
                    confirmation_id=context_request.plan.confirmation_request.confirmation_id,
                )
                server.state.virtual_sensors["cliffDetected"] = args.cliff_detected

                demo_clock = {"now": 100.0}
                expired_runtime = RobotRuntime(
                    runtime_client,
                    config,
                    confirmation_store=ConfirmationStore(ttl_seconds=1.0, _clock=lambda: demo_clock["now"]),
                )
                expired_request = expired_runtime.step(tracking=tracking, assistant=assistant)
                demo_clock["now"] = 101.0
                expired = expired_runtime.step(
                    tracking=tracking,
                    assistant=assistant,
                    confirmation_id=expired_request.plan.confirmation_request.confirmation_id,
                )
                ok = (
                    requested.confirmation_state == "requested"
                    and accepted.confirmation_state == "accepted"
                    and replay.confirmation_state == "already_used"
                    and wrong_action.confirmation_state == "action_mismatch"
                    and context_changed.confirmation_state == "context_changed"
                    and expired.confirmation_state == "expired"
                )
                print(json.dumps({
                    "runtimeMode": config.runtime_mode.value,
                    "dryRun": config.dry_run,
                    "request": runtime_result_to_jsonable(requested, config),
                    "confirm": runtime_result_to_jsonable(accepted, config),
                    "replay": runtime_result_to_jsonable(replay, config),
                    "wrongAction": runtime_result_to_jsonable(wrong_action, config),
                    "contextChanged": runtime_result_to_jsonable(context_changed, config),
                    "expired": runtime_result_to_jsonable(expired, config),
                }, ensure_ascii=False, indent=2))
                return 0 if ok else 1
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


def _assistant_command_plan(command: str) -> AssistantPlan:
    return AssistantPlan(
        command,
        (AssistantStep(AssistantAction.ROBOT_COMMAND, command, "runtime cli assistant command"),),
    )


if __name__ == "__main__":
    raise SystemExit(main())
