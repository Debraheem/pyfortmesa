"""Public Python API for optional MESA module wrappers.

Thermodynamic inputs use cgs units unless stated otherwise:
temperature `T` is in K, density `Rho` is in g/cm^3, and MESA logarithmic
outputs such as `lnPgas` are natural logs.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

import numpy as np

from .mesa_support import (
    Composition,
    EOS_DXA_RESULT_NAMES,
    EOS_RESULT_INDEX,
    EOS_RESULT_NAMES,
    KAP_CONTROL_UNSET,
    KAP_FRAC_NAMES,
    MESA_CONSTANT_NAMES,
    SAMPLE_ISOTOPES,
    _check_ierr,
    _eos_result_index,
    _inlist_is_set,
    _load_mesa_extension,
    _named_matrix_by_rows,
    _named_species_vector,
    _named_vector,
    _optional_control_value,
    _prepare_composition,
    _prepare_mesa_cache_env,
    _timed_api,
    composition,
    disable_timing,
    enable_timing,
    format_output_schema,
    format_timing_summary,
    iso_id,
    iso_ids,
    isotope_index,
    output_columns,
    output_schema,
    output_schema_names,
    print_output_schema,
    print_timing_summary,
    reset_timing,
    sample_composition,
    set_cache_root,
    set_inlist,
    timing,
    timing_enabled,
    timing_summary,
)


@_timed_api("constants")
def constants() -> dict[str, float]:
    """Return selected MESA `const_def` values in cgs units.

    Output keys are `standard_cgrav`, `crad`, `clight`, `Lsun`, `Rsun`, and
    `Msun`.
    """
    mesa_const = _load_mesa_extension("_mesa_const")
    values = mesa_const.mesa_const_values()
    *constant_values, ierr = values
    _check_ierr("MESA CONST", ierr)
    return _named_vector(MESA_CONSTANT_NAMES, constant_values)


@_timed_api("shutdown")
def shutdown(*, release_tables: bool = False) -> None:
    """Release persistent MESA state held by pyfortmesa wrappers.

    By default this frees the EOS/KAP handles owned by pyfortmesa and leaves
    MESA's loaded tables available for reuse in the same Python process. Pass
    `release_tables=True` only when no other code in the process is using MESA.
    """
    for label, module_name, function_name in (
        ("MESA KAP shutdown", "_mesa_kap", "mesa_kap_shutdown"),
        ("MESA EOS shutdown", "_mesa_eos", "mesa_eos_shutdown"),
    ):
        try:
            module = _load_mesa_extension(module_name)
        except RuntimeError:
            continue

        try:
            shutdown_function = getattr(module, function_name)
        except AttributeError as exc:
            raise RuntimeError(
                f"{module_name} is missing {function_name}; rebuild pyfortmesa."
            ) from exc

        ierr = shutdown_function(bool(release_tables))
        _check_ierr(label, ierr)

    if release_tables:
        try:
            module = _load_mesa_extension("_mesa_chem")
        except RuntimeError:
            return

        try:
            shutdown_function = getattr(module, "mesa_chem_shutdown")
        except AttributeError as exc:
            raise RuntimeError(
                "_mesa_chem is missing mesa_chem_shutdown; rebuild pyfortmesa."
            ) from exc

        ierr = shutdown_function()
        _check_ierr("MESA CHEM shutdown", ierr)


@_timed_api("composition_info")
def composition_info(
    comp: Composition | Mapping[str, float] | Iterable[float] | None,
) -> dict[str, float]:
    """Return MESA CHEM moments for a mass-fraction composition.

    Input `comp` may be a `Composition`, isotope-name mass-fraction mapping, or
    the legacy sample-composition vector. Outputs include H/He/Z mass
    fractions, mean atomic weights, electron fraction, mass correction, and
    `sumx`.
    """
    composition_data = _prepare_composition(comp)
    mesa_chem = _load_mesa_extension("_mesa_chem")
    values = mesa_chem.mesa_chem_composition_info(
        composition_data.chem_id,
        composition_data.xa,
    )
    (
        xh,
        xhe,
        xz,
        abar,
        zbar,
        z2bar,
        z53bar,
        ye,
        mass_correction,
        sumx,
        ierr,
    ) = values
    _check_ierr("MESA CHEM", ierr)
    return {
        "xh": float(xh),
        "xhe": float(xhe),
        "xz": float(xz),
        "abar": float(abar),
        "zbar": float(zbar),
        "z2bar": float(z2bar),
        "z53bar": float(z53bar),
        "ye": float(ye),
        "mass_correction": float(mass_correction),
        "sumx": float(sumx),
    }


def _eos_full_output_dict(
    composition_data: Composition,
    res: object,
    d_dlnRho: object,
    d_dlnT: object,
    d_dxa: object,
) -> dict[str, dict[str, float] | dict[str, dict[str, float]]]:
    return {
        "results": _named_vector(EOS_RESULT_NAMES, res),
        "d_dlnRho": _named_vector(EOS_RESULT_NAMES, d_dlnRho),
        "d_dlnT": _named_vector(EOS_RESULT_NAMES, d_dlnT),
        "d_dxa": _named_matrix_by_rows(EOS_DXA_RESULT_NAMES, composition_data.names, d_dxa),
    }


def _as_fortran_vector(values: Iterable[float] | Iterable[int], dtype: object) -> np.ndarray:
    if isinstance(values, np.ndarray):
        array = np.asarray(values, dtype=dtype)
    else:
        array = np.fromiter(values, dtype=dtype)
    return np.asfortranarray(array)


_PROFILE_INPUT_MODES = {
    "value": 0,
    "values": 0,
    "physical": 0,
    "linear": 0,
    "log": 1,
    "logs": 1,
    "ln": 1,
    "natural_log": 1,
    "natural_logs": 1,
    "log10": 2,
    "log_10": 2,
    "base10": 2,
    "base_10": 2,
}


def _profile_input_mode(input_mode: str | int) -> int:
    if isinstance(input_mode, bool):
        raise ValueError("input_mode must be 'value', 'log', or 'log10'")
    if isinstance(input_mode, int):
        if input_mode in {0, 1, 2}:
            return input_mode
        raise ValueError("input_mode integer must be 0, 1, or 2")

    key = str(input_mode).strip().lower().replace("-", "_").replace(" ", "_")
    try:
        return _PROFILE_INPUT_MODES[key]
    except KeyError as exc:
        raise ValueError("input_mode must be 'value', 'log', or 'log10'") from exc


def _profile_output_mode(output: str) -> str:
    key = str(output).strip().lower().replace("-", "_")
    if key in {"raw", "array", "arrays"}:
        return "raw"
    if key in {"dict", "dictionary", "named"}:
        return "dict"
    raise ValueError("output must be 'raw' or 'dict'")


def _prepare_profile_xa(chem_id_array: np.ndarray, xa: object, nzones: int) -> np.ndarray:
    xa_input = np.asarray(xa, dtype=np.float64)
    if xa_input.ndim == 1:
        if xa_input.shape != (chem_id_array.size,):
            raise ValueError("1D xa must have shape (species,)")
        xa_array = np.asfortranarray(
            np.broadcast_to(xa_input[:, np.newaxis], (chem_id_array.size, nzones))
        )
    else:
        xa_array = np.asfortranarray(xa_input)
        if xa_array.shape != (chem_id_array.size, nzones):
            raise ValueError("xa must have shape (species,) or (species, nzones)")

    if not np.all(np.isfinite(xa_array)):
        raise ValueError("xa values must be finite")
    if np.any(xa_array < 0.0):
        raise ValueError("xa values must be non-negative")
    return xa_array


def _prepare_profile_arrays(
    first_values: Iterable[float],
    second_values: Iterable[float],
    chem_id_values: Iterable[int],
    xa: object,
    *,
    input_mode: str | int,
    first_name: str,
    second_name: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    mode_value = _profile_input_mode(input_mode)
    first_array = _as_fortran_vector(first_values, np.float64)
    second_array = _as_fortran_vector(second_values, np.float64)
    chem_id_array = _as_fortran_vector(chem_id_values, np.int32)

    if first_array.ndim != 1 or second_array.ndim != 1:
        raise ValueError(f"{first_name} and {second_name} must be one-dimensional")
    if first_array.shape != second_array.shape:
        raise ValueError(f"{first_name} and {second_name} must have the same length")
    if chem_id_array.ndim != 1:
        raise ValueError("chem_id_values must be one-dimensional")
    if first_array.size <= 0:
        raise ValueError("profile must contain at least one zone")
    if not np.all(np.isfinite(first_array)):
        raise ValueError(f"{first_name} values must be finite")
    if not np.all(np.isfinite(second_array)):
        raise ValueError(f"{second_name} values must be finite")

    if mode_value == 0:
        if np.any(first_array <= 0.0):
            raise ValueError(f"{first_name} values must be positive")
        if np.any(second_array <= 0.0):
            raise ValueError(f"{second_name} values must be positive")

    xa_array = _prepare_profile_xa(chem_id_array, xa, first_array.size)

    return first_array, second_array, chem_id_array, xa_array


def _prepare_profile_coordinate(
    values: Iterable[float], chem_id_values: Iterable[int], xa: object,
    *, input_mode: str | int, name: str
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mode_value = _profile_input_mode(input_mode)
    value_array = _as_fortran_vector(values, np.float64)
    chem_id_array = _as_fortran_vector(chem_id_values, np.int32)

    if value_array.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional")
    if chem_id_array.ndim != 1:
        raise ValueError("chem_id_values must be one-dimensional")
    if value_array.size <= 0:
        raise ValueError("profile must contain at least one zone")
    if not np.all(np.isfinite(value_array)):
        raise ValueError(f"{name} values must be finite")
    if mode_value == 0 and np.any(value_array <= 0.0):
        raise ValueError(f"{name} values must be positive")

    xa_array = _prepare_profile_xa(chem_id_array, xa, value_array.size)
    return value_array, chem_id_array, xa_array


def _profile_value_array(
    values: Iterable[float] | float, nzones: int, name: str, *, positive: bool = False
) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    if array.ndim == 0:
        array = np.full(nzones, float(array), dtype=np.float64)
    elif array.ndim != 1:
        raise ValueError(f"{name} must be scalar or one-dimensional")
    elif array.size != nzones:
        raise ValueError(f"{name} must be scalar or have length nzones")

    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} values must be finite")
    if positive and np.any(array <= 0.0):
        raise ValueError(f"{name} values must be positive")
    return np.asfortranarray(array)


def _eos_profile_output(
    T: object, Rho: object, res: object, nzones: int, output: str
) -> dict[str, object]:
    result_array = np.asarray(res, dtype=np.float64)
    if result_array.shape != (len(EOS_RESULT_NAMES), nzones):
        raise RuntimeError(
            "MESA EOS profile wrapper returned result shape "
            f"{result_array.shape}; expected ({len(EOS_RESULT_NAMES)}, {nzones})"
        )

    if _profile_output_mode(output) == "raw":
        return {
            "T": np.asarray(T, dtype=np.float64),
            "Rho": np.asarray(Rho, dtype=np.float64),
            "results": result_array,
            "result_names": EOS_RESULT_NAMES,
        }

    return {
        "T": np.asarray(T, dtype=np.float64),
        "Rho": np.asarray(Rho, dtype=np.float64),
        "results": {
            name: result_array[index, :].copy()
            for index, name in enumerate(EOS_RESULT_NAMES)
        },
    }


def _eos_kap_profile_output(
    T: object, Rho: object, res: object, kappa: object, dlnkap_dlnRho: object,
    dlnkap_dlnT: object, nzones: int, output: str
) -> dict[str, object]:
    result_array = np.asarray(res, dtype=np.float64)
    if result_array.shape != (len(EOS_RESULT_NAMES), nzones):
        raise RuntimeError(
            "MESA EOS/KAP profile wrapper returned EOS result shape "
            f"{result_array.shape}; expected ({len(EOS_RESULT_NAMES)}, {nzones})"
        )

    profile = {
        "T": np.asarray(T, dtype=np.float64),
        "Rho": np.asarray(Rho, dtype=np.float64),
        "kappa": np.asarray(kappa, dtype=np.float64),
        "dlnkap_dlnRho": np.asarray(dlnkap_dlnRho, dtype=np.float64),
        "dlnkap_dlnT": np.asarray(dlnkap_dlnT, dtype=np.float64),
    }

    if _profile_output_mode(output) == "raw":
        return {
            **profile,
            "results": result_array,
            "result_names": EOS_RESULT_NAMES,
        }

    return {
        **profile,
        "results": {
            name: result_array[index, :].copy()
            for index, name in enumerate(EOS_RESULT_NAMES)
        },
    }


def _eos_solve_profile_output(
    value_name: str, log_name: str, value: object, log_value: object,
    res: object, d_dlnRho: object, d_dlnT: object, d_dxa: object,
    eos_calls: object, nzones: int, species: int
) -> dict[str, object]:
    result_array = np.asarray(res, dtype=np.float64)
    d_dlnRho_array = np.asarray(d_dlnRho, dtype=np.float64)
    d_dlnT_array = np.asarray(d_dlnT, dtype=np.float64)
    d_dxa_array = np.asarray(d_dxa, dtype=np.float64)
    if result_array.shape != (len(EOS_RESULT_NAMES), nzones):
        raise RuntimeError(
            "MESA EOS solve profile wrapper returned result shape "
            f"{result_array.shape}; expected ({len(EOS_RESULT_NAMES)}, {nzones})"
        )
    if d_dxa_array.shape != (len(EOS_DXA_RESULT_NAMES), species, nzones):
        raise RuntimeError(
            "MESA EOS solve profile wrapper returned d_dxa shape "
            f"{d_dxa_array.shape}; expected "
            f"({len(EOS_DXA_RESULT_NAMES)}, {species}, {nzones})"
        )

    return {
        value_name: np.asarray(value, dtype=np.float64),
        log_name: np.asarray(log_value, dtype=np.float64),
        "results": result_array,
        "d_dlnRho": d_dlnRho_array,
        "d_dlnT": d_dlnT_array,
        "d_dxa": d_dxa_array,
        "eos_calls": np.asarray(eos_calls, dtype=np.int32),
        "result_names": EOS_RESULT_NAMES,
        "d_dxa_result_names": EOS_DXA_RESULT_NAMES,
    }


@_timed_api("eos.dt")
def eos_dt(
    T: float,
    Rho: float,
    comp: Composition | Mapping[str, float] | Iterable[float] | None = None,
) -> dict[str, float]:
    """Evaluate MESA EOS at known `T`, `Rho`, and composition.

    Inputs are temperature in K, density in g/cm^3, and mass fractions. Outputs
    are `lnPgas`, `lnE`, `lnS`, `grad_ad`, and `gamma1`; logarithmic quantities
    are natural logs of MESA's cgs EOS quantities.
    """
    _prepare_mesa_cache_env()
    composition_data = _prepare_composition(comp)
    mesa_eos = _load_mesa_extension("_mesa_eos")
    values = mesa_eos.mesa_eos_composition(
        float(T),
        float(Rho),
        composition_data.chem_id,
        composition_data.xa,
    )
    lnPgas, lnE, lnS, grad_ad, gamma1, ierr = values
    _check_ierr("MESA EOS", ierr)
    return {
        "lnPgas": float(lnPgas),
        "lnE": float(lnE),
        "lnS": float(lnS),
        "grad_ad": float(grad_ad),
        "gamma1": float(gamma1),
    }


@_timed_api("eos.dt_full")
def eos_dt_full(
    T: float,
    Rho: float,
    comp: Composition | Mapping[str, float] | Iterable[float] | None = None,
) -> dict[str, dict[str, float] | dict[str, dict[str, float]]]:
    """Evaluate MESA EOS and return the full `eosDT_get` result vectors.

    Inputs are temperature in K, density in g/cm^3, and mass fractions. Output
    dictionaries are keyed by MESA EOS result names for `results`, `d_dlnRho`,
    `d_dlnT`, and composition derivatives `d_dxa`.
    """
    _prepare_mesa_cache_env()
    composition_data = _prepare_composition(comp)
    mesa_eos = _load_mesa_extension("_mesa_eos")
    values = mesa_eos.mesa_eos_composition_full(
        float(T),
        float(Rho),
        composition_data.chem_id,
        composition_data.xa,
    )
    res, d_dlnRho, d_dlnT, d_dxa, ierr = values
    _check_ierr("MESA EOS", ierr)
    return _eos_full_output_dict(composition_data, res, d_dlnRho, d_dlnT, d_dxa)


@_timed_api("eos.dt_profile")
def eos_dt_profile(
    T: Iterable[float],
    Rho: Iterable[float],
    chem_id_values: Iterable[int],
    xa: object,
    *,
    input_mode: str | int = "value",
    output: str = "raw",
) -> dict[str, object]:
    """Evaluate EOS across a profile.

    `input_mode` selects how `T` and `Rho` are interpreted: `"value"` for
    physical cgs values, `"log"` for natural logs, and `"log10"` for base-10
    logs. With `output="raw"`, `results` is a `(nresults, nzones)` array whose
    row order is `EOS_RESULT_NAMES`.
    """
    _prepare_mesa_cache_env()
    mode_value = _profile_input_mode(input_mode)
    T_array, Rho_array, chem_id_array, xa_array = _prepare_profile_arrays(
        T, Rho, chem_id_values, xa,
        input_mode=mode_value, first_name="T", second_name="Rho",
    )

    mesa_eos = _load_mesa_extension("_mesa_eos")
    values = mesa_eos.mesa_eos_profile(
        chem_id_array, mode_value, T_array, Rho_array, xa_array
    )
    out_T, out_Rho, res, ierr, failed_zone = values
    if int(ierr) != 0:
        raise RuntimeError(
            "MESA EOS profile call failed with "
            f"ierr={int(ierr)} at zone={int(failed_zone)}"
        )

    return _eos_profile_output(out_T, out_Rho, res, T_array.size, output)


def eos_dt_profile_from_logs(
    lnT: Iterable[float],
    lnd: Iterable[float],
    chem_id_values: Iterable[int],
    xa: object,
    *,
    output: str = "dict",
) -> dict[str, object]:
    """Compatibility alias for `eos_dt_profile(..., input_mode="log")`."""
    return eos_dt_profile(lnT, lnd, chem_id_values, xa, input_mode="log", output=output)


@_timed_api("kap.opacity_profile")
def kap_opacity_profile(
    T: Iterable[float],
    Rho: Iterable[float],
    chem_id_values: Iterable[int],
    xa: object,
    *,
    input_mode: str | int = "value",
    use_type2: bool | None = None,
    zbase: float | None = None,
    use_zbase_for_type1: bool | None = None,
    type2_full_off_X: float | None = None,
    type2_full_on_X: float | None = None,
    type2_full_off_dZ: float | None = None,
    type2_full_on_dZ: float | None = None,
) -> dict[str, object]:
    """Evaluate KAP across a profile.

    `input_mode` selects physical values (`"value"`), natural logs (`"log"`),
    or base-10 logs (`"log10"`) for `T` and `Rho`.
    """
    _prepare_mesa_cache_env()
    mode_value = _profile_input_mode(input_mode)
    T_array, Rho_array, chem_id_array, xa_array = _prepare_profile_arrays(
        T, Rho, chem_id_values, xa,
        input_mode=mode_value, first_name="T", second_name="Rho",
    )
    controls = _kap_control_args(
        use_type2=use_type2,
        zbase=zbase,
        use_zbase_for_type1=use_zbase_for_type1,
        type2_full_off_X=type2_full_off_X,
        type2_full_on_X=type2_full_on_X,
        type2_full_off_dZ=type2_full_off_dZ,
        type2_full_on_dZ=type2_full_on_dZ,
    )

    mesa_kap = _load_mesa_extension("_mesa_kap")
    values = mesa_kap.mesa_kap_profile(
        chem_id_array, mode_value, T_array, Rho_array, xa_array, *controls
    )
    T, Rho, kappa, dlnkap_dlnRho, dlnkap_dlnT, ierr, failed_zone = values
    if int(ierr) != 0:
        raise RuntimeError(
            "MESA KAP profile call failed with "
            f"ierr={int(ierr)} at zone={int(failed_zone)}"
        )

    return {
        "T": np.asarray(T, dtype=np.float64),
        "Rho": np.asarray(Rho, dtype=np.float64),
        "kappa": np.asarray(kappa, dtype=np.float64),
        "dlnkap_dlnRho": np.asarray(dlnkap_dlnRho, dtype=np.float64),
        "dlnkap_dlnT": np.asarray(dlnkap_dlnT, dtype=np.float64),
    }


def kap_opacity_profile_from_logs(
    lnT: Iterable[float],
    lnd: Iterable[float],
    chem_id_values: Iterable[int],
    xa: object,
    *,
    use_type2: bool | None = None,
    zbase: float | None = None,
    use_zbase_for_type1: bool | None = None,
    type2_full_off_X: float | None = None,
    type2_full_on_X: float | None = None,
    type2_full_off_dZ: float | None = None,
    type2_full_on_dZ: float | None = None,
) -> dict[str, object]:
    """Compatibility alias for `kap_opacity_profile(..., input_mode="log")`."""
    return kap_opacity_profile(
        lnT,
        lnd,
        chem_id_values,
        xa,
        input_mode="log",
        use_type2=use_type2,
        zbase=zbase,
        use_zbase_for_type1=use_zbase_for_type1,
        type2_full_off_X=type2_full_off_X,
        type2_full_on_X=type2_full_on_X,
        type2_full_off_dZ=type2_full_off_dZ,
        type2_full_on_dZ=type2_full_on_dZ,
    )


@_timed_api("kap.eos_kap_profile")
def eos_kap_profile(
    T: Iterable[float],
    Rho: Iterable[float],
    chem_id_values: Iterable[int],
    xa: object,
    *,
    input_mode: str | int = "value",
    output: str = "raw",
    use_type2: bool | None = None,
    zbase: float | None = None,
    use_zbase_for_type1: bool | None = None,
    type2_full_off_X: float | None = None,
    type2_full_on_X: float | None = None,
    type2_full_off_dZ: float | None = None,
    type2_full_on_dZ: float | None = None,
) -> dict[str, object]:
    """Evaluate EOS and KAP across a profile with one EOS call per zone."""
    _prepare_mesa_cache_env()
    mode_value = _profile_input_mode(input_mode)
    T_array, Rho_array, chem_id_array, xa_array = _prepare_profile_arrays(
        T, Rho, chem_id_values, xa,
        input_mode=mode_value, first_name="T", second_name="Rho",
    )
    controls = _kap_control_args(
        use_type2=use_type2,
        zbase=zbase,
        use_zbase_for_type1=use_zbase_for_type1,
        type2_full_off_X=type2_full_off_X,
        type2_full_on_X=type2_full_on_X,
        type2_full_off_dZ=type2_full_off_dZ,
        type2_full_on_dZ=type2_full_on_dZ,
    )

    mesa_kap = _load_mesa_extension("_mesa_kap")
    values = mesa_kap.mesa_eos_kap_profile(
        chem_id_array, mode_value, T_array, Rho_array, xa_array, *controls
    )
    (
        T,
        Rho,
        res,
        kappa,
        dlnkap_dlnRho,
        dlnkap_dlnT,
        ierr,
        failed_zone,
    ) = values
    if int(ierr) != 0:
        raise RuntimeError(
            "MESA EOS/KAP profile call failed with "
            f"ierr={int(ierr)} at zone={int(failed_zone)}"
        )

    return _eos_kap_profile_output(
        T, Rho, res, kappa, dlnkap_dlnRho, dlnkap_dlnT, T_array.size, output
    )


def eos_kap_profile_from_logs(
    lnT: Iterable[float],
    lnd: Iterable[float],
    chem_id_values: Iterable[int],
    xa: object,
    *,
    output: str = "dict",
    use_type2: bool | None = None,
    zbase: float | None = None,
    use_zbase_for_type1: bool | None = None,
    type2_full_off_X: float | None = None,
    type2_full_on_X: float | None = None,
    type2_full_off_dZ: float | None = None,
    type2_full_on_dZ: float | None = None,
) -> dict[str, object]:
    """Compatibility alias for `eos_kap_profile(..., input_mode="log")`."""
    return eos_kap_profile(
        lnT,
        lnd,
        chem_id_values,
        xa,
        input_mode="log",
        output=output,
        use_type2=use_type2,
        zbase=zbase,
        use_zbase_for_type1=use_zbase_for_type1,
        type2_full_off_X=type2_full_off_X,
        type2_full_on_X=type2_full_on_X,
        type2_full_off_dZ=type2_full_off_dZ,
        type2_full_on_dZ=type2_full_on_dZ,
    )


@_timed_api("eos.solve_rho")
def eos_solve_rho(
    T: float,
    other: str | int,
    other_value: float,
    Rho_guess: float,
    comp: Composition | Mapping[str, float] | Iterable[float] | None = None,
    *,
    logRho_tol: float = 1.0e-10,
    other_tol: float = 1.0e-10,
    max_iter: int = 100,
) -> dict[str, float | int | dict[str, float] | dict[str, dict[str, float]]]:
    """Solve for density using MESA `eosDT_get_Rho`.

    `T` is in K. `other` selects one EOS result, such as `"lnPgas"` or
    `"lnE"`. `other_value` must be in MESA's result units; for `lnPgas`, pass
    the natural log of the target gas pressure in cgs units.
    """
    _prepare_mesa_cache_env()
    composition_data = _prepare_composition(comp)
    other_index = _eos_result_index(other)
    mesa_eos = _load_mesa_extension("_mesa_eos")
    values = mesa_eos.mesa_eos_solve_rho(
        float(T),
        other_index,
        float(other_value),
        float(Rho_guess),
        composition_data.chem_id,
        composition_data.xa,
        float(logRho_tol),
        float(other_tol),
        int(max_iter),
    )
    rho_result, log_rho, res, d_dlnRho, d_dlnT, d_dxa, eos_calls, ierr = values
    _check_ierr("MESA EOS solve rho", ierr)
    output = _eos_full_output_dict(composition_data, res, d_dlnRho, d_dlnT, d_dxa)
    return {
        "Rho": float(rho_result),
        "logRho": float(log_rho),
        "eos_calls": int(eos_calls),
        **output,
    }


@_timed_api("eos.solve_t")
def eos_solve_t(
    Rho: float,
    other: str | int,
    other_value: float,
    T_guess: float,
    comp: Composition | Mapping[str, float] | Iterable[float] | None = None,
    *,
    logT_tol: float = 1.0e-10,
    other_tol: float = 1.0e-10,
    max_iter: int = 100,
) -> dict[str, float | int | dict[str, float] | dict[str, dict[str, float]]]:
    """Solve for temperature using MESA `eosDT_get_T`.

    `Rho` is in g/cm^3. `other` selects one EOS result, such as `"lnPgas"` or
    `"lnE"`. `other_value` must be in MESA's result units; for `lnPgas`, pass
    the natural log of the target gas pressure in cgs units.
    """
    _prepare_mesa_cache_env()
    composition_data = _prepare_composition(comp)
    other_index = _eos_result_index(other)
    mesa_eos = _load_mesa_extension("_mesa_eos")
    values = mesa_eos.mesa_eos_solve_t(
        float(Rho),
        other_index,
        float(other_value),
        float(T_guess),
        composition_data.chem_id,
        composition_data.xa,
        float(logT_tol),
        float(other_tol),
        int(max_iter),
    )
    T_result, log_T, res, d_dlnRho, d_dlnT, d_dxa, eos_calls, ierr = values
    _check_ierr("MESA EOS solve T", ierr)
    output = _eos_full_output_dict(composition_data, res, d_dlnRho, d_dlnT, d_dxa)
    return {
        "T": float(T_result),
        "logT": float(log_T),
        "eos_calls": int(eos_calls),
        **output,
    }


eos_solve_T = eos_solve_t


@_timed_api("eos.solve_rho_profile")
def eos_solve_rho_profile(
    T: Iterable[float],
    other: str | int,
    other_value: Iterable[float] | float,
    Rho_guess: Iterable[float] | float,
    chem_id_values: Iterable[int],
    xa: object,
    *,
    input_mode: str | int = "value",
    logRho_tol: float = 1.0e-10,
    other_tol: float = 1.0e-10,
    max_iter: int = 100,
) -> dict[str, object]:
    """Solve for density across a profile using `eosDT_get_Rho`.

    `input_mode` applies to the known `T` array only. `Rho_guess` is always a
    physical cgs density and may be scalar or length `nzones`.
    """
    _prepare_mesa_cache_env()
    mode_value = _profile_input_mode(input_mode)
    other_index = _eos_result_index(other)
    T_array, chem_id_array, xa_array = _prepare_profile_coordinate(
        T, chem_id_values, xa, input_mode=mode_value, name="T"
    )
    other_value_array = _profile_value_array(other_value, T_array.size, "other_value")
    Rho_guess_array = _profile_value_array(
        Rho_guess, T_array.size, "Rho_guess", positive=True
    )

    mesa_eos = _load_mesa_extension("_mesa_eos")
    values = mesa_eos.mesa_eos_solve_rho_profile(
        chem_id_array, mode_value, T_array, other_index,
        other_value_array, Rho_guess_array, xa_array,
        float(logRho_tol), float(other_tol), int(max_iter),
    )
    (
        rho_result,
        log_rho,
        res,
        d_dlnRho,
        d_dlnT,
        d_dxa,
        eos_calls,
        ierr,
        failed_zone,
    ) = values
    if int(ierr) != 0:
        raise RuntimeError(
            "MESA EOS solve rho profile call failed with "
            f"ierr={int(ierr)} at zone={int(failed_zone)}"
        )

    return _eos_solve_profile_output(
        "Rho", "logRho", rho_result, log_rho, res, d_dlnRho, d_dlnT, d_dxa,
        eos_calls, T_array.size, chem_id_array.size,
    )


@_timed_api("eos.solve_t_profile")
def eos_solve_t_profile(
    Rho: Iterable[float],
    other: str | int,
    other_value: Iterable[float] | float,
    T_guess: Iterable[float] | float,
    chem_id_values: Iterable[int],
    xa: object,
    *,
    input_mode: str | int = "value",
    logT_tol: float = 1.0e-10,
    other_tol: float = 1.0e-10,
    max_iter: int = 100,
) -> dict[str, object]:
    """Solve for temperature across a profile using `eosDT_get_T`.

    `input_mode` applies to the known `Rho` array only. `T_guess` is always a
    physical temperature in K and may be scalar or length `nzones`.
    """
    _prepare_mesa_cache_env()
    mode_value = _profile_input_mode(input_mode)
    other_index = _eos_result_index(other)
    Rho_array, chem_id_array, xa_array = _prepare_profile_coordinate(
        Rho, chem_id_values, xa, input_mode=mode_value, name="Rho"
    )
    other_value_array = _profile_value_array(other_value, Rho_array.size, "other_value")
    T_guess_array = _profile_value_array(
        T_guess, Rho_array.size, "T_guess", positive=True
    )

    mesa_eos = _load_mesa_extension("_mesa_eos")
    values = mesa_eos.mesa_eos_solve_t_profile(
        chem_id_array, mode_value, Rho_array, other_index,
        other_value_array, T_guess_array, xa_array,
        float(logT_tol), float(other_tol), int(max_iter),
    )
    (
        T_result,
        log_T,
        res,
        d_dlnRho,
        d_dlnT,
        d_dxa,
        eos_calls,
        ierr,
        failed_zone,
    ) = values
    if int(ierr) != 0:
        raise RuntimeError(
            "MESA EOS solve T profile call failed with "
            f"ierr={int(ierr)} at zone={int(failed_zone)}"
        )

    return _eos_solve_profile_output(
        "T", "logT", T_result, log_T, res, d_dlnRho, d_dlnT, d_dxa,
        eos_calls, Rho_array.size, chem_id_array.size,
    )


eos_solve_T_profile = eos_solve_t_profile


def _kap_control_args(
    *,
    use_type2: bool | None,
    zbase: float | None,
    use_zbase_for_type1: bool | None,
    type2_full_off_X: float | None,
    type2_full_on_X: float | None,
    type2_full_off_dZ: float | None,
    type2_full_on_dZ: float | None,
) -> tuple[int, float, int, float, float, float, float]:
    zbase_value = _optional_control_value(zbase, "zbase")
    use_type2_mode = _bool_control_mode(
        use_type2,
        default_when_unset=None if _inlist_is_set() else False,
    )
    use_zbase_for_type1_mode = _bool_control_mode(
        use_zbase_for_type1,
        default_when_unset=None,
    )

    if use_type2 is True and zbase_value <= 0.0 and not _inlist_is_set():
        raise ValueError("zbase must be positive when use_type2=True")

    return (
        use_type2_mode,
        zbase_value,
        use_zbase_for_type1_mode,
        _optional_control_value(type2_full_off_X, "type2_full_off_X"),
        _optional_control_value(type2_full_on_X, "type2_full_on_X"),
        _optional_control_value(type2_full_off_dZ, "type2_full_off_dZ"),
        _optional_control_value(type2_full_on_dZ, "type2_full_on_dZ"),
    )


def _bool_control_mode(
    value: bool | None,
    *,
    default_when_unset: bool | None,
) -> int:
    if value is None:
        if default_when_unset is None:
            return -1
        return int(default_when_unset)
    return int(bool(value))


@_timed_api("kap.opacity")
def kap_opacity(
    T: float,
    Rho: float,
    comp: Composition | Mapping[str, float] | Iterable[float] | None = None,
    *,
    use_type2: bool | None = None,
    zbase: float | None = None,
    use_zbase_for_type1: bool | None = None,
    type2_full_off_X: float | None = None,
    type2_full_on_X: float | None = None,
    type2_full_off_dZ: float | None = None,
    type2_full_on_dZ: float | None = None,
) -> dict[str, float]:
    """Evaluate MESA opacity at known `T`, `Rho`, and composition.

    Inputs are temperature in K, density in g/cm^3, and mass fractions. The
    wrapper first calls EOS for electron quantities needed by KAP. Outputs are
    opacity `kappa` in cm^2/g and logarithmic derivatives with respect to
    `Rho` and `T`.
    """
    _prepare_mesa_cache_env()
    composition_data = _prepare_composition(comp)
    controls = _kap_control_args(
        use_type2=use_type2,
        zbase=zbase,
        use_zbase_for_type1=use_zbase_for_type1,
        type2_full_off_X=type2_full_off_X,
        type2_full_on_X=type2_full_on_X,
        type2_full_off_dZ=type2_full_off_dZ,
        type2_full_on_dZ=type2_full_on_dZ,
    )
    mesa_kap = _load_mesa_extension("_mesa_kap")
    values = mesa_kap.mesa_kap_composition_with_controls(
        float(T),
        float(Rho),
        composition_data.chem_id,
        composition_data.xa,
        *controls,
    )
    kappa, dlnkap_dlnRho, dlnkap_dlnT, ierr = values
    _check_ierr("MESA KAP", ierr)
    return {
        "kappa": float(kappa),
        "dlnkap_dlnRho": float(dlnkap_dlnRho),
        "dlnkap_dlnT": float(dlnkap_dlnT),
    }


@_timed_api("kap.opacity_full")
def kap_opacity_full(
    T: float,
    Rho: float,
    comp: Composition | Mapping[str, float] | Iterable[float] | None = None,
    *,
    use_type2: bool | None = None,
    zbase: float | None = None,
    use_zbase_for_type1: bool | None = None,
    type2_full_off_X: float | None = None,
    type2_full_on_X: float | None = None,
    type2_full_off_dZ: float | None = None,
    type2_full_on_dZ: float | None = None,
) -> dict[str, float | dict[str, float]]:
    """Evaluate MESA opacity and return all direct `kap_get` outputs.

    Inputs are temperature in K, density in g/cm^3, and mass fractions. Outputs
    include `kappa`, logarithmic derivatives, opacity-source fractions, and
    composition derivatives `dlnkap_dxa`.
    """
    _prepare_mesa_cache_env()
    composition_data = _prepare_composition(comp)
    controls = _kap_control_args(
        use_type2=use_type2,
        zbase=zbase,
        use_zbase_for_type1=use_zbase_for_type1,
        type2_full_off_X=type2_full_off_X,
        type2_full_on_X=type2_full_on_X,
        type2_full_off_dZ=type2_full_off_dZ,
        type2_full_on_dZ=type2_full_on_dZ,
    )
    mesa_kap = _load_mesa_extension("_mesa_kap")
    values = mesa_kap.mesa_kap_composition_full_with_controls(
        float(T),
        float(Rho),
        composition_data.chem_id,
        composition_data.xa,
        *controls,
    )
    kap_fracs, kappa, dlnkap_dlnRho, dlnkap_dlnT, dlnkap_dxa, ierr = values
    _check_ierr("MESA KAP", ierr)
    return {
        "kappa": float(kappa),
        "dlnkap_dlnRho": float(dlnkap_dlnRho),
        "dlnkap_dlnT": float(dlnkap_dlnT),
        "kap_fracs": _named_vector(KAP_FRAC_NAMES, kap_fracs),
        "dlnkap_dxa": _named_species_vector(composition_data.names, dlnkap_dxa),
    }


class Chem:
    """Small Python handle for MESA CHEM composition calls."""

    def iso_id(self, name: str) -> int:
        """Return the MESA 1-based isotope id for one isotope name."""
        return iso_id(name)

    def iso_ids(self, names: Iterable[str]) -> tuple[int, ...]:
        """Return MESA 1-based isotope ids for isotope names."""
        return iso_ids(names)

    def composition(
        self,
        mass_fractions: Mapping[str, float],
        *,
        normalize: bool = False,
    ) -> Composition:
        """Return a `Composition` from isotope-name mass fractions."""
        return composition(mass_fractions, normalize=normalize)

    def composition_info(
        self,
        comp: Composition | Mapping[str, float] | Iterable[float] | None,
    ) -> dict[str, float]:
        """Return MESA CHEM moments for a mass-fraction composition."""
        return composition_info(comp)


class Eos:
    """Small Python handle for MESA EOS calls."""

    def dt(
        self,
        T: float,
        Rho: float,
        comp: Composition | Mapping[str, float] | Iterable[float] | None = None,
    ) -> dict[str, float]:
        """Evaluate EOS at temperature `T` in K and density `Rho` in g/cm^3."""
        return eos_dt(T, Rho, comp)

    def dt_full(
        self,
        T: float,
        Rho: float,
        comp: Composition | Mapping[str, float] | Iterable[float] | None = None,
    ) -> dict[str, dict[str, float] | dict[str, dict[str, float]]]:
        """Evaluate EOS and return full result and derivative dictionaries."""
        return eos_dt_full(T, Rho, comp)

    def dt_profile(
        self,
        T: Iterable[float],
        Rho: Iterable[float],
        chem_id_values: Iterable[int],
        xa: object,
        *,
        input_mode: str | int = "value",
        output: str = "raw",
    ) -> dict[str, object]:
        """Evaluate EOS across a profile."""
        return eos_dt_profile(
            T,
            Rho,
            chem_id_values,
            xa,
            input_mode=input_mode,
            output=output,
        )

    def dt_profile_from_logs(
        self,
        lnT: Iterable[float],
        lnd: Iterable[float],
        chem_id_values: Iterable[int],
        xa: object,
        *,
        output: str = "dict",
    ) -> dict[str, object]:
        """Evaluate EOS across a saved-model style profile."""
        return eos_dt_profile_from_logs(
            lnT,
            lnd,
            chem_id_values,
            xa,
            output=output,
        )

    def solve_rho(
        self,
        T: float,
        other: str | int,
        other_value: float,
        Rho_guess: float,
        comp: Composition | Mapping[str, float] | Iterable[float] | None = None,
        *,
        logRho_tol: float = 1.0e-10,
        other_tol: float = 1.0e-10,
        max_iter: int = 100,
    ) -> dict[str, float | int | dict[str, float] | dict[str, dict[str, float]]]:
        """Solve for density at known `T` and one selected EOS result."""
        return eos_solve_rho(
            T,
            other,
            other_value,
            Rho_guess,
            comp,
            logRho_tol=logRho_tol,
            other_tol=other_tol,
            max_iter=max_iter,
        )

    def solve_t(
        self,
        Rho: float,
        other: str | int,
        other_value: float,
        T_guess: float,
        comp: Composition | Mapping[str, float] | Iterable[float] | None = None,
        *,
        logT_tol: float = 1.0e-10,
        other_tol: float = 1.0e-10,
        max_iter: int = 100,
    ) -> dict[str, float | int | dict[str, float] | dict[str, dict[str, float]]]:
        """Solve for temperature at known `Rho` and one selected EOS result."""
        return eos_solve_t(
            Rho,
            other,
            other_value,
            T_guess,
            comp,
            logT_tol=logT_tol,
            other_tol=other_tol,
            max_iter=max_iter,
        )

    solve_T = solve_t

    def solve_rho_profile(
        self,
        T: Iterable[float],
        other: str | int,
        other_value: Iterable[float] | float,
        Rho_guess: Iterable[float] | float,
        chem_id_values: Iterable[int],
        xa: object,
        *,
        input_mode: str | int = "value",
        logRho_tol: float = 1.0e-10,
        other_tol: float = 1.0e-10,
        max_iter: int = 100,
    ) -> dict[str, object]:
        """Solve for density across a profile."""
        return eos_solve_rho_profile(
            T,
            other,
            other_value,
            Rho_guess,
            chem_id_values,
            xa,
            input_mode=input_mode,
            logRho_tol=logRho_tol,
            other_tol=other_tol,
            max_iter=max_iter,
        )

    def solve_t_profile(
        self,
        Rho: Iterable[float],
        other: str | int,
        other_value: Iterable[float] | float,
        T_guess: Iterable[float] | float,
        chem_id_values: Iterable[int],
        xa: object,
        *,
        input_mode: str | int = "value",
        logT_tol: float = 1.0e-10,
        other_tol: float = 1.0e-10,
        max_iter: int = 100,
    ) -> dict[str, object]:
        """Solve for temperature across a profile."""
        return eos_solve_t_profile(
            Rho,
            other,
            other_value,
            T_guess,
            chem_id_values,
            xa,
            input_mode=input_mode,
            logT_tol=logT_tol,
            other_tol=other_tol,
            max_iter=max_iter,
        )

    solve_T_profile = solve_t_profile


class Kap:
    """Small Python handle for MESA KAP opacity calls."""

    def __init__(
        self,
        *,
        use_type2: bool | None = None,
        zbase: float | None = None,
        use_zbase_for_type1: bool | None = None,
        type2_full_off_X: float | None = None,
        type2_full_on_X: float | None = None,
        type2_full_off_dZ: float | None = None,
        type2_full_on_dZ: float | None = None,
    ) -> None:
        """Store KAP controls used by this Python object.

        The underlying Fortran KAP handle is process-persistent. This Python
        object stores the controls to apply before each opacity call.
        """
        self._controls = {
            "use_type2": use_type2,
            "zbase": zbase,
            "use_zbase_for_type1": use_zbase_for_type1,
            "type2_full_off_X": type2_full_off_X,
            "type2_full_on_X": type2_full_on_X,
            "type2_full_off_dZ": type2_full_off_dZ,
            "type2_full_on_dZ": type2_full_on_dZ,
        }

    def opacity(
        self,
        T: float,
        Rho: float,
        comp: Composition | Mapping[str, float] | Iterable[float] | None = None,
    ) -> dict[str, float]:
        """Evaluate opacity at temperature `T` in K and density `Rho` in g/cm^3."""
        return kap_opacity(T, Rho, comp, **self._controls)

    def opacity_full(
        self,
        T: float,
        Rho: float,
        comp: Composition | Mapping[str, float] | Iterable[float] | None = None,
    ) -> dict[str, float | dict[str, float]]:
        """Evaluate opacity and return full result and derivative dictionaries."""
        return kap_opacity_full(T, Rho, comp, **self._controls)

    def opacity_profile(
        self,
        T: Iterable[float],
        Rho: Iterable[float],
        chem_id_values: Iterable[int],
        xa: object,
        *,
        input_mode: str | int = "value",
    ) -> dict[str, object]:
        """Evaluate opacity across a profile."""
        return kap_opacity_profile(
            T,
            Rho,
            chem_id_values,
            xa,
            input_mode=input_mode,
            **self._controls,
        )

    def opacity_profile_from_logs(
        self,
        lnT: Iterable[float],
        lnd: Iterable[float],
        chem_id_values: Iterable[int],
        xa: object,
    ) -> dict[str, object]:
        """Evaluate opacity across a saved-model style profile."""
        return kap_opacity_profile_from_logs(
            lnT,
            lnd,
            chem_id_values,
            xa,
            **self._controls,
        )

    def eos_kap_profile(
        self,
        T: Iterable[float],
        Rho: Iterable[float],
        chem_id_values: Iterable[int],
        xa: object,
        *,
        input_mode: str | int = "value",
        output: str = "raw",
    ) -> dict[str, object]:
        """Evaluate EOS and opacity across a profile."""
        return eos_kap_profile(
            T,
            Rho,
            chem_id_values,
            xa,
            input_mode=input_mode,
            output=output,
            **self._controls,
        )

    def eos_kap_profile_from_logs(
        self,
        lnT: Iterable[float],
        lnd: Iterable[float],
        chem_id_values: Iterable[int],
        xa: object,
        *,
        output: str = "dict",
    ) -> dict[str, object]:
        """Evaluate EOS and opacity across a saved-model style profile."""
        return eos_kap_profile_from_logs(
            lnT,
            lnd,
            chem_id_values,
            xa,
            output=output,
            **self._controls,
        )


__all__ = [
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
]
