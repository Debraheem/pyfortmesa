from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from pyfortmesa import mesa


def expect_value_error(label: str, call) -> bool:
    try:
        call()
    except ValueError as exc:
        print(f"{label}: {exc}")
        return True
    print(f"{label}: expected ValueError")
    return False


def main() -> int:
    chem_id = (1, 2)
    xa = np.asfortranarray(
        [
            [0.70, 0.69, 0.68],
            [0.30, 0.31, 0.32],
        ],
        dtype=np.float64,
    )
    eos = mesa.Eos()
    kap = mesa.Kap()

    checks = [
        expect_value_error(
            "nonpositive T",
            lambda: eos.dt_profile([1.0e6, 0.0, 2.0e6], [1.0, 1.0, 1.0], chem_id, xa),
        ),
        expect_value_error(
            "nonpositive Rho",
            lambda: kap.opacity_profile(
                [1.0e6, 2.0e6, 3.0e6],
                [1.0, -1.0, 1.0],
                chem_id,
                xa,
            ),
        ),
        expect_value_error(
            "shape mismatch",
            lambda: kap.eos_kap_profile([1.0e6, 2.0e6], [1.0], chem_id, xa),
        ),
        expect_value_error(
            "raw shape mismatch",
            lambda: eos.dt_raw(1.0e6, 1.0, chem_id, [0.70]),
        ),
        expect_value_error(
            "raw validation",
            lambda: kap.opacity_raw(1.0e6, 1.0, chem_id, [-0.10, 1.10], validate=True),
        ),
        expect_value_error(
            "combined raw validation",
            lambda: kap.eos_kap_raw(1.0e6, 1.0, chem_id, [-0.10, 1.10], validate=True),
        ),
    ]
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
