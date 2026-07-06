# TURB coverage

Status: future project. TURB is not active in the current branch.

Purpose when implemented: call selected MESA turbulence helper routines from
Python.

## Source

```text
$MESA_DIR/turb/public/turb.f90
```

## Available Now

No Python API and no Fortran wrapper are available yet.

## Not Wrapped Yet

```text
set_thermohaline
set_mlt
set_tdc
set_semiconvection
```

## Notes

TURB public routines are direct calculations driven by thermodynamic inputs and
control choices. Wrap them later with explicit Python arguments for the control
values instead of trying to hide star-control state.
