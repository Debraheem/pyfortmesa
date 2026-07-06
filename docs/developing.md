# Developing

This page collects the common development commands. If the `pyfortmesa` conda
environment is already active, use the shorter command. If not, use the
`conda run -n pyfortmesa ...` form.

## Environment setup

| Task | If `pyfortmesa` is active | Without activating first |
| --- | --- | --- |
| Install development requirements | `python -m pip install -r requirements-dev.txt` | `conda run -n pyfortmesa python -m pip install -r requirements-dev.txt` |
| Install editable checkout | `python -m pip install --no-build-isolation --editable .` | `conda run -n pyfortmesa python -m pip install --no-build-isolation --editable .` |
| Check import | `python -m pyfortmesa` | `conda run -n pyfortmesa python -m pyfortmesa` |

The editable install is useful while editing the package. The default `./test`
command runs against `src/` directly, so it does not require an editable install.

`requirements-dev.txt` includes `requirements.txt`, then adds the docs, testing,
and publishing tools used while developing the package.

## Package builds

A wheel is Python's built install file, with a `.whl` suffix. The normal build
installs the importable Python package, but not the compiled MESA wrappers. The
build for MESA calls is local because the compiled wrapper modules have to link
against the MESA libraries in your `MESA_DIR`.

| Task | If `pyfortmesa` is active | Without activating first | Notes |
| --- | --- | --- | --- |
| Build normal Python package | `./mk` | `conda run -n pyfortmesa ./mk` | Writes `dist/pyfortmesa-*.whl`; does not include MESA wrappers. |
| Install newest local build | `./install` | `conda run -n pyfortmesa ./install` | Installs the newest `dist/pyfortmesa-*.whl` into the selected environment. |
| Build source distribution | `./mk sdist` | `conda run -n pyfortmesa ./mk sdist` | Writes the source archive under `dist/`. |
| Build wheel and source distribution | `./mk all` | `conda run -n pyfortmesa ./mk all` | Runs `python -m build`. |
| Clean build output | `./clean` | `conda run -n pyfortmesa ./clean` | Removes `build/`, `dist/`, `.mesonpy-*`, caches, and Python bytecode. |

## Build for MESA calls

Only use this path when Python code needs to call MESA `const`, `chem`, `eos`,
or `kap`. Build MESA separately first.

The build expects:

```text
MESASDK_ROOT -> the MESA SDK location, for compiler and runtime tools
MESA_DIR     -> the MESA checkout to link against
```

It also expects four MESA pkg-config files from the MESA build. These are small
`.pc` text files that tell the compiler where the MESA shared libraries and
module files are:

```text
mesa-const.pc
mesa-chem.pc
mesa-eos.pc
mesa-kap.pc
```

Those files are produced by the MESA shared library build, not by the MESA SDK.
They should be under a directory like:

```text
$MESA_DIR/build/<build-name>/lib/pkgconfig/
```

The exact `<build-name>` is chosen by the MESA build system. To see what this
checkout finds, run:

```bash
find "$MESA_DIR/build" -path "*/lib/pkgconfig/mesa-*.pc" -print
python tools/mesa_pkg_config.py path
```

You do not normally set `PKG_CONFIG_PATH` by hand for this package. `./mk mesa`
runs `python tools/mesa_pkg_config.py path`, sets `PKG_CONFIG_PATH` from that
output, and then builds with `-Dwith_mesa=true`.

The MESA SDK setup and `MESA_DIR` are separate things. Sourcing the MESA SDK sets
up compilers and runtime libraries. Setting `MESA_DIR` tells this package which
MESA checkout to inspect and link against.

With an active environment:

```bash
conda activate pyfortmesa
python -m pip install -r requirements-dev.txt
export MESASDK_ROOT=/Applications/mesasdk
source "$MESASDK_ROOT/bin/mesasdk_init.sh"
export MESA_DIR=/path/to/current/mesa
./clean
./mk mesa
./install
```

Without activating first:

```bash
conda run -n pyfortmesa python -m pip install -r requirements-dev.txt
export MESASDK_ROOT=/Applications/mesasdk
source "$MESASDK_ROOT/bin/mesasdk_init.sh"
export MESA_DIR=/path/to/current/mesa
conda run -n pyfortmesa ./clean
conda run -n pyfortmesa ./mk mesa
conda run -n pyfortmesa ./install
```

`./clean` removes old local build output before the MESA build. That is useful
when switching between builds or changing `MESA_DIR`.

A useful preflight check is:

```bash
echo $MESA_DIR
python tools/mesa_pkg_config.py path
PKG_CONFIG_PATH=$(python tools/mesa_pkg_config.py path) pkg-config --cflags --libs mesa-const mesa-chem mesa-eos mesa-kap
```

## Docs

| Task | If `pyfortmesa` is active | Without activating first |
| --- | --- | --- |
| Build strict local site | `python -m mkdocs build --clean --strict --site-dir site` | `conda run -n pyfortmesa python -m mkdocs build --clean --strict --site-dir site` |
| Serve docs locally | `python -m mkdocs serve` | `conda run -n pyfortmesa python -m mkdocs serve` |

The public docs URL is:

```text
https://debraheem.github.io/pyfortmesa/
```

## Tests

| Task | If `pyfortmesa` is active | Without activating first |
| --- | --- | --- |
| Run checks that do not call MESA | `./test` | `conda run -n pyfortmesa ./test` |
| Run MESA checks after installing a build for MESA calls | `./test mesa` | `conda run -n pyfortmesa ./test mesa` |
| Run the profile timing suite | `tests/mesa/run_profile_timing_suite.sh` | `conda run -n pyfortmesa tests/mesa/run_profile_timing_suite.sh` |

MESA tests require `MESA_DIR` and a package build made with `./mk mesa`.
