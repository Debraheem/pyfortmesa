# Profile Performance Plan

Goal: make pyfortmesa usable from ordinary Python code as a fast repeated-call
MESA EOS/KAP backend, including profile-style calls that can use OpenMP inside
Fortran.

This is an implementation tracking note. Keep it updated as the timing and code
path changes.

## Current Profile Path

Saved model:

```text
$MESA_DIR/star/test_suite/20M_pre_ms_to_core_collapse/standard_after_core_he_burn.mod
```

Python reader:

```text
tests/mesa/mesa_mod_profile_reader.py
tests/mesa/eos_from_saved_model.py
```

For each zone, the saved-model inputs are:

```text
T(k)   = exp(lnT(k))
Rho(k) = exp(lnd(k))
xa(:, k) = isotope mass fractions from the .mod zone table
```

EOS profile wrapper:

```text
src/pyfortmesa/fortran/EOS/mesa_eos_public.f90
  mesa_eos_profile_from_logs
    -> eosDT_get(..., Rho(k), lnd(k)*iln10, T(k), lnT(k)*iln10, ...)
```

KAP profile wrapper:

```text
src/pyfortmesa/fortran/KAP/mesa_kap_public.f90
  mesa_kap_profile_from_logs
    -> eosDT_get(...) for lnfree_e, eta, and derivatives
    -> kap_get(...)
```

KAP is not a pure `kap_get` timer because MESA KAP needs the electron-state
quantities returned by EOS:

```text
lnfree_e = res(i_lnfree_e)
eta      = res(i_eta)
```

## Timing Interpretation

The cold-cache first call is not representative steady-state performance.
Recent timing showed a first EOS profile call taking about 78 s because MESA
wrote EOS cache files. After caches exist, the remaining first profile call in a
fresh Python process is about 0.68--0.70 s for the 880-zone saved model. That is
table/handle setup and the first EOS/KAP call path, not the steady-state loop.

The timing breakdown should distinguish:

```text
parse_seconds                 -> Python saved-model text parsing
profile_array_seconds         -> building Fortran-order lnT/lnd/xa arrays
iso_id_seconds                -> isotope name -> MESA chem_id lookup
eos_profile_call_seconds      -> Fortran EOS batch call
kap_profile_call_seconds      -> Fortran KAP batch call, including required EOS state
output_collect_seconds        -> Python sample-output object construction
shutdown_seconds              -> MESA handle/table cleanup
```

The package performance target is repeated calls in one Python process. That
means benchmark repeats should keep handles alive and call `mesa.shutdown()`
once at the end rather than inside every timed profile evaluation.

## In-Scope Fixes Now

1. Done: add `--warmup N` and `--repeat N` to the profile timing script.
2. Done: keep MESA EOS/KAP handles alive across warmup/repeat calls.
3. Done: call `mesa.shutdown()` once at the end of the Python worker and report
   it separately.
4. Done: build profile arrays and isotope ids once per worker, outside timed
   repeated calls.
5. Done in source: add a combined EOS+KAP profile wrapper so `--physics eos-kap`
   does not call EOS twice.
6. Done in docs: add fast real-workflow examples that batch profile calls, use
   OpenMP threads, reuse isotope ids, and defer shutdown.
7. Done in tests: add `--timing-json`, `profile_timing_report.py`, and
   `run_eos_from_saved_model.sh --summary-suite` so one command runs EOS, KAP,
   combined EOS+KAP, the thread sweep, and prints compact timing tables.
8. Done in source: add direct `T`/`Rho` profile methods
   `Eos.dt_profile(...)`, `Kap.opacity_profile(...)`, and
   `Kap.eos_kap_profile(...)` for solver code that does not already store
   MESA-style `lnT`/`lnd` columns.
9. Done in tests: add `tests/mesa/run_profile_timing_suite.sh` as the short
   standard wrapper around the summary suite.
10. Done in tests: add repo-level `./test` and `./test mesa` entrypoints that
    store command logs, `test_summary.txt`, `tmp_golden_output.txt`, golden
    diffs, and timing output under `tests/test_output/`.
11. Done in tests: add committed no-MESA golden output at
    `tests/test_output/golden/quick_test_output.txt` and compare it explicitly
    in `./test`.
12. Kept unchanged: OpenMP schedule/chunk-size tuning.

## Combined EOS+KAP Wrapper

For `--physics eos-kap`, the faster path should do this in one Fortran loop:

```text
T(k)   = exp(lnT(k))
Rho(k) = exp(lnd(k))
call eosDT_get(..., res(:, k), dres_dlnRho, dres_dlnT, ...)
call kap_get(..., res(i_lnfree_e), res(i_eta), ...)
```

This avoids the current duplicated EOS work:

