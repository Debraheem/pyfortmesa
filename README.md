# py_fortMESA

This repo contains a Python module for reading and running Fortran/MESA tools
from Python.

## Local install

From the top of this repository:

```bash
python -m pip install --editable .
```

The editable install points Python at this local source tree, so changes under
`src/py_fortmesa/` are picked up without reinstalling.

Run the current smoke test:

```bash
python -m py_fortmesa
```
