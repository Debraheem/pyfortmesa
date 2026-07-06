# pyfortmesa MESA module interface plan

Branch: `just_a_module`

Goal: expose selected MESA CONST, CHEM, EOS, and KAP calls from Python in a
clean, MESA-like way for arbitrary static compositions. NET and TURB are future
build projects and are not active implementation targets for this branch.

This is a tracking document. Update it as implementation decisions change.

Per-module coverage pages live in:

```text
docs/modules/README.md
```

## Supported MESA Layout

Support new MESA builds only. The selected `$MESA_DIR` must provide shared
module libraries and pkg-config metadata under:

```text
$MESA_DIR/build/*/lib/pkgconfig/mesa-*.pc
```

Required module metadata for this branch:

```text
mesa-const
mesa-chem
mesa-eos
mesa-kap
```

Future module metadata, not required for the current branch:

```text
mesa-net
mesa-turb
```

Current supported local dev source:

```text
/Users/owner/Documents/Software/dev/mesa_release/mesa_clean/main
```

This tree has the required `build/*/lib/pkgconfig/mesa-*.pc` layout. Before
building pyfortmesa against MESA, the user should set `$MESA_DIR` to this tree
or another compatible new MESA build and check:

```bash
echo $MESA_DIR
export PKG_CONFIG_PATH=$(find "$MESA_DIR/build" -path "*/lib/pkgconfig" -type d | paste -sd: -)
pkg-config --cflags --libs mesa-const mesa-chem mesa-eos mesa-kap
```

Do not hard-code a local MESA path in package code. Read `$MESA_DIR`.

## Implemented First Slice

Current code builds optional MESA-backed F2PY extensions when Meson receives:

```text
-Dwith_mesa=true
```

Implemented files:

```text
meson_options.txt
tools/mesa_pkg_config.py
src/pyfortmesa/mesa.py
src/pyfortmesa/mesa_support.py
src/pyfortmesa/fortran/CONST/mesa_const_public.f90
src/pyfortmesa/fortran/CHEM/mesa_chem_public.f90
src/pyfortmesa/fortran/EOS/mesa_eos_public.f90
src/pyfortmesa/fortran/KAP/mesa_kap_public.f90
```

Current Python API:

```python
from pyfortmesa import mesa

# Path A: one MESA-style controls file with both &eos and &kap namelists.
mesa.set_inlist("inlist_eos_and_kap")

# Input: MESA isotope names mapped to mass fractions. They must sum to 1.
mix = mesa.composition({"h1": 0.70, "he4": 0.28, "c12": 0.02})

eos_T = 1.0e7       # K
eos_rho = 1.0e2     # g/cm^3
kap_T = 1.0e6       # K
kap_rho = 1.0e-7    # g/cm^3

# Output: selected MESA const_def values.
const_result = mesa.constants()

# Output: composition moments from MESA CHEM.
chem_result = mesa.Chem().composition_info(mix)

# Output: EOS returns lnPgas, lnE, lnS, grad_ad, and gamma1.
eos_result = mesa.Eos().dt(T=eos_T, Rho=eos_rho, comp=mix)

# Output: full EOS returns MESA's eosDT_get result vector and derivatives.
eos_full = mesa.Eos().dt_full(T=eos_T, Rho=eos_rho, comp=mix)

# Output: inverse EOS solves use MESA eosDT_get_Rho/eosDT_get_T.
rho_solve = mesa.Eos().solve_rho(
    T=eos_T,
    other="lnPgas",
    other_value=eos_result["lnPgas"],
    Rho_guess=0.8 * eos_rho,
    comp=mix,
)
T_solve = mesa.Eos().solve_t(
    Rho=eos_rho,
    other="lnPgas",
    other_value=eos_result["lnPgas"],
    T_guess=0.9 * eos_T,
    comp=mix,
)

# Output: KAP returns kappa, dlnkap_dlnRho, and dlnkap_dlnT.
kap_result = mesa.Kap().opacity(T=kap_T, Rho=kap_rho, comp=mix)

# Output: full KAP also returns kap_fracs and dlnkap_dxa.
kap_full = mesa.Kap().opacity_full(T=kap_T, Rho=kap_rho, comp=mix)

# Path B: Python KAP controls can override defaults/inlist values.
kap_type2 = mesa.Kap(use_type2=True, zbase=0.02)
kap_type2_full = kap_type2.opacity_full(T=kap_T, Rho=kap_rho, comp=mix)
```

The named composition helper reads:

```text
$MESA_DIR/data/chem_data/isotopes.data
```

and builds:

