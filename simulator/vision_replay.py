from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
AI_CONTROLLER = ROOT / "ai-controller"
if str(AI_CONTROLLER) not in sys.path:
    sys.path.insert(0, str(AI_CONTROLLER))

from sesame_ai_robot.camera import ImageDirectorySource, MockCameraSource, OpenCVCameraSource
from sesame_ai_robot.detection import MockObjectDetector, result_to_jsonable


def build_source(args):
    if args.source == "mock":
        return MockCameraSource()
    if args.source == "images":
        return ImageDirectorySource(args.images)
    if args.source == "camera":
        return OpenCVCameraSource(args.index)
    raise ValueError(f"unsupported source: {args.source}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay visual input through the mock detector")
    parser.add_argument("--source", choices=("mock", "images", "camera"), default="mock")
    parser.add_argument("--images", type=Path, default=Path(__file__).parent / "test-images")
    parser.add_argument("--index", type=int, default=0)
    parser.add_argument("--frames", type=int, default=3)
    args = parser.parse_args()

    try:
        source = build_source(args)
    except RuntimeError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    detector = MockObjectDetector()
    results = []
    try:
        for _ in range(args.frames):
            results.append(result_to_jsonable(detector.detect(source.read())))
    finally:
        source.close()

    print(json.dumps({"frames": len(results), "results": results}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
