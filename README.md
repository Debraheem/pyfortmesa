# pyfortmesa

This repo contains a Python module for reading and running Fortran/MESA tools
from Python.

## Local install

For development, use an editable install.

From the top of this repository:

```bash
python -m pip install --editable .
```

The editable install points Python at this local source tree, so changes under
`src/pyfortmesa/` are picked up without reinstalling.

Run the current smoke test:

```bash
python -m pyfortmesa
```

## Wheel install

To test the package as a built installable artifact, build a wheel:

```bash
python -m build
```

Then install the generated wheel:

```bash
python -m pip install dist/pyfortmesa-0.3.0-py3-none-any.whl
```

Run the same smoke test:

```bash
python -m pyfortmesa
```

The wheel path is useful for checking distribution behavior. For normal
development work, prefer the editable install.
