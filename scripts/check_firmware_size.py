from __future__ import annotations

import argparse
from dataclasses import dataclass
import re
import sys
from pathlib import Path


FLASH_PATTERN = re.compile(r"Sketch uses\s+(\d+)\s+bytes.*?Maximum is\s+(\d+)\s+bytes", re.IGNORECASE)
RAM_PATTERN = re.compile(r"Global variables use\s+(\d+)\s+bytes.*?Maximum is\s+(\d+)\s+bytes", re.IGNORECASE)


@dataclass(frozen=True)
class SizeMetrics:
    flash_used: int
    flash_max: int
    ram_used: int
    ram_max: int

    @property
    def flash_percent(self) -> float:
        return self.flash_used / self.flash_max * 100

    @property
    def ram_percent(self) -> float:
        return self.ram_used / self.ram_max * 100

    @property
    def flash_remaining(self) -> int:
        return self.flash_max - self.flash_used

    @property
    def ram_remaining(self) -> int:
        return self.ram_max - self.ram_used


def parse_build_log(text: str) -> SizeMetrics:
    flash = FLASH_PATTERN.search(text)
    ram = RAM_PATTERN.search(text)
    if flash is None or ram is None:
        raise ValueError("could not parse firmware flash/RAM usage from build log")
    return SizeMetrics(
        flash_used=int(flash.group(1)),
        flash_max=int(flash.group(2)),
        ram_used=int(ram.group(1)),
        ram_max=int(ram.group(2)),
    )


def validate_metrics(metrics: SizeMetrics) -> None:
    values = {
        "flash_used": metrics.flash_used,
        "flash_max": metrics.flash_max,
        "ram_used": metrics.ram_used,
        "ram_max": metrics.ram_max,
    }
    for name, value in values.items():
        if value < 0:
            raise ValueError(f"{name} must not be negative")
    if metrics.flash_max <= 0 or metrics.ram_max <= 0:
        raise ValueError("maximum firmware sizes must be greater than zero")
    if metrics.flash_used > metrics.flash_max:
        raise ValueError("flash_used exceeds flash_max")
    if metrics.ram_used > metrics.ram_max:
        raise ValueError("ram_used exceeds ram_max")


def evaluate(metrics: SizeMetrics, flash_warning_percent: float, flash_failure_percent: float) -> tuple[int, str]:
    if flash_warning_percent <= 0 or flash_failure_percent <= 0:
        raise ValueError("thresholds must be greater than zero")
    if flash_warning_percent >= flash_failure_percent:
        raise ValueError("flash warning threshold must be lower than failure threshold")
    if metrics.flash_percent >= flash_failure_percent:
        return 2, "FAIL"
    if metrics.flash_percent >= flash_warning_percent:
        return 1, "WARNING"
    return 0, "OK"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check Sesame firmware size thresholds")
    parser.add_argument("--build-log", type=Path, help="Path to firmware build log to parse")
    parser.add_argument("--flash-used", type=int)
    parser.add_argument("--flash-max", type=int)
    parser.add_argument("--ram-used", type=int)
    parser.add_argument("--ram-max", type=int)
    parser.add_argument("--flash-warning-percent", type=float, default=88.0)
    parser.add_argument("--flash-failure-percent", type=float, default=92.0)
    parser.add_argument("--summary-file", type=Path)
    return parser


def metrics_from_args(args: argparse.Namespace) -> SizeMetrics:
    direct_values = (args.flash_used, args.flash_max, args.ram_used, args.ram_max)
    if args.build_log is not None:
        if any(value is not None for value in direct_values):
            raise ValueError("use either --build-log or direct size arguments, not both")
        return parse_build_log(read_log_text(args.build_log))
    if any(value is None for value in direct_values):
        raise ValueError("provide --build-log or all direct size arguments")
    return SizeMetrics(args.flash_used, args.flash_max, args.ram_used, args.ram_max)


def read_log_text(path: Path) -> str:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-16", "utf-16-le"):
        try:
            text = data.decode(encoding)
        except UnicodeDecodeError:
            continue
        if "Sketch uses" in text or "Global variables use" in text:
            return text
    return data.decode("utf-8", errors="replace").replace("\x00", "")


def format_report(metrics: SizeMetrics, status: str, warning: float, failure: float) -> str:
    return "\n".join([
        "# Firmware Size Report",
        "",
        f"Status: {status}",
        f"Flash: {metrics.flash_used} / {metrics.flash_max} bytes ({metrics.flash_percent:.2f}%), remaining {metrics.flash_remaining} bytes",
        f"RAM: {metrics.ram_used} / {metrics.ram_max} bytes ({metrics.ram_percent:.2f}%), remaining {metrics.ram_remaining} bytes",
        f"Flash warning threshold: {warning:.2f}%",
        f"Flash failure threshold: {failure:.2f}%",
        "",
    ])


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        metrics = metrics_from_args(args)
        validate_metrics(metrics)
        exit_code, status = evaluate(metrics, args.flash_warning_percent, args.flash_failure_percent)
    except Exception as exc:
        print(f"Firmware size check failed: {exc}", file=sys.stderr)
        return 2

    report = format_report(metrics, status, args.flash_warning_percent, args.flash_failure_percent)
    print(report)
    if args.summary_file is not None:
        args.summary_file.parent.mkdir(parents=True, exist_ok=True)
        args.summary_file.write_text(report, encoding="utf-8")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
