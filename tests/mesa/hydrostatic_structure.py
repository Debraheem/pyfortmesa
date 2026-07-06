"""Optional MESA integration example for a toy hydrostatic stellar model.

Run after installing with `./mk mesa`:

    tests/mesa/run_hydrostatic_structure.sh --with-mesa

This is a toy solver. It prints the input composition, MESA constants, CHEM
output, and the first/last shells from a simple spherical hydrostatic structure
problem. It is not a MESA star model.
"""

from __future__ import annotations

import math
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping

from pyfortmesa import mesa


@dataclass(frozen=True)
class MesaConstants:
    """Selected constants loaded from MESA const_def."""

    standard_cgrav: float
    crad: float
    clight: float
    Lsun: float
    Rsun: float
    Msun: float


@dataclass(frozen=True)
class Shell:
    """One point in the toy hydrostatic profile."""

    r: float
    m: float
    P: float
    T: float
    rho: float
    kappa: float
    grad_rad: float


def load_mesa_constants() -> MesaConstants:
    """Load the constants needed by this example from MESA const_def."""
    return MesaConstants(**mesa.constants())


def eos_pressure(eos: mesa.Eos, T: float, rho: float, comp: mesa.Composition) -> float:
    """Return MESA EOS pressure at fixed T and rho."""
    return math.exp(eos.dt(T, rho, comp)["lnPgas"])


def estimate_rho_for_pressure(
    eos: mesa.Eos,
    T: float,
    P: float,
    comp: mesa.Composition,
    rho_guess: float,
) -> float:
    """Use the MESA EOS to estimate rho such that Pgas(T, rho) = P."""
    solution = eos.solve_rho(
        T=T,
        other="lnPgas",
        other_value=math.log(P),
        Rho_guess=max(rho_guess, 1.0e-30),
        comp=comp,
    )
    rho = float(solution["Rho"])
    P_eos = math.exp(solution["results"]["lnPgas"])
    rel_err = abs(P_eos - P) / P
    if rel_err > 5.0e-3:
        raise RuntimeError(f"EOS closure error too large: {rel_err:.3e}")

    return rho


def solve_toy_hydrostatic_star(
    *,
    zones: int = 8,
    composition: mesa.Composition | None = None,
    constants: MesaConstants | None = None,
) -> list[Shell]:
    """Integrate a low-luminosity toy star using MESA EOS and KAP calls."""
    if composition is None:
        composition = mesa.composition({"h1": 0.70, "he4": 0.28, "c12": 0.02})
    if constants is None:
        constants = load_mesa_constants()

    eos = mesa.Eos()
    kap = mesa.Kap()

    r = 1.0e8
    T = 1.2e7
    rho = 40.0
    P = eos_pressure(eos, T, rho, composition)
    m = (4.0 / 3.0) * math.pi * r**3 * rho

    r_surface = 0.20 * constants.Rsun
    total_luminosity = 1.0e-3 * constants.Lsun
    luminosity_mass_scale = 0.20 * constants.Msun
    dr = (r_surface - r) / zones

    profile: list[Shell] = []

    for _ in range(zones + 1):
        # KAP at this shell; KAP gets its electron state from EOS.
        kap_result = kap.opacity(T, rho, composition)
        kappa = kap_result["kappa"]
        luminosity = total_luminosity * min(m / luminosity_mass_scale, 1.0)
        grad_rad = (
            3.0
            * kappa
            * P
            * luminosity
            / (
                16.0
                * math.pi
                * constants.crad
                * constants.clight
                * constants.standard_cgrav
                * m
                * T**4
            )
        )
        profile.append(Shell(r, m, P, T, rho, kappa, grad_rad))

        if len(profile) > zones:
            break

        dm_dr = 4.0 * math.pi * r**2 * rho
        dP_dr = -constants.standard_cgrav * m * rho / r**2
        dT_dr = (T / P) * min(grad_rad, 0.4) * dP_dr

        r_next = r + dr
        m_next = m + dm_dr * dr
        P_next = P + dP_dr * dr
        T_next = T + dT_dr * dr

        if min(m_next, P_next, T_next, r_next) <= 0.0:
            raise RuntimeError("toy hydrostatic integration stepped below zero")

        rho_guess = rho * (P_next / P) * (T / T_next)
        # Close the step with rho(P,T) from EOS.
        rho_next = estimate_rho_for_pressure(
            eos,
            T_next,
            P_next,
            composition,
            rho_guess,
        )

        r = r_next
        m = m_next
        P = P_next
        T = T_next
        rho = rho_next

    return profile


def profile_checks(
    profile: list[Shell],
    chem_output: Mapping[str, float],
) -> dict[str, bool]:
    """Return named checks for display without using assert statements."""
    if not profile:
        return {"profile_has_shells": False}

    return {
        "composition_sumx_close_to_1": math.isclose(
            chem_output["sumx"],
            1.0,
            rel_tol=0.0,
            abs_tol=1.0e-12,
        ),
        "composition_ye_in_range": 0.0 < chem_output["ye"] < 1.0,
        "has_at_least_8_shells": len(profile) >= 8,
        "r_positive": all(shell.r > 0.0 for shell in profile),
        "m_positive": all(shell.m > 0.0 for shell in profile),
        "P_positive": all(shell.P > 0.0 for shell in profile),
        "T_positive": all(shell.T > 0.0 for shell in profile),
        "rho_positive": all(shell.rho > 0.0 for shell in profile),
        "kappa_positive": all(shell.kappa > 0.0 for shell in profile),
        "r_increases_outward": profile[-1].r > profile[0].r,
        "m_increases_outward": profile[-1].m > profile[0].m,
        "P_decreases_outward": profile[-1].P < profile[0].P,
        "T_decreases_outward": profile[-1].T < profile[0].T,
        "rho_decreases_outward": profile[-1].rho < profile[0].rho,
    }


def composition_dict(comp: mesa.Composition) -> dict[str, float]:
    """Return isotope-name mass fractions for display."""
    return {
        name: float(value)
        for name, value in zip(comp.names, comp.xa, strict=True)
    }


def print_mapping(title: str, values: Mapping[str, float | bool]) -> None:
    """Print a short named-value block."""
    print(title)
    for name, value in values.items():
        if isinstance(value, bool):
            print(f"  {name} = {value}")
        else:
            print(f"  {name} = {value:.6e}")


def main() -> int:
    if os.environ.get("PYFORTMESA_WITH_MESA") != "1":
        print("skipped: set PYFORTMESA_WITH_MESA=1 to run the MESA integration test")
        return 0

    repo_root = Path(__file__).resolve().parents[2]
    mesa.set_inlist(repo_root / "inlist_eos_and_kap")

    try:
        composition = mesa.composition({"h1": 0.70, "he4": 0.28, "c12": 0.02})
        constants = load_mesa_constants()
        # CHEM gives the composition moments used for checks.
        chem_output = mesa.Chem().composition_info(composition)
        profile = solve_toy_hydrostatic_star(
            composition=composition,
            constants=constants,
        )
        checks = profile_checks(profile, chem_output)

        print("MESA hydrostatic structure example")
        print_mapping("input composition mass fractions:", composition_dict(composition))
        print_mapping("MESA const_def values used:", asdict(constants))
        print_mapping("CHEM output:", chem_output)
        print_mapping("first shell output:", asdict(profile[0]))
        print_mapping("last shell output:", asdict(profile[-1]))
        print_mapping("checks:", checks)
        print(f"zones = {len(profile)}")

        return 0 if all(checks.values()) else 1
    finally:
        mesa.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
