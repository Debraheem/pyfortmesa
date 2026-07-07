# chem

Status: active in the `./mk mesa` build. The isotope-name helpers also work in
plain Python as long as `MESA_DIR` points to a MESA tree with
`data/chem_data/isotopes.data`.

Purpose: map isotope-name mass fractions to MESA `chem_id` values and compute
basic composition moments with MESA `chem`.

## Fast start

```python
from pyfortmesa import mesa

mix = mesa.composition({"h1": 0.70, "he4": 0.28, "c12": 0.02})
info = mesa.Chem().composition_info(mix)

print(mix.names)
print(mix.chem_id)
print(info["abar"])
```

## Composition object

`mesa.composition(...)` returns a `Composition` object with these fields:

| field | units | shape | meaning |
| --- | --- | --- | --- |
| `names` | none | `(species,)` | MESA isotope names, normalized to lower case |
| `chem_id` | MESA id | `(species,)` | 1-based MESA isotope ids from `isotopes.data` |
| `xa` | mass fraction | `(species,)` | mass fractions in the same order as `names` |
| `species` | count | scalar | number of isotopes in the composition |

Scalar EOS/KAP helpers accept a `Composition` directly as `comp=mix`. Profile
helpers take the same information split into `chem_id_values` and
`xa(species, nzones)`.

Fixed-composition profile layout:

```python
import numpy as np

mix = mesa.composition({"h1": 0.70, "he4": 0.28, "c12": 0.02})
nzones = 1000
xa = np.asfortranarray(
    np.broadcast_to(mix.xa[:, None], (mix.species, nzones))
)
```

Zone-dependent composition layout:

```python
isotope_names = ("h1", "he4", "c12")
chem_id_values = mesa.iso_ids(isotope_names)

# caller layout: (nzones, species)
xa_by_zone = np.asarray(xa_by_zone, dtype=np.float64)

# pyfortmesa profile layout: (species, nzones)
xa = np.asfortranarray(xa_by_zone.T)
```

## Public API

### `mesa.composition(...)`

Signature:

```python
mesa.composition(
    mass_fractions: Mapping[str, float],
    *,
    normalize: bool = False,
) -> mesa.Composition
```

Inputs:

| argument | units | shape | meaning |
| --- | --- | --- | --- |
| `mass_fractions` | mass fraction | mapping | isotope name to mass fraction |
| `normalize` | bool | scalar | normalize values to sum to one if true |

Returns: `Composition`.

The input isotope names must exist in MESA `isotopes.data`. Values must be
finite and non-negative. They must sum to one unless `normalize=True`.

### `mesa.composition_info(...)`

Signature:

```python
mesa.composition_info(
    comp: Composition | Mapping[str, float] | Iterable[float] | None,
) -> dict[str, float]
```

Inputs:

| argument | units | shape | meaning |
| --- | --- | --- | --- |
| `comp` | mass fraction | `Composition`, mapping, legacy vector, or `None` | composition to summarize |

Returns: MESA composition moments.

| key | units | meaning |
| --- | --- | --- |
| `xh` | mass fraction | hydrogen mass fraction |
| `xhe` | mass fraction | helium mass fraction |
| `xz` | mass fraction | metal mass fraction |
| `abar` | amu-like mean | mean atomic mass |
| `zbar` | charge | mean charge |
| `z2bar` | charge squared | mean charge squared |
| `z53bar` | charge power | mean `Z^(5/3)` |
| `ye` | electrons per baryon | electron fraction |
| `mass_correction` | dimensionless | MESA mass correction |
| `sumx` | mass fraction | sum of mass fractions |

Example:

```python
mix = mesa.composition({"h1": 0.70, "he4": 0.28, "c12": 0.02})
info = mesa.composition_info(mix)
print(info["xh"], info["abar"], info["sumx"])
```

### `mesa.composition_info_full(...)`

Signature:

```python
mesa.composition_info_full(
    comp: Composition | Mapping[str, float] | Iterable[float] | None,
) -> dict[str, float | dict[str, float]]
```

Inputs: same as `mesa.composition_info(...)`.

Returns: the same scalar moments plus MESA composition partial derivatives in
the input species order.

| key | units | shape | meaning |
| --- | --- | --- | --- |
| `dabar_dx` | derivative | `(species,)` by isotope name | derivative of `abar` with respect to mass fraction |
| `dzbar_dx` | derivative | `(species,)` by isotope name | derivative of `zbar` with respect to mass fraction |
| `dmc_dx` | derivative | `(species,)` by isotope name | derivative of `mass_correction` with respect to mass fraction |

