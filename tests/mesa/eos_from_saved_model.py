"""Evaluate MESA EOS at every zone in a text `.mod` saved model.

This example reads a MESA star saved-model file, parses the profile mass
fractions, and passes `lnT`, `lnd`, isotope ids, and `xa(species, nzones)` to a
Fortran batch wrapper. The wrapper reconstructs `T` and `rho`, then calls
`eosDT_get` once per zone.

The saved model used here does not store EOS result columns such as `lnPgas` or
`gamma1`, so those values are printed as newly computed EOS outputs rather than
checked against reference EOS values from the file.
"""

from __future__ import annotations

import argparse
import json
import math
import multiprocessing as mp
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Iterable

import numpy as np

from mesa_mod_profile_reader import (
    SavedModelProfile,
    SavedModelZone,
    default_model_path,
    read_saved_model,
)


@dataclass(frozen=True)
class EosZoneOutput:
    """Small EOS output record for display and timing."""

    zone: int
    T: float
    rho: float
    sumx_mod: float
    lnPgas: float
    lnE: float
    grad_ad: float
    gamma1: float


@dataclass(frozen=True)
class KapZoneOutput:
    """Small KAP output record for display and timing."""

    zone: int
    T: float
    rho: float
    sumx_mod: float
    kappa: float
    dlnkap_dlnRho: float
    dlnkap_dlnT: float


@dataclass(frozen=True)
class BatchTiming:
    """Worker-local timing for one saved-model profile batch."""

    profile_array_seconds: float = 0.0
    iso_id_seconds: float = 0.0
    warmup_profile_seconds: float = 0.0
    eos_profile_call_seconds: float = 0.0
    kap_profile_call_seconds: float = 0.0
    eos_kap_profile_call_seconds: float = 0.0
    output_collect_seconds: float = 0.0
    shutdown_seconds: float = 0.0
    warmup_repeats: int = 0
    timed_repeats: int = 1

    @property
    def timed_profile_seconds(self) -> float:
        return (
            self.eos_profile_call_seconds
            + self.kap_profile_call_seconds
            + self.eos_kap_profile_call_seconds
        )

    @property
    def accounted_seconds(self) -> float:
        return (
            self.profile_array_seconds
            + self.iso_id_seconds
            + self.warmup_profile_seconds
            + self.eos_profile_call_seconds
            + self.kap_profile_call_seconds
            + self.eos_kap_profile_call_seconds
            + self.output_collect_seconds
            + self.shutdown_seconds
        )


@dataclass(frozen=True)
class ProfileEvaluation:
    """Outputs and per-batch timings from a profile evaluation."""

    eos_outputs: list[EosZoneOutput]
    kap_outputs: list[KapZoneOutput]
    batch_timings: list[BatchTiming]


@dataclass(frozen=True)
class TimingOutput:
    """Timing summary for the saved-model profile example."""

    parse_seconds: float
    profile_seconds: float
    eos_calls: int
    kap_calls: int
    nproc: int
    physics: str
    omp_num_threads: str
    warmup: int
    repeat: int
    timed_profile_seconds: float

    def calls_per_second(self, calls: int) -> float:
        if self.timed_profile_seconds <= 0.0:
            return math.inf
        return calls / self.timed_profile_seconds


def resolve_model_path(model: str | None) -> Path:
    """Resolve the requested saved model path."""
    if model is not None:
        return Path(model).expanduser().resolve()
    return default_model_path()


def profile_comparison(
    profile: SavedModelProfile,
    zones: tuple[SavedModelZone, ...],
) -> dict[str, float | bool]:
    """Compare parsed values against the saved-model text columns."""
    isotope_columns = profile.isotope_columns
    sumx_values = [zone.mass_fraction_sum(isotope_columns) for zone in zones]
    logT_roundtrip = [abs(math.log(zone.T) - zone.lnT) for zone in zones]
    lnd_roundtrip = [abs(math.log(zone.rho) - zone.lnd) for zone in zones]

    return {
        "header_n_shells": float(profile.n_shells or -1),
        "parsed_zones": float(len(profile.zones)),
        "evaluated_zones": float(len(zones)),
        "n_shells_match": profile.zone_count_matches_header,
        "header_species": float(profile.species or -1),
        "isotope_columns": float(len(isotope_columns)),
        "species_count_match": (
            profile.species is None or profile.species == len(isotope_columns)
        ),
        "max_abs_python_logT_roundtrip": max(logT_roundtrip),
        "max_abs_python_lnd_roundtrip": max(lnd_roundtrip),
        "min_sumx_from_mod": min(sumx_values),
        "max_sumx_from_mod": max(sumx_values),
        "eos_reference_columns_in_mod": _has_eos_reference_columns(profile),
    }


