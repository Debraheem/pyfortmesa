#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
caller_dir="$PWD"
test_file="tests/mesa/eos_from_saved_model.py"
reader_file="tests/mesa/mesa_mod_profile_reader.py"
report_file="tests/mesa/profile_timing_report.py"

with_mesa=0
has_model_arg=0
summary_suite=0
thread_sweep=0
thread_counts="${PYFORTMESA_THREAD_COUNTS:-1 2 4 6 8 10}"
uses_process_parallel=0
uses_parse_only=0
uses_physics_arg=0
uses_kap=0
script_args=()

# Split wrapper options from the Python worker options.
for arg in "$@"; do
  case "$arg" in
    --with-mesa)
      with_mesa=1
      ;;
    --summary-suite)
      summary_suite=1
      uses_kap=1
      ;;
    --thread-sweep)
      thread_sweep=1
      ;;
    --thread-sweep=*)
      thread_sweep=1
      thread_counts="${arg#--thread-sweep=}"
      ;;
    --parallel)
      uses_process_parallel=1
      script_args+=(--nproc "${PYFORTMESA_NPROC:-10}")
      ;;
    --parse-only)
      uses_parse_only=1
      script_args+=("$arg")
      ;;
    --physics)
      uses_physics_arg=1
      script_args+=("$arg")
      ;;
    --physics=*)
      uses_physics_arg=1
      case "${arg#--physics=}" in
        kap|eos-kap)
          uses_kap=1
          ;;
      esac
      script_args+=("$arg")
      ;;
    --model|--model=*)
      has_model_arg=1
      script_args+=("$arg")
      ;;
    --nproc|--nproc=*)
      uses_process_parallel=1
      script_args+=("$arg")
      ;;
    *)
      script_args+=("$arg")
      ;;
  esac
done

thread_counts="${thread_counts//,/ }"
# shellcheck disable=SC2206
thread_count_args=($thread_counts)

if [[ "$thread_sweep" == 1 && "$uses_process_parallel" == 1 ]]; then
  echo "error: --thread-sweep uses OpenMP threads; do not combine it with --parallel or --nproc"
  exit 2
fi

if [[ "$summary_suite" == 1 && "$uses_process_parallel" == 1 ]]; then
  echo "error: --summary-suite uses OpenMP threads; do not combine it with --parallel or --nproc"
  exit 2
fi

if [[ "$summary_suite" == 1 && "$uses_physics_arg" == 1 ]]; then
  echo "error: --summary-suite chooses physics=eos,kap,eos-kap itself; do not pass --physics"
  exit 2
fi

if [[ "$summary_suite" == 1 && "$uses_parse_only" == 1 ]]; then
  echo "error: --summary-suite needs MESA timing output; do not pass --parse-only"
  exit 2
fi

if [[ "$thread_sweep" == 1 && "${#thread_count_args[@]}" == 0 ]]; then
  echo "error: --thread-sweep needs at least one thread count"
  exit 2
fi

if [[ "$thread_sweep" == 1 || "$summary_suite" == 1 ]]; then
  for nthreads in "${thread_count_args[@]}"; do
    if [[ ! "$nthreads" =~ ^[1-9][0-9]*$ ]]; then
      echo "error: invalid OpenMP thread count '$nthreads'"
      exit 2
    fi
  done
fi

