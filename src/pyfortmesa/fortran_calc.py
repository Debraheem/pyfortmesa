def small_calc_fortran(x):
    """Return 3*x*x + 2 using the compiled Fortran extension."""
    from ._fortran_calc import small_calc_f

    return float(small_calc_f(float(x)))


def big_sum_fortran(n):
    """Return sum(0.5*i for i in 1..n) using the compiled Fortran extension."""
    from ._fortran_calc import big_sum_f

    return float(big_sum_f(int(n)))
