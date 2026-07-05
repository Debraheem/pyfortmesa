from pathlib import Path

from setuptools import find_packages, setup

setup(
    name="py-fortmesa",
    version="0.2.0",
    description="A Python package for running Fortran (specifically MESA) via Python",
    long_description=Path("README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    url="https://github.com/Debraheem/py_fortMESA",
    author="Ebraheem Farag",
    author_email="ebraheem.farag@yale.edu",
    license="LGPL-3.0-only",
    python_requires=">=3.10",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=["numpy"],
)
