"""Read the text saved-model format written by MESA star.

This is intentionally a small parser for MESA's ASCII `.mod` saved model files.
It does not call MESA star or load a restart photo. The profile table supplies
the thermodynamic inputs needed by the pyfortmesa eos examples:

    lnd = ln(rho)
    lnT = ln(T)
    isotope columns = zone mass fractions
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


DEFAULT_MODEL_RELATIVE_PATH = Path(
    "star/test_suite/20M_pre_ms_to_core_collapse/standard_after_core_he_burn.mod"
)


@dataclass(frozen=True)
class SavedModelZone:
    """One zone from a MESA text `.mod` saved model."""

    zone: int
    values: Mapping[str, float]

    @property
    def lnd(self) -> float:
        return self.values["lnd"]

    @property
    def lnT(self) -> float:
        return self.values["lnT"]

    @property
    def rho(self) -> float:
        return math.exp(self.lnd)

    @property
    def T(self) -> float:
        return math.exp(self.lnT)

    def mass_fractions(self, isotope_columns: tuple[str, ...]) -> dict[str, float]:
        """Return isotope mass fractions for this zone."""
        return {name: float(self.values[name]) for name in isotope_columns}

    def mass_fraction_sum(self, isotope_columns: tuple[str, ...]) -> float:
        """Return the sum of isotope mass fractions in this zone."""
        return sum(self.mass_fractions(isotope_columns).values())


@dataclass(frozen=True)
class SavedModelProfile:
    """Parsed MESA text `.mod` saved model."""

    path: Path
    metadata: Mapping[str, str]
    columns: tuple[str, ...]
    zones: tuple[SavedModelZone, ...]

    @property
    def n_shells(self) -> int | None:
        value = self.metadata.get("n_shells")
        return int(value) if value is not None else None

    @property
    def species(self) -> int | None:
        value = self.metadata.get("species")
        return int(value) if value is not None else None

    @property
    def isotope_columns(self) -> tuple[str, ...]:
        """Return columns interpreted as isotope mass fractions."""
        start = self.columns.index("neut")
        return self.columns[start:]

    @property
    def zone_count_matches_header(self) -> bool:
        return self.n_shells is None or len(self.zones) == self.n_shells

    def selected_zones(self, max_zones: int | None = None) -> tuple[SavedModelZone, ...]:
        """Return all zones or the first `max_zones` zones."""
        if max_zones is None or max_zones <= 0:
            return self.zones
        return self.zones[:max_zones]


def default_model_path() -> Path:
    """Return the default saved-model path under `$MESA_DIR`."""
    mesa_dir = os.environ.get("MESA_DIR")
    if not mesa_dir:
        raise RuntimeError("MESA_DIR is not set; pass --model or export MESA_DIR")
    return Path(mesa_dir).expanduser().resolve() / DEFAULT_MODEL_RELATIVE_PATH


def read_saved_model(path: str | os.PathLike[str]) -> SavedModelProfile:
    """Read a MESA text `.mod` saved model."""
    model_path = Path(path).expanduser().resolve()
    lines = model_path.read_text(encoding="utf-8").splitlines()
    columns_index = _find_columns_index(lines)
    columns = tuple(lines[columns_index].split())
    metadata = _read_metadata(lines[:columns_index])
    zones = _read_zones(lines[columns_index + 1 :], columns)

    return SavedModelProfile(
        path=model_path,
        metadata=metadata,
        columns=columns,
        zones=tuple(zones),
    )


def _find_columns_index(lines: list[str]) -> int:
    for index, line in enumerate(lines):
        fields = line.split()
        if fields[:2] == ["lnd", "lnT"] and "neut" in fields:
            return index
    raise ValueError("could not find saved-model zone column header")


def _read_metadata(lines: list[str]) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for line in lines:
        fields = line.split()
        if len(fields) < 2:
            continue
        if fields[0] == "!" or fields[0].isdigit():
            continue
        _record_known_metadata(metadata, fields, "version_number")
        _record_known_metadata(metadata, fields, "M/Msun")
        _record_known_metadata(metadata, fields, "model_number")
        _record_known_metadata(metadata, fields, "star_age")
        _record_known_metadata(metadata, fields, "initial_z")
        _record_known_metadata(metadata, fields, "n_shells")
        _record_known_metadata(metadata, fields, "net_name")
        _record_known_metadata(metadata, fields, "species")
        _record_known_metadata(metadata, fields, "Teff")
    return metadata


def _record_known_metadata(
    metadata: dict[str, str],
    fields: list[str],
    name: str,
) -> None:
    if name in fields:
        index = fields.index(name)
        if index + 1 < len(fields):
            metadata[name] = fields[index + 1].strip("'")


def _read_zones(
    lines: list[str],
    columns: tuple[str, ...],
) -> list[SavedModelZone]:
    zones: list[SavedModelZone] = []
    expected_fields = len(columns) + 1

    for line in lines:
        fields = line.split()
        if not fields:
            if zones:
                break
            continue
        if len(fields) != expected_fields or not fields[0].isdigit():
            if zones:
                break
            continue

        zone = int(fields[0])
        values = {
            name: _fortran_float(value)
            for name, value in zip(columns, fields[1:])
        }
        zones.append(SavedModelZone(zone=zone, values=values))

    if not zones:
        raise ValueError("saved model did not contain any zone rows")

    return zones


def _fortran_float(value: str) -> float:
    return float(value.replace("D", "E").replace("d", "e"))
