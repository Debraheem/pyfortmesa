# MESA modules

These pages describe the MESA wrapper surface provided by `pyfortmesa`. They are
not replacements for MESA's public module docs.

`pyfortmesa` is not a general MESA module reader. It wraps selected calls where
a small Python interface is useful for repeated microphysics work. For general
MESA module access, use [pyMesa](https://github.com/rjfarmer/pyMesa).

Active in the build for MESA calls:

```text
const -> selected values from MESA const_def
chem  -> composition helpers
eos   -> density-temperature eos calls and rho/T inverse solves
kap   -> opacity calls using eos electron quantities and Type2 controls
```

Not wrapped by `pyfortmesa`:

```text
net   -> reaction networks and one-zone burns
turb  -> turbulence helper routines
```

Module pages:

- [const](const.md)
- [chem](chem.md)
- [eos](eos.md)
- [kap](kap.md)

The useful static-composition path is:

```text
composition -> chem -> eos -> kap
constants   -> const
```

For fast calls from inside a numerical solver where `T`, `rho`, and
composition are already known, `net` is not part of the call path.
