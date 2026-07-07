# const

Status: active in the `./mk mesa` build.

Purpose: expose MESA `const_def` scalar real constants in Python so examples,
tests, and solver code use the same CGS values as the linked MESA build.

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

Returns: a dictionary of scalar `real(dp), parameter` constants from MESA
`const_def`. Values use the MESA names and cgs/MESA units.

| key | units | meaning |
| --- | --- | --- |
| `pi` | dimensionless | pi |
| `pi2` | dimensionless | `pi*pi` |
| `pi4` | dimensionless | `4*pi` |
| `eulercon` | dimensionless | Euler-Mascheroni constant |
| `eulernum` | dimensionless | base of natural logarithms |
| `ln2` | dimensionless | `log(2)` |
| `ln3` | dimensionless | `log(3)` |
| `lnPi` | dimensionless | `log(pi)` |
| `ln10` | dimensionless | `log(10)` |
| `iln10` | dimensionless | `1/log(10)` |
| `a2rad` | `rad deg^-1` | degrees to radians conversion |
| `rad2a` | `deg rad^-1` | radians to degrees conversion |
| `one_third` | dimensionless | `1/3` |
| `two_thirds` | dimensionless | `2/3` |
| `four_thirds` | dimensionless | `4/3` |
| `five_thirds` | dimensionless | `5/3` |
| `one_sixth` | dimensionless | `1/6` |
| `four_thirds_pi` | dimensionless | `4*pi/3` |
| `ln4pi3` | dimensionless | `log(4*pi/3)` |
| `two_13` | dimensionless | `2^(1/3)` |
| `four_13` | dimensionless | `4^(1/3)` |
| `sqrt2` | dimensionless | `sqrt(2)` |
| `sqrt_2_div_3` | dimensionless | `sqrt(2/3)` |
| `avo` | `mol^-1` | Avogadro constant |
| `amu` | `g` | atomic mass unit |
| `clight` | `cm s^-1` | speed of light in vacuum |
| `qe` | `esu` | elementary charge |
| `kerg` | `erg K^-1` | Boltzmann constant |
| `boltzm` | `erg K^-1` | Boltzmann constant alias |
| `planck_h` | `erg s` | Planck constant |
| `hbar` | `erg s` | reduced Planck constant |
| `cgas` | `erg K^-1 mol^-1` | ideal gas constant |
| `ev2erg` | `erg eV^-1` | electron-volt to erg conversion |
| `mev_to_ergs` | `erg MeV^-1` | MeV to erg conversion |
| `mev_amu` | `erg g^-1` | MeV per amu to specific energy conversion |
| `mev2gr` | `g MeV^-1` | MeV to mass conversion |
| `Qconv` | `erg mol^-1 MeV^-1` | MeV per particle to erg per mole conversion |
| `kev` | `eV K^-1` | temperature to electron-volt conversion |
| `boltz_sigma` | `erg cm^-2 s^-1 K^-4` | Stefan-Boltzmann constant |
| `crad` | `erg cm^-3 K^-4` | radiation density constant `a`; `Prad = crad*T**4/3` |
| `au` | `cm` | astronomical unit |
| `pc` | `cm` | parsec |
| `dayyer` | `day yr^-1` | days per Julian year |
| `secday` | `s day^-1` | seconds per day |
| `secyer` | `s yr^-1` | seconds per Julian year |
| `ly` | `cm` | light year |
| `mn` | `g` | neutron mass |
| `mp` | `g` | proton mass |
| `me` | `g` | electron mass |
| `rbohr` | `cm` | Bohr radius |
| `fine` | dimensionless | fine-structure constant |
| `hion` | `eV` | Rydberg ionization energy |
| `sige` | `cm^2` | Thomson cross section |
| `weinberg_theta` | dimensionless | `sin^2(theta_weinberg)` |
| `num_neu_fam` | dimensionless | number of neutrino families |
| `standard_cgrav` | `cm^3 g^-1 s^-2` | gravitational constant |
| `mu_sun` | `cm^3 s^-2` | solar gravitational parameter |
| `mu_earth` | `cm^3 s^-2` | Earth gravitational parameter |
| `mu_jupiter` | `cm^3 s^-2` | Jupiter gravitational parameter |
| `agesun` | `yr` | solar age |
| `Msun` | `g` | solar gravitational mass |
| `Rsun` | `cm` | solar radius |
| `Lsun` | `erg s^-1` | solar luminosity |
| `Teffsun` | `K` | solar effective temperature |
| `loggsun` | `log10(cm s^-2)` | solar surface gravity log |
| `mbolsun` | `mag` | solar bolometric magnitude |
| `m_earth` | `g` | Earth mass |
| `r_earth` | `cm` | Earth equatorial radius |
| `r_earth_polar` | `cm` | Earth polar radius |
| `m_jupiter` | `g` | Jupiter mass |
| `r_jupiter` | `cm` | Jupiter equatorial radius |
| `r_jupiter_polar` | `cm` | Jupiter polar radius |
| `semimajor_axis_jupiter` | `cm` | Jupiter semimajor axis |
| `arg_not_provided` | sentinel | MESA omitted-argument sentinel |
| `missing_value` | sentinel | alias for `arg_not_provided` |

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
`src/pyfortmesa/mesa_support.py`. The Fortran vector order must match that tuple.

## Common mistakes

- `crad` is the radiation density constant `a`, not radiation pressure itself.
  Use `Prad = crad*T**4/3`.
- MESA EOS output `lnPgas` is gas pressure. Add `Prad` yourself when you want
  total pressure.
- All physical constants returned here use cgs/MESA units.

## Not included

| MESA item | Reason |
| --- | --- |
| precision kind parameters such as `sp`, `dp`, `qp`, `i1`, `i2`, `i4`, `i8` | Compile-time Fortran kind tags, not runtime physical constants. |
| `strlen` and `max_extra_inlists` | Fortran/module configuration integers, not scalar real constants. |
| runtime path/cache variables such as `mesa_dir` and `mesa_caches_dir` | Mutable module state; use environment helpers instead. |
| mixing-type integer enums | Star/mesh classification constants, not needed by the current const/chem/eos/kap wrapper surface. |
