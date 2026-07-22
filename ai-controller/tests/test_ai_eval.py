import unittest
from pathlib import Path

from sesame_ai_robot.ai_eval import run_eval_file


class AIEvalTest(unittest.TestCase):
    def test_ai_interaction_eval_dataset_passes(self):
        root = Path(__file__).resolve().parents[1]
        summary = run_eval_file(root / "evals" / "ai_interaction_cases.json")

        self.assertEqual(summary["total"], 31)
        self.assertEqual(summary["passed"], summary["total"], summary["results"])
        self.assertGreaterEqual(summary["categories"]["normal_query"]["total"], 5)
        self.assertGreaterEqual(summary["categories"]["adversarial"]["total"], 5)


if __name__ == "__main__":
    unittest.main()
