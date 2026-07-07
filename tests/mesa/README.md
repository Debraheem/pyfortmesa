# MESA Test Scripts

These scripts are optional MESA checks, not the simplest usage
examples. They require pyfortmesa installed with `./mk mesa` and a valid
`MESA_DIR`.

Unit checks that do not call MESA live under `tests/unit/`. Timing and integration
scripts live here because they depend on MESA data, MESA tables, OpenMP, and
local machine performance. For the smallest copyable usage example, see
`tests/work/README.md`.

From the repository root, use the normal test entrypoint after installing the
matching package:

```bash
./test
./test mesa
```

`./test` runs the checks that do not call MESA and stores command logs under
`tests/test_output/`. `./test mesa` runs those checks first, then the MESA
runners in this directory, including the profile timing suite below.

## Profile Timing Suite

Run the standard saved model eos/kap timing report with:

```bash
tests/mesa/run_profile_timing_suite.sh
```

This is a short wrapper around:

```bash
tests/mesa/run_eos_from_saved_model.sh --with-mesa --summary-suite --warmup 1 --repeat 5
```

The suite runs:

```text
eos single run
kap single run
combined eos+kap single run
combined eos+kap OpenMP thread sweep
```

It prints compact timing tables. Raw per-run logs plus timing JSON files are
temporary by default; set `PYFORTMESA_PROFILE_REPORT_DIR` to keep them.
High-level pyfortmesa public calls are timed by the package timing collector;
the runner only adds saved-model parsing, array setup, output collection, and
sweep orchestration.

## Scalar/Profile Comparison

Run the scalar raw loop versus profile wrapper comparison with:

```bash
tests/mesa/run_scalar_profile_timing_compare.sh
```

This uses the same saved-model `T/Rho` arrays for both paths and runs two
composition cases:

```text
fixed_3  -> h1/he4/c12 = 0.70/0.28/0.02 at every zone
saved_22 -> the saved model's 22-isotope composition at each zone
```

The three physics rows are EOS-only, KAP-only, and fused EOS+KAP. The scalar
`eos-kap` row uses `Kap.eos_kap_raw(...)`, while the profile row uses
`Kap.eos_kap_profile(...)`.

By default it runs `OMP_NUM_THREADS=1` and `10`. Override with:

```bash
PYFORTMESA_COMPARE_THREAD_COUNTS="1 2 4 8" \
  tests/mesa/run_scalar_profile_timing_compare.sh
```

## Overrides

`run_profile_timing_suite.sh` has two convenience overrides:

```bash
PYFORTMESA_PROFILE_WARMUP=2 tests/mesa/run_profile_timing_suite.sh
PYFORTMESA_PROFILE_REPEAT=10 tests/mesa/run_profile_timing_suite.sh
```

They only change the wrapper defaults:

```text
PYFORTMESA_PROFILE_WARMUP -> --warmup, default 1
PYFORTMESA_PROFILE_REPEAT -> --repeat, default 5
```

Other useful controls are forwarded to `run_eos_from_saved_model.sh`:

```bash
tests/mesa/run_profile_timing_suite.sh --thread-sweep=1,2,4,8
PYFORTMESA_THREAD_COUNTS="1 3 6 12" tests/mesa/run_profile_timing_suite.sh
PYFORTMESA_SUMMARY_THREADS=8 tests/mesa/run_profile_timing_suite.sh
PYFORTMESA_PROFILE_REPORT_DIR=tests/test_output/custom_profile \
  tests/mesa/run_profile_timing_suite.sh
```

Meanings:

```text
--thread-sweep=...             -> explicit OpenMP thread counts for the sweep
PYFORTMESA_THREAD_COUNTS       -> default sweep counts if --thread-sweep is absent
PYFORTMESA_SUMMARY_THREADS     -> thread count for the eos/kap/eos+kap single runs
OMP_NUM_THREADS                -> fallback single run thread count
PYFORTMESA_PROFILE_REPORT_DIR  -> directory for raw logs and JSON timing files;
                                  unset means use a temporary directory
```

If neither `PYFORTMESA_SUMMARY_THREADS` nor `OMP_NUM_THREADS` is set, the
single run thread count defaults to the largest sweep count.

Do not combine the summary suite with `--physics`, `--parallel`, `--nproc`, or
`--parse-only`; the suite chooses physics modes itself and uses OpenMP thread
parallelism.

## Focused Commands

For focused debugging, use the lower-level runner directly:

```bash
tests/mesa/run_eos_from_saved_model.sh --with-mesa --physics eos --warmup 1 --repeat 5
tests/mesa/run_eos_from_saved_model.sh --with-mesa --physics kap --warmup 1 --repeat 5
tests/mesa/run_eos_from_saved_model.sh --with-mesa --physics eos-kap --warmup 1 --repeat 5
tests/mesa/run_eos_from_saved_model.sh --with-mesa --thread-sweep \
  --physics eos-kap --warmup 1 --repeat 5
```

kap timings include the eos electron state call required by `kap_get`. The
`eos-kap` timing uses the combined wrapper, so eos is evaluated once per zone
and then feeds kap.
