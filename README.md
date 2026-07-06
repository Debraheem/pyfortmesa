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

## Install

For local development from this checkout:

```bash
conda activate pyfortmesa
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pip install --no-build-isolation --editable .
```

That install gives the Python package and the `pyfortmesa.mesa` API. It does
not build the compiled MESA extension modules. Use the wheel build below for a
normal installable artifact.

A quick import check is:

```bash
python -m pyfortmesa
```

Expected output:

```text
pyfortmesa: MESA wrapper package
public module: pyfortmesa.mesa
```

## Wheel build

Build the normal Python wheel with:

```bash
conda activate pyfortmesa
python -m pip install -r requirements-dev.txt
./mk
./install
```

`./mk` runs the standard Python wheel build and writes `dist/pyfortmesa-*.whl`.
`./install` installs the newest wheel in `dist/` into the active Python
environment. This wheel is enough for imports, documentation, and the non-MESA
test suite, but it does not include the compiled MESA wrappers.

For source distributions or both wheel and source distribution:

```bash
./mk sdist
./mk all
```

## MESA-enabled wheel

Use a recent MESA tree with shared module libraries and pkg-config files under:

```text
$MESA_DIR/build/*/lib/pkgconfig/mesa-*.pc
```

Set up the MESA SDK and build the MESA-enabled wheel:

```bash
conda activate pyfortmesa
python -m pip install -r requirements-dev.txt
export MESASDK_ROOT=/Applications/mesasdk
source $MESASDK_ROOT/bin/mesasdk_init.sh
export MESA_DIR=/path/to/current/mesa
./mk mesa
./install
```

`./mk mesa` sets `PKG_CONFIG_PATH` from the MESA build tree and runs the wheel
build with `-Dwith_mesa=true`. The resulting wheel contains the compiled
`const`, `chem`, `eos`, and `kap` extension modules for that MESA build.

A useful check before building is:

```bash
echo $MESA_DIR
export PKG_CONFIG_PATH=$(find "$MESA_DIR/build" -path "*/lib/pkgconfig" -type d | paste -sd: -)
pkg-config --cflags --libs mesa-const mesa-chem mesa-eos mesa-kap
```

Classic static-only MESA installs are not supported by this wrapper. The package
should fail clearly for those layouts rather than trying to static-link them.

## Test

Run the non-MESA checks:

```bash
./test
```

After installing a MESA-enabled wheel, run the MESA-backed checks and profile
timing suite:

```bash
./test mesa
```

The standard saved-model timing report can also be run directly:

```bash
tests/mesa/run_profile_timing_suite.sh
```

Generated logs and timing JSON files are written under `tests/test_output/`.
The committed deterministic baseline is
`tests/test_output/golden/quick_test_output.txt`. MESA timings are not golden
files because they depend on the local MESA build and machine.

## Example eos and kap call

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

## Profile example

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

Use `mesa.Eos().dt_profile(...)` for eos-only profile work. Use
`mesa.Kap().opacity_profile(...)` for opacity-only work. When both eos and kap
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
only. The compiled MESA-enabled wheel is meant to link against a separately
built MESA tree supplied by the user.

## More documentation

- Usage examples: `docs/usage.md`
- Module reference: `docs/modules/README.md`
- Test runner notes: `docs/testing.md`
- Simple MESA work example: `tests/work/README.md`
- MESA-backed test scripts: `tests/mesa/README.md`
- Docs publishing: `docs/publishing.md`

Build the local documentation site with:

```bash
python -m pip install -r requirements-dev.txt
mkdocs serve
```

The GitHub Pages workflow is `.github/workflows/pages.yml`. In the GitHub repo,
set Pages -> Build and deployment -> Source to `GitHub Actions`.
