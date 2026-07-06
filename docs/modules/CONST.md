# CONST coverage

Status: active in the optional MESA-enabled build.

Purpose: expose selected values from MESA `const_def` so examples and tests do
not carry local hard-coded CGS constants.

## Source

```text
$MESA_DIR/const/public/const_def.f90
src/pyfortmesa/fortran/CONST/mesa_const_public.f90
src/pyfortmesa/mesa.py
src/pyfortmesa/mesa_support.py
```

## Available Now

Python:

```python
from pyfortmesa import mesa

constants = mesa.constants()
print(constants["standard_cgrav"])
```

Fortran wrapper:

```text
mesa_const_values
```

Returned fields:

```text
standard_cgrav
crad
clight
Lsun
Rsun
Msun
```

## Not Wrapped Yet

Most of `const_def` is not exposed. Add constants only when a Python example or
wrapper needs them, instead of mirroring the whole MESA constant namespace.

Likely future additions:

```text
boltzm
amu
avo
qe
hplanck
sigma
secday
secyer
pi
```

## Notes

The non-MESA teaching extension still has its own tiny
`src/pyfortmesa/fortran/const_def.f90` for `real(dp)`. That file is only a local
kind definition for the toy Fortran example. It is not a source of physical
constants.
