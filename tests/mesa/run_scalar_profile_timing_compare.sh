#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

: "${MESA_DIR:?Set MESA_DIR to a supported MESA tree first.}"

thread_counts="${PYFORTMESA_COMPARE_THREAD_COUNTS:-1 10}"

for omp_threads in $thread_counts; do
  echo "== scalar/profile comparison OMP_NUM_THREADS=$omp_threads"
  OMP_NUM_THREADS="$omp_threads" \
    env -u PYTHONPATH \
    python tests/mesa/scalar_profile_timing_compare.py "$@"
done
