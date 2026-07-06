# pyfortmesa usage

This page shows how to call the package from Python. Build and packaging
commands live in the top-level `README.md`.

## Small Fortran Example

After installing the normal wheel or editable package:

```python
from pyfortmesa import big_sum_fortran, small_calc_fortran

x = 4.0
n = 1000

print(f"small_calc_fortran({x}) = {small_calc_fortran(x)}")
print(f"big_sum_fortran({n}) = {big_sum_fortran(n)}")
```

Expected output:

```text
small_calc_fortran(4.0) = 50.0
big_sum_fortran(1000) = 250250.0
```

## MESA Example

First build and install the MESA-enabled wheel:

```bash
python -m pip install --upgrade build meson-python meson ninja numpy twine
export MESASDK_ROOT=/Applications/mesasdk
source $MESASDK_ROOT/bin/mesasdk_init.sh
export MESA_DIR=/Users/owner/Documents/Software/dev/mesa_release/mesa_clean/main
./mk mesa
./install
```

Then another Python script can call MESA constants, CHEM, EOS, and KAP through
`pyfortmesa`:

```python
from pyfortmesa import mesa

mesa.set_cache_root(".")

# Path A: read one MESA-style file with both &eos and &kap namelists.
mesa.set_inlist("inlist_eos_and_kap")

# Inputs: MESA isotope names mapped to mass fractions. They must sum to 1.
mix = mesa.composition({"h1": 0.70, "he4": 0.28, "c12": 0.02})

# Inputs: temperature in K and density in g/cm^3.
T_eos = 1.0e7
rho_eos = 1.0e2
T_kap = 1.0e6
rho_kap = 1.0e-7

constants = mesa.constants()
chem_output = mesa.Chem().composition_info(mix)
eos = mesa.Eos()
kap = mesa.Kap()

# Path B: Python overrides can be used instead of, or on top of, the inlist.
kap_type2 = mesa.Kap(use_type2=True, zbase=0.02)

eos_output = eos.dt_full(T=T_eos, Rho=rho_eos, comp=mix)
rho_solve = eos.solve_rho(
    T=T_eos,
    other="lnPgas",
    other_value=eos_output["results"]["lnPgas"],
    Rho_guess=0.8 * rho_eos,
    comp=mix,
)
kap_output = kap.opacity_full(T=T_kap, Rho=rho_kap, comp=mix)
kap_type2_output = kap_type2.opacity_full(T=T_kap, Rho=rho_kap, comp=mix)

print("MESA const_def values:", constants)
print("CHEM output:", chem_output)
print("EOS output:", eos_output["results"])
print("EOS solve_rho output:", rho_solve["Rho"])
print("KAP output:", kap_output)
print("KAP Type2 fractions:", kap_type2_output["kap_fracs"])

mesa.shutdown()
```

Useful output fields:

```text
mesa.constants()
  standard_cgrav, crad, clight, Lsun, Rsun, Msun

mesa.Chem().composition_info(...)
  xh, xhe, xz, abar, zbar, z2bar, z53bar, ye, mass_correction, sumx

mesa.Eos().dt_full(...)
  results, d_dlnRho, d_dlnT, d_dxa

mesa.Eos().solve_rho(...)
  Rho, logRho, eos_calls, results, d_dlnRho, d_dlnT, d_dxa

mesa.Eos().solve_t(...)
  T, logT, eos_calls, results, d_dlnRho, d_dlnT, d_dxa

mesa.Kap().opacity_full(...)
  kappa, dlnkap_dlnRho, dlnkap_dlnT, kap_fracs, dlnkap_dxa

mesa.Kap(use_type2=True, zbase=...)
  enables MESA Type2 opacity controls for that Python object
```

## Fast Profile Workflow

For real workflows that need EOS/KAP across many zones, do not call scalar EOS
or KAP once per zone from Python. Batch the profile and let the Fortran wrapper
parallelize the zone loop with OpenMP.

Set the OpenMP thread count before launching Python:

```bash
export OMP_NUM_THREADS=10
python run_microphysics.py
```

Use a long-lived Python process and keep setup out of the hot loop:

