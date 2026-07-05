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

Expected output:

```text
Python saw y = 50.0
```

You can also call the package function directly:

```bash
python -c "from pyfortmesa import small_calc; print(small_calc(4.0))"
```

Expected output:

```text
50.0
```

## Wheel install

To test the package as a built installable artifact, build a wheel:

```bash
python -m build
```

Then install the generated wheel:

```bash
python -m pip install dist/pyfortmesa-0.3.1-py3-none-any.whl
```

Run the same smoke test:

```bash
python -m pyfortmesa
```

The wheel path is useful for checking distribution behavior. For normal
development work, prefer the editable install.

## TestPyPI upload

TestPyPI is the practice package index. Use it before uploading to the real
PyPI index.

Start from the top of this repository:

```bash
cd /Users/owner/Documents/Work_research/new_models/fotran_python_pip/pyfortmesa
```

Optionally remove old generated build files first:

```bash
rm -rf dist build src/pyfortmesa.egg-info
```

Build the source distribution and wheel:

```bash
python -m build
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
```

## TestPyPI troubleshooting

If upload fails with `400 Bad Request`, rerun with verbose output:

```bash
python -m twine upload --repository testpypi --verbose dist/pyfortmesa-0.3.1*
```

Common causes are an already-uploaded version, a token for the wrong package
index, or a token scoped to a different TestPyPI project.
