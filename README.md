# pyfortmesa [![Repo Status][status-badge]][status-link] [![Version][version-badge]][version-link] [![PyPI][pypi-badge]][pypi-link] [![Docs][docs-badge]][docs-link] [![Python][python-badge]][python-link] [![MESA][mesa-badge]][mesa-link] [![License][license-badge]][license-link]

[status-link]: https://www.repostatus.org/#active
[status-badge]: https://www.repostatus.org/badges/latest/active.svg
[version-link]: https://github.com/Debraheem/pyfortmesa/releases/tag/v0.4.0
[version-badge]: https://img.shields.io/github/v/tag/Debraheem/pyfortmesa?label=version
[pypi-link]: https://pypi.org/project/pyfortmesa/
[pypi-badge]: https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fpypi.org%2Fpypi%2Fpyfortmesa%2Fjson&query=%24.info.version&label=pypi
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
It reads and calls selected MESA modules, currently `const`, `chem`, `eos`, and
`kap`, with a Python API for scalar calls and batched profile calls.

This is not a general MESA module reader. The point is to make repeated eos/kap
calls from Python cheap enough to use inside real model-building code: cache the
MESA setup, keep handles alive, batch zones into one Fortran call, and let
OpenMP parallelize the zone loop. For general access to arbitrary MESA modules,
use [pyMesa](https://github.com/rjfarmer/pyMesa).

`pyfortmesa` does not build or install MESA. Build MESA separately, then point
`MESA_DIR` at that tree.

## Documentation

Documentation: https://debraheem.github.io/pyfortmesa/

The site is built with MkDocs from the files under `docs/` and published with
GitHub Pages. The docs footer links back to the GitHub repository.

Useful docs and examples:

- Installation: `docs/installation.md`
- Usage examples: `docs/usage.md`
- MESA module reference: `docs/modules/README.md`
- Test runner notes: `docs/testing.md`
- Development commands: `docs/developing.md`
- Docs publishing: `docs/publishing.md`
- Simple MESA work example: `tests/work/README.md`
- MESA test scripts: `tests/mesa/README.md`

For local docs builds and GitHub Pages publishing notes, see
`docs/developing.md` and `docs/publishing.md`.

## Installation

Choose the install based on what you want to run. The examples below call MESA
`eos` and `kap`, so they need the `./mk mesa` build installed, not the
plain Python install.

`./mk` and `./mk mesa` are different builds. `./mk` builds the plain package.
That is enough for imports, docs, and checks that do not call MESA. `./mk mesa`
builds the pyfortmesa wheel with the compiled wrappers needed for MESA
`eos` and `kap` calls, and for `./test mesa`.

### Python install

Use this when you want to import `pyfortmesa`, read the docs, or use code
that does not call MESA's compiled `const`, `chem`, `eos`, or `kap` routines.

Install the released Python package from PyPI:

```bash
python -m pip install pyfortmesa
```

To install an exact source tag from GitHub instead:

```bash
python -m pip install "git+https://github.com/Debraheem/pyfortmesa.git@v0.4.0"
```

Or install from a local checkout:

```bash
python -m pip install .
```

This installs the Python files and `numpy`. It does not compile or include the
MESA wrapper extension modules, so it will not run the eos/kap examples below.

A quick import check is:

```bash
python -m pyfortmesa
```

Expected output:

```text
pyfortmesa: MESA wrapper package
public module: pyfortmesa.mesa
```

### MESA wrapper install

Use this path when Python code will call MESA `const`, `chem`, `eos`, or `kap`.
A wheel is just Python's built install file. This repo uses a local wheel
because the compiled wrappers must be built against the exact MESA tree and
compiler setup on your machine.

From a checkout:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

export MESASDK_ROOT=/Applications/mesasdk
source "$MESASDK_ROOT/bin/mesasdk_init.sh"
export MESA_DIR=/path/to/current/mesa

./clean
./mk mesa
./install
```

`./clean` removes old local build output before the MESA build. That is useful
when switching between builds or changing `MESA_DIR`.

MESA must be built with shared module libraries. A current MESA development
tree usually has this already. For a release tree, check
`$MESA_DIR/utils/makefile_header`; if it says `USE_SHARED = NO`, set
`USE_SHARED = YES`, then rebuild MESA with `./clean` and `./install`.
Static-only MESA builds are not supported.

`./mk mesa` finds the MESA pkg-config files under `MESA_DIR`, sets
`PKG_CONFIG_PATH` for this build, and writes `dist/pyfortmesa-*.whl`.
`./install` installs the newest wheel from `dist/` into the Python environment
running the command. After that, the usage examples below should work in that
environment.

More build commands, including `conda run -n pyfortmesa` forms, are in
`docs/developing.md`.

## Testing

Run the checks that do not call MESA:

```bash
./test
```

After installing the `./mk mesa` wheel, run the MESA checks and profile
timing suite:

```bash
./test mesa
```

The standard saved model timing report can also be run directly:

```bash
tests/mesa/run_profile_timing_suite.sh
```

The timing report prints compact tables. Raw per-run logs and timing JSON are
temporary by default; set `PYFORTMESA_PROFILE_REPORT_DIR` to keep them. The
committed deterministic baseline is
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

The examples in this section call MESA, so install the `./mk mesa` wheel
before running them.

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

`mix` is a scalar-call composition object. It stores the isotope names, matching
MESA `chem_id` values, and one mass-fraction vector. Scalar helpers accept it as
`comp=mix`.

### Profile example

For profile work, do not call scalar eos or kap once per zone from Python. Batch
the profile and let the Fortran wrapper run the zone loop. Profile helpers take
the composition in split form: `chem_id_values` gives the isotope order, and
`xa` gives the mass fractions with shape `(species, nzones)`.

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
chem_id_values = mesa.iso_ids(isotope_names)
kap = mesa.Kap()
i_gamma1 = mesa.EOS_RESULT_NAMES.index("gamma1")


def profile_xa(xa_by_zone):
    # solver layout: (nzones, species)
    # pyfortmesa profile layout: (species, nzones)
    return np.asfortranarray(np.asarray(xa_by_zone, dtype=np.float64).T)


try:
    for T, rho, xa_by_zone in profiles:
        out = kap.eos_kap_profile(T, rho, chem_id_values, profile_xa(xa_by_zone))
        gamma1 = out["results"][i_gamma1, :]
        kappa = out["kappa"]
finally:
    mesa.shutdown()
```

For a fixed-composition EOS profile on an arbitrary base-10 `logT`/`logRho`
track, build one `Composition` and pass its 1D `xa` vector. The wrapper
broadcasts fixed compositions over zones. Use `input_mode="log10"` when the
arrays are base-10 logs:

```python
log_rho = np.linspace(-2.0, 8.0, 1000)
log_T = np.linspace(3.0, 8.0, 1000)

mix = mesa.composition({"h1": 0.70, "he4": 0.28, "c12": 0.02})

out = mesa.Eos().dt_profile(log_T, log_rho, mix.chem_id, mix.xa, input_mode="log10")
```

For KAP profile work, choose points in a valid opacity-table region. A common
base-10 coordinate is `logR = logRho - 3*logT + 18`:

```python
log_T = np.linspace(3.75, 8.0, 1000)
log_R = np.full_like(log_T, -3.0)
log_rho = log_R + 3.0*log_T - 18.0

T = 10.0**log_T
rho = 10.0**log_rho

out = mesa.Kap().eos_kap_profile(T, rho, mix.chem_id, mix.xa)
```

Use `input_mode="log"` for natural-log arrays and `input_mode="log10"` for
base-10 arrays. The older `*_from_logs(...)` helpers are compatibility aliases
for natural-log input.

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
only. The `./mk mesa` build links against a separately built MESA tree
supplied by the user.