if (( ${#script_args[@]} > 0 )); then
  for ((i = 0; i < ${#script_args[@]}; i++)); do
    if [[ "${script_args[$i]}" == "--physics" ]]; then
      next_index=$((i + 1))
      if (( next_index < ${#script_args[@]} )); then
        case "${script_args[$next_index]}" in
          kap|eos-kap)
            uses_kap=1
            ;;
        esac
      fi
    fi
  done
fi

cd "$repo_root"

echo "== syntax check"
python -m py_compile "$reader_file" "$test_file" "$report_file"

echo "== saved-model parse check"
if [[ -n "${MESA_DIR:-}" || "$has_model_arg" == 1 ]]; then
  if (( ${#script_args[@]} > 0 )); then
    PYTHONPATH=src python "$test_file" --parse-only "${script_args[@]}"
  else
    PYTHONPATH=src python "$test_file" --parse-only
  fi
else
  echo "skipped parse check: MESA_DIR is not set; pass --model or export MESA_DIR"
fi

# From this point on, --with-mesa means real compiled MESA calls.
if [[ "$with_mesa" == 1 ]]; then
  export PYFORTMESA_CACHE_DIR="${PYFORTMESA_CACHE_DIR:-$caller_dir/.pyfortmesa_caches}"
  installed_location="$(
    python -c 'import pyfortmesa; print(pyfortmesa.__file__)' 2>/dev/null || true
  )"
  if ! import_check="$(python -c 'from pyfortmesa import mesa' 2>&1)"; then
    echo "pyfortmesa is installed, but this install does not export mesa."
    echo "current import location: ${installed_location:-not importable}"
    echo "import error:"
    echo "$import_check"
    echo
    echo "Run `./mk mesa` and install from the repo root:"
    echo "  ./mk mesa"
    echo "  ./install"
    exit 1
  fi
  if ! extension_check="$(python -c '
import importlib

eos = importlib.import_module("pyfortmesa._mesa_eos")
if not hasattr(eos, "mesa_eos_composition_full"):
    raise SystemExit(1)
if not hasattr(eos, "mesa_eos_profile_from_logs"):
    raise SystemExit(1)
if not hasattr(eos, "mesa_eos_shutdown"):
    raise SystemExit(1)
' 2>&1)"; then
    echo "pyfortmesa imports mesa, but the compiled EOS extension is missing or old."
    echo "current import location: ${installed_location:-not importable}"
    echo "extension error:"
    echo "$extension_check"
    echo
    echo "Run `./mk mesa` and install from the repo root:"
    echo "  ./mk mesa"
    echo "  ./install"
    exit 1
  fi
  if [[ "$uses_kap" == 1 ]]; then
    if ! kap_extension_check="$(python -c '
import importlib

kap = importlib.import_module("pyfortmesa._mesa_kap")
if not hasattr(kap, "mesa_kap_profile_from_logs"):
    raise SystemExit(1)
if not hasattr(kap, "mesa_eos_kap_profile_from_logs"):
    raise SystemExit(1)
' 2>&1)"; then
      echo "pyfortmesa imports mesa, but the compiled KAP extension is missing the profile wrapper."
      echo "current import location: ${installed_location:-not importable}"
      echo "extension error:"
      echo "$kap_extension_check"
      echo
      echo "Run `./mk mesa` and install from the repo root:"
      echo "  ./mk mesa"
      echo "  ./install"
      exit 1
    fi
  fi

  # Run one profile job, optionally pinning OMP_NUM_THREADS.
  run_profile_check() {
    if (( $# == 1 )); then
      echo "== MESA EOS profile check (OMP_NUM_THREADS=$1)"
      if (( ${#script_args[@]} > 0 )); then
        OMP_NUM_THREADS="$1" PYFORTMESA_WITH_MESA=1 python "$test_file" "${script_args[@]}"
      else
        OMP_NUM_THREADS="$1" PYFORTMESA_WITH_MESA=1 python "$test_file"
      fi
      return
    fi

    echo "== MESA EOS profile check (OMP_NUM_THREADS=${OMP_NUM_THREADS:-unset})"
    if (( ${#script_args[@]} > 0 )); then
      PYFORTMESA_WITH_MESA=1 python "$test_file" "${script_args[@]}"
    else
      PYFORTMESA_WITH_MESA=1 python "$test_file"
    fi
  }

  # Write temporary timing JSON files, then print one compact report.
  run_profile_summary_suite() {
    local keep_reports=0
    local report_dir
    local summary_threads
    local last_index
    local -a single_json_args=()
    local -a sweep_json_args=()
    if [[ -n "${PYFORTMESA_PROFILE_REPORT_DIR:-}" ]]; then
      report_dir="$PYFORTMESA_PROFILE_REPORT_DIR"
      keep_reports=1
    else
      report_dir="$(mktemp -d "${TMPDIR:-/tmp}/pyfortmesa-profile.XXXXXX")"
    fi
    mkdir -p "$report_dir"

    summary_threads="${PYFORTMESA_SUMMARY_THREADS:-${OMP_NUM_THREADS:-}}"
    if [[ -z "$summary_threads" ]]; then
      last_index=$((${#thread_count_args[@]} - 1))
      summary_threads="${thread_count_args[$last_index]}"
    fi
    if [[ ! "$summary_threads" =~ ^[1-9][0-9]*$ ]]; then
      echo "error: invalid summary OpenMP thread count '$summary_threads'"
      exit 2
    fi

    run_suite_case() {
      local kind="$1"
      local physics="$2"
      local nthreads="$3"
      local label="$4"
      local json_path="$report_dir/${label}.json"
      local log_path="$report_dir/${label}.log"

      echo "== profile timing suite: physics=$physics OMP_NUM_THREADS=$nthreads"
      if OMP_NUM_THREADS="$nthreads" PYFORTMESA_WITH_MESA=1 \
          python "$test_file" "${script_args[@]}" \
          --physics "$physics" --timing-json "$json_path" > "$log_path"; then
        echo "   log: $log_path"
      else
        cat "$log_path"
        exit 1
      fi

      if [[ "$kind" == "single" ]]; then
        single_json_args+=(--single "$json_path")
      else
        sweep_json_args+=(--sweep "$json_path")
      fi
    }

    run_suite_case single eos "$summary_threads" "single_eos_omp${summary_threads}"
    run_suite_case single kap "$summary_threads" "single_kap_omp${summary_threads}"
    run_suite_case single eos-kap "$summary_threads" "single_eos_kap_omp${summary_threads}"

    for nthreads in "${thread_count_args[@]}"; do
      run_suite_case sweep eos-kap "$nthreads" "sweep_eos_kap_omp${nthreads}"
    done

    python "$report_file" "${single_json_args[@]}" "${sweep_json_args[@]}"
    if [[ "$keep_reports" == 1 ]]; then
      echo "raw timing logs: $report_dir"
    else
      rm -rf "$report_dir"
      echo "raw timing logs discarded; set PYFORTMESA_PROFILE_REPORT_DIR to keep them"
    fi
  }

  if [[ "$summary_suite" == 1 ]]; then
    run_profile_summary_suite
  elif [[ "$thread_sweep" == 1 ]]; then
    for nthreads in "${thread_count_args[@]}"; do
      run_profile_check "$nthreads"
    done
  else
    run_profile_check
  fi
else
  echo "skipped MESA run: pass --with-mesa to call EOS"
fi
