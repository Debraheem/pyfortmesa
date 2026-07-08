"""Print compact timing tables from saved-model profile timing JSON files."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def load_report(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def number(report: dict[str, Any], section: str, name: str) -> float:
    value = report[section].get(name, 0.0)
    if isinstance(value, str):
        return float("nan")
    return float(value)


def text(report: dict[str, Any], section: str, name: str) -> str:
    return str(report[section].get(name, ""))


def per_profile_ms(report: dict[str, Any]) -> float:
    repeat = number(report, "timing", "repeat")
    if repeat <= 0.0:
        return math.inf
    return 1000.0 * number(report, "timing", "timed_profile_seconds") / repeat


def calls_per_second(report: dict[str, Any], name: str) -> str:
    value = report["timing"].get(name)
    if value is None:
        return "-"
    return f"{float(value):.3e}"


def print_single_summary(reports: list[dict[str, Any]]) -> None:
    if not reports:
        return

    print("single-run summary:")
    print(
        "  "
        f"{'physics':<8} {'omp':>5} {'global_s':>10} {'profile_s':>10} "
        f"{'warmup_s':>10} {'timed_s':>10} {'ms/profile':>11} "
        f"{'eos/s':>11} {'kap/s':>11}"
    )
    for report in reports:
        timing = report["timing"]
        print(
            "  "
            f"{timing['physics']:<8} "
            f"{str(timing['omp_num_threads']):>5} "
            f"{float(report['global_seconds']):10.6f} "
            f"{number(report, 'timing', 'profile_seconds'):10.6f} "
            f"{number(report, 'breakdown', 'warmup_profile_seconds'):10.6f} "
            f"{number(report, 'timing', 'timed_profile_seconds'):10.6f} "
            f"{per_profile_ms(report):11.3f} "
            f"{calls_per_second(report, 'eos_calls_per_second'):>11} "
            f"{calls_per_second(report, 'kap_calls_per_second'):>11}"
        )


def print_breakdown_summary(reports: list[dict[str, Any]]) -> None:
    if not reports:
        return

    print()
    print("global timing breakdown:")
    print(
        "  "
        f"{'physics':<8} {'profile_s':>10} {'array_s':>10} {'iso_s':>10} "
        f"{'warmup_s':>10} {'timed_s':>10} {'output_s':>10} "
        f"{'shutdown_s':>10}"
    )
    for report in reports:
        timing = report["timing"]
        breakdown = report["breakdown"]
        print(
            "  "
            f"{timing['physics']:<8} "
            f"{number(report, 'timing', 'profile_seconds'):10.6f} "
            f"{float(breakdown['profile_array_seconds']):10.6f} "
            f"{float(breakdown['iso_id_seconds']):10.6f} "
            f"{float(breakdown['warmup_profile_seconds']):10.6f} "
            f"{float(breakdown['timed_worker_seconds']):10.6f} "
            f"{float(breakdown['output_collect_seconds']):10.6f} "
            f"{float(breakdown['shutdown_seconds']):10.6f}"
        )


def print_sweep_summary(reports: list[dict[str, Any]]) -> None:
    if not reports:
        return

    reports = sorted(
        reports,
        key=lambda report: int(text(report, "timing", "omp_num_threads")),
    )
    base_seconds = number(reports[0], "timing", "timed_profile_seconds")
    best = min(reports, key=per_profile_ms)

    print()
    print("thread sweep summary:")
    print(
        "  "
        f"{'threads':>7} {'timed_s':>10} {'ms/profile':>11} "
        f"{'speedup':>8} {'efficiency':>10} {'eos/s':>11} {'kap/s':>11}"
    )
    for report in reports:
        threads = int(text(report, "timing", "omp_num_threads"))
        timed = number(report, "timing", "timed_profile_seconds")
        speedup = base_seconds / timed if timed > 0.0 else math.inf
        efficiency = speedup / threads
        print(
            "  "
            f"{threads:7d} "
            f"{timed:10.6f} "
            f"{per_profile_ms(report):11.3f} "
            f"{speedup:8.2f} "
            f"{efficiency:10.2f} "
            f"{calls_per_second(report, 'eos_calls_per_second'):>11} "
            f"{calls_per_second(report, 'kap_calls_per_second'):>11}"
        )

    print()
    print(
        "best thread-sweep point: "
        f"OMP_NUM_THREADS={text(best, 'timing', 'omp_num_threads')} "
        f"({per_profile_ms(best):.3f} ms/profile)"
    )


def print_header(reports: list[dict[str, Any]]) -> None:
    if not reports:
        return
    first = reports[0]
    timing = first["timing"]
    print("== saved-model profile timing report")
    print(f"model = {first['model']}")
    print(f"model_number = {first['model_number']}")
    print(f"net_name = {first['net_name']}")
    print(f"zones = {first['zones']}")
    print(f"species = {first['species']}")
    print(f"warmup = {timing['warmup']}")
    print(f"repeat = {timing['repeat']}")
    print()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize pyfortmesa saved-model profile timing JSON files."
    )
    parser.add_argument(
        "--single",
        action="append",
        default=[],
        type=Path,
        help="Timing JSON from an eos, kap, or eos+kap single run.",
    )
    parser.add_argument(
        "--sweep",
        action="append",
        default=[],
        type=Path,
        help="Timing JSON from one eos+kap thread-sweep run.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    single_reports = [load_report(path) for path in args.single]
    sweep_reports = [load_report(path) for path in args.sweep]
    all_reports = single_reports + sweep_reports

    print_header(all_reports)
    print_single_summary(single_reports)
    print_breakdown_summary(single_reports)
    print_sweep_summary(sweep_reports)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
