#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$repo_root"

mode="${1:-wheel}"

case "$mode" in
  wheel)
    python -m build --wheel
    ;;
  mesa)
    : "${MESA_DIR:?Set MESA_DIR to a supported new MESA tree first.}"
    export PKG_CONFIG_PATH="$(python tools/mesa_pkg_config.py path)"
    python -m build --wheel --no-isolation -Csetup-args=-Dwith_mesa=true
    ;;
  sdist)
    python -m build --sdist
    ;;
  all)
    python -m build
    ;;
  *)
    python -m build "$@"
    ;;
esac
