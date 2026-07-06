# KAP coverage

Status: active in the optional MESA-enabled build.

Purpose: call MESA opacity for known density, temperature, and static
composition. The wrapper calls EOS first so KAP receives MESA electron
quantities.

## Source

```text
$MESA_DIR/kap/public/kap_lib.f90
$MESA_DIR/kap/public/kap_def.f90
src/pyfortmesa/fortran/KAP/mesa_kap_public.f90
src/pyfortmesa/mesa.py
src/pyfortmesa/mesa_support.py
```

## Available Now

Python:

```python
from pyfortmesa import mesa

mesa.set_inlist("inlist_eos_and_kap")
mix = mesa.composition({"h1": 0.70, "he4": 0.28, "c12": 0.02})
T = 1.0e6
rho = 1.0e-7

kap = mesa.Kap()
kap_type2 = mesa.Kap(use_type2=True, zbase=0.02)
small = kap.opacity(T=T, Rho=rho, comp=mix)
full = kap.opacity_full(T=T, Rho=rho, comp=mix)
type2_full = kap_type2.opacity_full(T=T, Rho=rho, comp=mix)

print(small)
print(full["kap_fracs"])
print(type2_full["kap_fracs"])
```

Python helpers:

```text
mesa.Kap().opacity(...)
mesa.Kap().opacity_full(...)
mesa.Kap().opacity_profile(...)
mesa.Kap().opacity_profile_from_logs(...)
mesa.Kap().eos_kap_profile(...)
mesa.Kap().eos_kap_profile_from_logs(...)
mesa.Kap(use_type2=True, zbase=...).opacity_full(...)
mesa.kap_opacity(...)
mesa.kap_opacity_full(...)
mesa.kap_opacity_profile(...)
mesa.kap_opacity_profile_from_logs(...)
mesa.eos_kap_profile(...)
mesa.eos_kap_profile_from_logs(...)
```

Fortran wrappers:

```text
mesa_kap_sample_composition -> kap_get
mesa_kap_composition -> kap_get
mesa_kap_composition_full -> kap_get
mesa_kap_composition_with_controls -> kap_get
mesa_kap_composition_full_with_controls -> kap_get
mesa_kap_profile_from_logs -> EOS state then kap_get once per profile zone
mesa_eos_kap_profile_from_logs -> EOS and kap_get once per profile zone
```

Small output:

```text
kappa
dlnkap_dlnRho
dlnkap_dlnT
```

Full output:

```text
kappa
dlnkap_dlnRho
dlnkap_dlnT
kap_fracs["lowT"]
kap_fracs["highT"]
kap_fracs["Type2"]
kap_fracs["Compton"]
dlnkap_dxa[isotope_name]
```

## Not Wrapped Yet

```text
kap_init
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

## Notes

KAP handles are persistent inside the Fortran wrapper for the Python process.
The first KAP call initializes MESA EOS/KAP and allocates handles; later calls
reuse those handles.

Use the top-level cleanup call when finished:

```python
mesa.shutdown()
```

This frees pyfortmesa's persistent KAP handle and the EOS handle owned by the
KAP wrapper. Use `mesa.shutdown(release_tables=True)` only when no other code in
the Python process is using MESA and you also want to release loaded MESA table
state.

KAP controls have two supported paths:

```python
# Path A: one MESA-style file with both &eos and &kap namelists.
mesa.set_inlist("inlist_eos_and_kap")
kap = mesa.Kap()

# Path B: Python KAP overrides.
kap = mesa.Kap(use_type2=True, zbase=0.02)
```

The precedence is:

```text
MESA kap.defaults
  -> optional shared inlist_eos_and_kap
  -> optional Python KAP overrides
```

Available Type2-related Python controls:

```text
use_type2
zbase
use_zbase_for_type1
type2_full_off_X
type2_full_on_X
type2_full_off_dZ
type2_full_on_dZ
```

`None` for a threshold means leave the corresponding MESA default value on the
KAP handle, including values read from `inlist_eos_and_kap`.

`free_kap_handle`, `kap_shutdown`, and the KAP-owned EOS handle cleanup are
wrapped internally for `mesa.shutdown()` rather than exposed as separate public
Python functions.

If no inlist is set and no Python override is given, pyfortmesa keeps Type2 off
so ordinary KAP calls do not require `Zbase`. If an inlist is set, `mesa.Kap()`
leaves Type2 to the inlist unless Python keywords override it.
