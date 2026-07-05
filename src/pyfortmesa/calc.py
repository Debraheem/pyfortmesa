def small_calc(x, a=3.0, b=2.0):
    """Return a*x*x + b."""
    return a*x*x + b


def big_sum_python(n):
    """Return sum(0.5*i for i in 1..n) using a pure Python loop."""
    total = 0.0
    for i in range(1, int(n) + 1):
        total += 0.5*i
    return total
