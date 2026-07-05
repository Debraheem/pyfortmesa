"""Helpers for locating a user-selected MESA installation."""

from __future__ import annotations

import os
from pathlib import Path


def mesa_dir() -> Path:
    """Return MESA_DIR as a resolved path."""
    value = os.environ.get("MESA_DIR")
    if not value:
        raise RuntimeError("MESA_DIR is not set. Select a MESA version first.")
    return Path(value).expanduser().resolve()


def mesa_pkg_config_path() -> str:
    """Return pkg-config search paths for MESA module libraries."""
    build_dir = mesa_dir() / "build"
    paths = sorted(build_dir.glob("*/lib/pkgconfig"))
    if not paths:
        raise RuntimeError(f"No MESA pkg-config directories found under {build_dir}")
    return os.pathsep.join(str(path) for path in paths if path.is_dir())