```text
names  = ("h1", "he4", "c12", ...)
chem_id(i) = MESA 1-based isotope index for names(i)
sum_i xa(i) = 1
net_iso(chem_id(i)) = i
```

The F2PY wrapper infers `species` from the length of `chem_id`; Python passes
only `chem_id` and `xa` to the generated extension.

The CONST wrapper calls MESA `const_def` and returns selected constants used by
the example tests:

```text
standard_cgrav, crad, clight, Lsun, Rsun, Msun
```

The Python method is:

```python
mesa.constants()
```

The older sample composition helper remains for quick tests:

```text
xa = [X_h1, X_he4, X_c12, X_n14, X_o16, X_ne20, X_mg24]
```

The CHEM wrapper calls:

```text
basic_composition_info(species, chem_id, xa,
                       xh, xhe, xz,
                       abar, zbar, z2bar, z53bar, ye,
                       mass_correction, sumx)
```

and returns the same moments to Python.

The EOS wrapper calls:

```text
eosDT_get(handle, species, chem_id, net_iso, xa,
          Rho, log10(Rho), T, log10(T),
          res, d_dlnd, d_dlnT, d_dxa, ierr)
```

and returns:

```text
lnPgas = res(i_lnPgas)
lnE    = res(i_lnE)
lnS    = res(i_lnS)
grad_ad = res(i_grad_ad)
gamma1  = res(i_gamma1)
```

Full EOS output:

```text
$MESA_DIR/eos/public/eos_def.f90
```

defines `num_eos_basic_results = 26` for the current supported tree. The full
result vector includes:

```text
lnPgas, lnE, lnS, mu, lnfree_e, eta, grad_ad, chiRho, chiT,
Cp, Cv, dE_dRho, dS_dT, dS_dRho, gamma1, gamma3, phase,
latent_ddlnT, latent_ddlnRho,
HELM, OPAL/SCVH, FreeEOS, PC, Skye, CMS, ideal
```

`$MESA_DIR/star/private/eos_support.f90` and
`$MESA_DIR/star/private/micro.f90` use the full `res`, `dres_dlnRho`, and
`dres_dlnT` arrays. pyfortmesa now keeps the small teaching wrapper and also
adds:

```python
mesa.Eos().dt_full(T=..., Rho=..., comp=...)
```

returning dictionaries keyed by the MESA EOS result names for:

```text
results
d_dlnRho
d_dlnT
d_dxa
```

MESA only returns the first two EOS composition-derivative rows to the public
`eosDT_get` caller. Those are exposed as:

```text
d_dxa["lnPgas"][isotope_name]
d_dxa["lnE"][isotope_name]
```

The KAP wrapper first calls EOS, then passes EOS electron quantities to KAP:

```text
lnfree_e = res(i_lnfree_e)
eta      = res(i_eta)

kap_get(..., log10(Rho), log10(T),
        lnfree_e, d_lnfree_e_dlnRho, d_lnfree_e_dlnT,
        eta, d_eta_dlnRho, d_eta_dlnT,
        kap_fracs, kappa, dlnkap_dlnRho, dlnkap_dlnT, dlnkap_dxa, ierr)
```

The wrapper keeps the default Python behavior as Type2 off, but exposes
explicit controls:

```python
mesa.Kap(
    use_type2=True,
    zbase=0.02,
    use_zbase_for_type1=True,
    type2_full_off_X=None,
    type2_full_on_X=None,
    type2_full_off_dZ=None,
    type2_full_on_dZ=None,
)
```

`None` means leave the corresponding MESA `kap.defaults` value on the KAP
handle. `zbase` must be positive when Type2 is enabled.

Full KAP output:

```text
$MESA_DIR/kap/public/kap_lib.f90
```

main `kap_get` also returns:

```text
kap_fracs(num_kap_fracs)
dlnkap_dxa(species)
```

where `num_kap_fracs = 4` in `$MESA_DIR/kap/public/kap_def.f90`:

```text
lowT, highT, Type2, Compton
```

pyfortmesa now keeps the small teaching wrapper and also adds:

```python
mesa.Kap().opacity_full(T=..., Rho=..., comp=...)
```

returning:

```text
kappa
dlnkap_dlnRho
dlnkap_dlnT
kap_fracs["lowT" | "highT" | "Type2" | "Compton"]
dlnkap_dxa[isotope_name]
```

KAP also has public specialized routines for electron conduction, Compton
opacity, radiative opacity, OP mono opacity, mombarg support, and control
namelist access that are not wrapped yet.

Python sets MESA cache environment variables before calling MESA:

```text
MESA_CACHES_DIR
MESA_TEMP_CACHES_DIR
```

The default cache root is local to the directory where Python is run:

