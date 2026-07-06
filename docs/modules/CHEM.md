# CHEM coverage

Status: active in the optional MESA-enabled build.

Purpose: map isotope-name mass fractions to MESA `chem_id` values and compute
basic composition moments.

## Source

```text
$MESA_DIR/chem/public/chem_lib.f90
$MESA_DIR/data/chem_data/isotopes.data
src/pyfortmesa/fortran/CHEM/mesa_chem_public.f90
src/pyfortmesa/mesa.py
src/pyfortmesa/mesa_support.py
```

## Available Now

Python:

```python
from pyfortmesa import mesa

mix = mesa.composition({"h1": 0.70, "he4": 0.28, "c12": 0.02})
info = mesa.Chem().composition_info(mix)

print(info)
```

Python helpers:

```text
mesa.composition(...)
mesa.composition_info(...)
mesa.iso_id(...)
mesa.iso_ids(...)
mesa.isotope_index()
mesa.Chem().composition(...)
mesa.Chem().composition_info(...)
mesa.Chem().iso_id(...)
mesa.Chem().iso_ids(...)
```

Fortran wrapper:

```text
mesa_chem_composition_info -> basic_composition_info
mesa_chem_shutdown -> chem_shutdown
```

Returned fields:

```text
xh
xhe
xz
abar
zbar
z2bar
z53bar
ye
mass_correction
sumx
```

## Not Wrapped Yet

```text
chem_init
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

## Notes

`mesa.composition(...)` reads isotope names from MESA's `isotopes.data` and
builds:

```text
names -> chem_id -> xa
```

The EOS and KAP wrappers then build their local `net_iso` lookup from these
`chem_id` values. That lookup does not mean pyfortmesa is running MESA NET.

`mesa.shutdown(release_tables=True)` calls the CHEM shutdown wrapper after the
EOS/KAP handle cleanup. Normal `mesa.shutdown()` leaves CHEM table state loaded
for reuse in the same Python process.
