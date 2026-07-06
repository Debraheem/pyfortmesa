# pyfortmesa

`pyfortmesa` is a small Python interface to selected Fortran and MESA routines.
The MESA-enabled build currently wraps `const`, `chem`, `eos`, and `kap`, with
profile eos/kap calls intended for repeated microphysics work from Python.

This is not meant to be a general MESA module reader. The package should stay
focused on calls where a hand-written wrapper is useful: cached MESA setup,
Python composition inputs, batched zone calls, and OpenMP inside the Fortran
loop. For general MESA module access, use
[pyMesa](https://github.com/rjfarmer/pyMesa).

## Pages

- [Usage](usage.md)
- [MESA modules](modules/README.md)
- [Testing](testing.md)
- [Publishing the docs](publishing.md)

## Local docs preview

Install the docs dependency:

```bash
python -m pip install -r requirements-dev.txt
```

Serve the docs locally:

```bash
mkdocs serve
```

Then open:

```text
http://127.0.0.1:8000
```

Build the static site:

```bash
mkdocs build --strict
```

The generated HTML is written to `site/`.
