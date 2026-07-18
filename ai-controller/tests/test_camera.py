import unittest

from sesame_ai_robot.camera import CameraMonitor, MockCameraSource


class CameraMonitorTest(unittest.TestCase):
    def test_mock_camera_frame_shape(self):
        source = MockCameraSource(width=16, height=8)
        frame = source.read()

        self.assertEqual(frame.width, 16)
        self.assertEqual(frame.height, 8)
        self.assertEqual(len(frame.data), 128)
        self.assertEqual(frame.source, "mock-camera")

    def test_collect_stats(self):
        stats = CameraMonitor(MockCameraSource()).collect(frames=5)

        self.assertEqual(stats.frames, 5)
        self.assertGreater(stats.fps, 0)
        self.assertGreaterEqual(stats.average_latency_ms, 0)
        self.assertGreaterEqual(stats.max_latency_ms, stats.average_latency_ms)

    def test_rejects_zero_frames(self):
        with self.assertRaises(ValueError):
            CameraMonitor(MockCameraSource()).collect(frames=0)


if __name__ == "__main__":
    unittest.main()