def _has_eos_reference_columns(profile: SavedModelProfile) -> bool:
    eos_reference_names = {
        "lnPgas",
        "lnE",
        "lnS",
        "grad_ad",
        "gamma1",
        "pressure",
        "logP",
    }
    return any(name in eos_reference_names for name in profile.columns)


def evaluate_profile(
    profile: SavedModelProfile,
    zones: tuple[SavedModelZone, ...],
    *,
    nproc: int,
    inlist: Path,
    physics: str,
    warmup: int,
    repeat: int,
) -> ProfileEvaluation:
    """Evaluate selected MESA profile physics inside Fortran batches."""
    if nproc <= 1:
        return _evaluate_zone_batch(
            (zones, profile.isotope_columns, inlist, physics, warmup, repeat)
        )

    chunks = _chunk_zones(zones, nproc)
    work_items = [
        (chunk, profile.isotope_columns, inlist, physics, warmup, repeat)
        for chunk in chunks
        if chunk
    ]
    context = mp.get_context("spawn")
    with context.Pool(processes=nproc) as pool:
        batches = pool.map(_evaluate_zone_batch, work_items)

    eos_outputs = [
        output for batch in batches for output in batch.eos_outputs
    ]
    kap_outputs = [
        output for batch in batches for output in batch.kap_outputs
    ]
    timings = [
        timing for batch in batches for timing in batch.batch_timings
    ]
    return ProfileEvaluation(
        eos_outputs=sorted(eos_outputs, key=lambda output: output.zone),
        kap_outputs=sorted(kap_outputs, key=lambda output: output.zone),
        batch_timings=timings,
    )


