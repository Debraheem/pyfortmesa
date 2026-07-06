from __future__ import annotations

import io
import sys
from contextlib import redirect_stdout
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tests" / "mesa"))

import profile_timing_report  # noqa: E402


def report(
    physics: str,
    threads: int,
    timed_seconds: float,
    *,
    eos: bool = True,
    kap: bool = True,
) -> dict[str, object]:
    repeat = 5.0
    timing: dict[str, object] = {
        "parse_seconds": 0.01,
        "profile_seconds": 0.75,
        "eos_calls": 4400.0 if eos else 0.0,
        "kap_calls": 4400.0 if kap else 0.0,
        "nproc": 1.0,
        "omp_num_threads": str(threads),
        "physics": physics,
        "warmup": 1.0,
        "repeat": repeat,
        "timed_profile_seconds": timed_seconds,
    }
    if eos:
        timing["eos_calls_per_second"] = 4400.0 / timed_seconds
    if kap:
        timing["kap_calls_per_second"] = 4400.0 / timed_seconds

    return {
        "model": "/tmp/model.mod",
        "model_number": "1211",
        "net_name": "approx21.net",
        "zones": 880,
        "species": 22,
        "global_seconds": 0.76,
        "timing": timing,
        "breakdown": {
            "profile_array_seconds": 0.001,
            "iso_id_seconds": 0.035,
            "warmup_profile_seconds": 0.70,
            "eos_profile_call_seconds": timed_seconds if physics == "eos" else 0.0,
            "kap_profile_call_seconds": timed_seconds if physics == "kap" else 0.0,
            "eos_kap_profile_call_seconds": (
                timed_seconds if physics == "eos-kap" else 0.0
            ),
            "output_collect_seconds": 0.004,
            "shutdown_seconds": 0.001,
            "warmup_repeats": 1.0,
            "timed_repeats": repeat,
            "timed_worker_seconds": timed_seconds,
            "accounted_worker_seconds": 0.741,
            "unaccounted_python_seconds": 0.001,
        },
    }


def main() -> int:
    singles = [
        report("eos", 10, 0.012, eos=True, kap=False),
        report("kap", 10, 0.022, eos=False, kap=True),
        report("eos-kap", 10, 0.014, eos=True, kap=True),
    ]
    sweep = [
        report("eos-kap", 1, 0.100),
        report("eos-kap", 2, 0.050),
        report("eos-kap", 4, 0.025),
    ]

    output = io.StringIO()
    with redirect_stdout(output):
        profile_timing_report.print_header(singles + sweep)
        profile_timing_report.print_single_summary(singles)
        profile_timing_report.print_breakdown_summary(singles)
        profile_timing_report.print_sweep_summary(sweep)

    text = output.getvalue()
    required = [
        "saved-model profile timing report",
        "single-run summary:",
        "global timing breakdown:",
        "thread sweep summary:",
        "best thread-sweep point: OMP_NUM_THREADS=4",
        "eos-kap",
    ]
    missing = [fragment for fragment in required if fragment not in text]
    if missing:
        raise AssertionError(f"missing expected report fragments: {missing}")

    print("profile_timing_report: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
