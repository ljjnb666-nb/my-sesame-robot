import unittest

from visualizer import render_status, servo_bar


class VisualizerTest(unittest.TestCase):
    def test_servo_bar_has_stable_width(self):
        self.assertEqual(len(servo_bar(0)), len(servo_bar(180)))
        self.assertIn("#", servo_bar(90))

    def test_render_status_includes_required_sections(self):
        output = render_status({
            "emergencyStopActive": False,
            "communicationTimedOut": False,
            "currentCommand": "forward",
            "motionState": "moving",
            "currentFace": "walk",
            "virtualBatteryPercent": 88,
            "virtualServoAngles": [90] * 8,
            "virtualSensors": {
                "frontDistanceM": 1.0,
                "leftDistanceM": 0.8,
                "rightDistanceM": 0.7,
                "cliffDetected": False,
                "collisionDetected": False,
                "imuRollDeg": 0,
                "imuPitchDeg": 1,
            },
        })

        self.assertIn("Virtual servos", output)
        self.assertIn("Virtual sensors", output)
        self.assertIn("OLED", output)
        self.assertIn("S8", output)


if __name__ == "__main__":
    unittest.main()
