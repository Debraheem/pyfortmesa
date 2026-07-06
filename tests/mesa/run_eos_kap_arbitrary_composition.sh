#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
caller_dir="$PWD"
test_file="tests/mesa/eos_kap_arbitrary_composition.py"

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
  if ! python -c 'import importlib; importlib.import_module("pyfortmesa._mesa_eos"); importlib.import_module("pyfortmesa._mesa_kap")' >/dev/null 2>&1; then
    echo "pyfortmesa imports mesa, but the compiled EOS/KAP extensions are missing."
    echo "current import location: ${installed_location:-not importable}"
    echo
    echo "Rebuild and reinstall the MESA-enabled wheel from the repo root:"
    echo "  ./mk mesa"
    echo "  ./install"
    exit 1
  fi
if ! python -c '
import importlib

eos = importlib.import_module("pyfortmesa._mesa_eos")
kap = importlib.import_module("pyfortmesa._mesa_kap")
if not hasattr(eos, "mesa_eos_composition_full"):
    raise SystemExit(1)
if not hasattr(kap, "mesa_kap_composition_full"):
    raise SystemExit(1)
' >/dev/null 2>&1; then
    echo "pyfortmesa has old EOS/KAP extensions without the full-output symbols."
    echo "current import location: ${installed_location:-not importable}"
    echo
    echo "Rebuild and reinstall the MESA-enabled wheel from the repo root:"
    echo "  ./mk mesa"
    echo "  ./install"
    exit 1
  fi
  PYFORTMESA_WITH_MESA=1 python "$test_file"
else
  echo "skipped MESA-enabled run: pass --with-mesa to call EOS/KAP"
fi
