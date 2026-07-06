# MESA module coverage

These pages track what `pyfortmesa` can call now and what is still missing.
They are coverage notes, not replacements for MESA's public API docs.

Active in the current MESA-enabled build:

```text
CONST -> selected constants from MESA const_def
CHEM  -> composition helpers
EOS   -> density-temperature EOS calls plus inverse rho/T solves
KAP   -> opacity calls using EOS electron quantities plus Type2 controls
```

Future projects, not active in this branch:

```text
NET   -> reaction networks and one-zone burns
TURB  -> turbulence helper routines
```

Module pages:

- [CONST](CONST.md)
- [CHEM](CHEM.md)
- [EOS](EOS.md)
- [KAP](KAP.md)
- [NET](NET.md)
- [TURB](TURB.md)

The current useful zone-query path is:

```text
composition -> CHEM -> EOS -> KAP
constants   -> CONST
```

For a static-composition envelope or RSP-style known-`T,rho` zone call, NET is
not required. NET becomes relevant when Python needs reaction rates, abundance
evolution, or one-zone burns.
