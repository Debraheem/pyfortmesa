# pyfortmesa [![Repo Status][status-badge]][status-link] [![Version][version-badge]][version-link] [![Docs][docs-badge]][docs-link] [![Python][python-badge]][python-link] [![MESA][mesa-badge]][mesa-link] [![License][license-badge]][license-link]

[status-link]: https://www.repostatus.org/#experimental
[status-badge]: https://img.shields.io/badge/repo_status-experimental-orange.svg
[version-link]: https://github.com/Debraheem/pyfortmesa/releases/tag/v0.4.0
[version-badge]: https://img.shields.io/github/v/tag/Debraheem/pyfortmesa?label=version
[docs-link]: https://debraheem.github.io/pyfortmesa/
[docs-badge]: https://github.com/Debraheem/pyfortmesa/actions/workflows/pages.yml/badge.svg?branch=main
[python-link]: https://www.python.org/
[python-badge]: https://img.shields.io/badge/python-%3E%3D3.10-blue.svg
[mesa-link]: https://github.com/MESAHub/mesa
[mesa-badge]: https://img.shields.io/badge/MESA-eos%2Fkap-4c78a8.svg
[license-link]: https://www.gnu.org/licenses/lgpl-3.0.en.html
[license-badge]: https://img.shields.io/badge/license-LGPL--3.0--only-blue.svg

