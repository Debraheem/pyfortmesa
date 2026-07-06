# pyfortmesa

`pyfortmesa` is a small Python interface to selected MESA microphysics
routines. A build for MESA calls wraps `const`, `chem`, `eos`, and `kap`, with
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
- [Developing](developing.md)
- [Publishing the docs](publishing.md)

## Local docs preview

The local docs build and preview commands are listed in [Developing](developing.md).
