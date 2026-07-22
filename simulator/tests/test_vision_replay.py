import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[0]
AI_CONTROLLER = PROJECT / "ai-controller"
if str(AI_CONTROLLER) not in sys.path:
    sys.path.insert(0, str(AI_CONTROLLER))

from sesame_ai_robot.camera import ImageDirectorySource


class VisionReplayTest(unittest.TestCase):
    def test_image_directory_source_reads_pgm(self):
        source = ImageDirectorySource(ROOT / "test-images")
        frame = source.read()

        self.assertEqual(frame.width, 4)
        self.assertEqual(frame.height, 4)
        self.assertEqual(len(frame.data), 16)

    def test_vision_replay_mock_source(self):
        completed = subprocess.run(
            [sys.executable, str(ROOT / "vision_replay.py"), "--source", "mock", "--frames", "2"],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(completed.stdout)

        self.assertEqual(payload["frames"], 2)
        self.assertEqual(payload["results"][0]["detections"][0]["label"], "person")

    def test_vision_replay_image_source(self):
        completed = subprocess.run(
            [sys.executable, str(ROOT / "vision_replay.py"), "--source", "images", "--frames", "2"],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(completed.stdout)

        self.assertEqual(payload["frames"], 2)
        self.assertEqual(payload["results"][0]["frame"], {"width": 4, "height": 4})


if __name__ == "__main__":
    unittest.main()
