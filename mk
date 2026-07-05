#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$repo_root"

mode="${1:-wheel}"

case "$mode" in
  wheel)
    python -m build --wheel
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
