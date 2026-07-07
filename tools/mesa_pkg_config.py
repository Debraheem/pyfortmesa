#!/usr/bin/env python3
"""Small Meson helper for querying pkg-config from a selected MESA tree."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


PKG_CONFIG_PATTERNS = (
    "lib/pkgconfig",
    "build/lib/pkgconfig",
    "build/*/lib/pkgconfig",
)


def mesa_dir() -> Path:
    value = os.environ.get("MESA_DIR")
    if not value:
        raise SystemExit("MESA_DIR is not set")
    return Path(value).expanduser().resolve()


def _has_mesa_pc(path: Path) -> bool:
    return any(path.glob("mesa-*.pc"))


def pkg_config_dirs() -> list[Path]:
    root = mesa_dir()
    candidates = [root / "lib" / "pkgconfig", root / "build" / "lib" / "pkgconfig"]
    candidates.extend(sorted((root / "build").glob("*/lib/pkgconfig")))

    paths: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path.resolve())
        if key in seen:
            continue
        seen.add(key)
        if path.is_dir() and _has_mesa_pc(path):
            paths.append(path)
    return paths


def pkg_config_path() -> str:
    paths = pkg_config_dirs()
    if not paths:
        root = mesa_dir()
        searched = "\n  ".join(str(root / pattern) for pattern in PKG_CONFIG_PATTERNS)
        raise SystemExit(
            "No MESA pkg-config files were found.\n"
            f"Searched:\n  {searched}\n"
            "pyfortmesa needs a MESA build with shared module libraries. "
            "For release trees with USE_SHARED = NO, set USE_SHARED = YES in "
            "$MESA_DIR/utils/makefile_header and rebuild MESA."
        )
    return os.pathsep.join(str(path) for path in paths)


def run_pkg_config(flag: str, packages: list[str]) -> str:
    env = os.environ.copy()
    env["PKG_CONFIG_PATH"] = pkg_config_path()
    command = ["pkg-config", flag, *packages]
    if flag == "--libs":
        command = ["pkg-config", "--libs", "--static", *packages]
    try:
        result = subprocess.run(
            command,
            check=True,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError as exc:
        raise SystemExit("pkg-config was not found") from exc
    except subprocess.CalledProcessError as exc:
        sys.stderr.write(exc.stderr)
        raise SystemExit(exc.returncode) from exc
    return result.stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode",
        choices=("path", "cflags", "libs"),
        help="information to print",
    )
    parser.add_argument("packages", nargs="*", help="pkg-config package names")
    args = parser.parse_args()

    if args.mode == "path":
        print(pkg_config_path())
        return

    if not args.packages:
        raise SystemExit(f"{args.mode} requires at least one package")

    print(run_pkg_config(f"--{args.mode}", args.packages))


if __name__ == "__main__":
    main()
