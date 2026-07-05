# pyfortmesa

This repo contains a Python module for reading and running Fortran/MESA tools
from Python.

## Repository build stack

This package has pure Python code plus a small Fortran routine wrapped with
F2PY. The build stack is:

```text
pyproject.toml -> tells pip/build which backend to use
meson-python   -> connects Python packaging to Meson
Meson          -> configures the compiled-code build
Ninja          -> actually runs the compile commands
gfortran       -> compiles the Fortran source
```

Compiler note:

The small example extension only needs a working Fortran compiler. For the
intended MESA workflow, install the current
[MESA SDK](https://user.astro.wisc.edu/~townsend/static.php?ref=mesasdk) and
source its `mesasdk_init.sh` before building or calling MESA-related code. This
repo was tested with the MESA SDK `gfortran` from GCC 15.2.0, but the example
code does not intentionally require that exact compiler version.

Useful MESA links:

- [MESA installation docs](https://docs.mesastar.org/en/latest/installation.html)
- [MESA GitHub repository](https://github.com/MESAHub/mesa)

Current source roles:

```text
src/pyfortmesa/calc.py                 -> pure Python calculation
src/pyfortmesa/fortran/const_def.f90   -> MESA-like dp kind definition
src/pyfortmesa/fortran/small_calc.f90  -> Fortran calculations
src/pyfortmesa/fortran_calc.py         -> Python wrapper around F2PY extension
tests/test_module_import.py            -> quick correctness smoke test
tests/time_sum_benchmark.py            -> Python vs. Fortran timing script
f2py_f2cmap                            -> maps dp for F2PY wrappers
meson.build                            -> compiled-extension build recipe
```

The Fortran code uses `real(dp)`, similar to MESA style. The `dp` kind is
defined once in `const_def.f90`. F2PY also needs `f2py_f2cmap` so `dp` is
wrapped as C `double`.

## How the module works

The build and import path is:

```text
pyproject.toml
  -> selects meson-python as the build backend
meson.build
  -> tells Meson which Python and Fortran files to build
src/pyfortmesa/fortran/small_calc.f90
  -> contains Fortran routines meant to be callable from Python
f2py_f2cmap
  -> tells F2PY that real(dp) should be wrapped as C double
F2PY
  -> generates C/Python wrapper code for the Fortran routines
Meson + Ninja + gfortran
  -> compile the Fortran and wrapper code into _fortran_calc*.so
src/pyfortmesa/fortran_calc.py
  -> imports _fortran_calc and exposes clean Python functions
src/pyfortmesa/__init__.py
  -> exports the public package API
```

At runtime, Python code calls:

```text
pyfortmesa.small_calc_fortran(...)
  -> fortran_calc.py
  -> _fortran_calc*.so
  -> small_calc_f(...) in Fortran
```

## Local install

For development with compiled code, install the build tools and use an editable
install without build isolation.

From the top of this repository:

```bash
python -m pip install meson-python meson ninja numpy
python -m pip install --no-build-isolation --editable .
```

The editable install points Python at this local source tree. Meson rebuilds
the compiled Fortran extension when needed.

Run the current smoke test:

```bash
python -m pyfortmesa
```

Expected output:

```text
Python saw y = 50.0
Fortran saw y = 50.0
```

You can also call the package function directly:

```bash
python - <<'PY'
from pyfortmesa import small_calc, small_calc_fortran

print(small_calc(4.0))
print(small_calc_fortran(4.0))
PY
```

Expected output:

```text
50.0
50.0
```

## Wheel install

To test the package as a built installable artifact, build a wheel:

```bash
./clean
./mk
```

Then install the generated wheel:

```bash
./install
```

Run the same smoke test:

```bash
python -m pyfortmesa
```

The wheel path is useful for checking distribution behavior. For normal
development work, prefer the editable install.

## Rebuild after Fortran changes

After editing Fortran source, rebuild the wheel and reinstall it into the active
environment:

```bash
./mk
./install
```

These are separate steps:

```text
./mk
  -> builds a new wheel in dist/
  -> compiles the Fortran and creates the extension module

./install
  -> installs that already-built wheel into the active Python environment
  -> makes python -m pyfortmesa use the new compiled code
```

Then rerun the smoke test:

```bash
python -m pyfortmesa
python tests/test_module_import.py
```

For a clean rebuild:

```bash
./clean
./mk
./install
```

Typical workflow:

```bash
conda activate pyfortmesa
./clean
./mk
./install
python -m pyfortmesa
python tests/test_module_import.py
python tests/time_sum_benchmark.py 1000000
```

## Benchmark

Benchmark code lives outside `src` because timing is not part of the library
API. The benchmark calls package functions from `src`.

Run the default benchmark:

```bash
python tests/time_sum_benchmark.py
```

Run with a custom loop count:

```bash
python tests/time_sum_benchmark.py 10000000
```

The benchmark compares:

```text
big_sum_python(n)   -> pure Python loop
big_sum_fortran(n)  -> compiled Fortran loop
```

## Build scripts

Clean generated files:

```bash
./clean
```

Build only a wheel:

```bash
./mk
```

Install the newest built wheel from `dist/` into the active Python environment:

```bash
./install
```

`./install` is shorthand for the local testing command:

```bash
python -m pip install --force-reinstall --no-deps dist/pyfortmesa-*.whl
```

The script picks the newest wheel in `dist/`. `--force-reinstall` replaces the
currently installed copy, and `--no-deps` avoids changing dependencies such as
NumPy while you are only testing your local build.

Build only a source distribution:

```bash
./mk sdist
```

Build both source distribution and wheel:

```bash
./mk all
```

For Meson projects, source distributions are made from files tracked by git.
If `./mk all` fails during active development, commit or stage the new source
files first, or use the default wheel build while testing locally.

## TestPyPI upload

TestPyPI is the practice package index. Use it before uploading to the real
PyPI index.

Start from the top of this repository.

Optionally remove old generated build files first:

```bash
rm -rf dist build src/pyfortmesa.egg-info
```

Build the source distribution and wheel:

```bash
./clean
./mk all
```

Check the generated files:

```bash
python -m twine check dist/pyfortmesa-0.3.1*
```

Upload to TestPyPI:

```bash
python -m twine upload --repository testpypi dist/pyfortmesa-0.3.1*
```

When prompted, use a TestPyPI API token. If Twine asks for username and
password, use `__token__` as the username and paste the token as the password.

Version flow:

```text
pyproject.toml version -> local package metadata
python -m build -> local dist files
twine upload -> TestPyPI release
git tag -> GitHub label, not a TestPyPI upload
```

If TestPyPI still shows an older version, the new version was built locally but
has not been uploaded successfully yet.

## Test install from TestPyPI

After the upload succeeds, test the install from outside this repository.

```bash
python -m pip uninstall -y pyfortmesa
python -m pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  pyfortmesa==0.3.1
```

Then run:

```bash
cd ..
python -m pyfortmesa
```

Expected output:

```text
Python saw y = 50.0
Fortran saw y = 50.0
```

## TestPyPI troubleshooting

If upload fails with `400 Bad Request`, rerun with verbose output:

```bash
python -m twine upload --repository testpypi --verbose dist/pyfortmesa-0.3.1*
```

Common causes are an already-uploaded version, a token for the wrong package
index, or a token scoped to a different TestPyPI project.