Example:

```python
mix = mesa.composition({"h1": 0.70, "he4": 0.28, "c12": 0.02})
info = mesa.composition_info_full(mix)
print(info["dabar_dx"]["h1"])
```

### `mesa.iso_id(...)`

Signature:

```python
mesa.iso_id(name: str) -> int
```

Returns the MESA 1-based `chem_id` for one isotope name.

Example:

```python
ih1 = mesa.iso_id("h1")
```

### `mesa.iso_ids(...)`

Signature:

```python
mesa.iso_ids(names: Iterable[str]) -> tuple[int, ...]
```

Returns MESA 1-based `chem_id` values in the same order as `names`.

Example:

```python
isotope_names = ("h1", "he4", "c12")
chem_id_values = mesa.iso_ids(isotope_names)
```

### `mesa.isotope_index()`

Signature:

```python
mesa.isotope_index() -> dict[str, int]
```

Returns the full isotope-name to `chem_id` mapping read from
`$MESA_DIR/data/chem_data/isotopes.data`.

### `mesa.sample_composition(...)`

Signature:

```python
mesa.sample_composition(primary: str = "c12") -> np.ndarray
```

Returns a legacy seven-isotope mass-fraction vector in this order:

```text
h1, he4, c12, n14, o16, ne20, mg24
```

Use `mesa.composition(...)` for new code. Keep `sample_composition(...)` for
small legacy examples that expect the fixed seven-isotope order.

### `mesa.Chem()`

`mesa.Chem()` is a small class wrapper around the same helpers:

```python
chem = mesa.Chem()
mix = chem.composition({"h1": 0.70, "he4": 0.28, "c12": 0.02})
info = chem.composition_info(mix)
full_info = chem.composition_info_full(mix)
ids = chem.iso_ids(mix.names)
```

Methods:

```text
Chem().composition(...)
Chem().composition_info(...)
Chem().composition_info_full(...)
Chem().iso_id(...)
Chem().iso_ids(...)
```

## Source mapping

```text
$MESA_DIR/chem/public/chem_lib.f90
$MESA_DIR/data/chem_data/isotopes.data
src/pyfortmesa/fortran/chem/mesa_chem_public.f90
src/pyfortmesa/mesa.py
src/pyfortmesa/mesa_support.py
```

Fortran wrappers:

```text
mesa_chem_composition_info -> basic_composition_info
mesa_chem_composition_info_full -> composition_info
mesa_chem_shutdown -> chem_shutdown
```

`mesa_chem_shutdown` is not a public Python function. It is called by
`mesa.shutdown(release_tables=True)`.

## Common mistakes

- `chem_id` is an isotope id, not a mass fraction.
- Scalar helpers accept `comp=mix`, but profile helpers need
  `chem_id_values` and `xa(species, nzones)`.
- `mesa.composition(...)` does not run MESA `net`. It only maps isotope names
  and mass fractions into the layout expected by the EOS/KAP wrappers.

## Other CHEM candidates

The main MESA CHEM derivative path is exposed through
`mesa.composition_info_full(...)`, which wraps MESA `composition_info` and
returns `dabar_dx`, `dzbar_dx`, and `dmc_dx`.

Solar abundance lookup helpers and nuclear-data helpers are also available in
MESA, but they need a clearer Python shape before they should be public API.

## Not included

| MESA item | Reason |
| --- | --- |
| `chem_init` | Internal setup called by wrappers as needed; not useful as a Python user call. |
| `chem_shutdown` | Exposed through `mesa.shutdown(release_tables=True)` instead of a raw shutdown function. |
| `chem_get_solar`, `chem_Xsol`, `lodders03_element_atom_percent` | Solar abundance data; should be a deliberate abundance-table API, not one-off scalar wrappers. |
| `chem_get_element_id`, `generate_nuclide_names`, `generate_long_nuclide_names`, `lookup_ZN`, `lookup_ZN_isomeric_state` | Name/id conversion helpers; Python already reads isotope names, and string-array wrappers need careful shape handling. |
| `binding_energy`, `get_mass_excess`, `get_Q`, `get_partition_fcn_indx`, `get_stable_mass_frac` | Nuclear-data utilities; belong to a broader nuclear data API, not the current microphysics wrapper scope. |
| `generate_nuclide_set`, `get_nuclide_index_in_set`, `rates_category_id` | More MESA-internal than user-facing for the current package. |
