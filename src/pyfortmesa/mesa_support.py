"""Support helpers for the public pyfortmesa.mesa API."""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from functools import lru_cache
from importlib import import_module
from pathlib import Path

import numpy as np


# MESA environment.

PYFORTMESA_INLIST_ENV = "PYFORTMESA_INLIST"

def mesa_dir() -> Path:
    """Return the selected MESA source/build tree from `$MESA_DIR`."""
    value = os.environ.get("MESA_DIR")
    if not value:
        raise RuntimeError("MESA_DIR is not set. Select a MESA version first.")
    return Path(value).expanduser().resolve()


def mesa_pkg_config_path() -> str:
    """Return pkg-config search paths for shared MESA module libraries."""
    build_dir = mesa_dir() / "build"
    paths = sorted(build_dir.glob("*/lib/pkgconfig"))
    if not paths:
        raise RuntimeError(
            "No MESA pkg-config directories found under "
            f"{build_dir}. pyfortmesa's MESA wrappers support the new "
            "shared-library MESA layout only."
        )
    return os.pathsep.join(str(path) for path in paths if path.is_dir())


def set_cache_root(cache_root: str | os.PathLike[str] | None = ".") -> None:
    """Set where MESA EOS/KAP table caches should be written.

    `cache_root="."` writes under the current directory. `cache_root=None`
    leaves MESA cache paths at MESA's own defaults.
    """
    os.environ.pop("MESA_CACHES_DIR", None)
    os.environ.pop("MESA_TEMP_CACHES_DIR", None)

    if cache_root is None:
        os.environ["PYFORTMESA_CACHE_DIR"] = "mesa_default"
        return

    os.environ["PYFORTMESA_CACHE_DIR"] = str(cache_root)


def set_inlist(inlist: str | os.PathLike[str] | None) -> None:
    """Set the shared EOS/KAP controls inlist for later MESA handle creation.

    The path is explicit on purpose. pyfortmesa does not silently search the
    current directory for an inlist.
    """
    if inlist is None:
        os.environ.pop(PYFORTMESA_INLIST_ENV, None)
        return

    path = Path(inlist).expanduser().resolve(strict=True)
    os.environ[PYFORTMESA_INLIST_ENV] = str(path)


def _inlist_is_set() -> bool:
    return bool(os.environ.get(PYFORTMESA_INLIST_ENV))


def _prepare_mesa_cache_env() -> None:
    cache_root = os.environ.get("PYFORTMESA_CACHE_DIR")
    if cache_root is not None and cache_root.lower() in {"mesa_default", "default"}:
        return

    if cache_root is None:
        base = Path.cwd() / ".pyfortmesa_caches"
    else:
        base = Path(cache_root)

    mesa_caches_dir = Path(
        os.environ.setdefault("MESA_CACHES_DIR", str(base / "mesa_caches"))
    )
    mesa_temp_caches_dir = Path(
        os.environ.setdefault("MESA_TEMP_CACHES_DIR", str(base / "mesa_temp_caches"))
    )
    mesa_caches_dir.mkdir(parents=True, exist_ok=True)
    mesa_temp_caches_dir.mkdir(parents=True, exist_ok=True)


# Names and result-vector layouts.

SAMPLE_ISOTOPES = ("h1", "he4", "c12", "n14", "o16", "ne20", "mg24")
MESA_CONSTANT_NAMES = (
    "standard_cgrav",
    "crad",
    "clight",
    "Lsun",
    "Rsun",
    "Msun",
)
EOS_RESULT_NAMES = (
    "lnPgas",
    "lnE",
    "lnS",
    "mu",
    "lnfree_e",
    "eta",
    "grad_ad",
    "chiRho",
    "chiT",
    "Cp",
    "Cv",
    "dE_dRho",
    "dS_dT",
    "dS_dRho",
    "gamma1",
    "gamma3",
    "phase",
    "latent_ddlnT",
    "latent_ddlnRho",
    "HELM",
    "OPAL/SCVH",
    "FreeEOS",
    "PC",
    "Skye",
    "CMS",
    "ideal",
)
EOS_DXA_RESULT_NAMES = ("lnPgas", "lnE")
KAP_FRAC_NAMES = ("lowT", "highT", "Type2", "Compton")
EOS_RESULT_INDEX = {
    name: index
    for index, name in enumerate(EOS_RESULT_NAMES, start=1)
}
_EOS_RESULT_INDEX_LOWER = {
    name.lower(): index
    for name, index in EOS_RESULT_INDEX.items()
}
KAP_CONTROL_UNSET = -1.0


# Composition data.

@dataclass(frozen=True)
class Composition:
    """Mass fractions plus matching MESA `chem_id` values.

    `names` are isotope names, `chem_id` are MESA 1-based isotope ids, and `xa`
    are dimensionless mass fractions in the same order.
    """

    names: tuple[str, ...]
    chem_id: np.ndarray
    xa: np.ndarray

    @property
    def species(self) -> int:
        return len(self.names)


