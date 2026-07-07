# pyfortmesa usage

This page shows how to call the package from Python. Build and packaging
commands live in [Installation](installation.md) and [Developing](developing.md).

The MESA interface is narrow by design. It wraps selected `const`, `chem`,
`eos`, and `kap` calls for code that needs repeated eos/kap evaluations. It is
not a general MESA module reader; use [pyMesa](https://github.com/rjfarmer/pyMesa)
for that.

## MESA example

Real MESA eos/kap calls require the `./mk mesa` build for the shared
libraries in your `MESA_DIR`. Build and install that package first; the normal
commands are in [Installation](installation.md#mesa-wrapper-install).

Then a Python script can call MESA `const`, `chem`, `eos`, and `kap` wrappers
through `pyfortmesa`:

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
print("chem output:", chem_output)
print("eos output:", eos_output["results"])
print("eos solve_rho output:", rho_solve["Rho"])
print("kap output:", kap_output)
print("kap Type2 fractions:", kap_type2_output["kap_fracs"])

mesa.shutdown()
```

`mix` is a scalar-call composition object. It stores the isotope names, matching
MESA `chem_id` values, and one mass-fraction vector. Scalar helpers accept it as
`comp=mix`.

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

mesa.Eos().solve_rho_profile(...), mesa.Eos().solve_t_profile(...)
  profile arrays; results has shape (n_eos_results, nzones)

mesa.Kap().opacity_full(...)
  kappa, dlnkap_dlnRho, dlnkap_dlnT, kap_fracs, dlnkap_dxa

mesa.Kap(use_type2=True, zbase=...)
  enables MESA Type2 opacity controls for that Python object
```

## Profile calls

For profile work, do not call scalar eos or kap once per zone from Python.
Batch the profile and let the Fortran wrapper parallelize the zone loop with
OpenMP.

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
chem_id_values = mesa.iso_ids(isotope_names)
kap = mesa.Kap()
i_lnPgas = mesa.EOS_RESULT_NAMES.index("lnPgas")
i_gamma1 = mesa.EOS_RESULT_NAMES.index("gamma1")


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
    kap.eos_kap_profile(first_T, first_rho, chem_id_values, profile_xa(first_xa_by_zone))

    for T, rho, xa_by_zone in model_profiles:
        xa = profile_xa(xa_by_zone)

        # combined eos+kap: one eos call per zone, then kap uses that state.
        output = kap.eos_kap_profile(T, rho, chem_id_values, xa)

        lnPgas = output["results"][i_lnPgas, :]
        gamma1 = output["results"][i_gamma1, :]
        kappa = output["kappa"]
finally:
    mesa.shutdown()
```

Profile helpers take the composition in split form: `chem_id_values` gives the
isotope order, and `xa` gives either one fixed composition with shape
`(species,)` or zone mass fractions with shape `(species, nzones)`.

For a fixed-composition EOS profile on an arbitrary base-10 `logT`/`logRho`
track, build one `Composition` and pass its 1D `xa` vector. Use
`input_mode="log10"` when the arrays are base-10 logs:

```python
log_rho = np.linspace(-2.0, 8.0, 1000)
log_T = np.linspace(3.0, 8.0, 1000)

mix = mesa.composition({"h1": 0.70, "he4": 0.28, "c12": 0.02})

output = mesa.Eos().dt_profile(log_T, log_rho, mix.chem_id, mix.xa, input_mode="log10")
```

For KAP profile work, choose points in a valid opacity-table region. A common
base-10 coordinate is `logR = logRho - 3*logT + 18`:

```python
log_T = np.linspace(3.75, 8.0, 1000)
log_R = np.full_like(log_T, -3.0)
log_rho = log_R + 3.0*log_T - 18.0

T = 10.0**log_T
rho = 10.0**log_rho

output = mesa.Kap().eos_kap_profile(T, rho, mix.chem_id, mix.xa)
```

Use `input_mode="log"` for natural-log arrays and `input_mode="log10"` for
base-10 arrays. The older `*_from_logs(...)` helpers are compatibility aliases
for natural-log input.

Use `mesa.Eos().dt_profile(...)` when only eos is needed. Use
`mesa.Kap().opacity_profile(...)` when only opacity is needed; that path still
calls eos internally for `lnfree_e`, `eta`, and derivatives required by
`kap_get`. When both eos and kap are needed for the same zones,
`mesa.Kap().eos_kap_profile(...)` is the preferred path because it avoids
computing eos twice. The lower-level `*_from_logs(...)` variants remain
available as compatibility aliases for MESA-style `lnT` and `lnd` columns.

Keep MESA setup out of the hot loop. The first call may initialize tables and
create cache files. That work can be much more expensive than a hot profile
call, so set cache/inlist controls once, reuse isotope ids, batch zones, keep
the process alive, and call `mesa.shutdown()` only when the driver is done with
MESA.

MESA eos logarithmic result values such as `lnPgas` are natural logs. If you
solve from a target gas pressure, pass `math.log(Pgas)`.

Control precedence:

```text
MESA defaults
  -> optional shared inlist from mesa.set_inlist("inlist_eos_and_kap")
  -> optional Python kap overrides from mesa.Kap(...)
```

Call `mesa.set_inlist(...)` before the first eos or kap call in the Python
process. Passing `None` clears the environment variable for future handle
creation:

```python
mesa.set_inlist(None)
```

## Shutdown

`mesa.shutdown()` frees the persistent eos/kap handles owned by pyfortmesa and
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

That also calls the MESA kap, eos, and chem shutdown routines for loaded table
state.

## Module reference

The module pages describe the supported wrapper surface:

```text
docs/modules/README.md
docs/modules/const.md
docs/modules/chem.md
docs/modules/eos.md
docs/modules/kap.md
```

## Example Scripts

Run the print-based examples from an environment where the package is installed.
The MESA examples also require the `./mk mesa` build:

```bash
export MESA_DIR=/path/to/current/mesa
./test
./test mesa
tests/work/run_simple_chem_eos_kap.sh
tests/mesa/run_eos_kap_arbitrary_composition.sh --with-mesa
tests/mesa/run_hydrostatic_structure.sh --with-mesa
tests/mesa/run_eos_from_saved_model.sh --with-mesa
OMP_NUM_THREADS=10 tests/mesa/run_eos_from_saved_model.sh --with-mesa
tests/mesa/run_profile_timing_suite.sh
tests/mesa/run_eos_from_saved_model.sh --with-mesa --thread-sweep
tests/mesa/run_eos_from_saved_model.sh --with-mesa --thread-sweep --physics eos-kap
```

`./test` is the normal test entrypoint for checks that do not call MESA.
`./test mesa` adds the optional MESA checks and the saved model timing suite.
Both modes store raw test output under `tests/test_output/`, including
`test_summary.txt`, `tmp_golden_output.txt`, and `golden_compare.log`; set
`PYFORTMESA_TEST_OUTPUT_DIR` to choose a different output directory. The
committed golden baseline for checks that do not call MESA is
`tests/test_output/golden/quick_test_output.txt`. The MESA scripts print input
and output data. The `tests/work/` example is the smallest script to copy into
new work. They are examples and integration checks, not MESA star models.

`run_eos_from_saved_model.sh` reads:

```text
$MESA_DIR/star/test_suite/20M_pre_ms_to_core_collapse/standard_after_core_he_burn.mod
```

It passes `lnT`, `lnd`, isotope ids, and mass-fraction arrays to Fortran batch
wrappers. The default `--physics eos` path reconstructs `T = exp(lnT)` and
`rho = exp(lnd)` inside the eos loop, then calls `eosDT_get` once per zone using
that zone's own `xa(:, k)` profile composition. The `--physics kap` path calls a
kap profile wrapper; that wrapper calls eos internally for the electron
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
PYFORTMESA_THREAD_COUNTS="1 3 6 12" \
  tests/mesa/run_eos_from_saved_model.sh --with-mesa --thread-sweep
```

To time both profile paths in the same thread sweep:

```bash
tests/mesa/run_eos_from_saved_model.sh --with-mesa --thread-sweep --physics eos-kap
```

The timing breakdown separates Python profile-array setup, isotope-id lookup,
the eos profile call, the kap profile call, output collection, and shutdown.
The kap profile call includes its required internal eos call; it is not a pure
`kap_get`-only timer. The `--physics eos-kap` path uses a combined Fortran
wrapper so eos is evaluated once per zone and the same eos result feeds kap.

For ad hoc overhead checks inside normal Python code, enable the package timing
collector instead of writing an external wrapper:

```python
with mesa.timing():
    output = mesa.Kap().eos_kap_profile(T, rho, chem_id, xa)

print(mesa.format_timing_summary(sort_by="seconds"))
```

The summary records high-level pyfortmesa public calls such as
`kap.eos_kap_profile`. It does not write files unless the caller writes the
summary.

For steady-state timings, keep MESA handles alive across repeated calls in one
Python process:

```bash
tests/mesa/run_eos_from_saved_model.sh --with-mesa --physics eos --warmup 1 --repeat 5
tests/mesa/run_eos_from_saved_model.sh --with-mesa --physics kap --warmup 1 --repeat 5
tests/mesa/run_eos_from_saved_model.sh --with-mesa --physics eos-kap --warmup 1 --repeat 5
tests/mesa/run_eos_from_saved_model.sh --with-mesa --thread-sweep \
  --physics eos-kap --warmup 1 --repeat 5
```

For the standard report, use one command:

```bash
tests/mesa/run_profile_timing_suite.sh
```

That suite runs eos, kap, combined eos+kap, and the combined eos+kap thread
sweep, then prints compact single run, global-breakdown, and thread-sweep
tables. Raw per-run logs and timing JSON are temporary by default; set
`PYFORTMESA_PROFILE_REPORT_DIR` to keep them. The wrapper defaults to
`warmup=1` and `repeat=5`; override those with `PYFORTMESA_PROFILE_WARMUP` and
`PYFORTMESA_PROFILE_REPEAT`. The single run thread count is chosen from
`PYFORTMESA_SUMMARY_THREADS`, then `OMP_NUM_THREADS`, then the largest sweep
count.

The equivalent expanded command is:

```bash
tests/mesa/run_eos_from_saved_model.sh --with-mesa --summary-suite --warmup 1 --repeat 5
```

The call rate fields use only timed profile call seconds. Warmup, array setup,
output collection, and shutdown are reported separately.

The script also supports `--nproc`, but that uses separate Python processes.
Do not combine process parallelism with `--thread-sweep`; the runner rejects
that combination to avoid mixing process and thread parallelism.

The script prints parse time, profile wall time, call counts, calls per second,
public-call timing, Fortran reconstruction checks, and first/middle/last sample
outputs. Its `.mod` comparison checks the saved model inputs: zone count,
species count, round trip `lnT/lnd`, and mass-fraction sums. That `.mod` file
does not contain eos result columns such as `lnPgas` or `gamma1`.
