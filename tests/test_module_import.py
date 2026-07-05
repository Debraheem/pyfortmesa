from pyfortmesa import (
    big_sum_fortran,
    big_sum_python,
    small_calc,
    small_calc_fortran,
)

assert small_calc(4.0) == 50.0
assert small_calc_fortran(4.0) == 50.0
assert big_sum_python(1000) == 250250.0
assert big_sum_fortran(1000) == 250250.0

print("passed test")
