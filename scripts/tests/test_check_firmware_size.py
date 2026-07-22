from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_firmware_size


BUILD_LOG = """
Sketch uses 1138226 bytes (86%) of program storage space. Maximum is 1310720 bytes.
Global variables use 79456 bytes (24%) of dynamic memory, leaving 248224 bytes for local variables. Maximum is 327680 bytes.
"""


class FirmwareSizeCheckTest(unittest.TestCase):
    def test_parse_build_log(self):
        metrics = check_firmware_size.parse_build_log(BUILD_LOG)

        self.assertEqual(metrics.flash_used, 1138226)
        self.assertEqual(metrics.flash_max, 1310720)
        self.assertEqual(metrics.ram_used, 79456)
        self.assertEqual(metrics.ram_max, 327680)

    def test_read_utf16_build_log(self):
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "firmware.log"
            log.write_bytes(BUILD_LOG.encode("utf-16"))

            metrics = check_firmware_size.metrics_from_args(
                check_firmware_size.build_parser().parse_args(["--build-log", str(log)])
            )

        self.assertEqual(metrics.flash_used, 1138226)

    def test_normal_size_passes(self):
        exit_code = check_firmware_size.main([
            "--flash-used", "1138226",
            "--flash-max", "1310720",
            "--ram-used", "79456",
            "--ram-max", "327680",
        ])

        self.assertEqual(exit_code, 0)

    def test_warning_threshold_does_not_fail(self):
        exit_code = check_firmware_size.main([
            "--flash-used", "1160000",
            "--flash-max", "1310720",
            "--ram-used", "79456",
            "--ram-max", "327680",
            "--flash-warning-percent", "88",
            "--flash-failure-percent", "92",
        ])

        self.assertEqual(exit_code, 1)

    def test_failure_threshold_fails(self):
        exit_code = check_firmware_size.main([
            "--flash-used", "1206000",
            "--flash-max", "1310720",
            "--ram-used", "79456",
            "--ram-max", "327680",
            "--flash-warning-percent", "88",
            "--flash-failure-percent", "92",
        ])

        self.assertEqual(exit_code, 2)

    def test_invalid_inputs_fail(self):
        exit_code = check_firmware_size.main([
            "--flash-used", "1",
            "--flash-max", "0",
            "--ram-used", "1",
            "--ram-max", "1",
        ])

        self.assertEqual(exit_code, 2)

    def test_unparseable_log_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "firmware.log"
            log.write_text("no firmware size here", encoding="utf-8")

            exit_code = check_firmware_size.main(["--build-log", str(log)])

        self.assertEqual(exit_code, 2)


if __name__ == "__main__":
    unittest.main()
