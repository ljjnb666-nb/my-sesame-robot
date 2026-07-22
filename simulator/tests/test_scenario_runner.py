import tempfile
import unittest
from pathlib import Path

from scenario_runner import discover_scenarios, run_scenario


class ScenarioRunnerTest(unittest.TestCase):
    def test_runs_normal_walk_scenario(self):
        result = run_scenario(Path(__file__).parents[1] / "scenarios" / "normal_walk.json")

        self.assertTrue(result.passed, result.failures)

    def test_reports_failed_expectation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "failure.json"
            path.write_text(
                '{"steps":[{"command":"stop","expect":{"motionState":"moving"}}]}',
                encoding="utf-8",
            )

            result = run_scenario(path)

        self.assertFalse(result.passed)
        self.assertIn("expected motionState='moving'", result.failures[0])

    def test_discovers_json_scenarios(self):
        scenarios = discover_scenarios([Path(__file__).parents[1] / "scenarios"])

        self.assertTrue(any(path.name == "emergency_stop.json" for path in scenarios))


if __name__ == "__main__":
    unittest.main()
