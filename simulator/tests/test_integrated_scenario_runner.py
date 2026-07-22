import tempfile
import unittest
from pathlib import Path

from integrated_scenario_runner import discover_integrated_scenarios, run_integrated_scenario


class IntegratedScenarioRunnerTest(unittest.TestCase):
    def test_runs_following_fall_scenario(self):
        result = run_integrated_scenario(
            Path(__file__).parents[1] / "scenarios" / "integrated" / "following_fall.json"
        )

        self.assertTrue(result.passed, result.failures)

    def test_reports_failed_integrated_expectation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "failure.json"
            path.write_text(
                '{"steps":[{"expect":{"command":"walk_forward"}}]}',
                encoding="utf-8",
            )

            result = run_integrated_scenario(path)

        self.assertFalse(result.passed)
        self.assertIn("expected command='walk_forward'", result.failures[0])

    def test_discovers_integrated_json_scenarios(self):
        scenarios = discover_integrated_scenarios([Path(__file__).parents[1] / "scenarios" / "integrated"])

        self.assertTrue(any(path.name == "assistant_motion_blocked_by_obstacle.json" for path in scenarios))


if __name__ == "__main__":
    unittest.main()
