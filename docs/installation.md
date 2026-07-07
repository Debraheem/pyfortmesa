# Installation

Choose the install based on what you want to run. The examples in this manual
call MESA `eos` and `kap`, so they need the `./mk mesa` build installed,
not just the plain Python install.

`./mk` and `./mk mesa` are different builds. `./mk` builds the plain package.
That is enough for imports, docs, and checks that do not call MESA. `./mk mesa`
builds the pyfortmesa wheel with the compiled wrappers needed for MESA
`eos` and `kap` calls, and for `./test mesa`.

## Python install

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
MESA wrapper extension modules, so it will not run the eos/kap examples.

A quick import check is:

```bash
python -m pyfortmesa
```

Expected output:

```text
pyfortmesa: MESA wrapper package
public module: pyfortmesa.mesa
```

## MESA wrapper install

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
running the command.

More build commands, including `conda run -n pyfortmesa` forms, are in
[Developing](developing.md).
