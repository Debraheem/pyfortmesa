from __future__ import annotations

import math

from pyfortmesa import (
    big_sum_fortran,
    big_sum_python,
    small_calc,
    small_calc_fortran,
)


def show_result(
    label: str,
    input_value: float | int,
    output: float,
    expected: float,
) -> bool:
    ok = math.isclose(output, expected, rel_tol=0.0, abs_tol=1.0e-12)
    print(
        f"{label}: input={input_value}, output={output:.6e}, "
        f"expected={expected:.6e}, ok={ok}"
    )
    return ok


def main() -> int:
    checks = [
        show_result("small_calc", 4.0, small_calc(4.0), 50.0),
        show_result("small_calc_fortran", 4.0, small_calc_fortran(4.0), 50.0),
        show_result("big_sum_python", 1000, big_sum_python(1000), 250250.0),
        show_result("big_sum_fortran", 1000, big_sum_fortran(1000), 250250.0),
    ]
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
