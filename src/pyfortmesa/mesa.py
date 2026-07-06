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
    composition,
    iso_id,
    iso_ids,
    isotope_index,
    sample_composition,
    set_cache_root,
    set_inlist,
)


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
        "d_dxa": _named_matrix_by_rows(
            EOS_DXA_RESULT_NAMES,
            composition_data.names,
            d_dxa,
        ),
    }


def _as_fortran_vector(
    values: Iterable[float] | Iterable[int],
    dtype: object,
) -> np.ndarray:
    if isinstance(values, np.ndarray):
        array = np.asarray(values, dtype=dtype)
    else:
        array = np.fromiter(values, dtype=dtype)
    return np.asfortranarray(array)


def _prepare_profile_arrays(
    lnT: Iterable[float],
    lnd: Iterable[float],
    chem_id_values: Iterable[int],
    xa: object,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    lnT_array = _as_fortran_vector(lnT, np.float64)
    lnd_array = _as_fortran_vector(lnd, np.float64)
    chem_id_array = _as_fortran_vector(chem_id_values, np.int32)
    xa_array = np.asfortranarray(np.asarray(xa, dtype=np.float64))

    if lnT_array.ndim != 1 or lnd_array.ndim != 1:
        raise ValueError("lnT and lnd must be one-dimensional")
    if lnT_array.shape != lnd_array.shape:
        raise ValueError("lnT and lnd must have the same length")
    if chem_id_array.ndim != 1:
        raise ValueError("chem_id_values must be one-dimensional")
    if xa_array.shape != (chem_id_array.size, lnT_array.size):
        raise ValueError("xa must have shape (species, nzones)")
    if lnT_array.size <= 0:
        raise ValueError("profile must contain at least one zone")
    if not np.all(np.isfinite(lnT_array)):
        raise ValueError("lnT values must be finite")
    if not np.all(np.isfinite(lnd_array)):
        raise ValueError("lnd values must be finite")
    if not np.all(np.isfinite(xa_array)):
        raise ValueError("xa values must be finite")
    if np.any(xa_array < 0.0):
        raise ValueError("xa values must be non-negative")

    return lnT_array, lnd_array, chem_id_array, xa_array


def _profile_logs(
    T: Iterable[float],
    Rho: Iterable[float],
) -> tuple[np.ndarray, np.ndarray]:
    T_array = _as_fortran_vector(T, np.float64)
    Rho_array = _as_fortran_vector(Rho, np.float64)

    if T_array.ndim != 1 or Rho_array.ndim != 1:
        raise ValueError("T and Rho must be one-dimensional")
    if T_array.shape != Rho_array.shape:
        raise ValueError("T and Rho must have the same length")
    if T_array.size <= 0:
        raise ValueError("profile must contain at least one zone")
    if not np.all(np.isfinite(T_array)):
        raise ValueError("T values must be finite")
    if not np.all(np.isfinite(Rho_array)):
        raise ValueError("Rho values must be finite")
    if np.any(T_array <= 0.0):
        raise ValueError("T values must be positive")
    if np.any(Rho_array <= 0.0):
        raise ValueError("Rho values must be positive")

    return (
        np.asfortranarray(np.log(T_array)),
        np.asfortranarray(np.log(Rho_array)),
    )


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


def eos_dt_profile(
    T: Iterable[float],
    Rho: Iterable[float],
    chem_id_values: Iterable[int],
    xa: object,
) -> dict[str, object]:
    """Evaluate EOS across a profile using `T` and `Rho` arrays."""
    lnT, lnd = _profile_logs(T, Rho)
    return eos_dt_profile_from_logs(lnT, lnd, chem_id_values, xa)


def eos_dt_profile_from_logs(
    lnT: Iterable[float],
    lnd: Iterable[float],
    chem_id_values: Iterable[int],
    xa: object,
) -> dict[str, object]:
    """Evaluate EOS across a profile whose inputs are MESA natural-log columns.

    Inputs `lnT` and `lnd` are the saved-model natural logs of temperature and
    density. `xa` must have shape `(species, nzones)`. The Fortran wrapper
    reconstructs `T = exp(lnT)` and `Rho = exp(lnd)` inside the EOS loop.
    """
    _prepare_mesa_cache_env()
    lnT_array, lnd_array, chem_id_array, xa_array = _prepare_profile_arrays(
        lnT,
        lnd,
        chem_id_values,
        xa,
    )

    mesa_eos = _load_mesa_extension("_mesa_eos")
    values = mesa_eos.mesa_eos_profile_from_logs(
        chem_id_array,
        lnT_array,
        lnd_array,
        xa_array,
    )
    T, Rho, res, ierr, failed_zone = values
    if int(ierr) != 0:
        raise RuntimeError(
            "MESA EOS profile call failed with "
            f"ierr={int(ierr)} at zone={int(failed_zone)}"
        )

    result_array = np.asarray(res, dtype=np.float64)
    if result_array.shape != (len(EOS_RESULT_NAMES), lnT_array.size):
        raise RuntimeError(
            "MESA EOS profile wrapper returned result shape "
            f"{result_array.shape}; expected "
            f"({len(EOS_RESULT_NAMES)}, {lnT_array.size})"
        )

    return {
        "T": np.asarray(T, dtype=np.float64),
        "Rho": np.asarray(Rho, dtype=np.float64),
        "results": {
            name: result_array[index, :].copy()
            for index, name in enumerate(EOS_RESULT_NAMES)
        },
    }


def kap_opacity_profile(
    T: Iterable[float],
    Rho: Iterable[float],
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
    """Evaluate KAP across a profile using `T` and `Rho` arrays."""
    lnT, lnd = _profile_logs(T, Rho)
    return kap_opacity_profile_from_logs(
        lnT,
        lnd,
        chem_id_values,
        xa,
        use_type2=use_type2,
        zbase=zbase,
        use_zbase_for_type1=use_zbase_for_type1,
        type2_full_off_X=type2_full_off_X,
        type2_full_on_X=type2_full_on_X,
        type2_full_off_dZ=type2_full_off_dZ,
        type2_full_on_dZ=type2_full_on_dZ,
    )


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
    """Evaluate KAP across a saved-model style profile.

    The KAP wrapper calls EOS internally for the electron quantities required
    by `kap_get`, then evaluates opacity for each profile zone.
    """
    _prepare_mesa_cache_env()
    lnT_array, lnd_array, chem_id_array, xa_array = _prepare_profile_arrays(
        lnT,
        lnd,
        chem_id_values,
        xa,
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
    values = mesa_kap.mesa_kap_profile_from_logs(
        chem_id_array,
        lnT_array,
        lnd_array,
        xa_array,
        *controls,
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


def eos_kap_profile(
    T: Iterable[float],
    Rho: Iterable[float],
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
    """Evaluate EOS and KAP across a profile using `T` and `Rho` arrays."""
    lnT, lnd = _profile_logs(T, Rho)
    return eos_kap_profile_from_logs(
        lnT,
        lnd,
        chem_id_values,
        xa,
        use_type2=use_type2,
        zbase=zbase,
        use_zbase_for_type1=use_zbase_for_type1,
        type2_full_off_X=type2_full_off_X,
        type2_full_on_X=type2_full_on_X,
        type2_full_off_dZ=type2_full_off_dZ,
        type2_full_on_dZ=type2_full_on_dZ,
    )


def eos_kap_profile_from_logs(
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
    """Evaluate EOS and KAP across a profile with one EOS call per zone."""
    _prepare_mesa_cache_env()
    lnT_array, lnd_array, chem_id_array, xa_array = _prepare_profile_arrays(
        lnT,
        lnd,
        chem_id_values,
        xa,
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
    values = mesa_kap.mesa_eos_kap_profile_from_logs(
        chem_id_array,
        lnT_array,
        lnd_array,
        xa_array,
        *controls,
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

    result_array = np.asarray(res, dtype=np.float64)
    if result_array.shape != (len(EOS_RESULT_NAMES), lnT_array.size):
        raise RuntimeError(
            "MESA EOS/KAP profile wrapper returned EOS result shape "
            f"{result_array.shape}; expected "
            f"({len(EOS_RESULT_NAMES)}, {lnT_array.size})"
        )

    return {
        "T": np.asarray(T, dtype=np.float64),
        "Rho": np.asarray(Rho, dtype=np.float64),
        "results": {
            name: result_array[index, :].copy()
            for index, name in enumerate(EOS_RESULT_NAMES)
        },
        "kappa": np.asarray(kappa, dtype=np.float64),
        "dlnkap_dlnRho": np.asarray(dlnkap_dlnRho, dtype=np.float64),
        "dlnkap_dlnT": np.asarray(dlnkap_dlnT, dtype=np.float64),
    }


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
    mesa_eos = _load_mesa_extension("_mesa_eos")
    values = mesa_eos.mesa_eos_solve_rho(
        float(T),
        _eos_result_index(other),
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
    output = _eos_full_output_dict(
        composition_data,
        res,
        d_dlnRho,
        d_dlnT,
        d_dxa,
    )
    return {
        "Rho": float(rho_result),
        "logRho": float(log_rho),
        "eos_calls": int(eos_calls),
        **output,
    }


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
    mesa_eos = _load_mesa_extension("_mesa_eos")
    values = mesa_eos.mesa_eos_solve_t(
        float(Rho),
        _eos_result_index(other),
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
    output = _eos_full_output_dict(
        composition_data,
        res,
        d_dlnRho,
        d_dlnT,
        d_dxa,
    )
    return {
        "T": float(T_result),
        "logT": float(log_T),
        "eos_calls": int(eos_calls),
        **output,
    }


eos_solve_T = eos_solve_t


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
    mesa_kap = _load_mesa_extension("_mesa_kap")
    controls = _kap_control_args(
        use_type2=use_type2,
        zbase=zbase,
        use_zbase_for_type1=use_zbase_for_type1,
        type2_full_off_X=type2_full_off_X,
        type2_full_on_X=type2_full_on_X,
        type2_full_off_dZ=type2_full_off_dZ,
        type2_full_on_dZ=type2_full_on_dZ,
    )
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
    mesa_kap = _load_mesa_extension("_mesa_kap")
    controls = _kap_control_args(
        use_type2=use_type2,
        zbase=zbase,
        use_zbase_for_type1=use_zbase_for_type1,
        type2_full_off_X=type2_full_off_X,
        type2_full_on_X=type2_full_on_X,
        type2_full_off_dZ=type2_full_off_dZ,
        type2_full_on_dZ=type2_full_on_dZ,
    )
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
    ) -> dict[str, object]:
        """Evaluate EOS across a profile using `T` and `Rho` arrays."""
        return eos_dt_profile(T, Rho, chem_id_values, xa)

    def dt_profile_from_logs(
        self,
        lnT: Iterable[float],
        lnd: Iterable[float],
        chem_id_values: Iterable[int],
        xa: object,
    ) -> dict[str, object]:
        """Evaluate EOS across a saved-model style profile."""
        return eos_dt_profile_from_logs(lnT, lnd, chem_id_values, xa)

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
    ) -> dict[str, object]:
        """Evaluate opacity across a profile using `T` and `Rho` arrays."""
        return kap_opacity_profile(
            T,
            Rho,
            chem_id_values,
            xa,
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
    ) -> dict[str, object]:
        """Evaluate EOS and opacity across a profile using `T` and `Rho` arrays."""
        return eos_kap_profile(
            T,
            Rho,
            chem_id_values,
            xa,
            **self._controls,
        )

    def eos_kap_profile_from_logs(
        self,
        lnT: Iterable[float],
        lnd: Iterable[float],
        chem_id_values: Iterable[int],
        xa: object,
    ) -> dict[str, object]:
        """Evaluate EOS and opacity across a saved-model style profile."""
        return eos_kap_profile_from_logs(
            lnT,
            lnd,
            chem_id_values,
            xa,
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
    "eos_dt",
    "eos_dt_full",
    "eos_dt_profile",
    "eos_kap_profile_from_logs",
    "eos_kap_profile",
    "eos_dt_profile_from_logs",
    "eos_solve_T",
    "eos_solve_rho",
    "eos_solve_t",
    "iso_id",
    "iso_ids",
    "isotope_index",
    "kap_opacity",
    "kap_opacity_full",
    "kap_opacity_profile",
    "kap_opacity_profile_from_logs",
    "sample_composition",
    "set_cache_root",
    "set_inlist",
    "shutdown",
]
