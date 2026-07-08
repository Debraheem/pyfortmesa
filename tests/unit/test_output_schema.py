from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from pyfortmesa import mesa


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_eos_kap_profile_schema() -> None:
    rows = mesa.output_schema("eos_kap_profile")
    columns = mesa.output_columns("eos_kap_profile")

    require("eos_kap_profile" in mesa.output_schema_names(), "missing schema name")
    require(rows[0]["column"] == "T", "first eos-kap profile column should be T")
    require(rows[0]["units"] == "K", "T units should be K")
    require("results.lnPgas" in columns, "missing eos lnPgas profile column")
    require("kappa" in columns, "missing kap kappa profile column")
    require(rows[0]["shape"] == "(nzones,)", "profile output should be zone-shaped")


def test_output_schema_names_include_aliases() -> None:
    canonical = mesa.output_schema_names()
    names = mesa.output_schema_names(include_aliases=True)

    require("eos_dt_full" in canonical, "missing canonical eos schema name")
    require("eos_solve_t" in canonical, "missing canonical temperature solver schema")
    require("eos_solve_t_profile" in canonical, "missing temperature profile solver schema")
    require("eos" in names, "missing eos schema alias")
    require("kap" in names, "missing kap schema alias")


def test_full_scalar_schema_expands_species() -> None:
    columns = mesa.output_columns("kap_opacity_full", species=("h1", "he4"))
    single_species_columns = mesa.output_columns("kap_opacity_full", species="h1")

    require("kap_fracs.Type2" in columns, "missing Type2 fraction")
    require("dlnkap_dxa.h1" in columns, "missing h1 opacity composition derivative")
    require("dlnkap_dxa.he4" in columns, "missing he4 opacity composition derivative")
    require("dlnkap_dxa.h1" in single_species_columns, "single string means one isotope")
    require("dlnkap_dxa.h" not in single_species_columns, "single species string was split")


def test_format_output_schema() -> None:
    text = mesa.format_output_schema("eos_dt_full", species=("h1",))

    require("results.lnPgas" in text, "formatted schema should include lnPgas")
    require("units=ln(dyn/cm^2)" in text, "formatted schema should include units")
    require("d_dxa.lnPgas.h1" in text, "formatted schema should include species")


def test_unknown_schema_name() -> None:
    try:
        mesa.output_schema("not_a_schema")
    except ValueError as exc:
        require("unknown output schema" in str(exc), "wrong error for bad schema")
    else:
        raise AssertionError("unknown schema should raise ValueError")


if __name__ == "__main__":
    test_eos_kap_profile_schema()
    test_output_schema_names_include_aliases()
    test_full_scalar_schema_expands_species()
    test_format_output_schema()
    test_unknown_schema_name()
    print("output_schema: ok")
