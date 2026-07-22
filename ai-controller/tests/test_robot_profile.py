from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from sesame_ai_robot.robot_profile import RobotProfile, get_capability, get_personality, load_profile


def write_profile(tmp: str, text: str) -> Path:
    path = Path(tmp) / "robot_profile.yaml"
    path.write_text(text, encoding="utf-8")
    return path


class RobotProfileTest(unittest.TestCase):
    def test_missing_profile_returns_defaults(self):
        with TemporaryDirectory() as tmp:
            profile = load_profile(Path(tmp) / "missing.yaml")

            self.assertEqual(profile.name, "Sesame Robot")
            self.assertEqual(profile.capabilities, ())

    def test_loads_name_capabilities_personality_and_limits(self):
        with TemporaryDirectory() as tmp:
            path = write_profile(tmp, """
name: Desk Bot
personality:
  tone: calm
capabilities:
  - simulator
  - virtual_hardware
limits:
  memory_storage: local_json
""")

            profile = load_profile(path)

            self.assertEqual(profile.name, "Desk Bot")
            self.assertTrue(profile.get_capability("simulator"))
            self.assertEqual(profile.get_personality("tone"), "calm")
            self.assertEqual(profile.limits["memory_storage"], "local_json")

    def test_module_get_capability_uses_loaded_profile(self):
        with TemporaryDirectory() as tmp:
            path = write_profile(tmp, "name: Desk Bot\ncapabilities:\n  - simulator\n")

            self.assertTrue(get_capability("simulator", path))

    def test_module_get_personality_uses_loaded_profile(self):
        with TemporaryDirectory() as tmp:
            path = write_profile(tmp, "name: Desk Bot\npersonality:\n  tone: concise\n")

            self.assertEqual(get_personality("tone", path), "concise")

    def test_personality_string_can_be_read_as_description(self):
        profile = RobotProfile(personality="quiet helper")

        self.assertEqual(profile.get_personality("description"), "quiet helper")

    def test_invalid_yaml_mapping_is_rejected(self):
        with TemporaryDirectory() as tmp:
            path = write_profile(tmp, "- not: a root mapping\n")

            with self.assertRaises(ValueError):
                load_profile(path)

    def test_invalid_yaml_indentation_is_rejected(self):
        with TemporaryDirectory() as tmp:
            path = write_profile(tmp, "name: Desk Bot\n    bad: indent\n")

            with self.assertRaises(ValueError):
                load_profile(path)

    def test_unknown_root_field_is_rejected(self):
        with TemporaryDirectory() as tmp:
            path = write_profile(tmp, "name: Desk Bot\nowner: user\n")

            with self.assertRaises(ValueError):
                load_profile(path)

    def test_safety_override_field_is_rejected(self):
        with TemporaryDirectory() as tmp:
            path = write_profile(tmp, "name: Desk Bot\nsafety_override: true\n")

            with self.assertRaises(ValueError):
                load_profile(path)

    def test_forbidden_key_case_variant_is_rejected(self):
        with TemporaryDirectory() as tmp:
            path = write_profile(tmp, "name: Desk Bot\nSafety_Override: true\n")

            with self.assertRaises(ValueError):
                load_profile(path)

    def test_forbidden_key_hyphen_variant_is_rejected(self):
        with TemporaryDirectory() as tmp:
            path = write_profile(tmp, "name: Desk Bot\nruntime-authorized-actions:\n  - walk_forward\n")

            with self.assertRaises(ValueError):
                load_profile(path)

    def test_confirmation_override_field_is_rejected(self):
        with TemporaryDirectory() as tmp:
            path = write_profile(tmp, "name: Desk Bot\nconfirmation_required: false\n")

            with self.assertRaises(ValueError):
                load_profile(path)

    def test_arbiter_rules_field_is_rejected(self):
        with TemporaryDirectory() as tmp:
            path = write_profile(tmp, "name: Desk Bot\narbiter_rules:\n  walk_forward: allow\n")

            with self.assertRaises(ValueError):
                load_profile(path)

    def test_safety_severity_nested_field_is_rejected(self):
        with TemporaryDirectory() as tmp:
            path = write_profile(tmp, "name: Desk Bot\nlimits:\n  safety_severity: ok\n")

            with self.assertRaises(ValueError):
                load_profile(path)

    def test_real_robot_gate_field_is_rejected(self):
        with TemporaryDirectory() as tmp:
            path = write_profile(tmp, "name: Desk Bot\nlimits:\n  allow-real-robot: true\n")

            with self.assertRaises(ValueError):
                load_profile(path)

    def test_runtime_mode_field_is_rejected(self):
        with TemporaryDirectory() as tmp:
            path = write_profile(tmp, "name: Desk Bot\nruntime_mode: real_robot\n")

            with self.assertRaises(ValueError):
                load_profile(path)

    def test_capabilities_must_be_a_list_or_string(self):
        with TemporaryDirectory() as tmp:
            path = write_profile(tmp, "name: Desk Bot\ncapabilities:\n  camera: true\n")

            with self.assertRaises(ValueError):
                load_profile(path)

    def test_limits_must_be_mapping(self):
        with TemporaryDirectory() as tmp:
            path = write_profile(tmp, "name: Desk Bot\nlimits:\n  - bad\n")

            with self.assertRaises(ValueError):
                load_profile(path)

    def test_duplicate_root_key_is_rejected(self):
        with TemporaryDirectory() as tmp:
            path = write_profile(tmp, "name: One\nname: Two\n")

            with self.assertRaises(ValueError):
                load_profile(path)

    def test_duplicate_nested_key_is_rejected(self):
        with TemporaryDirectory() as tmp:
            path = write_profile(tmp, "name: Desk Bot\npersonality:\n  tone: calm\n  tone: loud\n")

            with self.assertRaises(ValueError):
                load_profile(path)

    def test_yaml_comments_are_ignored(self):
        with TemporaryDirectory() as tmp:
            path = write_profile(tmp, "name: Desk Bot # comment\ncapabilities:\n  - simulator # comment\n")

            profile = load_profile(path)

            self.assertEqual(profile.name, "Desk Bot")
            self.assertTrue(profile.get_capability("simulator"))

    def test_hash_inside_quoted_string_is_preserved(self):
        with TemporaryDirectory() as tmp:
            path = write_profile(tmp, 'name: "Desk # Bot"\n')

            self.assertEqual(load_profile(path).name, "Desk # Bot")

    def test_deep_yaml_structure_is_rejected(self):
        with TemporaryDirectory() as tmp:
            path = write_profile(tmp, "name: Desk Bot\npersonality:\n  tone:\n    nested: bad\n")

            with self.assertRaises(ValueError):
                load_profile(path)

    def test_personality_list_is_rejected(self):
        with TemporaryDirectory() as tmp:
            path = write_profile(tmp, "name: Desk Bot\npersonality:\n  - calm\n")

            with self.assertRaises(ValueError):
                load_profile(path)

    def test_default_repository_profile_loads(self):
        profile = load_profile()

        self.assertTrue(profile.name)
        self.assertTrue(profile.get_capability("simulator"))


if __name__ == "__main__":
    unittest.main()
