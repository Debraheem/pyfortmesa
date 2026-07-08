"""Optional MESA eos/kap example for a named composition."""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np

from pyfortmesa import mesa


def call_eos_and_kap() -> None:
    """Call MESA eos and kap through pyfortmesa for one composition."""
    repo_root = Path(__file__).resolve().parents[2]
    mesa.set_inlist(repo_root / "inlist_eos_and_kap")

    # MESA isotope names and mass fractions.
    mass_fractions = {"h1": 0.70, "he4": 0.28, "c12": 0.02}
    mix = mesa.composition(mass_fractions)

    # eos and kap state points.
    eos_T = 1.0e7
    eos_rho = 1.0e2
    kap_T = 1.0e6
    kap_rho = 1.0e-7

    eos = mesa.Eos()
    kap = mesa.Kap()
    kap_type2 = mesa.Kap(use_type2=True, zbase=0.02)

    # eos at fixed T and rho, then two inverse checks.
    eos_result = eos.dt(T=eos_T, Rho=eos_rho, comp=mix)
    eos_full_result = eos.dt_full(T=eos_T, Rho=eos_rho, comp=mix)
    eos_raw_result = eos.dt_raw(eos_T, eos_rho, mix.chem_id, mix.xa)
    eos_full_raw_result = eos.dt_full_raw(eos_T, eos_rho, mix.chem_id, mix.xa)
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

    # kap at fixed T and rho. kap asks eos for electron state internally.
    kap_result = kap.opacity(T=kap_T, Rho=kap_rho, comp=mix)
    kap_full_result = kap.opacity_full(T=kap_T, Rho=kap_rho, comp=mix)
    kap_raw_result = kap.opacity_raw(kap_T, kap_rho, mix.chem_id, mix.xa)
    eos_kap_raw_result = kap.eos_kap_raw(kap_T, kap_rho, mix.chem_id, mix.xa)
    kap_full_raw_result = kap.opacity_full_raw(kap_T, kap_rho, mix.chem_id, mix.xa)
    kap_type2_result = kap_type2.opacity_full(T=kap_T, Rho=kap_rho, comp=mix)

    eos_short_names = ("lnPgas", "lnE", "lnS", "grad_ad", "gamma1")
    eos_short_from_dict = tuple(eos_result[name] for name in eos_short_names)
    if not np.allclose(eos_raw_result, eos_short_from_dict, rtol=1.0e-12, atol=0.0):
        raise AssertionError("eos.dt_raw does not match eos.dt")

    eos_raw_res, eos_raw_dlnrho, eos_raw_dlnt, eos_raw_dxa = eos_full_raw_result
    eos_full_res = np.asarray(
        [eos_full_result["results"][name] for name in mesa.EOS_RESULT_NAMES]
    )
    eos_full_dlnrho = np.asarray(
        [eos_full_result["d_dlnRho"][name] for name in mesa.EOS_RESULT_NAMES]
    )
    eos_full_dlnt = np.asarray(
        [eos_full_result["d_dlnT"][name] for name in mesa.EOS_RESULT_NAMES]
    )
    eos_full_dxa = np.asarray(
        [
            [eos_full_result["d_dxa"][row][name] for name in mix.names]
            for row in mesa.EOS_DXA_RESULT_NAMES
        ]
    )
    if not np.allclose(eos_raw_res, eos_full_res, rtol=1.0e-12, atol=0.0):
        raise AssertionError("eos.dt_full_raw results do not match eos.dt_full")
    if not np.allclose(eos_raw_dlnrho, eos_full_dlnrho, rtol=1.0e-12, atol=0.0):
        raise AssertionError("eos.dt_full_raw d_dlnRho does not match eos.dt_full")
    if not np.allclose(eos_raw_dlnt, eos_full_dlnt, rtol=1.0e-12, atol=0.0):
        raise AssertionError("eos.dt_full_raw d_dlnT does not match eos.dt_full")
    if not np.allclose(eos_raw_dxa, eos_full_dxa, rtol=1.0e-12, atol=0.0):
        raise AssertionError("eos.dt_full_raw d_dxa does not match eos.dt_full")

    kap_short_names = ("kappa", "dlnkap_dlnRho", "dlnkap_dlnT")
    kap_short_from_dict = tuple(kap_result[name] for name in kap_short_names)
    if not np.allclose(kap_raw_result, kap_short_from_dict, rtol=1.0e-12, atol=0.0):
        raise AssertionError("kap.opacity_raw does not match kap.opacity")

    eos_kap_res, eos_kap_kappa, eos_kap_dlnrho, eos_kap_dlnt = eos_kap_raw_result
    eos_at_kap = eos.dt_full_raw(kap_T, kap_rho, mix.chem_id, mix.xa)[0]
    if not np.allclose(eos_kap_res, eos_at_kap, rtol=1.0e-12, atol=0.0):
        raise AssertionError("kap.eos_kap_raw eos results do not match eos.dt_full_raw")
    if not np.allclose(
        (eos_kap_kappa, eos_kap_dlnrho, eos_kap_dlnt), kap_short_from_dict,
        rtol=1.0e-12, atol=0.0
    ):
        raise AssertionError("kap.eos_kap_raw kap outputs do not match kap.opacity")

    kap_raw_kappa, kap_raw_dlnrho, kap_raw_dlnt, kap_raw_fracs, kap_raw_dxa = (
        kap_full_raw_result
    )
    kap_full_short = tuple(kap_full_result[name] for name in kap_short_names)
    kap_full_fracs = np.asarray(
        [kap_full_result["kap_fracs"][name] for name in mesa.KAP_FRAC_NAMES]
    )
    kap_full_dxa = np.asarray(
        [kap_full_result["dlnkap_dxa"][name] for name in mix.names]
    )
    if not np.allclose(
        (kap_raw_kappa, kap_raw_dlnrho, kap_raw_dlnt), kap_full_short,
        rtol=1.0e-12, atol=0.0
    ):
        raise AssertionError("kap.opacity_full_raw scalars do not match")
    if not np.allclose(kap_raw_fracs, kap_full_fracs, rtol=1.0e-12, atol=0.0):
        raise AssertionError("kap.opacity_full_raw kap_fracs do not match")
    if not np.allclose(kap_raw_dxa, kap_full_dxa, rtol=1.0e-12, atol=0.0):
        raise AssertionError("kap.opacity_full_raw dlnkap_dxa does not match")

    print("MESA eos/kap arbitrary-composition example")
    print(f"composition mass fractions = {mass_fractions}")
    print(f"eos input: T = {eos_T:.6e} K, rho = {eos_rho:.6e} g/cm^3")
    print(f"kap input: T = {kap_T:.6e} K, rho = {kap_rho:.6e} g/cm^3")
    print(f"eos output = {eos_result}")
    print(f"eos full result names = {list(eos_full_result['results'])}")
    print(f"eos d_dxa output = {eos_full_result['d_dxa']}")
    print(f"eos solve_rho output rho = {eos_rho_solve['Rho']:.6e} g/cm^3")
    print(f"eos solve_t output T = {eos_T_solve['T']:.6e} K")
    print(f"kap output = {kap_result}")
    print(f"kap opacity fractions = {kap_full_result['kap_fracs']}")
    print(f"kap dlnkap_dxa output = {kap_full_result['dlnkap_dxa']}")
    print(f"kap Type2-controlled opacity fractions = {kap_type2_result['kap_fracs']}")
    print("raw scalar parity checks = ok")


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
