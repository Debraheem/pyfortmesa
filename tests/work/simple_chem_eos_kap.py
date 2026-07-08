"""Small MESA chem/eos/kap work example.

Run this after installing pyfortmesa with `./mk mesa`. It is intentionally
shorter than the timing tests; use it as a starting point for real Python code.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np

from pyfortmesa import mesa


def main() -> int:
    if os.environ.get("PYFORTMESA_WITH_MESA") != "1":
        print("skipped: set PYFORTMESA_WITH_MESA=1 after installing ./mk mesa")
        return 0

    repo_root = Path(__file__).resolve().parents[2]
    mesa.set_cache_root(".")
    mesa.set_inlist(repo_root / "inlist_eos_and_kap")

    mass_fractions = {"h1": 0.70, "he4": 0.28, "c12": 0.02}
    mix = mesa.composition(mass_fractions)

    eos = mesa.Eos()
    kap = mesa.Kap()

    try:
        # One scalar chem, eos, and kap call.
        chem_info = mesa.Chem().composition_info(mix)
        eos_out = eos.dt_full(T=1.0e7, Rho=1.0e2, comp=mix)
        kap_out = kap.opacity_full(T=1.0e6, Rho=1.0e-7, comp=mix)

        print("composition:", mass_fractions)
        print("chem abar:", chem_info["abar"])
        print("eos lnPgas:", eos_out["results"]["lnPgas"])
        print("kap kappa:", kap_out["kappa"])

        isotope_names = ("h1", "he4", "c12")
        chem_id = mesa.iso_ids(isotope_names)
        T_profile = np.array([1.0e6, 2.0e6, 5.0e6, 1.0e7], dtype=np.float64)
        rho_profile = np.array([1.0e-7, 1.0e-6, 1.0e-3, 1.0e2], dtype=np.float64)
        xa_by_zone = np.array(
            [
                [0.70, 0.28, 0.02],
                [0.70, 0.28, 0.02],
                [0.69, 0.29, 0.02],
                [0.68, 0.30, 0.02],
            ],
            dtype=np.float64,
        )
        xa_profile = np.asfortranarray(xa_by_zone.T)

        # One profile call. Fortran loops over zones.
        out = kap.eos_kap_profile(T_profile, rho_profile, chem_id, xa_profile)
        i_gamma1 = mesa.EOS_RESULT_NAMES.index("gamma1")
        print("profile gamma1:", out["results"][i_gamma1, :])
        print("profile kappa:", out["kappa"])
    finally:
        mesa.shutdown()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
