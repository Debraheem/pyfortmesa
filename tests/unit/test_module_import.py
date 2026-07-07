from __future__ import annotations

from pyfortmesa import mesa


REQUIRED_MESA_API = (
    "Chem",
    "Eos",
    "Kap",
    "composition",
    "composition_info_full",
    "constants",
    "iso_id",
    "iso_ids",
    "isotope_index",
    "format_output_schema",
    "output_columns",
    "output_schema",
    "output_schema_names",
    "print_output_schema",
    "sample_composition",
    "set_cache_root",
    "set_inlist",
    "shutdown",
)


def main() -> int:
    missing = [name for name in REQUIRED_MESA_API if not hasattr(mesa, name)]
    for name in REQUIRED_MESA_API:
        print(f"mesa_api: {name}, ok={name not in missing}")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