Author: [Ebraheem Farag](https://github.com/Debraheem)

⚠️ **Warning: Experimental** ⚠️

This package is under active development and the Python API may still change.

`pyfortmesa` is a focused Python wrapper for selected MESA microphysics calls.
It currently wraps the MESA `const`, `chem`, `eos`, and `kap` modules, with a
Python API for scalar calls and batched profile calls.

This is not a general MESA module reader. The point is to make repeated eos/kap
calls from Python cheap enough to use inside real model-building code: cache the
MESA setup, keep handles alive, batch zones into one Fortran call, and let
OpenMP parallelize the zone loop. For general access to arbitrary MESA modules,
use [pyMesa](https://github.com/rjfarmer/pyMesa).

`pyfortmesa` does not build or install MESA. Build MESA separately, then point
`MESA_DIR` at that tree.

## Documentation

Documentation: https://debraheem.github.io/pyfortmesa/

Useful source files:

- Usage examples: `docs/usage.md`
- Module reference: `docs/modules/README.md`
- Test runner notes: `docs/testing.md`
- Simple MESA work example: `tests/work/README.md`
- MESA test scripts: `tests/mesa/README.md`
- Docs publishing: `docs/publishing.md`

Build the local documentation site with:

```bash
python -m pip install -r requirements-dev.txt
mkdocs serve
```

The GitHub Pages workflow is `.github/workflows/pages.yml`. In the GitHub repo,
set Pages -> Build and deployment -> Source to `GitHub Actions`.

## Installation

There are two normal install paths.

### Python install

This is the usual Python package install. Use it when you want to import
`pyfortmesa`, read the docs, or use code that does not call MESA's compiled
`const`, `chem`, `eos`, or `kap` routines.

Until `pyfortmesa` is on PyPI, install it from GitHub:

```bash
python -m pip install "git+https://github.com/Debraheem/pyfortmesa.git@v0.4.0"
```

or from a local checkout:

```bash
python -m pip install .
```

This installs the Python files and `numpy`. It does not compile or include the
MESA wrapper extension modules, so it is not enough for real MESA eos/kap calls.

A quick import check is:

```bash
python -m pyfortmesa
```

Expected output:

```text
pyfortmesa: MESA wrapper package
public module: pyfortmesa.mesa
```

### Build for MESA calls

Use this when Python code will call MESA `const`, `chem`, `eos`, or `kap`.
This build is local to your MESA checkout because the compiled wrapper modules
must link against the shared MESA libraries in your `MESA_DIR`.

This repo uses a local wheel for MESA calls because pip installs compiled
extension modules from a built `.whl` file, and those modules have to be built
against the MESA libraries in your `MESA_DIR`.

Use a recent MESA tree with shared module libraries and pkg-config files under:

```text
$MESA_DIR/build/*/lib/pkgconfig/mesa-*.pc
```

Build and install the package for MESA calls with:

```bash
conda activate pyfortmesa
python -m pip install -r requirements-dev.txt
export MESASDK_ROOT=/Applications/mesasdk
source $MESASDK_ROOT/bin/mesasdk_init.sh
export MESA_DIR=/path/to/current/mesa
./mk mesa
./install
```

`./mk mesa` finds the MESA pkg-config files and builds `dist/pyfortmesa-*.whl`
with the compiled `const`, `chem`, `eos`, and `kap` wrappers. `./install`
installs that build into the active Python environment.

A useful check before building is:

```bash
echo $MESA_DIR
export PKG_CONFIG_PATH=$(find "$MESA_DIR/build" -path "*/lib/pkgconfig" -type d | paste -sd: -)
pkg-config --cflags --libs mesa-const mesa-chem mesa-eos mesa-kap
```

Classic static MESA installs are not supported by this wrapper. The package
should fail clearly for those layouts rather than trying to link them statically.

### Development setup

Use this when editing the package, building docs, or checking package builds:

```bash
conda activate pyfortmesa
python -m pip install -r requirements-dev.txt
python -m pip install --no-build-isolation --editable .
```

The default repository test command runs against the source tree directly:

```bash
./test
```

It does not require the editable install, but it does require a Python
environment with the runtime and test dependencies available.

To check the normal Python package build:

```bash
python -m pip install build
./mk
./install
```

That build is still Python only. It is useful for packaging checks, not for MESA
eos/kap calls.

For a source distribution or a full Python package build:

```bash
./mk sdist
./mk all
```

## Testing

Run the checks that do not call MESA:

```bash
./test
```

After installing a build for MESA calls, run the MESA checks and profile
timing suite:

```bash
./test mesa
```

The standard saved model timing report can also be run directly:

```bash
tests/mesa/run_profile_timing_suite.sh
```

Generated logs and timing JSON files are written under `tests/test_output/`.
The committed deterministic baseline is
`tests/test_output/golden/quick_test_output.txt`. MESA timings are not golden
files because they depend on the local MESA build and machine.

## It's fast!

The profile timing suite uses a saved 20 Msun MESA test suite model after core
helium burning:

```text
star/test_suite/20M_pre_ms_to_core_collapse/standard_after_core_he_burn.mod
```

That model has 880 zones and 22 isotopes. The numbers below are from one local
run with `warmup = 1` and `repeat = 5`, so absolute times depend on the machine
and MESA build. The useful point is the scaling: batch the zones into one
Fortran call, keep MESA handles alive, and let OpenMP parallelize the zone loop.

```text
single run summary, OMP_NUM_THREADS=10:
  physics    global_s  profile_s  ms/profile       eos/s       kap/s
  eos         0.725953   0.717115       2.479   3.550e+05           -
  kap         0.778931   0.770056       2.709           -   3.248e+05
  eos-kap     0.756551   0.747703       2.688   3.274e+05   3.274e+05

combined eos+kap thread sweep:
  threads  ms/profile  speedup  efficiency       eos/s       kap/s
        1      19.692     1.00        1.00   4.469e+04   4.469e+04
        2      10.358     1.90        0.95   8.496e+04   8.496e+04
        4       5.437     3.62        0.91   1.618e+05   1.618e+05
        6       3.686     5.34        0.89   2.387e+05   2.387e+05
        8       2.919     6.75        0.84   3.015e+05   3.015e+05
       10       2.679     7.35        0.74   3.285e+05   3.285e+05
```

The kap timing includes the eos electron state call required by MESA
`kap_get`. When both eos and kap are needed for the same profile, the combined
`eos_kap_profile` path computes the eos state once per zone and then passes it
to kap.

## Usage

### Example eos and kap call

```python
from pyfortmesa import mesa

mesa.set_cache_root(".")
mesa.set_inlist("inlist_eos_and_kap")

mix = mesa.composition({"h1": 0.70, "he4": 0.28, "c12": 0.02})

eos = mesa.Eos()
kap = mesa.Kap()

T_eos = 1.0e7      # K
rho_eos = 1.0e2    # g/cm^3
T_kap = 1.0e6      # K
rho_kap = 1.0e-7   # g/cm^3

eos_out = eos.dt_full(T=T_eos, Rho=rho_eos, comp=mix)
kap_out = kap.opacity_full(T=T_kap, Rho=rho_kap, comp=mix)

print(eos_out["results"]["lnPgas"])
print(kap_out["kappa"])

mesa.shutdown()
```

`mesa.set_inlist(...)` should be called before the first eos or kap call in a
Python process. The file can contain both `&eos` and `&kap` namelists.

### Profile example

For profile work, do not call scalar eos or kap once per zone from Python. Batch
the profile and let the Fortran wrapper run the zone loop.

```bash
export OMP_NUM_THREADS=10
python run_microphysics.py
```

```python
import numpy as np

from pyfortmesa import mesa

mesa.set_cache_root(".")
mesa.set_inlist("inlist_eos_and_kap")

isotope_names = ("h1", "he4", "c12")
chem_id = mesa.iso_ids(isotope_names)
kap = mesa.Kap()


def profile_xa(xa_by_zone):
    # solver layout: (nzones, species)
    # pyfortmesa profile layout: (species, nzones)
    return np.asfortranarray(np.asarray(xa_by_zone, dtype=np.float64).T)


try:
    for T, rho, xa_by_zone in profiles:
        out = kap.eos_kap_profile(T, rho, chem_id, profile_xa(xa_by_zone))
        gamma1 = out["results"]["gamma1"]
        kappa = out["kappa"]
finally:
    mesa.shutdown()
```

Use `mesa.Eos().dt_profile(...)` for eos profile work. Use
`mesa.Kap().opacity_profile(...)` for opacity work. When both eos and kap
are needed for the same zones, prefer `mesa.Kap().eos_kap_profile(...)` so the
eos state is computed once per zone and then passed to kap.

## Cite

If you use `pyfortmesa`, please cite it as:

```bibtex
@software{Farag_pyfortmesa_2026,
  author = {Farag, Ebraheem},
  title = {{pyfortmesa}},
  url = {https://github.com/Debraheem/pyfortmesa},
  version = {0.4.0},
  year = {2026}
}
```

## License

`pyfortmesa` is distributed under the GNU Lesser General Public License v3.0
only. The build for MESA calls links against a separately built MESA tree
supplied by the user.
