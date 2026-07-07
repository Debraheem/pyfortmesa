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

!!! warning "Experimental"
    This package is under active development and the Python API may still change.

`pyfortmesa` is a small Python interface to selected MESA microphysics
routines. It reads and calls selected MESA modules, currently `const`, `chem`,
`eos`, and `kap`, with profile eos/kap calls intended for repeated microphysics
work from Python.

This is not meant to be a general MESA module reader. The package should stay
focused on calls where a hand-written wrapper is useful: cached MESA setup,
Python composition inputs, batched zone calls, and OpenMP inside the Fortran
loop. For general MESA module access, use
[pyMesa](https://github.com/rjfarmer/pyMesa).

## Pages

- [Installation](installation.md)
- [Usage](usage.md)
- [MESA modules](modules/README.md)
- [Testing](testing.md)
- [Developing](developing.md)
- [Publishing the docs](publishing.md)

## Local docs preview

The local docs build and preview commands are listed in [Developing](developing.md).