```text
.pyfortmesa_caches/mesa_caches/
.pyfortmesa_caches/mesa_temp_caches/
```

Users can override this with:

```bash
export PYFORTMESA_CACHE_DIR=/path/to/cache/root
```

or from Python before the first EOS/KAP call:

```python
mesa.set_cache_root(".")
```

`PYFORTMESA_CACHE_DIR=mesa_default` or `mesa.set_cache_root(None)` leaves MESA
cache paths at MESA's own defaults.

## Controls, Defaults, and Handles

pyfortmesa supports two explicit control paths:

```python
# Path A: one MESA-style file containing both &eos and &kap namelists.
mesa.set_inlist("inlist_eos_and_kap")
eos = mesa.Eos()
kap = mesa.Kap()

# Path B: Python KAP overrides.
kap = mesa.Kap(use_type2=True, zbase=0.02)
```

The control precedence is:

```text
MESA module defaults
  -> optional shared inlist_eos_and_kap from mesa.set_inlist(...)
  -> optional Python KAP overrides from mesa.Kap(...)
```

The inlist path is explicit. pyfortmesa does not silently read `./inlist` or
`./inlist_eos_and_kap` from the current directory. Call `mesa.set_inlist(...)`
before the first EOS/KAP call in a Python process.

If no inlist is set, pyfortmesa keeps Type2 KAP off by default so simple KAP
calls do not require `Zbase`. If an inlist is set, `mesa.Kap()` leaves Type2 to
the inlist unless Python keywords override it.

EOS and KAP handles are process-persistent in the current wrapper sources.
They are initialized and allocated on the first Python call, then reused by
later calls in the same Python process. The composition arrays are still built
per call because they depend on the requested mixture.

`mesa.shutdown()` frees pyfortmesa's saved EOS/KAP handles and resets wrapper
state. It is the normal cleanup call for scripts and examples. It is exposed as
one Python command, but the Fortran cleanup is module-specific because the KAP
wrapper owns a KAP handle and its own EOS handle.

`mesa.shutdown(release_tables=True)` is the heavier long-process path. It frees
the handles and also calls the MESA KAP, EOS, and CHEM shutdown routines for
loaded table state. Use it only when no other code in the Python process is
using MESA.

## Public API Coverage Target

The active target for this branch is to cover the CHEM/EOS/KAP calls needed for
arbitrary static-composition zone queries:

```text
composition -> CHEM -> EOS -> KAP
constants   -> CONST
```

The wrappers should not expose raw Fortran pointer plumbing directly to normal
Python users. Direct numerical calls can be thin wrappers; lifecycle, handle,
table, and control routines should sit behind small Python objects.

NET and TURB are future build projects. Keep their source inventories here for
planning, but do not require them in the current build or tests.

### CHEM

Source:

```text
$MESA_DIR/chem/public/chem_lib.f90
```

Wrapped now:

```text
basic_composition_info
```

Still to wrap:

```text
chem_init
chem_shutdown
lodders03_element_atom_percent
get_nuclide_index_in_set
generate_nuclide_set
composition_info
get_composition_info
chem_get_solar
generate_nuclide_names
generate_long_nuclide_names
binding_energy
get_mass_excess
get_Q
get_partition_fcn_indx
get_stable_mass_frac
```

### EOS

Source:

```text
$MESA_DIR/eos/public/eos_lib.f90
```

Wrapped now:

```text
eosDT_get
eosDT_get_T
eosDT_get_Rho
```

Still to wrap:

```text
eos_init
eos_shutdown
free_eos_handle
eos_ptr
eosDT_get_component
helmeos2_eval
eosPT_get
eos_gamma_DP_get_ET
eos_gamma_DE_get_PT
eos_gamma_DT_get_P_energy
eos_gamma_PRho_get_T_energy
eos_gamma_PT_get_rho_energy
eos_gamma_DE_get
eos_gamma_PT_get
eos_gamma_DT_get
eos_fermi_dirac_integral
eos_get_helm_results
eos_convert_helm_results
eosPT_get_T
num_eos_files_loaded
eos_get_control_namelist
eos_set_control_namelist
```

### KAP

Source:

```text
$MESA_DIR/kap/public/kap_lib.f90
```

Wrapped now:

```text
kap_get
KAP handle Type2 control fields:
  use_Type2_opacities
  Zbase
  use_Zbase_for_Type1
  kap_Type2_full_off_X
  kap_Type2_full_on_X
  kap_Type2_full_off_dZ
  kap_Type2_full_on_dZ
```

Still to wrap:

