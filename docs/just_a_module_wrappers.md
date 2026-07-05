# MESA just-a-module wrapper plan

Branch: `just_a_module`

Goal: call selected MESA public module APIs from Python through small Fortran
wrappers.

## Shell setup

This branch assumes MESA is selected by the user environment:

```bash
mesa-r26.04.1
echo $MESA_DIR
```

That alias should export something like:

```bash
export MESA_DIR=/Users/owner/Documents/Software/mesa-r26.04.1
```

The MESA SDK also needs to be active:

```bash
export MESASDK_ROOT=/Applications/mesasdk
source $MESASDK_ROOT/bin/mesasdk_init.sh
```

For current MESA builds, module libraries advertise their include and link flags
through pkg-config files under:

```text
$MESA_DIR/build/*/lib/pkgconfig
```

A useful local check is:

```bash
export PKG_CONFIG_PATH=$(find "$MESA_DIR/build" -path "*/lib/pkgconfig" -type d | paste -sd: -)
pkg-config --cflags --libs --static mesa-eos
pkg-config --cflags --libs --static mesa-kap
```

Python helper:

```python
from pyfortmesa.mesa_env import mesa_dir, mesa_pkg_config_path

print(mesa_dir())
print(mesa_pkg_config_path())
```

## Source references

MESA docs:

- https://docs.mesastar.org/en/26.4.1/using_mesa/just_a_module.html
- https://doi.org/10.5281/zenodo.4763740

MESA public APIs to wrap first:

```text
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

The Zenodo makefiles show the older idea:

```text
sample Fortran source -> MESA include path -> MESA module libraries
```

For this repo, the modern equivalent should be:

```text
Python
  -> F2PY extension
  -> small pyfortmesa Fortran wrapper
  -> MESA public API
  -> MESA module libraries found from $MESA_DIR/build/*/lib/pkgconfig
```

## Wrapper layout

Current skeleton files:

```text
src/pyfortmesa/fortran/EOS/mesa_eos_public.f90
src/pyfortmesa/fortran/KAP/mesa_kap_public.f90
```

`mesa_eos_7` wraps `eosDT_get` for a seven-isotope composition:

```text
[h1, he4, c12, n14, o16, ne20, mg24]
```

It returns a small set of common EOS quantities:

```text
lnPgas, lnE, lnS, grad_ad, gamma1
```

`mesa_kap_7` wraps `kap_get` for the same composition. It first calls EOS so
that KAP receives `lnfree_e`, `eta`, and their derivatives from the EOS instead
of using dummy values.

## Next implementation step

Do not make MESA a required dependency for the base package. Add an optional
Meson build path later, probably something like:

```text
-Dwith_mesa=true
```

When enabled, Meson should:

1. require `$MESA_DIR`
2. require pkg-config visibility for `mesa-eos` and/or `mesa-kap`
3. build F2PY wrappers for the files under `fortran/EOS` and `fortran/KAP`
4. expose Python functions with ordinary Python defaults for the composition

Until then, the existing toy Fortran extension remains the default build.
