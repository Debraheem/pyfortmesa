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

if [[ "${1:-}" != "--with-mesa" ]]; then
  echo "skipped MESA run: pass --with-mesa to call eos/kap"
  exit 0
fi

: "${MESA_DIR:?Set MESA_DIR to a supported MESA tree first.}"
export PYFORTMESA_CACHE_DIR="${PYFORTMESA_CACHE_DIR:-$caller_dir/.pyfortmesa_caches}"

echo "== MESA integration check"
PYFORTMESA_WITH_MESA=1 python "$test_file"