```text
kap_init
kap_shutdown
free_kap_handle
kap_ptr
kap_setup_tables
kap_setup_hooks
kap_get_elect_cond_opacity
kap_get_compton_opacity
kap_get_radiative_opacity
kap_get_op_mono
load_op_mono_data
call_load_op_master
get_op_mono_params
op_mono_get_radacc
op_mono_get_kap
op_mono_alt_get_kap
get_op_mono_args
kap_get_control_namelist
kap_set_control_namelist
call_compute_grad_mombarg
call_compute_gamma_grid_mombarg
call_compute_kappa_mombarg
call_compute_kappa_grid_mombarg
```

### NET

Source:

```text
$MESA_DIR/net/public/net_lib.f90
```

Branch status:

```text
future project; not required for current EOS/KAP zone queries
```

Still to wrap:

```text
net_init
net_shutdown
free_net_handle
net_ptr
net_start_def
net_finish_def
read_net_file
net_add_iso
net_add_isos
net_remove_iso
net_remove_isos
net_add_reaction
net_add_reactions
net_remove_reaction
net_remove_reactions
show_net_reactions
show_net_reactions_and_info
show_net_species
show_net_params
net_set_fe56ec_fake_factor
net_set_logTcut
net_set_eps_nuc_cancel
net_setup_tables
get_chem_id_table
get_chem_id_table_ptr
get_net_iso_table
get_net_iso_table_ptr
get_reaction_id_table
get_reaction_id_table_ptr
get_net_reaction_table
get_net_reaction_table_ptr
net_get
net_get_rates_only
net_get_symbolic_d_dxdt_dx
net_get_with_Qs
net_1_zone_burn
net_1_zone_burn_const_density
net_1_zone_burn_const_P
clean_up_fractions
clean1
```

### TURB

Source:

```text
$MESA_DIR/turb/public/turb.f90
```

Branch status:

```text
future project; not required for current EOS/KAP zone queries
```

Still to wrap:

```text
set_thermohaline
set_mlt
set_tdc
set_semiconvection
```

## MESA Integration Tests

Optional EOS/KAP print example:

```text
tests/mesa/eos_kap_arbitrary_composition.py
tests/mesa/run_eos_kap_arbitrary_composition.sh
```

Run it only after building/installing the MESA-enabled wheel:

```bash
tests/mesa/run_eos_kap_arbitrary_composition.sh --with-mesa
```

This script prints the named composition, the input `T` and `rho`, and the EOS
and KAP result dictionaries. It intentionally avoids Python `assert`
statements and shows the returned values.

Optional test file:

```text
tests/mesa/hydrostatic_structure.py
```

Run it only after building/installing the MESA-enabled wheel:

```bash
tests/mesa/run_hydrostatic_structure.sh --with-mesa
```

Without `--with-mesa`, the runner checks syntax and verifies that the test
skips safely when MESA integration is not explicitly enabled.

The test calls `mesa.constants()`, `Chem`, `Eos`, and `Kap`, then integrates a
toy spherical hydrostatic profile. It is not a MESA star model.

Equations:

```text
dm/dr = 4*pi*r^2*rho
dP/dr = -G*m*rho/r^2
dlnT/dlnP = grad_rad
grad_rad = 3*kappa*P*L/(16*pi*a*c*G*m*T^4)
```

Saved-model EOS timing example:

```text
tests/mesa/mesa_mod_profile_reader.py
tests/mesa/eos_from_saved_model.py
tests/mesa/run_eos_from_saved_model.sh
```

Run it only after building/installing the MESA-enabled wheel:

```bash
conda activate pyfortmesa
export MESA_DIR=/Users/owner/Documents/Software/dev/mesa_release/mesa_clean/main
tests/mesa/run_eos_from_saved_model.sh --with-mesa
OMP_NUM_THREADS=10 tests/mesa/run_eos_from_saved_model.sh --with-mesa
tests/mesa/run_eos_from_saved_model.sh --with-mesa --thread-sweep
tests/mesa/run_eos_from_saved_model.sh --with-mesa --thread-sweep --physics eos-kap
tests/mesa/run_eos_from_saved_model.sh --with-mesa --nproc 10
```

This reads the text saved model:

```text
$MESA_DIR/star/test_suite/20M_pre_ms_to_core_collapse/standard_after_core_he_burn.mod
```

It does not call `star_read_model` or run a MESA star model. The parser uses the
ASCII table columns written in the saved model:

```text
lnd, lnT, lnR, L, dq, v, mlt_vc, isotope mass fractions
```

For each selected zone, the Python parser reads the profile mass fractions from
the isotope columns and builds:

```text
xa(species, nzones) = mass fractions from neut ... ni56
chem_id(species) = MESA isotope ids for the same columns
```

Then the Fortran batch wrappers loop over zones:

