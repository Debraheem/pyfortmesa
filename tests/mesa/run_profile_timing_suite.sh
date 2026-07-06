#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

warmup="${PYFORTMESA_PROFILE_WARMUP:-1}"
repeat="${PYFORTMESA_PROFILE_REPEAT:-5}"

exec tests/mesa/run_eos_from_saved_model.sh \
  --with-mesa \
  --summary-suite \
  --warmup "$warmup" \
  --repeat "$repeat" \
  "$@"