def sample_composition(primary: str = "c12") -> np.ndarray:
    """Return a legacy 7-isotope sample mass-fraction vector.

    The vector order is `h1, he4, c12, n14, o16, ne20, mg24`; the selected
    isotope receives mass fraction 1.
    """
    xa = np.zeros(len(SAMPLE_ISOTOPES), dtype=np.float64)
    try:
        xa[SAMPLE_ISOTOPES.index(primary.lower())] = 1.0
    except ValueError as exc:
        names = ", ".join(SAMPLE_ISOTOPES)
        raise ValueError(f"primary must be one of: {names}") from exc
    return xa


def composition(
    mass_fractions: Mapping[str, float],
    *,
    normalize: bool = False,
) -> Composition:
    """Return a MESA composition from isotope-name mass fractions.

    Inputs are dimensionless mass fractions keyed by MESA isotope names. Values
    must sum to 1 unless `normalize=True`.
    """
    if not mass_fractions:
        raise ValueError("mass_fractions must not be empty")

    isotope_ids = isotope_index()
    names: list[str] = []
    values: list[float] = []

    for raw_name, raw_value in mass_fractions.items():
        name = _normalize_isotope_name(raw_name)
        if name in names:
            raise ValueError(f"duplicate isotope name after normalization: {name}")
        if name not in isotope_ids:
            raise ValueError(f"unknown MESA isotope: {raw_name}")
        value = float(raw_value)
        if not np.isfinite(value):
            raise ValueError(f"mass fraction for {raw_name} is not finite")
        if value < 0.0:
            raise ValueError(f"mass fraction for {raw_name} is negative")
        names.append(name)
        values.append(value)

    xa = np.asarray(values, dtype=np.float64)
    total = float(xa.sum())
    if total <= 0.0:
        raise ValueError("at least one mass fraction must be positive")

    if normalize:
        xa = xa / total
    elif not np.isclose(total, 1.0, rtol=1.0e-10, atol=1.0e-12):
        raise ValueError(
            "mass fractions must sum to 1.0; pass normalize=True to normalize"
        )

    chem_id = np.asarray([isotope_ids[name] for name in names], dtype=np.int32)
    return Composition(
        names=tuple(names),
        chem_id=np.asfortranarray(chem_id),
        xa=np.asfortranarray(xa, dtype=np.float64),
    )


def isotope_index() -> dict[str, int]:
    """Return MESA isotope names mapped to 1-based `chem_id` values."""
    return dict(_load_isotope_index(str(mesa_dir())))


def iso_id(name: str) -> int:
    """Return the MESA 1-based `chem_id` for one isotope name."""
    isotope_ids = isotope_index()
    normalized = _normalize_isotope_name(name)
    try:
        return isotope_ids[normalized]
    except KeyError as exc:
        raise ValueError(f"unknown MESA isotope: {name}") from exc


def iso_ids(names: Iterable[str]) -> tuple[int, ...]:
    """Return MESA 1-based `chem_id` values for isotope names."""
    return tuple(iso_id(name) for name in names)


def _prepare_composition(
    comp: Composition | Mapping[str, float] | Iterable[float] | None,
) -> Composition:
    if comp is None:
        return composition({"c12": 1.0})

    if isinstance(comp, Composition):
        _validate_composition(comp)
        return comp

    if isinstance(comp, Mapping):
        return composition(comp)

    values = np.asarray(list(comp), dtype=np.float64)

    if values.shape != (len(SAMPLE_ISOTOPES),):
        names = ", ".join(SAMPLE_ISOTOPES)
        raise ValueError(
            "array-like composition must contain mass fractions for "
            f"the sample isotopes: {names}"
        )

    return composition(dict(zip(SAMPLE_ISOTOPES, values, strict=True)))


def _validate_composition(comp: Composition) -> None:
    if comp.species <= 0:
        raise ValueError("composition must contain at least one isotope")

    if comp.chem_id.shape != (comp.species,):
        raise ValueError("composition chem_id shape does not match names")

    if comp.xa.shape != (comp.species,):
        raise ValueError("composition xa shape does not match names")

    if not np.all(np.isfinite(comp.xa)):
        raise ValueError("composition mass fractions must be finite")

    if np.any(comp.xa < 0.0):
        raise ValueError("composition mass fractions must not be negative")

    if np.any(comp.chem_id <= 0):
        raise ValueError("composition chem_id values must be positive")

    if not np.isclose(float(comp.xa.sum()), 1.0, rtol=1.0e-10, atol=1.0e-12):
        raise ValueError("composition mass fractions must sum to 1.0")


