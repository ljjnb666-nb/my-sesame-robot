import unittest

from sesame_ai_robot.camera import MockCameraSource
from sesame_ai_robot.detection import BoundingBox, Detection, DetectionResult, MockObjectDetector
from sesame_ai_robot.face_identity import FaceIdentity, MockFaceRecognizer
from sesame_ai_robot.tracking import TrackingConfig, TrackingController, TrackingState


def confirmed_identity():
    return MockFaceRecognizer(FaceIdentity("owner", "Owner", 0.0), confidence=0.9, threshold=0.75).identify(MockCameraSource().read())


def unconfirmed_identity():
    return MockFaceRecognizer(None, confidence=0.9, threshold=0.75).identify(MockCameraSource().read())


class TrackingControllerTest(unittest.TestCase):
    def test_emergency_stop_wins(self):
        decision = TrackingController().update(
            MockObjectDetector().detect(MockCameraSource().read()),
            confirmed_identity(),
            {"emergencyStopActive": True},
        )

        self.assertEqual(decision.state, TrackingState.EMERGENCY_STOP)
        self.assertIsNone(decision.command)

    def test_unconfirmed_identity_does_not_follow(self):
        decision = TrackingController(TrackingConfig(allow_following=True)).update(
            MockObjectDetector().detect(MockCameraSource().read()),
            unconfirmed_identity(),
            {"emergencyStopActive": False},
        )

        self.assertEqual(decision.state, TrackingState.SEARCHING)
        self.assertIsNone(decision.command)

    def test_following_disabled_tracks_without_motion(self):
        decision = TrackingController().update(
            MockObjectDetector().detect(MockCameraSource().read()),
            confirmed_identity(),
            {"emergencyStopActive": False},
        )

        self.assertEqual(decision.state, TrackingState.TRACKING)
        self.assertIsNone(decision.command)

    def test_obstacle_stops_even_when_following_allowed(self):
        decision = TrackingController(TrackingConfig(allow_following=True)).update(
            MockObjectDetector().detect(MockCameraSource().read()),
            confirmed_identity(),
            {"emergencyStopActive": False, "virtualSensors": {"frontDistanceM": 0.2}},
        )

        self.assertEqual(decision.state, TrackingState.STOPPED)
        self.assertEqual(decision.command, "stop")

    def test_following_command_uses_target_position(self):
        frame = MockCameraSource(width=100, height=100).read()
        result = DetectionResult(
            source=frame.source,
            captured_at=frame.captured_at,
            processed_at=frame.captured_at,
            frame_width=100,
            frame_height=100,
            detections=(Detection("person", 0.9, BoundingBox(70, 20, 10, 30)),),
        )

        decision = TrackingController(TrackingConfig(allow_following=True)).update(
            result,
            confirmed_identity(),
            {"emergencyStopActive": False, "virtualSensors": {"frontDistanceM": 1.0}},
        )

        self.assertEqual(decision.state, TrackingState.FOLLOWING)
        self.assertEqual(decision.command, "turn_right")


if __name__ == "__main__":
    unittest.main()