```text
rho(k) = exp(lnd(k))
T(k) = exp(lnT(k))
composition = xa(:, k)
EOS profile call = eosDT_get(handle, ..., T(k), rho(k), xa(:, k), ...)
KAP profile call = eosDT_get(...) for electron quantities, then kap_get(...)
```

The profile loops are OpenMP-parallel inside Fortran. Set `OMP_NUM_THREADS`
before launching the runner to change the number of Fortran threads, or use the
normal thread-sweep runner option:

```bash
OMP_NUM_THREADS=10 tests/mesa/run_eos_from_saved_model.sh --with-mesa
tests/mesa/run_eos_from_saved_model.sh --with-mesa --thread-sweep
tests/mesa/run_eos_from_saved_model.sh --with-mesa --thread-sweep=1,2,4,8
```

The timing output reports parse time, profile wall time, number of EOS calls,
process count, and EOS calls per second for the default `--physics eos` path. With
`--physics kap`, it reports KAP call counts and KAP calls per second. With
`--physics eos-kap`, it uses the combined EOS+KAP profile wrapper, which calls
EOS once per zone and then passes `lnfree_e`, `eta`, and their derivatives to
`kap_get`.

Steady-state timing should use warmup and repeated profile calls in one Python
process:

```bash
tests/mesa/run_eos_from_saved_model.sh --with-mesa --physics eos --warmup 1 --repeat 5
tests/mesa/run_eos_from_saved_model.sh --with-mesa --physics kap --warmup 1 --repeat 5
tests/mesa/run_eos_from_saved_model.sh --with-mesa --physics eos-kap --warmup 1 --repeat 5
tests/mesa/run_eos_from_saved_model.sh --with-mesa --thread-sweep --physics eos-kap --warmup 1 --repeat 5
```

For an OpenMP-threaded run, the process count is still `nproc = 1`; `--nproc`
is separate Python process parallelism. The runner rejects combining
`--thread-sweep` with `--parallel` or `--nproc` to avoid oversubscription. The
comparison output checks what exists in the `.mod` file: parsed zones against
`n_shells`, isotope columns against `species`, Fortran-reconstructed `lnT/lnd`
round trip, and mass-fraction sums. The saved model does not include EOS result
columns such as `lnPgas` or `gamma1`, so those are printed as newly computed
pyfortmesa/MESA EOS outputs.

EOS closure:

```text
Pgas(T, rho) = P
```

The test enforces this with a short pressure-correction loop:

```text
rho <- rho * P_target/P_eos(T, rho)
```

KAP closure:

```text
kappa = kappa(T, rho, composition)
```

The current script uses MESA `const_def` values for `standard_cgrav`, `crad`,
`clight`, `Lsun`, `Rsun`, and `Msun`. It prints input/output data and named
checks instead of asserting on hidden values.

## Current Next Steps

1. Done: verify named-composition CHEM, EOS, and KAP calls from an unpacked
   MESA-enabled wheel.
2. Done: add optional CHEM/EOS/KAP hydrostatic integration test.
3. Done in source: add `Eos.dt_full(...)` and `Kap.opacity_full(...)` for the
   main full-output public calls. User still needs to rebuild/install the
   MESA-enabled wheel to exercise them.
4. Done in source: add `mesa.constants()` backed by MESA `const_def` for the
   example/test constants.
5. Done in source: add persistent EOS/KAP handles so repeated Python calls do
   not reinitialize and reallocate the MESA handles each time.
6. Done in source: add EOS inverse solves `eosDT_get_Rho` and `eosDT_get_T`
   through `mesa.Eos().solve_rho(...)` and `mesa.Eos().solve_t(...)`.
7. Done in source: add explicit KAP Type2 opacity controls through
   `mesa.Kap(...)`.
8. Done in source: add one explicit MESA-style `inlist_eos_and_kap` path read
   by both EOS and KAP handles.
9. Done in source: add `mesa.shutdown()` for persistent handle cleanup and
   `mesa.shutdown(release_tables=True)` for optional MESA table-state release.
10. Future branch/project: start NET separately after its required
   initialization and table setup are scoped separately.
11. Future branch/project: add `Turb` handles after their required
   initialization and table setup are scoped separately.
12. Later: package/release to real PyPI after the MESA wrapper surface is
    stable.
13. Keep old/classic MESA layouts unsupported on this branch.

## Unsupported Static Layout

The inspected `mesa-r26.04.1` tree is useful as source/API evidence, but it is
not a supported build target for this branch. Its `utils/makefile_header` says:

```text
USE_SHARED = NO
```

and comments that shared libraries are needed if MESA is to be usable in
Python. That release install has static libraries only:

