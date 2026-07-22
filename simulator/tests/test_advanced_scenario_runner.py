import tempfile
import unittest
from pathlib import Path

from advanced_scenario_runner import discover_advanced_scenarios, run_advanced_scenario


class AdvancedScenarioRunnerTest(unittest.TestCase):
    def test_runs_fall_detection_scenario(self):
        result = run_advanced_scenario(Path(__file__).parents[1] / "scenarios" / "advanced" / "fall_detection.json")

        self.assertTrue(result.passed, result.failures)

    def test_reports_failed_advanced_expectation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "failure.json"
            path.write_text(
                '{"steps":[{"action":"assess_posture","sensor":{"imuRollDeg":72},'
                '"expect":{"command":"stop"}}]}',
                encoding="utf-8",
            )

            result = run_advanced_scenario(path)

        self.assertFalse(result.passed)
        self.assertIn("expected command='stop'", result.failures[0])

    def test_discovers_advanced_json_scenarios(self):
        scenarios = discover_advanced_scenarios([Path(__file__).parents[1] / "scenarios" / "advanced"])

        self.assertTrue(any(path.name == "charging_gate.json" for path in scenarios))


if __name__ == "__main__":
    unittest.main()
