#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

: "${MESA_DIR:?Set MESA_DIR to a supported MESA tree first.}"
PYFORTMESA_WITH_MESA=1 python tests/work/simple_chem_eos_kap.py
