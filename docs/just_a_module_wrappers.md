# MESA just-a-module wrapper plan

Branch: `just_a_module`

Goal: call selected MESA public module APIs from Python through small Fortran
wrappers.

## Shell setup

This branch assumes a new shared-library MESA build is selected by the user
environment:

```bash
echo $MESA_DIR
```

That environment should point at the MESA tree to wrap:

```bash
export MESA_DIR=/Users/owner/Documents/Software/dev/mesa_release/mesa_clean/main
```

That path is the current local dev source supported by this branch. Package code
should still read `$MESA_DIR` instead of hard-coding it.

The MESA SDK also needs to be active:

```bash
export MESASDK_ROOT=/Applications/mesasdk
source $MESASDK_ROOT/bin/mesasdk_init.sh
```

For supported MESA builds, module libraries advertise their include and link
flags through pkg-config files under:

```text
$MESA_DIR/build/*/lib/pkgconfig
```

A useful local check is:

```bash
export PKG_CONFIG_PATH=$(find "$MESA_DIR/build" -path "*/lib/pkgconfig" -type d | paste -sd: -)
pkg-config --cflags --libs mesa-const mesa-chem mesa-eos mesa-kap
```

Python helper:

```python
from pyfortmesa.mesa_support import mesa_dir, mesa_pkg_config_path

print(mesa_dir())
print(mesa_pkg_config_path())
```

## Source references

MESA docs:

- https://docs.mesastar.org/en/26.4.1/using_mesa/just_a_module.html
- https://doi.org/10.5281/zenodo.4763740

Those references explain the public-module pattern. They are not the build
target for this branch if the local tree is classic/static-only.

MESA public APIs to wrap first:

```text
$MESA_DIR/chem/public/chem_lib.f90 -> chem_init, basic_composition_info
$MESA_DIR/const/public/const_def.f90 -> standard_cgrav, crad, clight, solar units
$MESA_DIR/eos/public/eos_lib.f90  -> eos_init, alloc_eos_handle, eosDT_get
$MESA_DIR/eos/public/eos_def.f90  -> EOS result indices such as i_lnPgas
$MESA_DIR/kap/public/kap_lib.f90  -> kap_init, alloc_kap_handle, kap_get
$MESA_DIR/kap/public/kap_def.f90  -> KAP constants such as num_kap_fracs
```

The MESA sample programs are still the best usage examples:

```text
$MESA_DIR/eos/test/src/sample_eos.f90
$MESA_DIR/kap/test/src/sample_kap.f90
```

The Zenodo makefiles show the older static-link idea:

```text
sample Fortran source -> MESA include path -> MESA module libraries
```

For this repo, the supported equivalent is:

```text
Python
  -> F2PY extension
  -> small pyfortmesa Fortran wrapper
  -> MESA public API
  -> MESA module libraries found from $MESA_DIR/build/*/lib/pkgconfig
```

## Wrapper layout

Current wrapper files:

```text
src/pyfortmesa/fortran/CONST/mesa_const_public.f90
src/pyfortmesa/fortran/CHEM/mesa_chem_public.f90
src/pyfortmesa/fortran/EOS/mesa_eos_public.f90
src/pyfortmesa/fortran/KAP/mesa_kap_public.f90
src/pyfortmesa/mesa.py
src/pyfortmesa/mesa_support.py
```

`mesa_const_values` wraps selected MESA `const_def` values used by examples:

```text
standard_cgrav, crad, clight, Lsun, Rsun, Msun
```

The Python method is:

```python
mesa.constants()
```

`mesa_chem_composition_info` wraps `basic_composition_info` for an arbitrary
composition selected by MESA isotope names in Python. It returns:

```text
xh, xhe, xz, abar, zbar, z2bar, z53bar, ye, mass_correction, sumx
```

`mesa_eos_composition` wraps `eosDT_get` for an arbitrary composition selected
by MESA isotope names in Python. The Python side reads:

```text
$MESA_DIR/data/chem_data/isotopes.data
```

and passes MESA `chem_id` values and mass fractions through F2PY.

The composition data flow is:

```text
{"h1": 0.70, "he4": 0.28, "c12": 0.02}
  -> chem_id = [chem_get_nuclide_index("h1"), ...]
  -> net_iso(chem_id(i)) = i
  -> xa(i)
```

`mesa_eos_sample_composition` remains as a simple sample-composition wrapper:

```text
[h1, he4, c12, n14, o16, ne20, mg24]
```

It returns a small set of common EOS quantities:

```text
lnPgas, lnE, lnS, grad_ad, gamma1
```

`mesa_eos_composition_full` wraps the same `eosDT_get` call but returns the
full MESA result arrays:

```text
res(num_eos_basic_results)
dres_dlnRho(num_eos_basic_results)
dres_dlnT(num_eos_basic_results)
dres_dxa(num_eos_d_dxa_results, species)
```

The Python method is:

```python
mesa.Eos().dt_full(T=..., Rho=..., comp=...)
```

It returns dictionaries keyed by MESA EOS result names.

`mesa_kap_composition` wraps `kap_get` for the same named-composition path. It
first calls EOS so that KAP receives `lnfree_e`, `eta`, and their derivatives
from the EOS instead of using dummy values. `mesa_kap_sample_composition`
remains as the quick sample wrapper.

`mesa_kap_composition_full` returns the full direct `kap_get` outputs:

```text
kappa
dlnkap_dlnRho
dlnkap_dlnT
kap_fracs(lowT, highT, Type2, Compton)
dlnkap_dxa(species)
```

The Python method is:

```python
mesa.Kap().opacity_full(T=..., Rho=..., comp=...)
```

## Build and call

Do not make MESA a required dependency for the base package. The optional MESA
build path is:

```bash
export MESA_DIR=/Users/owner/Documents/Software/dev/mesa_release/mesa_clean/main
./mk mesa
./install
```

That is shorthand for building with:

```text
-Dwith_mesa=true
```

Python use:

```python
from pyfortmesa import mesa

# Input: MESA isotope names mapped to mass fractions. They must sum to 1.
mix = mesa.composition({"h1": 0.70, "he4": 0.28, "c12": 0.02})

eos_T = 1.0e7       # K
eos_rho = 1.0e2     # g/cm^3
kap_T = 1.0e6       # K
kap_rho = 1.0e-7    # g/cm^3

# Output: composition moments from MESA CHEM.
print(mesa.Chem().composition_info(mix))

# Output: selected constants from MESA const_def.
print(mesa.constants())

# Output: EOS returns lnPgas, lnE, lnS, grad_ad, and gamma1.
print(mesa.Eos().dt(T=eos_T, Rho=eos_rho, comp=mix))

# Output: KAP returns kappa, dlnkap_dlnRho, and dlnkap_dlnT.
print(mesa.Kap().opacity(T=kap_T, Rho=kap_rho, comp=mix))
```

Current limitation: the KAP handle uses `use_Type2_opacities = .false.` for
this first wrapper. That keeps the API simple while the composition and handle
setup are still being made general.

The existing toy Fortran extension remains the default build when `./mk` is run
without the `mesa` argument.
