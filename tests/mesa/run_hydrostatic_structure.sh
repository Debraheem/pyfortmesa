#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
caller_dir="$PWD"
test_file="tests/mesa/hydrostatic_structure.py"

cd "$repo_root"

echo "== syntax check"
python -m py_compile "$test_file"

echo "== safe default check"
PYTHONPATH=src python "$test_file"

if [[ "${1:-}" == "--with-mesa" ]]; then
  echo "== MESA-enabled integration check"
  export PYFORTMESA_CACHE_DIR="${PYFORTMESA_CACHE_DIR:-$caller_dir/.pyfortmesa_caches}"
  installed_location="$(
    python -c 'import pyfortmesa; print(pyfortmesa.__file__)' 2>/dev/null || true
  )"
  if ! python -c 'from pyfortmesa import mesa' >/dev/null 2>&1; then
    echo "pyfortmesa is installed, but this install does not export mesa."
    echo "current import location: ${installed_location:-not importable}"
    echo
    echo "Rebuild and reinstall the MESA-enabled wheel from the repo root:"
    echo "  ./mk mesa"
    echo "  ./install"
    exit 1
  fi
  if ! python -c 'import importlib; importlib.import_module("pyfortmesa._mesa_const"); importlib.import_module("pyfortmesa._mesa_chem"); importlib.import_module("pyfortmesa._mesa_eos"); importlib.import_module("pyfortmesa._mesa_kap")' >/dev/null 2>&1; then
    echo "pyfortmesa imports mesa, but the compiled MESA extensions are missing."
    echo "current import location: ${installed_location:-not importable}"
    echo
    echo "Rebuild and reinstall the MESA-enabled wheel from the repo root:"
    echo "  ./mk mesa"
    echo "  ./install"
    exit 1
  fi
  PYFORTMESA_WITH_MESA=1 python "$test_file"
else
  echo "skipped MESA-enabled run: pass --with-mesa to call CHEM/EOS/KAP"
fi