```python
import numpy as np

from pyfortmesa import mesa

mesa.set_cache_root(".")
mesa.set_inlist("inlist_eos_and_kap")

isotope_names = ("h1", "he4", "c12")
chem_id = mesa.iso_ids(isotope_names)
kap = mesa.Kap()


def profile_xa(xa_by_zone):
    """Convert solver mass fractions to the profile wrapper layout.

    xa_by_zone has shape (nzones, species). The profile wrappers expect
    xa with shape (species, nzones).
    """
    return np.asfortranarray(np.asarray(xa_by_zone, dtype=np.float64).T)


try:
    # `model_profiles` is supplied by the caller's solver. Each item is one
    # model/profile with T, rho, and xa arrays.
    first_T, first_rho, first_xa_by_zone = model_profiles[0]

    # Optional warmup: pays table/cache/handle setup before timing a loop.
    kap.eos_kap_profile(first_T, first_rho, chem_id, profile_xa(first_xa_by_zone))

    for T, rho, xa_by_zone in model_profiles:
        xa = profile_xa(xa_by_zone)

        # Combined EOS+KAP: one EOS call per zone, then KAP uses that state.
        output = kap.eos_kap_profile(T, rho, chem_id, xa)

        lnPgas = output["results"]["lnPgas"]
        gamma1 = output["results"]["gamma1"]
        kappa = output["kappa"]
finally:
    mesa.shutdown()
```

Use `mesa.Eos().dt_profile(...)` when only EOS is needed. Use
`mesa.Kap().opacity_profile(...)` when only opacity is needed; that path still
calls EOS internally for `lnfree_e`, `eta`, and derivatives required by
`kap_get`. When both EOS and KAP are needed for the same zones,
`mesa.Kap().eos_kap_profile(...)` is the preferred path because it avoids
computing EOS twice. The lower-level `*_from_logs(...)` variants remain
available when the caller already has MESA-style `lnT` and `lnd` columns.

The main performance lesson is lifecycle amortization. The first call may
initialize tables and create MESA cache files. That work can be much more
expensive than a hot profile call, so a solver should set cache/inlist controls
once, reuse isotope ids, batch zones, keep the process alive, and call
`mesa.shutdown()` only when it is done with MESA.

MESA EOS logarithmic result values such as `lnPgas` are natural logs. If you
solve from a target gas pressure, pass `math.log(Pgas)`.

Control precedence:

```text
MESA defaults
  -> optional shared inlist from mesa.set_inlist("inlist_eos_and_kap")
  -> optional Python KAP overrides from mesa.Kap(...)
```

Call `mesa.set_inlist(...)` before the first EOS or KAP call in the Python
process. Passing `None` clears the environment variable for future handle
creation:

```python
mesa.set_inlist(None)
```

## Shutdown

`mesa.shutdown()` frees the persistent EOS/KAP handles owned by pyfortmesa and
resets the wrapper state:

```python
try:
    eos_output = mesa.Eos().dt(T=T_eos, Rho=rho_eos, comp=mix)
    kap_output = mesa.Kap().opacity(T=T_kap, Rho=rho_kap, comp=mix)
finally:
    mesa.shutdown()
```

That is the normal cleanup path. It does not unload all MESA table data because
keeping the tables available is useful for repeated calls in the same Python
process.

For a long-lived notebook or service, use the heavier path only when no other
code in the process is using MESA:

```python
mesa.shutdown(release_tables=True)
```

That also calls the MESA KAP, EOS, and CHEM shutdown routines for loaded table
state.

## Module Coverage

The per-module coverage pages list what is available now and what is still
missing:

```text
docs/modules/README.md
docs/modules/CONST.md
docs/modules/CHEM.md
docs/modules/EOS.md
docs/modules/KAP.md
docs/modules/NET.md
docs/modules/TURB.md
```

## Example Scripts

Run the print-based examples after installing the matching build:

```bash
conda activate pyfortmesa
export MESA_DIR=/Users/owner/Documents/Software/dev/mesa_release/mesa_clean/main
./test
./test mesa
tests/mesa/run_eos_kap_arbitrary_composition.sh --with-mesa
tests/mesa/run_hydrostatic_structure.sh --with-mesa
tests/mesa/run_eos_from_saved_model.sh --with-mesa
OMP_NUM_THREADS=10 tests/mesa/run_eos_from_saved_model.sh --with-mesa
tests/mesa/run_profile_timing_suite.sh
tests/mesa/run_eos_from_saved_model.sh --with-mesa --thread-sweep
tests/mesa/run_eos_from_saved_model.sh --with-mesa --thread-sweep --physics eos-kap
```