```text
$MESA_DIR/lib/libchem.a
$MESA_DIR/lib/libeos.a
$MESA_DIR/lib/libkap.a
$MESA_DIR/lib/libnet.a
$MESA_DIR/lib/libturb.a
```

It also uses the classic layout:

```text
$MESA_DIR/include/*.mod
$MESA_DIR/lib/lib*.a
```

and does not provide the new `build/*/lib/pkgconfig/mesa-*.pc` metadata.

Decision for this branch:

1. Require the new shared-library/pkg-config MESA layout.
2. Fail fast for classic static-only MESA installs.
3. Do not add a static-link fallback unless there is a separate reason later.
4. pyfortmesa does not compile or install MESA.

## MESA Build Order

From the inspected `mesa-r26.04.1` install script, the relevant conceptual
module order is:

```text
const
utils
math
mtx
auto_diff
forum
num
interp_1d
interp_2d
chem
colors
eos
kap
rates
neu
net
ionization
atm
turb
sample
star_data
gyre
adipls
star
binary
astero
```

From `mesa-r26.04.1/utils/makefile_header`, useful library groups are:

```text
LIBS_MATRIX:
  mtx const math utils

LIBS_MESA_NUMERICS:
  interp_2d interp_1d num auto_diff forum mtx const math utils

LIBS_MESA_MICRO:
  net eos kap rates neu chem + LIBS_MESA_NUMERICS

LIBS_MESA_MACRO:
  ionization atm colors turb + LIBS_MESA_MICRO
```

Per-module dependencies from module makefiles:

```text
chem -> interp_1d num matrix libs
eos  -> chem + numerics
kap  -> eos chem + numerics
net  -> eos rates chem + numerics
turb -> matrix libs
```

For this branch, do not hand-write link order in Meson. Use pkg-config
dependencies from the new MESA build and keep this order only as a dependency
map for understanding initialization and module layering.

## MESA Usage References

Module examples:

```text
chem/test/src/test_chem.f90
eos/test/src/sample_eos.f90
eos/plotter/src/eos_plotter.f90
kap/test/src/sample_kap.f90
kap/plotter/src/kap_plotter.f90
net/test/src/sample_net.f90
net/test/src/mod_one_zone_burn.f90
turb/test/src/test_turb.f90
```

Notes:

```text
eos and kap have plotters.
net has one-zone burn examples rather than a plotter.
turb has direct test programs and a debug plotting script under turb/test.
chem has direct tests.
```

Star usage references:

```text
star/private/star_private_def.f90  -> init order
star/private/eos_support.f90       -> eosDT_get in star
star/private/kap_support.f90       -> kap_get in star
star/private/net.f90               -> net_get in star
star/private/struct_burn_mix.f90   -> net_1_zone_burn calls
star/private/turb_support.f90      -> set_MLT, set_TDC, semiconvection, thermohaline
star/defaults/star_job.defaults    -> cache dirs, chem/rates filenames
star/defaults/controls.defaults    -> MLT, TDC, net, composition controls
```

## Initialization Pattern

Use the MESA order from `star_private_def.f90` as the full-reference pattern:

```text
const_init
math_init
chem_init
eos_init
kap_init
rates_init
net_init
```

For smaller wrappers, initialize only what is needed:

```text
chem only:
  const_init -> math_init -> chem_init

eos:
  const_init -> math_init -> chem_init -> eos_init -> alloc_eos_handle

kap:
  const_init -> math_init -> chem_init -> eos_init -> kap_init
  -> alloc_eos_handle -> alloc_kap_handle

net:
  const_init -> math_init -> chem_init -> rates_init -> net_init
  -> alloc_net_handle -> read_net_file -> net_finish_def -> net_setup_tables

turb:
  usually no table init; call public routines with explicit thermodynamic inputs
```

## Local Inlist Design

Use one repo-local MESA-style file for EOS and KAP:

```text
inlist_eos_and_kap
```

MESA-native namelists in the same file:

```text
&eos
/

&kap
/
```

The Python setup call is:

```python
mesa.set_inlist("inlist_eos_and_kap")
```

The Fortran wrappers then pass the same path to:

```text
alloc_eos_handle_using_inlist(...)
alloc_kap_handle_using_inlist(...)
```

This matches MESA's normal style better than separate local files. Future
pyfortmesa-owned namelists, not part of this branch:

```text
net/inlist_net  -> pyfortmesa controls such as net_name, rates paths, cache suffix
turb/inlist_turb -> pyfortmesa controls such as MLT_option and TDC parameters
```

Reason: MESA `net` and `turb` do not expose the same general module namelist
reader pattern as `eos` and `kap`. NET reads network files; TURB public
routines are direct calculations normally driven by `star` controls.

