from .calc import small_calc
from .fortran_calc import small_calc_fortran


def main():
    y = small_calc(4.0)
    print(f"Python saw y = {y}")
    y_fortran = small_calc_fortran(4.0)
    print(f"Fortran saw y = {y_fortran}")


if __name__ == "__main__":
    main()