@lru_cache(maxsize=None)
def _load_isotope_index(mesa_root: str) -> dict[str, int]:
    isotope_file = Path(mesa_root) / "data" / "chem_data" / "isotopes.data"
    if not isotope_file.exists():
        raise RuntimeError(f"MESA isotope data file not found: {isotope_file}")

    isotope_ids: dict[str, int] = {}
    with isotope_file.open("r", encoding="utf-8") as handle:
        for line in handle:
            fields = line.split()
            if not _is_isotope_header(fields):
                continue
            name = _normalize_isotope_name(fields[0])
            isotope_ids[name] = len(isotope_ids) + 1

    if not isotope_ids:
        raise RuntimeError(f"No isotope entries found in {isotope_file}")

    return isotope_ids


def _is_isotope_header(fields: list[str]) -> bool:
    if len(fields) < 6:
        return False
    if not any(char.isalpha() for char in fields[0]):
        return False
    try:
        float(fields[1])
        int(fields[2])
        int(fields[3])
        float(fields[4])
        float(fields[5])
    except ValueError:
        return False
    return True


def _normalize_isotope_name(name: str) -> str:
    return str(name).strip().lower()


def _eos_result_index(which: str | int) -> int:
    if isinstance(which, bool):
        raise TypeError("EOS result selector must be a result name or integer index")

    if isinstance(which, int):
        if which < 1 or which > len(EOS_RESULT_NAMES):
            raise ValueError(
                f"EOS result index must be between 1 and {len(EOS_RESULT_NAMES)}"
            )
        return which

    key = str(which).strip()
    try:
        return EOS_RESULT_INDEX[key]
    except KeyError:
        try:
            return _EOS_RESULT_INDEX_LOWER[key.lower()]
        except KeyError as exc:
            names = ", ".join(EOS_RESULT_NAMES)
            raise ValueError(
                f"unknown EOS result selector {which!r}; use: {names}"
            ) from exc


def _optional_control_value(value: float | None, name: str) -> float:
    if value is None:
        return KAP_CONTROL_UNSET

    control_value = float(value)
    if not np.isfinite(control_value):
        raise ValueError(f"{name} must be finite")
    if control_value < 0.0:
        raise ValueError(f"{name} must be non-negative")
    return control_value


# F2PY extension and result helpers.

def _load_mesa_extension(module_name: str):
    try:
        return import_module(f".{module_name}", __package__)
    except ImportError as exc:
        raise RuntimeError(
            "MESA wrappers are not available in this pyfortmesa install. "
            "Rebuild with MESA_DIR set and Meson option -Dwith_mesa=true."
        ) from exc


def _check_ierr(label: str, ierr: int) -> None:
    if int(ierr) != 0:
        raise RuntimeError(f"{label} call failed with ierr={int(ierr)}")


def _named_vector(names: tuple[str, ...], values: object) -> dict[str, float]:
    array = np.asarray(values, dtype=np.float64).reshape(-1)
    if array.shape != (len(names),):
        raise RuntimeError(
            f"MESA wrapper returned {array.size} values; expected {len(names)}"
        )
    return {name: float(value) for name, value in zip(names, array, strict=True)}


def _named_species_vector(
    names: tuple[str, ...],
    values: object,
) -> dict[str, float]:
    array = np.asarray(values, dtype=np.float64).reshape(-1)
    if array.shape != (len(names),):
        raise RuntimeError(
            f"MESA wrapper returned {array.size} species values; "
            f"expected {len(names)}"
        )
    return {name: float(value) for name, value in zip(names, array, strict=True)}


def _named_matrix_by_rows(
    row_names: tuple[str, ...],
    column_names: tuple[str, ...],
    values: object,
) -> dict[str, dict[str, float]]:
    array = np.asarray(values, dtype=np.float64)
    expected_shape = (len(row_names), len(column_names))
    transposed_shape = (len(column_names), len(row_names))

    if array.shape == transposed_shape:
        array = array.T
    elif array.shape != expected_shape:
        raise RuntimeError(
            f"MESA wrapper returned matrix shape {array.shape}; "
            f"expected {expected_shape}"
        )

    return {
        row_name: _named_species_vector(column_names, array[row_index, :])
        for row_index, row_name in enumerate(row_names)
    }


__all__ = [
    "Composition",
    "EOS_DXA_RESULT_NAMES",
    "EOS_RESULT_INDEX",
    "EOS_RESULT_NAMES",
    "KAP_CONTROL_UNSET",
    "KAP_FRAC_NAMES",
    "MESA_CONSTANT_NAMES",
    "SAMPLE_ISOTOPES",
    "composition",
    "iso_id",
    "iso_ids",
    "isotope_index",
    "mesa_dir",
    "mesa_pkg_config_path",
    "sample_composition",
    "set_cache_root",
    "set_inlist",
]
