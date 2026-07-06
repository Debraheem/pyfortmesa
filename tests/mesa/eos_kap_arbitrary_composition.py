"""Optional MESA EOS/KAP example for a named composition."""

from __future__ import annotations

import os
from pathlib import Path

from pyfortmesa import mesa


def call_eos_and_kap() -> None:
    """Call MESA EOS and KAP through pyfortmesa for one composition."""
    repo_root = Path(__file__).resolve().parents[2]
    mesa.set_inlist(repo_root / "inlist_eos_and_kap")

    # Inputs: MESA isotope names mapped to mass fractions. They must sum to 1.
    mass_fractions = {"h1": 0.70, "he4": 0.28, "c12": 0.02}
    mix = mesa.composition(mass_fractions)

    # Inputs: temperature in K and density in g/cm^3.
    eos_T = 1.0e7
    eos_rho = 1.0e2
    kap_T = 1.0e6
    kap_rho = 1.0e-7

    eos = mesa.Eos()
    kap = mesa.Kap()
    kap_type2 = mesa.Kap(use_type2=True, zbase=0.02)

    # Outputs: EOS returns log thermodynamic quantities and derivatives.
    eos_result = eos.dt(T=eos_T, Rho=eos_rho, comp=mix)
    eos_full_result = eos.dt_full(T=eos_T, Rho=eos_rho, comp=mix)
    eos_rho_solve = eos.solve_rho(
        T=eos_T,
        other="lnPgas",
        other_value=eos_result["lnPgas"],
        Rho_guess=0.8 * eos_rho,
        comp=mix,
    )
    eos_T_solve = eos.solve_t(
        Rho=eos_rho,
        other="lnPgas",
        other_value=eos_result["lnPgas"],
        T_guess=0.9 * eos_T,
        comp=mix,
    )

    # Outputs: KAP returns opacity and logarithmic opacity derivatives.
    kap_result = kap.opacity(T=kap_T, Rho=kap_rho, comp=mix)
    kap_full_result = kap.opacity_full(T=kap_T, Rho=kap_rho, comp=mix)
    kap_type2_result = kap_type2.opacity_full(T=kap_T, Rho=kap_rho, comp=mix)

    print("MESA EOS/KAP arbitrary-composition example")
    print(f"composition mass fractions = {mass_fractions}")
    print(f"EOS input: T = {eos_T:.6e} K, rho = {eos_rho:.6e} g/cm^3")
    print(f"KAP input: T = {kap_T:.6e} K, rho = {kap_rho:.6e} g/cm^3")
    print(f"EOS output = {eos_result}")
    print(f"EOS full result names = {list(eos_full_result['results'])}")
    print(f"EOS d_dxa output = {eos_full_result['d_dxa']}")
    print(f"EOS solve_rho output rho = {eos_rho_solve['Rho']:.6e} g/cm^3")
    print(f"EOS solve_t output T = {eos_T_solve['T']:.6e} K")
    print(f"KAP output = {kap_result}")
    print(f"KAP opacity fractions = {kap_full_result['kap_fracs']}")
    print(f"KAP dlnkap_dxa output = {kap_full_result['dlnkap_dxa']}")
    print(f"KAP Type2-controlled opacity fractions = {kap_type2_result['kap_fracs']}")


def main() -> int:
    if os.environ.get("PYFORTMESA_WITH_MESA") != "1":
        print("skipped: set PYFORTMESA_WITH_MESA=1 to run the MESA integration test")
        return 0

    try:
        call_eos_and_kap()
    finally:
        mesa.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