def _evaluate_zone_batch(
    args: tuple[
        tuple[SavedModelZone, ...],
        tuple[str, ...],
        Path,
        str,
        int,
        int,
    ],
) -> ProfileEvaluation:
    zones, isotope_columns, inlist, physics, warmup, repeat = args

    from pyfortmesa import mesa

    mesa.set_inlist(inlist)

    timing = BatchTiming()
    eos_outputs: list[EosZoneOutput] = []
    kap_outputs: list[KapZoneOutput] = []
    timing_active = False

    try:
        # Setup work: not part of the timed profile call.
        array_start = perf_counter()
        lnT, lnd, xa = _profile_arrays(zones, isotope_columns)
        profile_array_seconds = perf_counter() - array_start

        iso_start = perf_counter()
        chem_id_values = mesa.iso_ids(isotope_columns)
        iso_id_seconds = perf_counter() - iso_start

        eos_profile_call_seconds = 0.0
        kap_profile_call_seconds = 0.0
        eos_kap_profile_call_seconds = 0.0
        output_collect_seconds = 0.0
        warmup_profile_seconds = 0.0
        eos_result_full = None
        kap_result = None
        eos = mesa.Eos() if physics == "eos" else None
        kap = mesa.Kap() if physics in {"kap", "eos-kap"} else None

        mesa.enable_timing(reset=True)
        timing_active = True
        for _ in range(warmup):
            _call_profile_physics(physics, eos, kap, lnT, lnd, chem_id_values, xa)
        warmup_profile_seconds = _timing_seconds(mesa.timing_summary())
        mesa.reset_timing()

        for _ in range(repeat):
            eos_result_full, kap_result = _call_profile_physics(
                physics, eos, kap, lnT, lnd, chem_id_values, xa
            )
        call_seconds = _profile_call_seconds(mesa.timing_summary())
        eos_profile_call_seconds = call_seconds["eos"]
        kap_profile_call_seconds = call_seconds["kap"]
        eos_kap_profile_call_seconds = call_seconds["eos_kap"]
        mesa.disable_timing()
        timing_active = False

        collect_start = perf_counter()
        if eos_result_full is not None:
            eos_result = eos_result_full["results"]
            eos_outputs = [
                EosZoneOutput(
                    zone=zone.zone,
                    T=float(eos_result_full["T"][index]),
                    rho=float(eos_result_full["Rho"][index]),
                    sumx_mod=float(xa[:, index].sum()),
                    lnPgas=float(eos_result["lnPgas"][index]),
                    lnE=float(eos_result["lnE"][index]),
                    grad_ad=float(eos_result["grad_ad"][index]),
                    gamma1=float(eos_result["gamma1"][index]),
                )
                for index, zone in enumerate(zones)
            ]

        if kap_result is not None:
            kap_outputs = [
                KapZoneOutput(
                    zone=zone.zone,
                    T=float(kap_result["T"][index]),
                    rho=float(kap_result["Rho"][index]),
                    sumx_mod=float(xa[:, index].sum()),
                    kappa=float(kap_result["kappa"][index]),
                    dlnkap_dlnRho=float(kap_result["dlnkap_dlnRho"][index]),
                    dlnkap_dlnT=float(kap_result["dlnkap_dlnT"][index]),
                )
                for index, zone in enumerate(zones)
            ]
        output_collect_seconds = perf_counter() - collect_start

        timing = BatchTiming(
            profile_array_seconds=profile_array_seconds,
            iso_id_seconds=iso_id_seconds,
            warmup_profile_seconds=warmup_profile_seconds,
            eos_profile_call_seconds=eos_profile_call_seconds,
            kap_profile_call_seconds=kap_profile_call_seconds,
            eos_kap_profile_call_seconds=eos_kap_profile_call_seconds,
            output_collect_seconds=output_collect_seconds,
            warmup_repeats=warmup,
            timed_repeats=repeat,
        )
    finally:
        if timing_active:
            mesa.disable_timing()
        shutdown_start = perf_counter()
        mesa.shutdown()
        shutdown_seconds = perf_counter() - shutdown_start

    timing = BatchTiming(
        profile_array_seconds=timing.profile_array_seconds,
        iso_id_seconds=timing.iso_id_seconds,
        warmup_profile_seconds=timing.warmup_profile_seconds,
        eos_profile_call_seconds=timing.eos_profile_call_seconds,
        kap_profile_call_seconds=timing.kap_profile_call_seconds,
        eos_kap_profile_call_seconds=timing.eos_kap_profile_call_seconds,
        output_collect_seconds=timing.output_collect_seconds,
        shutdown_seconds=shutdown_seconds,
        warmup_repeats=timing.warmup_repeats,
        timed_repeats=timing.timed_repeats,
    )
    return ProfileEvaluation(
        eos_outputs=eos_outputs,
        kap_outputs=kap_outputs,
        batch_timings=[timing],
    )


def _call_profile_physics(
    physics: str,
    eos: object | None,
    kap: object | None,
    lnT: np.ndarray,
    lnd: np.ndarray,
    chem_id_values: np.ndarray,
    xa: np.ndarray,
) -> tuple[object | None, object | None]:
    if physics == "eos-kap":
        if kap is None:
            raise RuntimeError("KAP object is not initialized")
        # One Fortran loop: EOS first, then KAP uses that electron state.
        combined = kap.eos_kap_profile_from_logs(lnT, lnd, chem_id_values, xa)
        return combined, combined

    if physics == "eos":
        if eos is None:
            raise RuntimeError("EOS object is not initialized")
        # One Python call for the whole profile; Fortran loops over zones.
        eos_output = eos.dt_profile_from_logs(lnT, lnd, chem_id_values, xa)
        return eos_output, None

    if physics == "kap":
        if kap is None:
            raise RuntimeError("KAP object is not initialized")
        # KAP asks EOS for lnfree_e and eta before kap_get.
        kap_output = kap.opacity_profile_from_logs(lnT, lnd, chem_id_values, xa)
        return None, kap_output

    raise ValueError(f"unsupported physics: {physics}")


def _timing_seconds(rows: Iterable[dict[str, float | int | str]]) -> float:
    return sum(float(row["seconds"]) for row in rows)


