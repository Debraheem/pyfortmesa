# pyfortmesa

This repo contains a Python module for reading and running Fortran/MESA tools
from Python.

## Repository build stack

This package has pure Python code plus a small Fortran routine wrapped with
F2PY. The build stack is:

```text
pyproject.toml -> tells pip/build which backend to use
meson-python   -> connects Python packaging to Meson
Meson          -> configures the compiled-code build
Ninja          -> actually runs the compile commands
gfortran       -> compiles the Fortran source
```

Compiler note:

The small example extension only needs a working Fortran compiler. For the
intended MESA workflow, install the current
[MESA SDK](https://user.astro.wisc.edu/~townsend/static.php?ref=mesasdk) and
source its `mesasdk_init.sh` before building or calling MESA-related code. This
repo was tested with the MESA SDK `gfortran` from GCC 15.2.0, but the example
code does not intentionally require that exact compiler version.

Dependency summary:

```text
runtime Python dependency:
  numpy >= 2.0

local build/dev Python tools:
  build, meson-python, meson, ninja, twine

external compiled-code tools:
  gfortran
  pkg-config  -> required only for ./mk mesa

optional MESA-backed build:
  MESA SDK active in the shell
  MESA_DIR set to a supported new shared-library MESA tree
  mesa-const, mesa-chem, mesa-eos, and mesa-kap pkg-config metadata
```

Useful MESA links:

- [MESA installation docs](https://docs.mesastar.org/en/latest/installation.html)
- [MESA GitHub repository](https://github.com/MESAHub/mesa)

## MESA wrapper target

The current toy Fortran extension does not need MESA. The optional MESA-backed
wrappers target new MESA builds only: `$MESA_DIR` must point at a MESA tree with
shared module libraries and pkg-config files under:

```text
$MESA_DIR/build/*/lib/pkgconfig/mesa-*.pc
```

For current local development, the supported dev MESA source tree is:

```text
/Users/owner/Documents/Software/dev/mesa_release/mesa_clean/main
```

Set `$MESA_DIR` to that tree, or to another new MESA build with the same
shared-library/pkg-config layout. Package code should read `$MESA_DIR`; it
should not hard-code this local path.

Quick check:

```bash
echo $MESA_DIR
export PKG_CONFIG_PATH=$(find "$MESA_DIR/build" -path "*/lib/pkgconfig" -type d | paste -sd: -)
pkg-config --cflags --libs mesa-const mesa-chem mesa-eos mesa-kap
```

Classic/static-only MESA installs such as a tree built with `USE_SHARED = NO`
are source/API references only for this branch. pyfortmesa should fail clearly
for those layouts instead of trying to static-link them. pyfortmesa does not
compile or install MESA itself.

Current source roles:

```text
src/pyfortmesa/calc.py                 -> pure Python calculation
src/pyfortmesa/mesa.py                 -> Python API for optional MESA wrappers
src/pyfortmesa/mesa_support.py         -> MESA env/cache/composition helpers
src/pyfortmesa/fortran/const_def.f90   -> MESA-like dp kind definition
src/pyfortmesa/fortran/small_calc.f90  -> Fortran calculations
src/pyfortmesa/fortran/CONST/          -> MESA const_def wrapper source
src/pyfortmesa/fortran/CHEM/           -> MESA CHEM wrapper source
src/pyfortmesa/fortran/EOS/            -> MESA EOS wrapper source
src/pyfortmesa/fortran/KAP/            -> MESA KAP wrapper source
src/pyfortmesa/fortran_calc.py         -> Python wrapper around F2PY extension
tests/unit/test_module_import.py       -> quick correctness smoke test
tests/benchmarks/time_sum_benchmark.py -> Python vs. Fortran timing script
tests/mesa/eos_kap_arbitrary_composition.py -> optional EOS/KAP test
tests/mesa/run_eos_kap_arbitrary_composition.sh -> EOS/KAP test runner
tests/mesa/hydrostatic_structure.py    -> optional MESA integration test
tests/mesa/run_hydrostatic_structure.sh -> MESA integration test runner
tests/mesa/mesa_mod_profile_reader.py  -> text .mod saved-model reader
tests/mesa/eos_from_saved_model.py     -> EOS timing across a saved model
tests/mesa/run_eos_from_saved_model.sh -> saved-model EOS test runner
tests/mesa/run_profile_timing_suite.sh -> saved-model profile timing report
test                                    -> repo-level test runner with logs
meson.build                            -> compiled-extension build recipe
meson_options.txt                      -> optional with_mesa build switch
tools/f2py_f2cmap                      -> maps dp for F2PY wrappers
tools/mesa_pkg_config.py               -> MESA pkg-config helper for Meson
inlist_eos_and_kap                     -> example shared EOS/KAP controls file
```

The Fortran code uses `real(dp)`, similar to MESA style. The `dp` kind is
defined once in `const_def.f90`. F2PY also needs `tools/f2py_f2cmap` so `dp` is
wrapped as C `double`.

For examples focused on using the package from Python, see:

```text
docs/usage.md
```

For per-module wrapper coverage, see:

```text
docs/modules/README.md
```

## How the module works

The build and import path is:

```text
pyproject.toml
  -> selects meson-python as the build backend
meson.build
  -> tells Meson which Python and Fortran files to build
src/pyfortmesa/fortran/small_calc.f90
  -> contains Fortran routines meant to be callable from Python
tools/f2py_f2cmap
  -> tells F2PY that real(dp) should be wrapped as C double
F2PY
  -> generates C/Python wrapper code for the Fortran routines
Meson + Ninja + gfortran
  -> compile the Fortran and wrapper code into _fortran_calc*.so
src/pyfortmesa/fortran_calc.py
  -> imports _fortran_calc and exposes clean Python functions
src/pyfortmesa/__init__.py
  -> exports the public package API
```

At runtime, Python code calls:

```text
pyfortmesa.small_calc_fortran(...)
  -> fortran_calc.py
  -> _fortran_calc*.so
  -> small_calc_f(...) in Fortran
```

## Local install

For development with compiled code, install the build tools and use an editable
install without build isolation.

From the top of this repository:

```bash
python -m pip install --upgrade pip
python -m pip install --upgrade build meson-python meson ninja numpy twine
python -m pip install --no-build-isolation --editable .
```

The editable install points Python at this local source tree. The `dev` extra
in `pyproject.toml` records the same Python build/upload tools used by `./mk`,
`./install`, and the TestPyPI workflow.

Run the current smoke test:

```bash
python -m pyfortmesa
```

Expected output:

```text
Python saw y = 50.0
Fortran saw y = 50.0
```

You can also call the package function directly:

```bash
python - <<'PY'
from pyfortmesa import small_calc, small_calc_fortran

print(small_calc(4.0))
print(small_calc_fortran(4.0))
PY
```

Expected output:

```text
50.0
50.0
```

## Wheel install

To test the package as a built installable artifact, build a wheel:

```bash
./clean
./mk
```

Then install the generated wheel:

```bash
./install
```

Run the same smoke test:

```bash
python -m pyfortmesa
```

The wheel path is useful for checking distribution behavior. For normal
development work, prefer the editable install.

## Rebuild after Fortran changes

After editing Fortran source, rebuild the wheel and reinstall it into the active
environment:

```bash
./mk
./install
```

These are separate steps:

```text
./mk
  -> builds a new wheel in dist/
  -> compiles the Fortran and creates the extension module

./install
  -> installs that already-built wheel into the active Python environment
  -> makes python -m pyfortmesa use the new compiled code
```

Then rerun the smoke test:

```bash
./test
```

`./test` runs the normal non-MESA checks and writes the command output under
`tests/test_output/`. The summary file is `tests/test_output/test_summary.txt`,
with one `.log` file per check. It also writes a deterministic candidate golden
file to `tests/test_output/tmp_golden_output.txt` and compares it with the
committed baseline at `tests/test_output/golden/quick_test_output.txt`. Diff
output, when there is any, is written to `tests/test_output/golden_compare.log`.
Set
`PYFORTMESA_TEST_OUTPUT_DIR=/path/to/output` to write generated logs somewhere
else.

For a clean rebuild:

```bash
./clean
./mk
./install
```

Typical workflow:

```bash
conda activate pyfortmesa
./clean
./mk
./install
./test
python tests/benchmarks/time_sum_benchmark.py 1000000
```

## MESA-backed build

The default wheel does not include MESA. To build the optional
CONST/CHEM/EOS/KAP wrappers:

```bash
conda activate pyfortmesa
python -m pip install --upgrade build meson-python meson ninja numpy twine
export MESASDK_ROOT=/Applications/mesasdk
source $MESASDK_ROOT/bin/mesasdk_init.sh
export MESA_DIR=/Users/owner/Documents/Software/dev/mesa_release/mesa_clean/main
./mk mesa
./install
./test mesa
```

`./test mesa` runs the same quick checks, then the optional MESA-backed
EOS/KAP, hydrostatic, and saved-model profile timing checks. It stores the raw
test output and timing logs under `tests/test_output/`. The golden comparison
still covers only the deterministic no-MESA quick checks; MESA timings stay in
logs because they are machine-dependent. Use `./test` without an argument for
the no-MESA test set.

Then an arbitrary Python script can call the package:

```python
from pyfortmesa import mesa

# Path A: MESA-style controls file. Call this before first EOS/KAP use.
mesa.set_inlist("inlist_eos_and_kap")

# Input: MESA isotope names mapped to mass fractions. They must sum to 1.
mix = mesa.composition({"h1": 0.70, "he4": 0.28, "c12": 0.02})

constants = mesa.constants()
eos_T = 1.0e7       # K
eos_rho = 1.0e2     # g/cm^3
kap_T = 1.0e6       # K
kap_rho = 1.0e-7    # g/cm^3

chem = mesa.Chem()
eos = mesa.Eos()
kap = mesa.Kap()

# Path B: Python overrides. These override KAP values from defaults/inlist.
kap_type2 = mesa.Kap(use_type2=True, zbase=0.02)

# Output: selected constants from MESA const_def.
print(constants)

# Output: composition moments from MESA CHEM.
print(chem.composition_info(mix))

# Output: EOS returns lnPgas, lnE, lnS, grad_ad, and gamma1.
print(eos.dt(T=eos_T, Rho=eos_rho, comp=mix))

# Output: full EOS returns MESA's eosDT_get result vector and derivatives.
eos_full = eos.dt_full(T=eos_T, Rho=eos_rho, comp=mix)
print(eos_full["results"])
print(eos_full["d_dlnRho"])
print(eos_full["d_dlnT"])
print(eos_full["d_dxa"])

# Output: inverse EOS solves use MESA eosDT_get_Rho/eosDT_get_T.
rho_solve = eos.solve_rho(
    T=eos_T,
    other="lnPgas",
    other_value=eos_full["results"]["lnPgas"],
    Rho_guess=0.8 * eos_rho,
    comp=mix,
)
print(rho_solve["Rho"])

# Output: KAP returns kappa, dlnkap_dlnRho, and dlnkap_dlnT.
print(kap.opacity(T=kap_T, Rho=kap_rho, comp=mix))

# Output: full KAP also returns opacity-source fractions and dlnkap/dxa.
kap_full = kap.opacity_full(T=kap_T, Rho=kap_rho, comp=mix)
print(kap_full["kap_fracs"])
print(kap_full["dlnkap_dxa"])

# Output: Type2 KAP is opt in and requires a positive Zbase.
kap_type2_full = kap_type2.opacity_full(T=kap_T, Rho=kap_rho, comp=mix)
print(kap_type2_full["kap_fracs"])

# Free pyfortmesa's persistent EOS/KAP handles when the script is done.
mesa.shutdown()
```

For repeated profile-style work, use the batched wrappers instead of calling EOS
or KAP one zone at a time from Python. Set the OpenMP thread count before
starting Python:

```bash
export OMP_NUM_THREADS=10
python run_microphysics.py
```

Then keep one Python process alive, reuse isotope ids, and call the profile
wrapper for each model state:

```python
import numpy as np

from pyfortmesa import mesa

mesa.set_cache_root(".")
mesa.set_inlist("inlist_eos_and_kap")

isotope_names = ("h1", "he4", "c12")
chem_id = mesa.iso_ids(isotope_names)
kap = mesa.Kap()


def profile_xa(xa_by_zone):
    """Return mass fractions in pyfortmesa profile layout.

    xa_by_zone has shape (nzones, species). The profile wrappers expect
    xa with shape (species, nzones).
    """
    return np.asfortranarray(np.asarray(xa_by_zone, dtype=np.float64).T)


try:
    # `profiles` is supplied by the caller's solver. Each item is one
    # model/profile with T, rho, and xa arrays.
    for T, rho, xa_by_zone in profiles:
        xa = profile_xa(xa_by_zone)

        # Fast EOS+KAP path: one OpenMP-parallel Fortran loop.
        # EOS is evaluated once per zone and feeds the KAP call.
        eos_kap = kap.eos_kap_profile(T, rho, chem_id, xa)

        gamma1 = eos_kap["results"]["gamma1"]
        grad_ad = eos_kap["results"]["grad_ad"]
        kappa = eos_kap["kappa"]
finally:
    mesa.shutdown()
```

For EOS-only profile work, use `mesa.Eos().dt_profile(...)`. For opacity-only
profile work, use `mesa.Kap().opacity_profile(...)`; that path still calls EOS
internally for the electron-state quantities KAP needs. When the caller needs
both EOS and KAP, prefer `mesa.Kap().eos_kap_profile(...)` so EOS is not
evaluated twice for the same zone. The lower-level `*_from_logs(...)` variants
remain available when the caller already has MESA-style `lnT` and `lnd` columns.

The important performance rule is to amortize MESA lifecycle costs. The first
call may initialize tables and write cache files, so it is not representative of
steady-state speed. Real workflows should set cache/inlist controls once,
precompute isotope ids, batch zones into profile calls, let OpenMP parallelize
inside Fortran, and call `mesa.shutdown()` only when the whole driver is done.

`mesa.composition(...)` reads isotope names from:

```text
$MESA_DIR/data/chem_data/isotopes.data
```

and builds the arrays passed through F2PY to MESA:

```text
isotope names -> chem_id values -> net_iso mapping -> xa mass fractions
```

Here `net_iso` is MESA's lookup from a chemistry isotope id to the local
species index. It does not mean pyfortmesa is running the NET reaction network.

Mass fractions must sum to 1.0 unless `normalize=True` is passed.

The older sample 7-isotope vector is still available for quick tests:

```text
h1, he4, c12, n14, o16, ne20, mg24
```

```python
xa = mesa.sample_composition("h1")
print(mesa.Eos().dt(1.0e9, 1.0e4, xa))
```

Current MESA API coverage:

```text
CHEM
  wrapped now:
    basic_composition_info -> mesa.Chem().composition_info(...)
    chem_shutdown -> mesa.shutdown(release_tables=True)
  planned:
    chem_init lifecycle, solar abundance helpers, isotope names,
    binding-energy/Q helpers, stable-mass-fraction helpers

EOS
  wrapped now:
    eosDT_get -> mesa.Eos().dt(...)
    eosDT_get -> mesa.Eos().dt_full(...)
    eosDT_get profile loop -> mesa.Eos().dt_profile(...)
    eosDT_get log-profile loop -> mesa.Eos().dt_profile_from_logs(...)
    eosDT_get_Rho -> mesa.Eos().solve_rho(...)
    eosDT_get_T -> mesa.Eos().solve_t(...)
  planned:
    eosPT_get, eosPT_get_T, eos_gamma_* calls, HELM result helpers,
    Fermi-Dirac integral, control namelist get/set

KAP
  wrapped now:
    kap_get -> mesa.Kap().opacity(...)
    kap_get -> mesa.Kap().opacity_full(...)
    kap_get profile loop -> mesa.Kap().opacity_profile(...)
    combined EOS+KAP profile loop -> mesa.Kap().eos_kap_profile(...)
    Type2 fields -> mesa.Kap(use_type2=True, zbase=...)
  planned:
    elect_cond, Compton, radiative, op_mono, mombarg, and control namelist calls

NET
  future project:
    net construction, read_net_file, table setup, net_get, rates-only,
    one-zone burn helpers, cleanup helpers

TURB
  future project:
    public turb setters in $MESA_DIR/turb/public/turb.f90
```

NET and TURB are not needed for the current EOS/KAP zone-query workflow. The
current MESA-enabled build uses CHEM to define the composition, EOS to evaluate
thermodynamic quantities, and KAP to evaluate opacity.

For an RSP-style zone call where `T`, `rho`, and composition are already known,
the current `Eos.dt_full(...)` plus `Kap.opacity_full(...)` path is the relevant
one. `Eos.solve_rho(...)` and `Eos.solve_t(...)` are available when the Python
code wants MESA to invert the EOS, for example to solve for `rho` from
`Pgas,T` or for `T` from `rho,egas`. MESA EOS log result values such as
`lnPgas` are natural logs.

There are two supported control paths:

```python
# Path A: one MESA-style controls file with both &eos and &kap namelists.
mesa.set_inlist("inlist_eos_and_kap")
eos = mesa.Eos()
kap = mesa.Kap()

# Path B: Python KAP overrides for values you want to set in code.
kap = mesa.Kap(use_type2=True, zbase=0.02)
```

The precedence is:

```text
MESA module defaults
  -> optional shared inlist_eos_and_kap from mesa.set_inlist(...)
  -> optional Python KAP overrides from mesa.Kap(...)
```

Call `mesa.set_inlist(...)` before the first EOS or KAP call in that Python
process. pyfortmesa does not silently search for an inlist in the current
directory.

If no inlist is set and no Python override is given, pyfortmesa keeps Type2 KAP
off by default so a simple opacity call does not require `Zbase`. If an inlist
is set, `mesa.Kap()` leaves Type2 controls to the inlist; explicit Python
keywords still override it.

EOS and KAP handles are persistent inside the Fortran wrappers for the Python
process. The first call initializes MESA and allocates handles; later calls
reuse them while rebuilding composition arrays per requested mixture.

Call `mesa.shutdown()` when the Python code is done with MESA. That frees
pyfortmesa's persistent EOS/KAP handles and resets the wrapper state. It is one
top-level command for users; internally the cleanup is module-specific because
the KAP wrapper owns a KAP handle and its own EOS handle.

```python
try:
    print(eos.dt(T=eos_T, Rho=eos_rho, comp=mix))
    print(kap.opacity(T=kap_T, Rho=kap_rho, comp=mix))
finally:
    mesa.shutdown()
```

By default `mesa.shutdown()` leaves MESA's loaded tables in memory so later calls
in the same Python process can reuse them. In a long-lived notebook or service,
use this only when no other code in the process is using MESA:

```python
mesa.shutdown(release_tables=True)
```

That also calls MESA's module shutdown path for loaded KAP, EOS, and CHEM table
state. Process exit still reclaims everything, so short scripts do not need the
heavier table-release path.

The public MESA routines are not all the same shape. Some are direct numerical
queries; others need handles, initialized tables, output work arrays, namelist
controls, or callback-style setup. pyfortmesa should wrap those behind small
Python objects instead of exposing raw Fortran pointer/control plumbing.

First calls may create MESA cache files. By default, pyfortmesa writes them
under a local cache directory in the directory where Python is run:

```text
.pyfortmesa_caches/mesa_caches/
.pyfortmesa_caches/mesa_temp_caches/
```

To write `mesa_caches/` and `mesa_temp_caches/` directly in the current
directory:

```bash
export PYFORTMESA_CACHE_DIR=.
```

To choose another cache root:

```bash
export PYFORTMESA_CACHE_DIR=/path/to/cache/root
```

From Python, set the same control before the first EOS/KAP call:

```python
from pyfortmesa import mesa

mesa.set_cache_root(".")
```

Use `mesa.set_cache_root(None)` or `PYFORTMESA_CACHE_DIR=mesa_default` to leave
MESA cache paths at MESA's own defaults.

## MESA integration test

After installing a MESA-enabled wheel, run the optional EOS/KAP arbitrary
composition example:

```bash
tests/mesa/run_eos_kap_arbitrary_composition.sh --with-mesa
```

That script prints the named composition, the input `T` and `rho`, and the EOS
and KAP result dictionaries. It does not assert on the values; it is meant to
show what another Python script would call.

After installing a MESA-enabled wheel, run the optional hydrostatic structure
test:

```bash
tests/mesa/run_hydrostatic_structure.sh --with-mesa
```

Without `--with-mesa`, the runner only checks syntax and verifies that the test
skips safely when MESA integration is not explicitly enabled.

With `--with-mesa`, the runner uses `PYFORTMESA_CACHE_DIR` if it is already set.
Otherwise it writes caches under `.pyfortmesa_caches/` in the directory where
you launched the runner.

The hydrostatic test calls CHEM, EOS, and KAP through pyfortmesa, then
integrates a toy spherical hydrostatic model. It solves:

```text
dm/dr = 4*pi*r^2*rho
dP/dr = -G*m*rho/r^2
dlnT/dlnP = grad_rad
grad_rad = 3*kappa*P*L/(16*pi*a*c*G*m*T^4)
```

EOS closes the model by enforcing `Pgas(T, rho) = P` for `rho` at each shell
with a short pressure-correction loop. KAP supplies
`kappa(T, rho, composition)` for `grad_rad`. This is a wrapper integration
test, not a MESA star model.

The saved-model EOS timing example reads the text `.mod` file:

```text
$MESA_DIR/star/test_suite/20M_pre_ms_to_core_collapse/standard_after_core_he_burn.mod
```

It parses the zone table in Python, then passes arrays of `lnT`, `lnd`, isotope
ids, and mass fractions to Fortran batch wrappers. The EOS wrapper reconstructs
`T = exp(lnT)` and `rho = exp(lnd)` inside the EOS loop, then calls `eosDT_get`
once per zone using that zone's own `xa(:, k)` profile composition. The KAP
profile wrapper does the same reconstruction, calls EOS for the electron
quantities required by `kap_get`, then calls `kap_get` once per zone. These zone
loops are OpenMP-parallel inside Fortran, following MESA star's `foreach_cell`
pattern. The runner prints parse time, profile wall time, call counts, calls per
second, phase-level timing, Fortran reconstruction checks, and sample outputs:

```bash
conda activate pyfortmesa
export MESA_DIR=/Users/owner/Documents/Software/dev/mesa_release/mesa_clean/main
tests/mesa/run_eos_from_saved_model.sh --with-mesa
```

The default profile physics is EOS only. To time the KAP profile path, or both
paths in one process:

```bash
tests/mesa/run_eos_from_saved_model.sh --with-mesa --physics kap
tests/mesa/run_eos_from_saved_model.sh --with-mesa --physics eos-kap
```

The KAP profile timing includes the internal EOS call needed to provide
`lnfree_e`, `eta`, and their derivatives to `kap_get`; it is not a pure
`kap_get`-only timer. The `eos-kap` path uses a combined Fortran wrapper so EOS
is evaluated once per zone and the same EOS result feeds KAP.

For steady-state timings, use a warmup and repeated timed calls in one Python
process. This keeps MESA handles alive and moves cache/table setup out of the
timed measurements:

```bash
tests/mesa/run_eos_from_saved_model.sh --with-mesa --physics eos --warmup 1 --repeat 5
tests/mesa/run_eos_from_saved_model.sh --with-mesa --physics kap --warmup 1 --repeat 5
tests/mesa/run_eos_from_saved_model.sh --with-mesa --physics eos-kap --warmup 1 --repeat 5
```

For the standard timing report, use the one-command summary suite. It runs the
EOS, KAP, combined EOS+KAP, and EOS+KAP thread-sweep timings, then prints compact
single-run, global-breakdown, and thread-sweep tables:

```bash
./test mesa
```

or run just the profile timing suite:

```bash
tests/mesa/run_profile_timing_suite.sh
```

The summary suite writes raw per-run logs and timing JSON files under
`tests/test_output/` and prints that path at the end. The wrapper uses
`PYFORTMESA_PROFILE_WARMUP=1` and
`PYFORTMESA_PROFILE_REPEAT=5` by default, and forwards any extra arguments to
`run_eos_from_saved_model.sh`. By default the single EOS/KAP/EOS+KAP runs use
`PYFORTMESA_SUMMARY_THREADS`, then `OMP_NUM_THREADS`, then the largest
thread-sweep count. The sweep counts still default to `1 2 4 6 8 10` and can be
changed with `--thread-sweep=...` or `PYFORTMESA_THREAD_COUNTS`.

The expanded command is:

```bash
tests/mesa/run_eos_from_saved_model.sh --with-mesa --summary-suite --warmup 1 --repeat 5
```

Set the Fortran OpenMP thread count with `OMP_NUM_THREADS` before launching the
runner. This changes the number of threads used by the single-process Fortran
profile loop. The timing output still reports `nproc = 1`; that is expected for
an OpenMP-threaded run.

```bash
OMP_NUM_THREADS=10 tests/mesa/run_eos_from_saved_model.sh --with-mesa
```

For the standard profile thread-scaling test, use `--thread-sweep`. The default
thread counts are `1 2 4 6 8 10`:

```bash
tests/mesa/run_eos_from_saved_model.sh --with-mesa --thread-sweep
```

Custom thread counts can be passed either way:

```bash
tests/mesa/run_eos_from_saved_model.sh --with-mesa --thread-sweep=1,2,4,8
PYFORTMESA_THREAD_COUNTS="1 3 6 12" tests/mesa/run_eos_from_saved_model.sh --with-mesa --thread-sweep
```

For EOS and KAP timing in the same thread sweep:

```bash
tests/mesa/run_eos_from_saved_model.sh --with-mesa --thread-sweep --physics eos-kap --warmup 1 --repeat 5
```

For a process-parallel timing run using 10 Python processes:

```bash
tests/mesa/run_eos_from_saved_model.sh --with-mesa --parallel
```

or explicitly:

```bash
tests/mesa/run_eos_from_saved_model.sh --with-mesa --nproc 10
```

Do not combine `--parallel` or `--nproc` with `--thread-sweep`; the runner
rejects that combination to avoid mixing process and thread parallelism. The
call-rate fields use timed profile-call seconds only; warmup, array setup,
output collection, and shutdown are reported separately. The
comparison section checks the data that exists in the `.mod` file: parsed zone
count versus `n_shells`, species count versus isotope columns,
Fortran-reconstructed `lnT/lnd` round trip, and mass-fraction sums. The saved
model does not store EOS result columns such as `lnPgas` or `gamma1`, so those
are printed as newly computed EOS outputs rather than reference comparisons.

## Benchmark

Benchmark code lives outside `src` because timing is not part of the library
API. The benchmark calls package functions from `src`.

Run the default benchmark:

```bash
python tests/benchmarks/time_sum_benchmark.py
```

Run with a custom loop count:

```bash
python tests/benchmarks/time_sum_benchmark.py 10000000
```

The benchmark compares:

```text
big_sum_python(n)   -> pure Python loop
big_sum_fortran(n)  -> compiled Fortran loop
```

## Build scripts

Clean generated files:

```bash
./clean
```

Build only a wheel:

```bash
./mk
```

Build a wheel with optional MESA CONST/CHEM/EOS/KAP wrappers:

```bash
export MESA_DIR=/Users/owner/Documents/Software/dev/mesa_release/mesa_clean/main
./mk mesa
```

Install the newest built wheel from `dist/` into the active Python environment:

```bash
./install
```

`./install` is shorthand for the local testing command:

```bash
python -m pip install --force-reinstall --no-deps dist/pyfortmesa-*.whl
```

The script picks the newest wheel in `dist/`. `--force-reinstall` replaces the
currently installed copy, and `--no-deps` avoids changing dependencies such as
NumPy while you are only testing your local build.

Build only a source distribution:

```bash
./mk sdist
```

Build both source distribution and wheel:

```bash
./mk all
```

For Meson projects, source distributions are made from files tracked by git.
If `./mk all` fails during active development, commit or stage the new source
files first, or use the default wheel build while testing locally.

## TestPyPI upload

TestPyPI is the practice package index. Use it before uploading to the real
PyPI index.

Start from the top of this repository.

Optionally remove old generated build files first:

```bash
rm -rf dist build src/pyfortmesa.egg-info
```

Build the source distribution and wheel:

```bash
./clean
./mk all
```

Check the generated files:

```bash
python -m twine check dist/pyfortmesa-0.3.1*
```

Upload to TestPyPI:

```bash
python -m twine upload --repository testpypi dist/pyfortmesa-0.3.1*
```

When prompted, use a TestPyPI API token. If Twine asks for username and
password, use `__token__` as the username and paste the token as the password.

Version flow:

```text
pyproject.toml version -> local package metadata
python -m build -> local dist files
twine upload -> TestPyPI release
git tag -> GitHub label, not a TestPyPI upload
```

If TestPyPI still shows an older version, the new version was built locally but
has not been uploaded successfully yet.

## Test install from TestPyPI

After the upload succeeds, test the install from outside this repository.

```bash
python -m pip uninstall -y pyfortmesa
python -m pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  pyfortmesa==0.3.1
```

Then run:

```bash
cd ..
python -m pyfortmesa
```

Expected output:

```text
Python saw y = 50.0
Fortran saw y = 50.0
```

## TestPyPI troubleshooting

If upload fails with `400 Bad Request`, rerun with verbose output:

```bash
python -m twine upload --repository testpypi --verbose dist/pyfortmesa-0.3.1*
```

Common causes are an already-uploaded version, a token for the wrong package
index, or a token scoped to a different TestPyPI project.
