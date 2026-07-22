import unittest

from sesame_ai_robot.camera import MockCameraSource
from sesame_ai_robot.detection import BoundingBox, Detection, DetectionResult, MockObjectDetector, result_to_jsonable


class DetectionTest(unittest.TestCase):
    def test_bounding_box_center_and_normalization(self):
        box = BoundingBox(x=10, y=20, width=30, height=40)

        self.assertEqual(box.center_x, 25)
        self.assertEqual(box.center_y, 40)
        normalized = box.normalized(frame_width=100, frame_height=200)
        self.assertEqual(normalized, BoundingBox(x=0.1, y=0.1, width=0.3, height=0.2))

    def test_mock_detector_returns_person_and_object(self):
        frame = MockCameraSource(width=320, height=240).read()
        result = MockObjectDetector().detect(frame)

        self.assertEqual(result.frame_width, 320)
        self.assertEqual(result.frame_height, 240)
        self.assertGreaterEqual(result.latency_ms, 0)
        self.assertEqual(result.best("person").label, "person")
        self.assertEqual(result.best("person").center, (160.0, 120.0))
        self.assertEqual(result.best("missing"), None)

    def test_result_to_jsonable_is_stable(self):
        frame = MockCameraSource(width=100, height=100).read()
        detection = Detection("person", 0.8, BoundingBox(10, 20, 30, 40), distance_m=1.5)
        result = DetectionResult(
            source=frame.source,
            captured_at=frame.captured_at,
            processed_at=frame.captured_at + 0.01,
            frame_width=frame.width,
            frame_height=frame.height,
            detections=(detection,),
        )

        payload = result_to_jsonable(result)
        self.assertEqual(payload["frame"], {"width": 100, "height": 100})
        self.assertEqual(payload["detections"][0]["label"], "person")
        self.assertEqual(payload["detections"][0]["center"], {"x": 25.0, "y": 40.0})
        self.assertEqual(payload["detections"][0]["distanceM"], 1.5)


if __name__ == "__main__":
    unittest.main()
