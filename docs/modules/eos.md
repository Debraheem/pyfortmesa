# eos

Status: active in the build for MESA calls.

Purpose: call MESA `eos` for known density, temperature, and static composition.

## Source

```text
$MESA_DIR/eos/public/eos_lib.f90
$MESA_DIR/eos/public/eos_def.f90
src/pyfortmesa/fortran/eos/mesa_eos_public.f90
src/pyfortmesa/mesa.py
src/pyfortmesa/mesa_support.py
```

## Python interface

Python:

```python
from pyfortmesa import mesa

mesa.set_inlist("inlist_eos_and_kap")
mix = mesa.composition({"h1": 0.70, "he4": 0.28, "c12": 0.02})
T = 1.0e7
rho = 1.0e2

eos = mesa.Eos()
small = eos.dt(T=T, Rho=rho, comp=mix)
full = eos.dt_full(T=T, Rho=rho, comp=mix)
rho_solve = eos.solve_rho(
    T=T,
    other="lnPgas",
    other_value=small["lnPgas"],
    Rho_guess=0.8 * rho,
    comp=mix,
)
T_solve = eos.solve_t(
    Rho=rho,
    other="lnPgas",
    other_value=small["lnPgas"],
    T_guess=0.9 * T,
    comp=mix,
)

print(small)
print(full["results"])
print(rho_solve["Rho"])
print(T_solve["T"])
```

Python helpers:

```text
mesa.Eos().dt(...)
mesa.Eos().dt_full(...)
mesa.Eos().dt_profile(...)
mesa.Eos().dt_profile_from_logs(...)
mesa.Eos().solve_rho(...)
mesa.Eos().solve_t(...)
mesa.eos_dt(...)
mesa.eos_dt_full(...)
mesa.eos_dt_profile(...)
mesa.eos_dt_profile_from_logs(...)
mesa.eos_solve_rho(...)
mesa.eos_solve_t(...)
```

Fortran wrappers:

```text
mesa_eos_sample_composition -> eosDT_get
mesa_eos_composition -> eosDT_get
mesa_eos_composition_full -> eosDT_get
mesa_eos_profile_from_logs -> eosDT_get once per profile zone
mesa_eos_solve_rho -> eosDT_get_Rho
mesa_eos_solve_t -> eosDT_get_T
```

Small output:

```text
lnPgas
lnE
lnS
grad_ad
gamma1
```

Full result vector:

```text
lnPgas
lnE
lnS
mu
lnfree_e
eta
grad_ad
chiRho
chiT
Cp
Cv
dE_dRho
dS_dT
dS_dRho
gamma1
gamma3
phase
latent_ddlnT
latent_ddlnRho
HELM
OPAL/SCVH
FreeEOS
PC
Skye
CMS
ideal
```

Full derivative output:

```text
d_dlnRho[result_name]
d_dlnT[result_name]
d_dxa["lnPgas"][isotope_name]
d_dxa["lnE"][isotope_name]
```

## Not provided

```text
eos_init
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

## Notes

`eos` handles are persistent inside the Fortran wrapper for the Python process.
The first eos call initializes MESA and allocates the handle; later calls reuse
that handle.

Use the top-level cleanup call when finished:

```python
mesa.shutdown()
```

This frees pyfortmesa's persistent eos/kap handles. Use
`mesa.shutdown(release_tables=True)` only when no other code in the Python
process is using MESA and you also want to release loaded MESA table state.

`eos` controls can come from the shared MESA-style inlist:

```python
mesa.set_inlist("inlist_eos_and_kap")
```

The file contains an `&eos` namelist and should be set before the first eos/kap
call in the Python process. If no inlist is set, MESA `eos` module defaults are
used.

`solve_rho` and `solve_t` use MESA's `eosDT_get_Rho` and `eosDT_get_T`. The
`other` selector may be a result name such as `lnPgas` or a 1-based `eos_def`
index. For logarithmic result names, pass MESA's natural-log value; for example
use `math.log(Pgas)` when solving from gas pressure.

`free_eos_handle` and `eos_shutdown` are wrapped internally for
`mesa.shutdown()` rather than exposed as separate public Python functions.
