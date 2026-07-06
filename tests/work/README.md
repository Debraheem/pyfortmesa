# Simple work example

This directory is for small, readable examples. It is not the timing suite.

After installing a build for MESA calls for your `MESA_DIR`:

```bash
conda activate pyfortmesa
export MESA_DIR=/path/to/current/mesa
./mk mesa
./install
tests/work/run_simple_chem_eos_kap.sh
```

The example does four things:

1. Sets the cache root and `inlist_eos_and_kap` once.
2. Builds one composition from isotope-name mass fractions.
3. Calls `chem`, scalar `eos`, and scalar `kap`.
4. Calls the combined profile wrapper with precomputed isotope ids and a
   Fortran-ordered `xa(species, zones)` array.

That last call is the pattern to copy when both eos and kap are needed across a
profile.
