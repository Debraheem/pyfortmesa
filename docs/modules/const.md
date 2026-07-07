# const

Status: active in the `./mk mesa` build.

Purpose: expose selected MESA `const_def` values in CGS units so examples and
tests do not carry local hard-coded constants.

## Fast start

```python
from pyfortmesa import mesa

constants = mesa.constants()

T = 1.0e7
Prad = constants["crad"] * T**4 / 3.0
print(Prad)
```

## Public API

### `mesa.constants()`

Signature:

```python
mesa.constants() -> dict[str, float]
```

Inputs: none.

Returns: a dictionary of selected CGS constants from MESA `const_def`.

| key | units | meaning |
| --- | --- | --- |
| `standard_cgrav` | `cm^3 g^-1 s^-2` | gravitational constant |
| `crad` | `erg cm^-3 K^-4` | radiation density constant `a`; `Prad = crad*T**4/3` |
| `clight` | `cm s^-1` | speed of light in vacuum |
| `Lsun` | `erg s^-1` | solar luminosity |
| `Rsun` | `cm` | solar radius |
| `Msun` | `g` | solar gravitational mass |

Example:

```python
import numpy as np

from pyfortmesa import mesa

constants = mesa.constants()
eos = mesa.Eos()
mix = mesa.composition({"h1": 0.70, "he4": 0.28, "c12": 0.02})

T = 1.0e7
rho = 1.0e2
out = eos.dt_full(T=T, Rho=rho, comp=mix)

Pgas = np.exp(out["results"]["lnPgas"])
Prad = constants["crad"] * T**4 / 3.0
Ptot = Pgas + Prad
```

## Source mapping

```text
$MESA_DIR/const/public/const_def.f90
src/pyfortmesa/fortran/const/mesa_const_public.f90
src/pyfortmesa/mesa.py
src/pyfortmesa/mesa_support.py
```

Fortran wrapper:

```text
mesa_const_values
```

Python output order is defined by `MESA_CONSTANT_NAMES` in
`src/pyfortmesa/mesa_support.py`.

## Common mistakes

- `crad` is the radiation density constant `a`, not radiation pressure itself.
  Use `Prad = crad*T**4/3`.
- `mesa.constants()` returns only selected values, not the whole MESA
  `const_def` namespace.
- All returned values are CGS constants.

## Not included

| MESA item | Reason |
| --- | --- |
| all of `const_def` | Too broad; pyfortmesa is a selected microphysics wrapper, not a namespace mirror. |
| constants with no current example or wrapper use | Add them when a Python workflow needs them, and document units in this page at the same time. |
