"""Small command-line smoke check for the installed package."""

from . import mesa


def main() -> None:
    print("pyfortmesa: MESA wrapper package")
    print(f"public module: {mesa.__name__}")


if __name__ == "__main__":
    main()