## Public Python Shape

Do not expose raw F2PY-generated MESA function names as the user API. Use small
Python functions/classes that validate inputs and call compiled wrappers.

Current target:

```python
from pyfortmesa import mesa
from pyfortmesa.mesa import Chem, Eos, Kap

mesa.set_inlist("inlist_eos_and_kap")

chem = Chem()
ids = chem.iso_ids(["h1", "he4", "c12"])

eos = Eos()
out = eos.dt(T=1.0e7, rho=10.0, isotopes=["h1", "he4"], xa=[0.70, 0.30])

kap = Kap()
out = kap.opacity(T=1.0e7, rho=10.0, isotopes=["h1", "he4"], xa=[0.70, 0.30])
```

The first implementation should expose small, stable wrappers:

```text
chem:
  iso_id(name)
  iso_ids(names)
  composition_info(isotopes, xa)

eos:
  dt(T, rho, isotopes, xa)

kap:
  opacity(T, rho, isotopes, xa)
```

Do not try to auto-wrap every MESA public function first. Many public functions
have Fortran pointers, derived types, callbacks, and MESA-specific state that
need a stable Python-facing contract.

## Composition Strategy

To support arbitrary mixtures:

1. Python accepts isotope names and mass fractions.
2. Python parses `$MESA_DIR/data/chem_data/isotopes.data` and maps names to
   MESA `chem_id` values.
3. The Fortran wrapper builds:

```text
chem_id(species)
net_iso(num_chem_isos)
xa(species)
```

4. Wrapper passes those arrays to MESA public APIs.

This is implemented for EOS and KAP. Keep the Python parser because it makes
the user-facing API independent of extra Fortran string handling.

## RSP-Style EOS/KAP Scope

For an RSP-like code that already has `T`, `rho`, and a static composition at a
zone, the current wrapper set is enough for the MESA microphysics call:

```text
composition -> eosDT_get -> kap_get
```

This matches the direct RSP evaluation path:

```text
$MESA_DIR/star/private/rsp_step.f90
  do1_eos_and_kap
    -> eval_mesa_eos_and_kap

$MESA_DIR/star/private/rsp_eval_eos_and_kap.f90
  eval1_mesa_eos_and_kap
    -> get_eos / eosDT_get
    -> kap_get
```

The current Python equivalents are:

```python
eos = mesa.Eos()
kap = mesa.Kap()

eos_out = eos.dt_full(T=T, Rho=rho, comp=mix)
kap_out = kap.opacity_full(T=T, Rho=rho, comp=mix)
```

The EOS solve helpers are used when the Python code wants to reproduce the RSP
inverse-EOS paths, where one thermodynamic variable is unknown and MESA must
solve for it. Examples in `rsp_eval_eos_and_kap.f90` include:

```text
eval1_mesa_eosDEgas_and_kap -> solve_eos_given_DEgas
eval1_mesa_eosDE_and_kap    -> solve_eos_given_DE
set_Rho_for_new_Pgas        -> eosDT_get_Rho
set_T_for_new_egas          -> eosDT_get_T
set_T_for_new_Pgas          -> eosDT_get_T
set_T_for_new_energy        -> eosDT_get_T
```

Current implementation:

```text
Direct known-T,rho queries still use eosDT_get.
Inverse queries now expose eosDT_get_Rho and eosDT_get_T through Python.
```

## NET Scope Decision

NET is not needed for the current goal:

```text
given T, rho, and a static composition -> call EOS and KAP
```

The EOS/KAP public APIs need two composition-mapping arrays:

```text
chem_id(species)
net_iso(num_chem_isos)
```

Here `net_iso` means the lookup from a MESA chemistry isotope id to the local
species index used by the caller. It is not, by itself, a call to the NET
reaction network. pyfortmesa already builds this mapping directly from isotope
names and mass fractions, so it does not need `mesa-net` for EOS/KAP queries.

MESA RSP uses the same pattern. In:

```text
$MESA_DIR/star/private/rsp_eval_eos_and_kap.f90
```

the per-zone evaluation path imports CHEM/EOS/KAP support and calls EOS/KAP
with `chem_id`, `net_iso`, and `xa`. It does not call `net_get` or evolve
nuclear abundances in the EOS/KAP loop. The main RSP step calls:

```text
rsp_step.f90 -> do1_eos_and_kap -> eval_mesa_eos_and_kap
```

The one `use net` occurrence in the classic RSP path is in:

```text
$MESA_DIR/star/private/rsp.f90
```