```text
mesa_eos_profile_from_logs(...)  -> EOS once
mesa_kap_profile_from_logs(...)  -> EOS again, then KAP
```

The expected output for combined profile timing is:

```text
eos_kap_profile_call_seconds
eos_calls = nzones
kap_calls = nzones
```

Implemented code references:

```text
src/pyfortmesa/fortran/KAP/mesa_kap_public.f90
  mesa_eos_kap_profile_from_logs

src/pyfortmesa/mesa.py
  eos_kap_profile
  eos_kap_profile_from_logs
  Kap.eos_kap_profile
  Kap.eos_kap_profile_from_logs

tests/mesa/eos_from_saved_model.py
  --warmup
  --repeat
  --physics eos-kap
```

For steady-state timing, prefer:

```bash
./test mesa
```

or run only the profile suite:

```bash
tests/mesa/run_profile_timing_suite.sh
```

The `eos_calls_per_second` and `kap_calls_per_second` values use only timed
profile-call seconds, not warmup, setup, output collection, or shutdown.

The expanded command is:

```bash
tests/mesa/run_eos_from_saved_model.sh --with-mesa --summary-suite --warmup 1 --repeat 5
```

For focused debugging, the individual commands are still available:

```bash
tests/mesa/run_eos_from_saved_model.sh --with-mesa --physics eos --warmup 1 --repeat 5
tests/mesa/run_eos_from_saved_model.sh --with-mesa --physics kap --warmup 1 --repeat 5
tests/mesa/run_eos_from_saved_model.sh --with-mesa --physics eos-kap --warmup 1 --repeat 5
tests/mesa/run_eos_from_saved_model.sh --with-mesa --thread-sweep --physics eos-kap --warmup 1 --repeat 5
```

## Latest Pasted Timing

Command set:

```bash
tests/mesa/run_eos_from_saved_model.sh --with-mesa --physics eos --warmup 1 --repeat 5
tests/mesa/run_eos_from_saved_model.sh --with-mesa --physics kap --warmup 1 --repeat 5
tests/mesa/run_eos_from_saved_model.sh --with-mesa --physics eos-kap --warmup 1 --repeat 5
tests/mesa/run_eos_from_saved_model.sh --with-mesa --thread-sweep --physics eos-kap --warmup 1 --repeat 5
```

The saved model had 880 zones. With `repeat = 5`, each timed row represents
4,400 EOS calls, 4,400 KAP calls, or both.

Single 10-thread runs:

| physics | warmup_profile_seconds | timed_profile_seconds | seconds/profile | calls/s | main interpretation |
| --- | ---: | ---: | ---: | ---: | --- |
| eos | 76.63513 | 0.01303229 | 0.002606 | 337,623 | cold EOS cache write dominated the warmup |
| kap | 0.7598785 | 0.01335925 | 0.002672 | 329,360 | KAP timing includes required EOS electron-state call |
| eos-kap | 0.6877732 | 0.01389958 | 0.002780 | 316,556 | combined wrapper avoids duplicate EOS work |

Combined EOS+KAP thread sweep:

| OMP_NUM_THREADS | timed_profile_seconds | seconds/profile | speedup vs 1 thread | parallel efficiency |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 0.09914125 | 0.019828 | 1.00 | 1.00 |
| 2 | 0.05113071 | 0.010226 | 1.94 | 0.97 |
| 4 | 0.02710088 | 0.005420 | 3.66 | 0.91 |
| 6 | 0.01854475 | 0.003709 | 5.35 | 0.89 |
| 8 | 0.01469637 | 0.002939 | 6.75 | 0.84 |
| 10 | 0.01371354 | 0.002743 | 7.23 | 0.72 |

Readout:

1. The steady-state Fortran profile loop is already scaling well for this
   880-zone profile. Ten OpenMP threads give about 7.2x speedup over one thread.
2. The biggest measured cost left in a fresh process is warmup/table setup, not
   the repeated profile loop. In a long-lived Python process or JAX-side caller,
   this should be paid once and then amortized.
3. `iso_id_seconds` is about 0.034--0.036 s per process in this run. That is
   small compared with cold table setup, but larger than a hot 10-thread profile
   call. Reusing isotope-id arrays in caller code is important for tiny repeated
   jobs.
4. Default `mesa.shutdown()` is normally about 0.0013 s here because
   `release_tables=False` frees wrapper handles without unloading tables. The
   one cold EOS run measured about 0.515 s at shutdown, but that is not a
   per-call cost and should not be inside a hot loop.

## Out of Scope For This Pass

1. OpenMP schedule/chunk-size tuning.
2. Pure `kap_get` microbenchmark with precomputed electron quantities.
3. Bigger synthetic model generation or JAX integration.
4. MESA table/cache policy changes inside MESA itself.
