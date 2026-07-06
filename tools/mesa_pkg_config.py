#!/usr/bin/env python3
"""Small Meson helper for querying pkg-config from a selected MESA tree."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def mesa_dir() -> Path:
    value = os.environ.get("MESA_DIR")
    if not value:
        raise SystemExit("MESA_DIR is not set")
    return Path(value).expanduser().resolve()


def pkg_config_path() -> str:
    build_dir = mesa_dir() / "build"
    paths = sorted(path for path in build_dir.glob("*/lib/pkgconfig") if path.is_dir())
    if not paths:
        raise SystemExit(
            f"No MESA pkg-config directories found under {build_dir}. "
            "This build path supports the new shared-library MESA layout only."
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
