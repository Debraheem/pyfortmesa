"""Support helpers for the public pyfortmesa.mesa API."""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from functools import lru_cache, wraps
from importlib import import_module
from pathlib import Path
from threading import RLock
from time import perf_counter

import numpy as np


# MESA environment.

PYFORTMESA_INLIST_ENV = "PYFORTMESA_INLIST"
_MESA_CACHE_ENV_PREPARED = False


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
    """Set where MESA eos/kap table caches should be written.

    `cache_root="."` writes under the current directory. `cache_root=None`
    leaves MESA cache paths at MESA's own defaults.
    """
    global _MESA_CACHE_ENV_PREPARED

    _MESA_CACHE_ENV_PREPARED = False
    os.environ.pop("MESA_CACHES_DIR", None)
    os.environ.pop("MESA_TEMP_CACHES_DIR", None)

    if cache_root is None:
        os.environ["PYFORTMESA_CACHE_DIR"] = "mesa_default"
        return

    os.environ["PYFORTMESA_CACHE_DIR"] = str(cache_root)


def set_inlist(inlist: str | os.PathLike[str] | None) -> None:
    """Set the shared eos/kap controls inlist for later MESA handle creation.

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
    global _MESA_CACHE_ENV_PREPARED

    if _MESA_CACHE_ENV_PREPARED:
        return

    cache_root = os.environ.get("PYFORTMESA_CACHE_DIR")
    if cache_root is not None and cache_root.lower() in {"mesa_default", "default"}:
        _MESA_CACHE_ENV_PREPARED = True
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
    _MESA_CACHE_ENV_PREPARED = True


# Names and result-vector layouts.

SAMPLE_ISOTOPES = ("h1", "he4", "c12", "n14", "o16", "ne20", "mg24")
MESA_CONSTANT_NAMES = (
    "pi",
    "pi2",
    "pi4",
    "eulercon",
    "eulernum",
    "ln2",
    "ln3",
    "lnPi",
    "ln10",
    "iln10",
    "a2rad",
    "rad2a",
    "one_third",
    "two_thirds",
    "four_thirds",
    "five_thirds",
    "one_sixth",
    "four_thirds_pi",
    "ln4pi3",
    "two_13",
    "four_13",
    "sqrt2",
    "sqrt_2_div_3",
    "avo",
    "amu",
    "clight",
    "qe",
    "kerg",
    "boltzm",
    "planck_h",
    "hbar",
    "cgas",
    "ev2erg",
    "mev_to_ergs",
    "mev_amu",
    "mev2gr",
    "Qconv",
    "kev",
    "boltz_sigma",
    "crad",
    "au",
    "pc",
    "dayyer",
    "secday",
    "secyer",
    "ly",
    "mn",
    "mp",
    "me",
    "rbohr",
    "fine",
    "hion",
    "sige",
    "weinberg_theta",
    "num_neu_fam",
    "standard_cgrav",
    "mu_sun",
    "mu_earth",
    "mu_jupiter",
    "agesun",
    "Msun",
    "Rsun",
    "Lsun",
    "Teffsun",
    "loggsun",
    "mbolsun",
    "m_earth",
    "r_earth",
    "r_earth_polar",
    "m_jupiter",
    "r_jupiter",
    "r_jupiter_polar",
    "semimajor_axis_jupiter",
    "arg_not_provided",
    "missing_value",
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
EOS_RESULT_INDEX = {name: index for index, name in enumerate(EOS_RESULT_NAMES, start=1)}
_EOS_RESULT_INDEX_LOWER = {name.lower(): index for name, index in EOS_RESULT_INDEX.items()}
KAP_CONTROL_UNSET = -1.0

# Lowercase aliases are supported, but the all-caps names remain canonical.
sample_isotopes = SAMPLE_ISOTOPES
mesa_constant_names = MESA_CONSTANT_NAMES
eos_result_names = EOS_RESULT_NAMES
eos_dxa_result_names = EOS_DXA_RESULT_NAMES
kap_frac_names = KAP_FRAC_NAMES
eos_result_index = EOS_RESULT_INDEX
kap_control_unset = KAP_CONTROL_UNSET


# Optional timing state.

@dataclass
class _TimingEntry:
    calls: int = 0
    seconds: float = 0.0


_TIMING_ENABLED = False
_TIMING_LOCK = RLock()
_TIMING_DATA: dict[str, _TimingEntry] = {}
_TIMING_ORDER: list[str] = []


class _NullTimer:
    __slots__ = ()

    def __enter__(self) -> None:
        return None

    def __exit__(self, exc_type, exc, traceback) -> bool:
        return False


class _Timer:
    __slots__ = ("name", "start")

    def __init__(self, name: str) -> None:
        self.name = name
        self.start = 0.0

    def __enter__(self) -> None:
        self.start = perf_counter()
        return None

    def __exit__(self, exc_type, exc, traceback) -> bool:
        _record_timing(self.name, perf_counter() - self.start)
        return False


class TimingScope:
    """Context manager returned by `mesa.timing(...)`."""

    def __init__(self, *, reset: bool = True) -> None:
        self.reset = reset
        self._previous_enabled = False

    def __enter__(self) -> "TimingScope":
        global _TIMING_ENABLED
        with _TIMING_LOCK:
            self._previous_enabled = _TIMING_ENABLED
            if self.reset:
                _reset_timing_locked()
            _TIMING_ENABLED = True
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        global _TIMING_ENABLED
        with _TIMING_LOCK:
            _TIMING_ENABLED = self._previous_enabled
        return False

    def summary(self) -> tuple[dict[str, float | int | str], ...]:
        return timing_summary()

    def format(self) -> str:
        return format_timing_summary()


_NULL_TIMER = _NullTimer()


def _timed(name: str) -> _NullTimer | _Timer:
    if not _TIMING_ENABLED:
        return _NULL_TIMER
    return _Timer(name)


def _timed_api(name: str):
    def decorate(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            if not _TIMING_ENABLED:
                return function(*args, **kwargs)
            start = perf_counter()
            try:
                return function(*args, **kwargs)
            finally:
                _record_timing(name, perf_counter() - start)

        return wrapper

    return decorate


def _record_timing(name: str, seconds: float) -> None:
    with _TIMING_LOCK:
        entry = _TIMING_DATA.get(name)
        if entry is None:
            entry = _TimingEntry()
            _TIMING_DATA[name] = entry
            _TIMING_ORDER.append(name)
        entry.calls += 1
        entry.seconds += seconds


def _reset_timing_locked() -> None:
    _TIMING_DATA.clear()
    _TIMING_ORDER.clear()


def enable_timing(*, reset: bool = True) -> None:
    """Enable process-local pyfortmesa timing collection."""
    global _TIMING_ENABLED
    with _TIMING_LOCK:
        if reset:
            _reset_timing_locked()
        _TIMING_ENABLED = True


def disable_timing() -> None:
    """Disable pyfortmesa timing collection without clearing accumulated data."""
    global _TIMING_ENABLED
    with _TIMING_LOCK:
        _TIMING_ENABLED = False


def reset_timing() -> None:
    """Clear accumulated pyfortmesa timing data."""
    with _TIMING_LOCK:
        _reset_timing_locked()


def timing_enabled() -> bool:
    """Return whether pyfortmesa timing collection is enabled."""
    return _TIMING_ENABLED


def timing(*, reset: bool = True) -> TimingScope:
    """Return a context manager that enables pyfortmesa timing."""
    return TimingScope(reset=reset)


def timing_summary(*, sort_by: str = "order") -> tuple[dict[str, float | int | str], ...]:
    """Return accumulated pyfortmesa timing rows."""
    with _TIMING_LOCK:
        rows = [
            {
                "name": name,
                "calls": entry.calls,
                "seconds": entry.seconds,
                "seconds_per_call": entry.seconds / entry.calls if entry.calls else 0.0,
            }
            for name in _TIMING_ORDER
            if (entry := _TIMING_DATA.get(name)) is not None
        ]

    total = sum(float(row["seconds"]) for row in rows)
    for row in rows:
        row["fraction"] = float(row["seconds"]) / total if total > 0.0 else 0.0

    if sort_by == "seconds":
        return tuple(sorted(rows, key=lambda row: float(row["seconds"]), reverse=True))
    if sort_by != "order":
        raise ValueError("sort_by must be 'order' or 'seconds'")
    return tuple(rows)


def format_timing_summary(*, sort_by: str = "order") -> str:
    """Return a compact timing summary for display."""
    rows = timing_summary(sort_by=sort_by)
    if not rows:
        return "pyfortmesa timing: no recorded calls"

    total = sum(float(row["seconds"]) for row in rows)
    lines = ["pyfortmesa timing:"]
    lines.append("  name                           calls      seconds      per_call   fraction")
    for row in rows:
        lines.append(
            f"  {str(row['name']):<30} {int(row['calls']):5d} "
            f"{float(row['seconds']):12.6e} {float(row['seconds_per_call']):12.6e} "
            f"{float(row['fraction']):8.3f}"
        )
    lines.append(f"  {'total':<30} {'':>5} {total:12.6e}")
    return "\n".join(lines)


def print_timing_summary(*, sort_by: str = "order") -> None:
    """Print `format_timing_summary(...)`."""
    print(format_timing_summary(sort_by=sort_by))


EOS_SHORT_RESULT_NAMES = ("lnPgas", "lnE", "lnS", "grad_ad", "gamma1")
EOS_SCHEMA_NAMES = (
    "eos_dt",
    "eos_dt_full",
    "eos_dt_profile",
    "eos_dt_profile_from_logs",
    "eos_solve_rho",
    "eos_solve_rho_profile",
    "eos_solve_t",
    "eos_solve_t_profile",
)
KAP_SCHEMA_NAMES = (
    "kap_opacity",
    "kap_opacity_full",
    "kap_opacity_profile",
    "kap_opacity_profile_from_logs",
)
EOS_KAP_SCHEMA_NAMES = (
    "eos_kap_profile",
    "eos_kap_profile_from_logs",
)
OUTPUT_SCHEMA_NAMES = EOS_SCHEMA_NAMES + KAP_SCHEMA_NAMES + EOS_KAP_SCHEMA_NAMES
_OUTPUT_SCHEMA_ALIASES = {
    "eos": "eos_dt_full",
    "eos_full": "eos_dt_full",
    "eos_profile": "eos_dt_profile",
    "kap": "kap_opacity_full",
    "kap_full": "kap_opacity_full",
    "kap_profile": "kap_opacity_profile",
    "eos_kap": "eos_kap_profile",
    "eos-kap": "eos_kap_profile",
}

_EOS_RESULT_UNITS = {
    "lnPgas": "ln(dyn/cm^2)",
    "lnE": "ln(erg/g)",
    "lnS": "ln(erg/g/K)",
    "mu": "dimensionless",
    "lnfree_e": "ln(free electrons per nucleon)",
    "eta": "dimensionless",
    "grad_ad": "dimensionless",
    "chiRho": "dimensionless",
    "chiT": "dimensionless",
    "Cp": "erg/g/K",
    "Cv": "erg/g/K",
    "dE_dRho": "erg cm^3/g^2",
    "dS_dT": "erg/g/K^2",
    "dS_dRho": "erg cm^3/g^2/K",
    "gamma1": "dimensionless",
    "gamma3": "dimensionless",
    "phase": "dimensionless",
    "latent_ddlnT": "erg/g",
    "latent_ddlnRho": "erg/g",
    "HELM": "fraction",
    "OPAL/SCVH": "fraction",
    "FreeEOS": "fraction",
    "PC": "fraction",
    "Skye": "fraction",
    "CMS": "fraction",
    "ideal": "fraction",
}
_EOS_RESULT_COMMENTS = {
    "lnPgas": "natural log gas pressure",
    "lnE": "natural log specific internal energy",
    "lnS": "natural log specific entropy",
    "mu": "mean molecular weight per gas particle",
    "lnfree_e": "natural log free electrons per nucleon",
    "eta": "electron degeneracy parameter",
    "grad_ad": "dlnT/dlnP at constant entropy",
    "chiRho": "dlnP/dlnRho at constant T",
    "chiT": "dlnP/dlnT at constant Rho",
    "Cp": "specific heat at constant total pressure",
    "Cv": "specific heat at constant volume",
    "dE_dRho": "dE/dRho at constant T",
    "dS_dT": "dS/dT at constant Rho",
    "dS_dRho": "dS/dRho at constant T",
    "gamma1": "dlnP/dlnRho at constant entropy",
    "gamma3": "gamma3 - 1 = dlnT/dlnRho at constant entropy",
    "phase": "1 solid, 0 liquid, in-between for blend",
    "latent_ddlnT": "T*dS/dlnT from phase transition",
    "latent_ddlnRho": "T*dS/dlnRho from phase transition",
    "HELM": "eos blend fraction",
    "OPAL/SCVH": "eos blend fraction",
    "FreeEOS": "eos blend fraction",
    "PC": "eos blend fraction",
    "Skye": "eos blend fraction",
    "CMS": "eos blend fraction",
    "ideal": "eos blend fraction",
}
_KAP_FRAC_COMMENTS = {
    "lowT": "low-temperature opacity fraction",
    "highT": "high-temperature opacity fraction",
    "Type2": "Type2 opacity fraction",
    "Compton": "Compton opacity fraction",
}


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


def _schema_species(species: Composition | Iterable[str] | None) -> tuple[str, ...]:
    if species is None:
        return ()
    if isinstance(species, Composition):
        return species.names
    if isinstance(species, str):
        return (species,)
    return tuple(str(name) for name in species)


def _schema_field(
    column: str, units: str, shape: str, comment: str, *, path: str | None = None
) -> dict[str, str]:
    return {
        "column": column,
        "path": path or column,
        "units": units,
        "shape": shape,
        "comment": comment,
    }


def _eos_result_schema(
    prefix: str, shape: str, *, raw_profile: bool = False
) -> list[dict[str, str]]:
    return [
        _schema_field(
            f"{prefix}.{name}", _EOS_RESULT_UNITS[name], shape,
            _EOS_RESULT_COMMENTS[name],
            path=(
                f'{prefix}[EOS_RESULT_NAMES.index("{name}"), :]'
                if raw_profile
                else f'{prefix}["{name}"]'
            ),
        )
        for name in EOS_RESULT_NAMES
    ]


def _eos_scalar_derivative_schema(
    prefix: str, shape: str, *, raw_profile: bool = False
) -> list[dict[str, str]]:
    variable = prefix[2:]
    return [
        _schema_field(
            f"{prefix}.{name}", _eos_log_derivative_units(name, variable), shape,
            f"derivative of {name} with respect to {variable}",
            path=(
                f'{prefix}[EOS_RESULT_NAMES.index("{name}"), :]'
                if raw_profile
                else f'{prefix}["{name}"]'
            ),
        )
        for name in EOS_RESULT_NAMES
    ]


def _eos_log_derivative_units(name: str, variable: str) -> str:
    units = _EOS_RESULT_UNITS[name]
    if units.startswith("ln(") or units in {"dimensionless", "fraction"}:
        return "dimensionless"
    return f"{units} per {variable}"


def _eos_dxa_schema(
    species: tuple[str, ...], *, shape: str = "scalar", raw_profile: bool = False
) -> list[dict[str, str]]:
    names = species or ("<isotope>",)
    return [
        _schema_field(
            f"d_dxa.{result_name}.{isotope}", "per mass fraction", shape,
            f"d {result_name} / d xa[{isotope}]",
            path=(
                f'd_dxa[EOS_DXA_RESULT_NAMES.index("{result_name}"), '
                f'species_index["{isotope}"], :]'
                if raw_profile
                else f'd_dxa["{result_name}"]["{isotope}"]'
            ),
        )
        for result_name in EOS_DXA_RESULT_NAMES
        for isotope in names
    ]


def _kap_dxa_schema(species: tuple[str, ...]) -> list[dict[str, str]]:
    names = species or ("<isotope>",)
    return [
        _schema_field(
            f"dlnkap_dxa.{isotope}", "per mass fraction", "scalar",
            f"d ln(kappa) / d xa[{isotope}]",
            path=f'dlnkap_dxa["{isotope}"]',
        )
        for isotope in names
    ]


def _eos_short_schema(shape: str) -> list[dict[str, str]]:
    return [
        _schema_field(name, _EOS_RESULT_UNITS[name], shape, _EOS_RESULT_COMMENTS[name])
        for name in EOS_SHORT_RESULT_NAMES
    ]


def _profile_base_schema() -> list[dict[str, str]]:
    return [
        _schema_field("T", "K", "(nzones,)", "temperature"),
        _schema_field("Rho", "g/cm^3", "(nzones,)", "density"),
    ]


def _kap_base_schema(shape: str) -> list[dict[str, str]]:
    return [
        _schema_field("kappa", "cm^2/g", shape, "Rosseland mean opacity"),
        _schema_field(
            "dlnkap_dlnRho", "dimensionless", shape,
            "d ln(kappa) / d ln(Rho) at constant T",
        ),
        _schema_field(
            "dlnkap_dlnT", "dimensionless", shape,
            "d ln(kappa) / d ln(T) at constant Rho",
        ),
    ]


def _kap_frac_schema() -> list[dict[str, str]]:
    return [
        _schema_field(
            f"kap_fracs.{name}",
            "fraction",
            "scalar",
            _KAP_FRAC_COMMENTS[name],
            path=f'kap_fracs["{name}"]',
        )
        for name in KAP_FRAC_NAMES
    ]


def _normalize_output_schema_name(name: str) -> str:
    key = str(name).strip()
    key = _OUTPUT_SCHEMA_ALIASES.get(key, key)
    if key not in OUTPUT_SCHEMA_NAMES:
        valid = ", ".join(output_schema_names())
        raise ValueError(f"unknown output schema {name!r}; use one of: {valid}")
    return key


def output_schema_names(*, include_aliases: bool = False) -> tuple[str, ...]:
    """Return accepted names for `output_schema(...)`."""
    names = OUTPUT_SCHEMA_NAMES
    if include_aliases:
        names = names + tuple(_OUTPUT_SCHEMA_ALIASES)
    return names


def output_schema(
    name: str, *, species: Composition | Iterable[str] | None = None
) -> tuple[dict[str, str], ...]:
    """Return output fields for a pyfortmesa eos/kap helper.

    Each row has `column`, `path`, `units`, `shape`, and `comment` keys. The
    helper is metadata-only; it does not import or call the compiled MESA
    wrappers.
    """
    key = _normalize_output_schema_name(name)
    species_names = _schema_species(species)

    if key == "eos_dt":
        rows = _eos_short_schema("scalar")
    elif key in {"eos_dt_full", "eos_solve_rho", "eos_solve_t"}:
        rows = []
        if key == "eos_solve_rho":
            rows.extend(
                [
                    _schema_field("Rho", "g/cm^3", "scalar", "solved density"),
                    _schema_field("logRho", "log10(g/cm^3)", "scalar", "log10 density"),
                    _schema_field("eos_calls", "count", "scalar", "eos solver calls"),
                ]
            )
        elif key == "eos_solve_t":
            rows.extend(
                [
                    _schema_field("T", "K", "scalar", "solved temperature"),
                    _schema_field("logT", "log10(K)", "scalar", "log10 temperature"),
                    _schema_field("eos_calls", "count", "scalar", "eos solver calls"),
                ]
            )
        rows.extend(_eos_result_schema("results", "scalar"))
        rows.extend(_eos_scalar_derivative_schema("d_dlnRho", "scalar"))
        rows.extend(_eos_scalar_derivative_schema("d_dlnT", "scalar"))
        rows.extend(_eos_dxa_schema(species_names))
    elif key in {"eos_dt_profile", "eos_dt_profile_from_logs"}:
        rows = _profile_base_schema()
        rows.extend(_eos_result_schema("results", "(nzones,)", raw_profile=True))
    elif key in {"eos_solve_rho_profile", "eos_solve_t_profile"}:
        rows = []
        if key == "eos_solve_rho_profile":
            rows.extend(
                [
                    _schema_field("Rho", "g/cm^3", "(nzones,)", "solved density"),
                    _schema_field("logRho", "log10(g/cm^3)", "(nzones,)", "log10 density"),
                    _schema_field("eos_calls", "count", "(nzones,)", "eos solver calls"),
                ]
            )
        else:
            rows.extend(
                [
                    _schema_field("T", "K", "(nzones,)", "solved temperature"),
                    _schema_field("logT", "log10(K)", "(nzones,)", "log10 temperature"),
                    _schema_field("eos_calls", "count", "(nzones,)", "eos solver calls"),
                ]
            )
        rows.extend(_eos_result_schema("results", "(nzones,)", raw_profile=True))
        rows.extend(_eos_scalar_derivative_schema("d_dlnRho", "(nzones,)", raw_profile=True))
        rows.extend(_eos_scalar_derivative_schema("d_dlnT", "(nzones,)", raw_profile=True))
        rows.extend(_eos_dxa_schema(species_names, shape="(nzones,)", raw_profile=True))
    elif key == "kap_opacity":
        rows = _kap_base_schema("scalar")
    elif key == "kap_opacity_full":
        rows = _kap_base_schema("scalar")
        rows.extend(_kap_frac_schema())
        rows.extend(_kap_dxa_schema(species_names))
    elif key in {"kap_opacity_profile", "kap_opacity_profile_from_logs"}:
        rows = _profile_base_schema()
        rows.extend(_kap_base_schema("(nzones,)"))
    else:
        rows = _profile_base_schema()
        rows.extend(_eos_result_schema("results", "(nzones,)", raw_profile=True))
        rows.extend(_kap_base_schema("(nzones,)"))

    return tuple(rows)


def output_columns(
    name: str, *, species: Composition | Iterable[str] | None = None
) -> tuple[str, ...]:
    """Return flat DataFrame-style column names for an output schema."""
    return tuple(row["column"] for row in output_schema(name, species=species))


def format_output_schema(
    name: str, *, species: Composition | Iterable[str] | None = None
) -> str:
    """Return a comment-style field summary for a pyfortmesa output."""
    rows = output_schema(name, species=species)
    if not rows:
        return ""
    width = max(len(row["column"]) for row in rows)
    return "\n".join(
        f'{row["column"]:<{width}}  # units={row["units"]}; '
        f'shape={row["shape"]}; {row["comment"]}'
        for row in rows
    )


def print_output_schema(
    name: str, *, species: Composition | Iterable[str] | None = None
) -> None:
    """Print `format_output_schema(...)` for interactive use."""
    print(format_output_schema(name, species=species))


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


def composition(mass_fractions: Mapping[str, float], *, normalize: bool = False) -> Composition:
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
    isotope_ids = isotope_index()
    values: list[int] = []
    for name in names:
        normalized = _normalize_isotope_name(name)
        try:
            values.append(isotope_ids[normalized])
        except KeyError as exc:
            raise ValueError(f"unknown MESA isotope: {name}") from exc
    return tuple(values)


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
        raise TypeError("eos result selector must be a result name or integer index")

    if isinstance(which, int):
        if which < 1 or which > len(EOS_RESULT_NAMES):
            raise ValueError(
                f"eos result index must be between 1 and {len(EOS_RESULT_NAMES)}"
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
                f"unknown eos result selector {which!r}; use: {names}"
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


def _named_species_vector(names: tuple[str, ...], values: object) -> dict[str, float]:
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
    "eos_dxa_result_names",
    "eos_result_index",
    "eos_result_names",
    "kap_control_unset",
    "kap_frac_names",
    "mesa_constant_names",
    "sample_isotopes",
    "composition",
    "disable_timing",
    "enable_timing",
    "format_timing_summary",
    "iso_id",
    "iso_ids",
    "isotope_index",
    "format_output_schema",
    "mesa_dir",
    "mesa_pkg_config_path",
    "output_columns",
    "output_schema",
    "output_schema_names",
    "print_output_schema",
    "print_timing_summary",
    "reset_timing",
    "sample_composition",
    "set_cache_root",
    "set_inlist",
    "timing",
    "timing_enabled",
    "timing_summary",
]
