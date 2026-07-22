import unittest

from sesame_ai_robot.virtual_hardware import (
    FAULTS,
    HardwareAdapter,
    HardwareSafetyError,
    ManualClock,
    SimulatorHardwareAdapter,
    VirtualHardwareRobotClient,
)
from sesame_ai_robot.runtime import RobotRuntime, RobotRuntimeConfig
from sesame_ai_robot.tracking import TrackingDecision, TrackingState


class VirtualHardwareTest(unittest.TestCase):
    def test_servo_motion_updates_structured_state(self):
        hardware = SimulatorHardwareAdapter(clock=ManualClock(0.0))

        result = hardware.set_servo(0, 100, 100)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(hardware.state.servos[0].current_angle, 100.0)
        self.assertEqual(hardware.events[-1]["eventType"], "servo_motion_completed")

    def test_invalid_servo_action_does_not_change_actuator_state(self):
        hardware = SimulatorHardwareAdapter(clock=ManualClock(0.0))
        hardware.set_servo(0, 100, 100)

        with self.assertRaises(HardwareSafetyError):
            hardware.set_servo(0, 220, 100)

        self.assertEqual(hardware.state.servos[0].current_angle, 100.0)
        self.assertEqual(hardware.events[-1]["eventType"], "action_rejected")

    def test_motor_auto_stops_at_deadline_boundary(self):
        clock = ManualClock(10.0)
        hardware = SimulatorHardwareAdapter(clock=clock)

        hardware.set_motor(0, 0.2, 1.0)
        clock.advance(1.0)
        hardware.tick()

        self.assertEqual(hardware.state.motors[0].direction, "stop")
        self.assertEqual(hardware.state.motors[0].current_output, 0.0)

    def test_motor_failure_leaves_motor_stopped(self):
        hardware = SimulatorHardwareAdapter(clock=ManualClock(0.0))

        with self.assertRaises(HardwareSafetyError):
            hardware.set_motor(0, 2.0, 0.1)

        self.assertEqual(hardware.state.motors[0].direction, "stop")
        self.assertEqual(hardware.state.motors[0].current_output, 0.0)

    def test_all_named_faults_can_be_injected_and_cleared(self):
        hardware = SimulatorHardwareAdapter(clock=ManualClock(0.0))

        for fault in sorted(FAULTS):
            with self.subTest(fault=fault):
                hardware.inject_fault(fault)
                self.assertIn(fault, hardware.state.faults)
                hardware.clear_fault(fault)
                self.assertNotIn(fault, hardware.state.faults)

    def test_communication_loss_stops_actuators_fail_closed(self):
        hardware = SimulatorHardwareAdapter(clock=ManualClock(0.0))
        hardware.set_motor(0, 0.2, 1.0)
        hardware.inject_fault("communication_lost")

        with self.assertRaises(HardwareSafetyError):
            hardware.set_servo(0, 100)

        self.assertTrue(hardware.state.emergency_stop)
        self.assertEqual(hardware.state.motors[0].direction, "stop")

    def test_camera_and_microphone_faults_are_explicit(self):
        hardware = SimulatorHardwareAdapter(clock=ManualClock(0.0))

        hardware.inject_fault("camera_timeout")
        with self.assertRaisesRegex(HardwareSafetyError, "camera timeout"):
            hardware.capture_camera_frame()
        hardware.clear_fault("all")
        hardware.inject_fault("microphone_unavailable")
        with self.assertRaisesRegex(HardwareSafetyError, "microphone unavailable"):
            hardware.capture_audio(0.1)

    def test_hardware_adapter_does_not_open_on_import_or_init(self):
        adapter = HardwareAdapter(device="COM9")

        self.assertFalse(adapter.connected)
        with self.assertRaises(HardwareSafetyError):
            adapter.open()

    def test_runtime_can_dispatch_through_virtual_hardware_client(self):
        hardware = SimulatorHardwareAdapter(clock=ManualClock(0.0))
        client = VirtualHardwareRobotClient(hardware)
        runtime = RobotRuntime(client, RobotRuntimeConfig(dry_run=False))

        result = runtime.step(tracking=TrackingDecision(TrackingState.FOLLOWING, "walk_forward", "test"))

        self.assertTrue(result.sent_command)
        self.assertEqual(client.current_command, "walk_forward")
        self.assertEqual(hardware.state.motors[0].direction, "forward")


if __name__ == "__main__":
    unittest.main()
