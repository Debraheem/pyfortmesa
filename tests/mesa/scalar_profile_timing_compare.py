"""Compare scalar raw loops and profile wrappers on identical inputs."""

from __future__ import annotations

import argparse
import math
import os
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Callable

import numpy as np

from mesa_mod_profile_reader import default_model_path, read_saved_model


@dataclass(frozen=True)
class CompositionCase:
    name: str
    species: int
    chem_id: np.ndarray
    xa_profile: np.ndarray
    scalar_xa: Callable[[int], np.ndarray]


@dataclass(frozen=True)
class TimingRow:
    case: str
    physics: str
    species: int
    zones: int
    scalar_us_per_zone: float
    profile_us_per_zone: float

    @property
    def scalar_over_profile(self) -> float:
        return self.scalar_us_per_zone / self.profile_us_per_zone


def resolve_model_path(model: str | None) -> Path:
    if model is not None:
        return Path(model).expanduser().resolve()
    return default_model_path()


def timed_repeat(repeat: int, call: Callable[[], object]) -> float:
    start = perf_counter()
    for _ in range(repeat):
        call()
    return perf_counter() - start


def build_cases(mesa: object, isotope_names: tuple[str, ...], xa_saved: np.ndarray) -> list[CompositionCase]:
    fixed_mix = mesa.composition({"h1": 0.70, "he4": 0.28, "c12": 0.02})
    saved_chem_id = np.asfortranarray(mesa.iso_ids(isotope_names), dtype=np.int32)
    return [
        CompositionCase(
            name="fixed_3",
            species=fixed_mix.xa.size,
            chem_id=fixed_mix.chem_id,
            xa_profile=fixed_mix.xa,
            scalar_xa=lambda _index, xa=fixed_mix.xa: xa,
        ),
        CompositionCase(
            name="saved_22",
            species=saved_chem_id.size,
            chem_id=saved_chem_id,
            xa_profile=xa_saved,
            scalar_xa=lambda index, xa=xa_saved: xa[:, index],
        ),
    ]


def compare_case(
    mesa: object,
    case: CompositionCase,
    T: np.ndarray,
    Rho: np.ndarray,
    *,
    warmup: int,
    repeat: int,
) -> list[TimingRow]:
    eos = mesa.Eos()
    kap = mesa.Kap()
    zones = T.size

    def scalar_eos() -> None:
        for k in range(zones):
            eos.dt_raw(T[k], Rho[k], case.chem_id, case.scalar_xa(k))

    def scalar_kap() -> None:
        for k in range(zones):
            kap.opacity_raw(T[k], Rho[k], case.chem_id, case.scalar_xa(k))

    def scalar_eos_kap() -> None:
        for k in range(zones):
            kap.eos_kap_raw(T[k], Rho[k], case.chem_id, case.scalar_xa(k))

    def profile_eos() -> object:
        return eos.dt_profile(T, Rho, case.chem_id, case.xa_profile, output="raw")

    def profile_kap() -> object:
        return kap.opacity_profile(T, Rho, case.chem_id, case.xa_profile)

    def profile_eos_kap() -> object:
        return kap.eos_kap_profile(T, Rho, case.chem_id, case.xa_profile, output="raw")

    calls: tuple[tuple[str, Callable[[], object], Callable[[], object]], ...] = (
        ("eos", scalar_eos, profile_eos),
        ("kap", scalar_kap, profile_kap),
        ("eos-kap", scalar_eos_kap, profile_eos_kap),
    )
    rows: list[TimingRow] = []
    for physics, scalar_call, profile_call in calls:
        for _ in range(warmup):
            scalar_call()
            profile_call()

        scalar_seconds = timed_repeat(repeat, scalar_call)
        profile_seconds = timed_repeat(repeat, profile_call)
        rows.append(
            TimingRow(
                case=case.name,
                physics=physics,
                species=case.species,
                zones=zones,
                scalar_us_per_zone=1.0e6 * scalar_seconds / (repeat * zones),
                profile_us_per_zone=1.0e6 * profile_seconds / (repeat * zones),
            )
        )
    return rows


def print_rows(rows: list[TimingRow], *, warmup: int, repeat: int) -> None:
    omp_threads = os.environ.get("OMP_NUM_THREADS", "unset")
    print("scalar/profile identical-input timing")
    print(f"OMP_NUM_THREADS = {omp_threads}")
    print(f"warmup = {warmup}")
    print(f"repeat = {repeat}")
    print()
    print(
        "  "
        f"{'case':<10} {'physics':<8} {'species':>7} {'zones':>7} "
        f"{'scalar_us/zone':>15} {'profile_us/zone':>15} {'scalar/profile':>14}"
    )
    for row in rows:
        print(
            "  "
            f"{row.case:<10} {row.physics:<8} {row.species:7d} {row.zones:7d} "
            f"{row.scalar_us_per_zone:15.3f} "
            f"{row.profile_us_per_zone:15.3f} "
            f"{row.scalar_over_profile:14.3f}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare scalar raw loops and profile wrappers using the same "
            "saved-model T/Rho arrays and composition inputs."
        )
    )
    parser.add_argument("--model", help="Saved .mod path. Defaults under $MESA_DIR.")
    parser.add_argument(
        "--max-zones",
        type=int,
        default=0,
        help="Use only the first N zones. Default 0 means all zones.",
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=int(os.environ.get("PYFORTMESA_COMPARE_WARMUP", "1")),
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=int(os.environ.get("PYFORTMESA_COMPARE_REPEAT", "5")),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.warmup < 0:
        raise ValueError("warmup must be non-negative")
    if args.repeat <= 0:
        raise ValueError("repeat must be positive")

    from pyfortmesa import mesa

    profile = read_saved_model(resolve_model_path(args.model))
    zones = profile.selected_zones(args.max_zones)
    T = np.asfortranarray([zone.T for zone in zones], dtype=np.float64)
    Rho = np.asfortranarray([zone.rho for zone in zones], dtype=np.float64)
    isotope_names = profile.isotope_columns
    xa_saved = np.asfortranarray(
        [[zone.values[name] for zone in zones] for name in isotope_names],
        dtype=np.float64,
    )

    repo_root = Path(__file__).resolve().parents[2]
    mesa.set_cache_root(".")
    mesa.set_inlist(repo_root / "inlist_eos_and_kap")

    try:
        rows: list[TimingRow] = []
        for case in build_cases(mesa, isotope_names, xa_saved):
            rows.extend(
                compare_case(mesa, case, T, Rho, warmup=args.warmup, repeat=args.repeat)
            )
        print_rows(rows, warmup=args.warmup, repeat=args.repeat)
    finally:
        mesa.shutdown()

    if any(not math.isfinite(row.scalar_over_profile) for row in rows):
        raise RuntimeError("non-finite timing ratio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
