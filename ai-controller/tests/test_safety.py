import unittest

from sesame_ai_robot.safety import SafetyConfig, SafetyMonitor, SafetySeverity, SensorSnapshot


class SafetyMonitorTest(unittest.TestCase):
    def test_allows_safe_snapshot(self):
        assessment = SafetyMonitor().assess(SensorSnapshot(front_distance_m=1.0, battery_percent=80))

        self.assertEqual(assessment.severity, SafetySeverity.OK)
        self.assertTrue(assessment.allows_motion)

    def test_front_obstacle_requests_stop(self):
        assessment = SafetyMonitor().assess(SensorSnapshot(front_distance_m=0.2))

        self.assertEqual(assessment.severity, SafetySeverity.STOP)
        self.assertEqual(assessment.command, "stop")

    def test_collision_requests_emergency_stop(self):
        assessment = SafetyMonitor().assess(SensorSnapshot(collision_detected=True))

        self.assertEqual(assessment.severity, SafetySeverity.EMERGENCY_STOP)
        self.assertEqual(assessment.command, "emergency_stop")

    def test_cliff_requests_emergency_stop(self):
        assessment = SafetyMonitor().assess(SensorSnapshot(cliff_detected=True))

        self.assertEqual(assessment.severity, SafetySeverity.EMERGENCY_STOP)
        self.assertEqual(assessment.command, "emergency_stop")

    def test_tilt_requests_emergency_stop(self):
        assessment = SafetyMonitor().assess(SensorSnapshot(imu_roll_deg=42))

        self.assertEqual(assessment.severity, SafetySeverity.EMERGENCY_STOP)

    def test_low_battery_requests_stop(self):
        assessment = SafetyMonitor(SafetyConfig(low_battery_percent=20)).assess(SensorSnapshot(battery_percent=10))

        self.assertEqual(assessment.severity, SafetySeverity.STOP)
        self.assertEqual(assessment.command, "stop")

    def test_reads_robot_status_virtual_sensors(self):
        snapshot = SensorSnapshot.from_robot_status({
            "virtualBatteryPercent": 55,
            "virtualSensors": {
                "frontDistanceM": 0.8,
                "cliffDetected": False,
                "collisionDetected": True,
                "imuPitchDeg": 5,
            },
        })

        self.assertEqual(snapshot.battery_percent, 55)
        self.assertEqual(snapshot.front_distance_m, 0.8)
        self.assertTrue(snapshot.collision_detected)
        self.assertEqual(snapshot.imu_pitch_deg, 5.0)

    def test_real_sensor_fields_override_virtual_fields(self):
        snapshot = SensorSnapshot.from_robot_status({
            "battery": {"percent": 80},
            "sensors": {
                "frontDistanceM": 0.5,
                "leftDistanceM": 0.4,
                "rightDistanceM": 0.3,
                "cliffDetected": False,
                "collisionDetected": False,
                "imuRollDeg": 1.5,
                "imuPitchDeg": -2.0,
            },
            "virtualBatteryPercent": 10,
            "virtualSensors": {
                "frontDistanceM": 0.1,
                "cliffDetected": True,
            },
        })

        self.assertEqual(snapshot.battery_percent, 80)
        self.assertEqual(snapshot.front_distance_m, 0.5)
        self.assertFalse(snapshot.cliff_detected)
        self.assertEqual(snapshot.imu_pitch_deg, -2.0)


if __name__ == "__main__":
    unittest.main()