def _profile_call_seconds(
    rows: Iterable[dict[str, float | int | str]]
) -> dict[str, float]:
    seconds = {"eos": 0.0, "kap": 0.0, "eos_kap": 0.0}
    for row in rows:
        name = str(row["name"])
        value = float(row["seconds"])
        if name == "eos.dt_profile":
            seconds["eos"] += value
        elif name == "kap.opacity_profile":
            seconds["kap"] += value
        elif name == "kap.eos_kap_profile":
            seconds["eos_kap"] += value
    return seconds


def _profile_arrays(
    zones: tuple[SavedModelZone, ...],
    isotope_columns: tuple[str, ...],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return saved-model arrays for one Fortran batch EOS call."""
    lnT = np.asfortranarray([zone.lnT for zone in zones], dtype=np.float64)
    lnd = np.asfortranarray([zone.lnd for zone in zones], dtype=np.float64)
    xa = np.asfortranarray(
        [
            [zone.values[name] for zone in zones]
            for name in isotope_columns
        ],
        dtype=np.float64,
    )
    return lnT, lnd, xa


def fortran_reconstruction_comparison(
    zones: tuple[SavedModelZone, ...],
    outputs: list[EosZoneOutput] | list[KapZoneOutput],
) -> dict[str, float | bool]:
    """Compare Fortran-reconstructed `T` and `rho` to `.mod` log columns."""
    output_by_zone = {output.zone: output for output in outputs}
    logT_diffs = []
    lnd_diffs = []
    for zone in zones:
        output = output_by_zone[zone.zone]
        logT_diffs.append(abs(math.log(output.T) - zone.lnT))
        lnd_diffs.append(abs(math.log(output.rho) - zone.lnd))

    return {
        "compared_zones": float(len(zones)),
        "max_abs_fortran_logT_minus_mod_lnT": max(logT_diffs),
        "max_abs_fortran_lnrho_minus_mod_lnd": max(lnd_diffs),
        "all_reconstructed_T_positive": all(output.T > 0.0 for output in outputs),
        "all_reconstructed_rho_positive": all(output.rho > 0.0 for output in outputs),
    }


def _chunk_zones(
    zones: tuple[SavedModelZone, ...],
    nproc: int,
) -> list[tuple[SavedModelZone, ...]]:
    chunk_count = min(nproc, len(zones))
    chunk_size = math.ceil(len(zones) / chunk_count)
    return [
        zones[start : start + chunk_size]
        for start in range(0, len(zones), chunk_size)
    ]


def sample_outputs(
    outputs: list[EosZoneOutput] | list[KapZoneOutput],
) -> list[EosZoneOutput] | list[KapZoneOutput]:
    """Return first, middle, and last outputs for compact display."""
    if len(outputs) <= 3:
        return outputs

    return [
        outputs[0],
        outputs[len(outputs) // 2],
        outputs[-1],
    ]


def print_mapping(title: str, values: dict[str, float | bool | str]) -> None:
    """Print a short named-value block."""
    print(title)
    for name, value in values.items():
        if isinstance(value, bool):
            print(f"  {name} = {value}")
        elif isinstance(value, str):
            print(f"  {name} = {value}")
        else:
            print(f"  {name} = {value:.6e}")


def print_eos_outputs(outputs: Iterable[EosZoneOutput]) -> None:
    """Print selected EOS outputs."""
    print("sample EOS outputs:")
    for output in outputs:
        values = asdict(output)
        print(
            "  "
            f"zone={values['zone']:4d} "
            f"T={values['T']:.6e} K "
            f"rho={values['rho']:.6e} g/cm^3 "
            f"sumx_mod={values['sumx_mod']:.12e} "
            f"lnPgas={values['lnPgas']:.6e} "
            f"lnE={values['lnE']:.6e} "
            f"grad_ad={values['grad_ad']:.6e} "
            f"gamma1={values['gamma1']:.6e}"
        )


def print_kap_outputs(outputs: Iterable[KapZoneOutput]) -> None:
    """Print selected KAP outputs."""
    print("sample KAP outputs:")
    for output in outputs:
        values = asdict(output)
        print(
            "  "
            f"zone={values['zone']:4d} "
            f"T={values['T']:.6e} K "
            f"rho={values['rho']:.6e} g/cm^3 "
            f"sumx_mod={values['sumx_mod']:.12e} "
            f"kappa={values['kappa']:.6e} "
            f"dlnkap_dlnRho={values['dlnkap_dlnRho']:.6e} "
            f"dlnkap_dlnT={values['dlnkap_dlnT']:.6e}"
        )


def sum_batch_timings(batch_timings: list[BatchTiming]) -> BatchTiming:
    """Return cumulative worker timings across profile batches."""
    return BatchTiming(
        profile_array_seconds=sum(t.profile_array_seconds for t in batch_timings),
        iso_id_seconds=sum(t.iso_id_seconds for t in batch_timings),
        warmup_profile_seconds=sum(t.warmup_profile_seconds for t in batch_timings),
        eos_profile_call_seconds=sum(
            t.eos_profile_call_seconds for t in batch_timings
        ),
        kap_profile_call_seconds=sum(
            t.kap_profile_call_seconds for t in batch_timings
        ),
        eos_kap_profile_call_seconds=sum(
            t.eos_kap_profile_call_seconds for t in batch_timings
        ),
        output_collect_seconds=sum(t.output_collect_seconds for t in batch_timings),
        shutdown_seconds=sum(t.shutdown_seconds for t in batch_timings),
        warmup_repeats=max((t.warmup_repeats for t in batch_timings), default=0),
        timed_repeats=max((t.timed_repeats for t in batch_timings), default=1),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Call pyfortmesa profile physics across a MESA text .mod saved model."
    )
    parser.add_argument(
        "--model",
        help="Path to a MESA text .mod saved model. Defaults under $MESA_DIR.",
    )
    parser.add_argument(
        "--max-zones",
        type=int,
        default=0,
        help="Evaluate only the first N zones. Default 0 means all zones.",
    )
    parser.add_argument(
        "--nproc",
        type=int,
        default=int(os.environ.get("PYFORTMESA_NPROC", "1")),
        help="Number of Python processes for profile calls. Use 10 for a 10-core run.",
    )
    parser.add_argument(
        "--physics",
        choices=("eos", "kap", "eos-kap"),
        default="eos",
        help=(
            "Profile physics to time. KAP timing includes the EOS electron-state "
            "call required by kap_get."
        ),
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=0,
        help="Number of untimed profile calls before measuring.",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Number of timed profile calls in one Python process.",
    )
    parser.add_argument(
        "--parse-only",
        action="store_true",
        help="Parse the saved model and print comparisons without EOS calls.",
    )
    parser.add_argument(
        "--timing-json",
        type=Path,
        help="Write machine-readable timing output to this JSON file.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.warmup < 0:
        raise ValueError("--warmup must be non-negative")
    if args.repeat <= 0:
        raise ValueError("--repeat must be positive")

    model_path = resolve_model_path(args.model)

    parse_start = perf_counter()
    profile = read_saved_model(model_path)
    zones = profile.selected_zones(args.max_zones)
    parse_seconds = perf_counter() - parse_start

    print("MESA saved-model EOS profile example")
    print(f"model = {profile.path}")
    print(f"model_number = {profile.metadata.get('model_number', 'unknown')}")
    print(f"net_name = {profile.metadata.get('net_name', 'unknown')}")
    print(f"physics = {args.physics}")
    print_mapping("comparison with saved-model file:", profile_comparison(profile, zones))
    print(f"parse_seconds = {parse_seconds:.6e}")

    if args.parse_only:
        print("parse-only mode: no EOS calls made")
        return 0

    if os.environ.get("PYFORTMESA_WITH_MESA") != "1":
        print("skipped: set PYFORTMESA_WITH_MESA=1 to run EOS calls")
        return 0

    repo_root = Path(__file__).resolve().parents[2]
    inlist = repo_root / "inlist_eos_and_kap"

    profile_start = perf_counter()
    evaluation = evaluate_profile(
        profile,
        zones,
        nproc=max(args.nproc, 1),
        inlist=inlist,
        physics=args.physics,
        warmup=args.warmup,
        repeat=args.repeat,
    )
    profile_seconds = perf_counter() - profile_start
    worker_timing = sum_batch_timings(evaluation.batch_timings)
    eos_calls = 0
    kap_calls = 0
    if args.physics in {"eos", "eos-kap"}:
        eos_calls = len(zones) * args.repeat
    if args.physics in {"kap", "eos-kap"}:
        kap_calls = len(zones) * args.repeat
    timing = TimingOutput(
        parse_seconds=parse_seconds,
        profile_seconds=profile_seconds,
        eos_calls=eos_calls,
        kap_calls=kap_calls,
        nproc=max(args.nproc, 1),
        physics=args.physics,
        omp_num_threads=os.environ.get("OMP_NUM_THREADS", "unset"),
        warmup=args.warmup,
        repeat=args.repeat,
        timed_profile_seconds=worker_timing.timed_profile_seconds,
    )

    timing_values: dict[str, float | bool | str] = {
        "parse_seconds": timing.parse_seconds,
        "profile_seconds": timing.profile_seconds,
        "eos_calls": float(timing.eos_calls),
        "kap_calls": float(timing.kap_calls),
        "nproc": float(timing.nproc),
        "omp_num_threads": timing.omp_num_threads,
        "physics": timing.physics,
        "warmup": float(timing.warmup),
        "repeat": float(timing.repeat),
        "timed_profile_seconds": timing.timed_profile_seconds,
    }
    if timing.eos_calls > 0:
        timing_values["eos_calls_per_second"] = timing.calls_per_second(
            timing.eos_calls
        )
    if timing.kap_calls > 0:
        timing_values["kap_calls_per_second"] = timing.calls_per_second(
            timing.kap_calls
        )
    print_mapping(
        "timing:",
        timing_values,
    )

    breakdown_values: dict[str, float | bool | str] = {
        "profile_array_seconds": worker_timing.profile_array_seconds,
        "iso_id_seconds": worker_timing.iso_id_seconds,
        "warmup_profile_seconds": worker_timing.warmup_profile_seconds,
        "eos_profile_call_seconds": worker_timing.eos_profile_call_seconds,
        "kap_profile_call_seconds": worker_timing.kap_profile_call_seconds,
        "eos_kap_profile_call_seconds": worker_timing.eos_kap_profile_call_seconds,
        "output_collect_seconds": worker_timing.output_collect_seconds,
        "shutdown_seconds": worker_timing.shutdown_seconds,
        "warmup_repeats": float(worker_timing.warmup_repeats),
        "timed_repeats": float(worker_timing.timed_repeats),
        "timed_worker_seconds": worker_timing.timed_profile_seconds,
        "accounted_worker_seconds": worker_timing.accounted_seconds,
    }
    if timing.nproc == 1:
        breakdown_values["unaccounted_python_seconds"] = (
            timing.profile_seconds - worker_timing.accounted_seconds
        )
    print_mapping("profile timing breakdown:", breakdown_values)

    if args.timing_json is not None:
        report = {
            "model": str(profile.path),
            "model_number": profile.metadata.get("model_number", "unknown"),
            "net_name": profile.metadata.get("net_name", "unknown"),
            "zones": len(zones),
            "species": len(profile.isotope_columns),
            "global_seconds": parse_seconds + profile_seconds,
            "timing": timing_values,
            "breakdown": breakdown_values,
        }
        args.timing_json.parent.mkdir(parents=True, exist_ok=True)
        args.timing_json.write_text(json.dumps(report, indent=2) + "\n")

    reconstruction_outputs = evaluation.eos_outputs or evaluation.kap_outputs
    print_mapping(
        "Fortran reconstruction compared to saved-model columns:",
        fortran_reconstruction_comparison(zones, reconstruction_outputs),
    )
    if evaluation.eos_outputs:
        print_eos_outputs(sample_outputs(evaluation.eos_outputs))
    if evaluation.kap_outputs:
        print_kap_outputs(sample_outputs(evaluation.kap_outputs))

    if not _has_eos_reference_columns(profile):
        print(
            "note: this .mod file stores lnd, lnT, and composition, "
            "but not EOS result columns such as lnPgas or gamma1."
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
