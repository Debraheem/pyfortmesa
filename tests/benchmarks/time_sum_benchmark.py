#!/usr/bin/env python
import argparse
from time import perf_counter

from pyfortmesa import big_sum_fortran, big_sum_python


def time_call(label, func, n):
    start = perf_counter()
    value = func(n)
    elapsed = perf_counter() - start
    print(f"{label} big sum = {value:.1f} ({elapsed:.6f} s)")
    return value, elapsed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "n",
        nargs="?",
        type=int,
        default=5_000_000,
        help="number of loop iterations",
    )
    args = parser.parse_args()

    # Warm up imports and extension loading before timing the loops.
    big_sum_python(10)
    big_sum_fortran(10)

    print(f"Timing sum(0.5*i) for i = 1..{args.n}")
    python_value, python_time = time_call("Python", big_sum_python, args.n)
    fortran_value, fortran_time = time_call("Fortran", big_sum_fortran, args.n)

    if python_value != fortran_value:
        raise RuntimeError("Python and Fortran benchmark results differ")

    if fortran_time > 0.0:
        print(f"Fortran speedup = {python_time/fortran_time:.1f}x")


if __name__ == "__main__":
    main()