`./test` is the normal no-MESA test entrypoint. `./test mesa` adds the optional
MESA-backed checks and the saved-model timing suite. Both modes store raw test
output under `tests/test_output/`, including `test_summary.txt`,
`tmp_golden_output.txt`, and `golden_compare.log`; set
`PYFORTMESA_TEST_OUTPUT_DIR` to choose a different output directory. The
committed no-MESA golden baseline is
`tests/test_output/golden/quick_test_output.txt`. The MESA scripts print input
and output data. They are examples and integration checks, not MESA star models.

`run_eos_from_saved_model.sh` reads:

```text
$MESA_DIR/star/test_suite/20M_pre_ms_to_core_collapse/standard_after_core_he_burn.mod
```

It passes `lnT`, `lnd`, isotope ids, and mass-fraction arrays to Fortran batch
wrappers. The default `--physics eos` path reconstructs `T = exp(lnT)` and
`rho = exp(lnd)` inside the EOS loop, then calls `eosDT_get` once per zone using
that zone's own `xa(:, k)` profile composition. The `--physics kap` path calls a
KAP profile wrapper; that wrapper calls EOS internally for the electron
quantities required by `kap_get`, then calls `kap_get` once per zone. The zone
loops are OpenMP-parallel inside Fortran, so the preferred threaded timing run
sets `OMP_NUM_THREADS` before launching the runner:

```bash
OMP_NUM_THREADS=10 tests/mesa/run_eos_from_saved_model.sh --with-mesa
```

The output field `nproc` is the number of Python processes, not the number of
OpenMP threads. For the standard OpenMP thread sweep, leave `--nproc` off and
use `--thread-sweep`. The default thread counts are `1 2 4 6 8 10`:

```bash
tests/mesa/run_eos_from_saved_model.sh --with-mesa --thread-sweep
tests/mesa/run_eos_from_saved_model.sh --with-mesa --thread-sweep=1,2,4,8
PYFORTMESA_THREAD_COUNTS="1 3 6 12" tests/mesa/run_eos_from_saved_model.sh --with-mesa --thread-sweep
```

To time both profile paths in the same thread sweep:

```bash
tests/mesa/run_eos_from_saved_model.sh --with-mesa --thread-sweep --physics eos-kap
```

The timing breakdown separates Python profile-array setup, isotope-id lookup,
the EOS profile call, the KAP profile call, output collection, and shutdown.
The KAP profile call includes its required internal EOS call; it is not a pure
`kap_get`-only timer. The `--physics eos-kap` path uses a combined Fortran
wrapper so EOS is evaluated once per zone and the same EOS result feeds KAP.

For steady-state timings, keep MESA handles alive across repeated calls in one
Python process:

```bash
tests/mesa/run_eos_from_saved_model.sh --with-mesa --physics eos --warmup 1 --repeat 5
tests/mesa/run_eos_from_saved_model.sh --with-mesa --physics kap --warmup 1 --repeat 5
tests/mesa/run_eos_from_saved_model.sh --with-mesa --physics eos-kap --warmup 1 --repeat 5
tests/mesa/run_eos_from_saved_model.sh --with-mesa --thread-sweep --physics eos-kap --warmup 1 --repeat 5
```

For the standard report, use one command:

```bash
tests/mesa/run_profile_timing_suite.sh
```

That suite runs EOS, KAP, combined EOS+KAP, and the combined EOS+KAP thread
sweep, then prints compact single-run, global-breakdown, and thread-sweep
tables. It also writes the raw logs and timing JSON files under local
`tests/test_output/` for inspection. The wrapper defaults to `warmup=1` and `repeat=5`; override those with
`PYFORTMESA_PROFILE_WARMUP` and `PYFORTMESA_PROFILE_REPEAT`. The single-run
thread count is chosen from `PYFORTMESA_SUMMARY_THREADS`, then `OMP_NUM_THREADS`,
then the largest sweep count.

The equivalent expanded command is:

```bash
tests/mesa/run_eos_from_saved_model.sh --with-mesa --summary-suite --warmup 1 --repeat 5
```

The call-rate fields use only timed profile-call seconds. Warmup, array setup,
output collection, and shutdown are reported separately.

The script also supports `--nproc`, but that uses separate Python processes.
Do not combine process parallelism with `--thread-sweep`; the runner rejects
that combination to avoid mixing process and thread parallelism.

The script prints parse time, profile wall time, call counts, calls per second,
phase-level timing, Fortran reconstruction checks, and first/middle/last sample
outputs. Its `.mod` comparison checks the saved-model inputs: zone count,
species count, round-trip `lnT/lnd`, and mass-fraction sums. That `.mod` file
does not contain EOS result columns such as `lnPgas` or `gamma1`.