where `build_rsp_model` calls `do_micro_change_net` to select/build the network
bookkeeping for the initial RSP model, defaulting to `o18_and_ne22.net` if the
user has not requested another net. That is setup for the model's species
arrays; it is not a per-zone nuclear burning calculation.

Decision:

```text
Do not develop NET further on this branch.
Do not require mesa-net in the current pyfortmesa MESA build.
Use CHEM/EOS/KAP for arbitrary static-composition EOS/KAP zone calls.
Treat NET as a later project for reaction rates, one-zone burning, and network
table management.
```

## Implementation Steps

1. Done: add one example `inlist_eos_and_kap` file with `&eos` and `&kap`.
2. Done: add a Meson helper that reads `$MESA_DIR` and checks:
   ```text
   $MESA_DIR/build/*/lib/pkgconfig
   pkg-config metadata for mesa-const/chem/eos/kap
   shared libraries referenced by those pkg-config files
   ```
3. Done: add optional Meson option:
   ```text
   -Dwith_mesa=true
   ```
4. Done: add `Chem` convenience handle and CHEM composition-info wrapper.
5. Done for EOS/KAP: add arbitrary-mixture helper shared by MESA-backed calls.
6. Done: add EOS wrapper and Python `Eos.dt`.
7. Done: add KAP wrapper and Python `Kap.opacity`.
8. Done: add full EOS and KAP output wrappers.
9. Done: add print-based tests/examples that skip unless
   `PYFORTMESA_WITH_MESA=1` and the MESA-enabled wheel is installed.
10. Done: use MESA `const_def` values in the hydrostatic example instead of
    hard-coded CGS constants.
11. Done in source: add persistent EOS/KAP handles.
12. Done in source: add EOS inverse solve wrappers.
13. Done in source: add explicit KAP Type2 controls.
14. Done in source: add explicit shutdown/cleanup wrappers for pyfortmesa's
    persistent MESA handles.
15. Done in source: add a text `.mod` saved-model reader and EOS timing example
    that can call every zone serially, with OpenMP threads via
    `OMP_NUM_THREADS`, or with `--nproc 10` process parallelism.
16. Done in build system: include F2PY's generated
    `*-f2pywrappers2.f90` outputs for EOS and KAP because those source files
    define wrapper-state Fortran modules.
17. Done in source: initialize MESA EOS/KAP handles before allocating
    `net_iso_store(num_chem_isos)`. `num_chem_isos` is populated by MESA CHEM
    initialization, so using it first caused `ierr=-2` before any real zone
    call in the saved-model EOS profile path.
18. Done in source: parallelize the saved-model EOS profile loop inside
    Fortran with OpenMP, following MESA star's pattern in
    `$MESA_DIR/star/private/star_utils.f90::foreach_cell` and
    `$MESA_DIR/star/private/micro.f90::do_eos`. The Python process stays single;
    `OMP_NUM_THREADS` controls the number of Fortran threads.
19. Done in source: make the profile thread sweep a normal runner option via
    `tests/mesa/run_eos_from_saved_model.sh --with-mesa --thread-sweep`.
20. Done in source: add phase-level profile timing and a KAP profile timing
    path. The KAP profile wrapper calls EOS internally for the electron state
    required by `kap_get`, so it is an EOS+KAP microphysics timing for opacity.
21. Done in source: add `--warmup` and `--repeat` profile timing controls so
    repeated calls keep MESA handles alive and shutdown is measured once at the
    end.
22. Done in source: add `mesa_eos_kap_profile_from_logs` so combined EOS+KAP
    timing avoids duplicate EOS work.
23. Leave NET and TURB as future projects.

## Verification Policy

Non-MESA checks can run normally:

```bash
python -m pyfortmesa
python tests/unit/test_module_import.py
```

MESA-linked checks should be opt-in:

```bash
tests/mesa/run_hydrostatic_structure.sh --with-mesa
```

Per project rule, Codex should not compile MESA or run MESA models unless the
user explicitly permits it. Building this package against an already-built MESA
tree is a separate step and should be requested explicitly.

## Current Decision

Proceed in this order on the current branch:

```text
chem -> composition helper -> eos -> kap
const -> constants helper
eos inverse solves -> KAP Type2 controls
```

Keep the base package installable without MESA. MESA-backed modules should be
optional and gated by an explicit build option. When enabled, support only the
new shared-library/pkg-config MESA layout and fail clearly for classic
static-only installs such as the inspected `mesa-r26.04.1` tree.

The current working slice is:

```text
MESA constants helper + isotope-name composition helper
  -> CHEM -> EOS direct/inverse -> KAP direct/Type2-controlled
```

Next implementation target:

```text
NET as a separate branch/project; real PyPI release later.
```
