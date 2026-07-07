from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from pyfortmesa import mesa


EXPECTED_PUBLIC_API = (
    "Chem",
    "Composition",
    "EOS_DXA_RESULT_NAMES",
    "EOS_RESULT_INDEX",
    "EOS_RESULT_NAMES",
    "Eos",
    "KAP_CONTROL_UNSET",
    "KAP_FRAC_NAMES",
    "Kap",
    "MESA_CONSTANT_NAMES",
    "SAMPLE_ISOTOPES",
    "composition",
    "composition_info",
    "constants",
    "disable_timing",
    "enable_timing",
    "eos_dt",
    "eos_dt_full",
    "eos_dt_profile",
    "eos_kap_profile_from_logs",
    "eos_kap_profile",
    "eos_dt_profile_from_logs",
    "eos_solve_T",
    "eos_solve_T_profile",
    "eos_solve_rho",
    "eos_solve_rho_profile",
    "eos_solve_t",
    "eos_solve_t_profile",
    "format_timing_summary",
    "iso_id",
    "iso_ids",
    "isotope_index",
    "kap_opacity",
    "kap_opacity_full",
    "kap_opacity_profile",
    "kap_opacity_profile_from_logs",
    "format_output_schema",
    "output_columns",
    "output_schema",
    "output_schema_names",
    "print_output_schema",
    "print_timing_summary",
    "reset_timing",
    "sample_composition",
    "set_cache_root",
    "set_inlist",
    "shutdown",
    "timing",
    "timing_enabled",
    "timing_summary",
)


DOC_REQUIREMENTS = {
    "docs/modules/const.md": (
        "mesa.constants()",
        "standard_cgrav",
        "crad",
        "Prad =",
        "## Not included",
    ),
    "docs/modules/chem.md": (
        "mesa.composition(",
        "mesa.composition_info(",
        "mesa.iso_id(",
        "mesa.iso_ids(",
        "mesa.isotope_index(",
        "mesa.sample_composition(",
        "mesa.Chem()",
        "## Not included",
    ),
    "docs/modules/eos.md": (
        "mesa.eos_dt(",
        "mesa.eos_dt_full(",
        "mesa.eos_dt_profile(",
        "mesa.eos_dt_profile_from_logs(",
        "mesa.eos_solve_rho(",
        "mesa.eos_solve_rho_profile(",
        "mesa.eos_solve_t(",
        "mesa.eos_solve_t_profile(",
        "mesa.eos_solve_T(",
        "mesa.eos_solve_T_profile(",
        "mesa.Eos()",
        "input_mode",
        "Pgas",
        "Prad",
        "## Not included",
    ),
    "docs/modules/kap.md": (
        "mesa.kap_opacity(",
        "mesa.kap_opacity_full(",
        "mesa.kap_opacity_profile(",
        "mesa.kap_opacity_profile_from_logs(",
        "mesa.eos_kap_profile(",
        "mesa.eos_kap_profile_from_logs(",
        "mesa.Kap",
        "input_mode",
        "logR =",
        "## Not included",
    ),
    "docs/modules/api_helpers.md": (
        "mesa.set_cache_root(",
        "mesa.set_inlist(",
        "mesa.shutdown(",
        "mesa.output_schema(",
        "mesa.output_columns(",
        "mesa.format_output_schema(",
        "mesa.print_output_schema(",
        "mesa.output_schema_names(",
        "mesa.timing(",
        "mesa.enable_timing(",
        "mesa.disable_timing(",
        "mesa.reset_timing(",
        "mesa.timing_summary(",
        "mesa.format_timing_summary(",
        "mesa.print_timing_summary(",
    ),
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_expected_public_api_is_exported() -> None:
    public = tuple(mesa.__all__)
    require(public == EXPECTED_PUBLIC_API, "mesa.__all__ does not match audit list")

    for name in EXPECTED_PUBLIC_API:
        require(hasattr(mesa, name), f"missing public mesa API: {name}")


def test_public_api_docs_cover_selected_surface() -> None:
    for relative_path, required_strings in DOC_REQUIREMENTS.items():
        path = REPO_ROOT / relative_path
        text = path.read_text(encoding="utf-8")

        for required in required_strings:
            require(required in text, f"{relative_path} missing {required!r}")


if __name__ == "__main__":
    test_expected_public_api_is_exported()
    test_public_api_docs_cover_selected_surface()
    print("public_api_docs: ok")
