# const

Status: active in the build for MESA calls.

Purpose: expose selected values from MESA `const_def` so examples and tests do
not carry local hard-coded CGS constants.

## Source

```text
$MESA_DIR/const/public/const_def.f90
src/pyfortmesa/fortran/const/mesa_const_public.f90
src/pyfortmesa/mesa.py
src/pyfortmesa/mesa_support.py
```

## Python interface

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

## Not provided

Most of `const_def` is not exposed. Add constants only when a Python example or
wrapper needs them, instead of mirroring the whole MESA constant namespace.
