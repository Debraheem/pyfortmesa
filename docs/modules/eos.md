# eos

Status: active in the `./mk mesa` build.

Purpose: call MESA `eos` for known density, temperature, and static
composition, including scalar calls, profile calls, and inverse density or
temperature solves.

## Fast start

```python
import numpy as np

from pyfortmesa import mesa

mesa.set_inlist("inlist_eos_and_kap")

mix = mesa.composition({"h1": 0.70, "he4": 0.28, "c12": 0.02})
eos = mesa.Eos()

T = 1.0e7
rho = 1.0e2

small = eos.dt(T=T, Rho=rho, comp=mix)
full = eos.dt_full(T=T, Rho=rho, comp=mix)

Pgas = np.exp(full["results"]["lnPgas"])
Prad = mesa.constants()["crad"] * T**4 / 3.0
Ptot = Pgas + Prad
```

## Pressure and energy conventions

MESA's EOS result vector stores gas pressure:

```text
results["lnPgas"] = ln(Pgas)
Pgas = total pressure - radiation pressure
```

Radiation pressure is not a separate EOS result. Reconstruct it from
temperature:

```python
Pgas = np.exp(out["results"]["lnPgas"])
Prad = mesa.constants()["crad"] * T**4 / 3.0
Ptot = Pgas + Prad
```

For energy:

```python
Etotal = np.exp(out["results"]["lnE"])
Erad = mesa.constants()["crad"] * T**4 / Rho
Egas = Etotal - Erad
```

So `lnPgas` is gas-only, while other thermodynamic quantities such as `lnE`,
`lnS`, `Cp`, `grad_ad`, `chiRho`, `chiT`, and `gamma1` are MESA EOS
thermodynamic results and should not be treated as a gas-only namespace.

## Public API

### `mesa.eos_dt(...)` and `mesa.Eos().dt(...)`

Signature:

```python
mesa.eos_dt(
    T: float,
    Rho: float,
    comp: Composition | Mapping[str, float] | Iterable[float] | None = None,
) -> dict[str, float]
```

Inputs:

| argument | units | shape | meaning |
| --- | --- | --- | --- |
| `T` | K | scalar | temperature |
| `Rho` | `g cm^-3` | scalar | density |
| `comp` | mass fraction | scalar composition | `Composition`, isotope mapping, legacy vector, or `None` |

Returns the small teaching output:

| key | units | meaning |
| --- | --- | --- |
| `lnPgas` | `ln(dyn cm^-2)` | natural log gas pressure |
| `lnE` | `ln(erg g^-1)` | natural log specific internal energy |
| `lnS` | `ln(erg g^-1 K^-1)` | natural log specific entropy |
| `grad_ad` | dimensionless | `dlnT/dlnP` at constant entropy |
| `gamma1` | dimensionless | `dlnP/dlnRho` at constant entropy |

Example:

```python
small = mesa.Eos().dt(T=1.0e7, Rho=1.0e2, comp=mix)
print(small["gamma1"])
```

### `mesa.eos_dt_full(...)` and `mesa.Eos().dt_full(...)`

Signature:

```python
mesa.eos_dt_full(
    T: float,
    Rho: float,
    comp: Composition | Mapping[str, float] | Iterable[float] | None = None,
) -> dict[str, dict[str, float] | dict[str, dict[str, float]]]
```

Inputs are the same as `eos_dt(...)`.

Returns:

| key | shape | meaning |
| --- | --- | --- |
| `results` | dict by EOS result name | full MESA `eosDT_get` result vector |
| `d_dlnRho` | dict by EOS result name | derivative at constant `T` |
| `d_dlnT` | dict by EOS result name | derivative at constant `Rho` |
| `d_dxa` | nested dict | composition derivatives for `lnPgas` and `lnE` |

Representative result names:

```text
lnPgas, lnE, lnS, mu, lnfree_e, eta, grad_ad, chiRho, chiT,
Cp, Cv, dE_dRho, dS_dT, dS_dRho, gamma1, gamma3, phase,
latent_ddlnT, latent_ddlnRho,
HELM, OPAL/SCVH, FreeEOS, PC, Skye, CMS, ideal
```

Example:

```python
full = mesa.Eos().dt_full(T=1.0e7, Rho=1.0e2, comp=mix)
print(full["results"]["lnPgas"])
print(full["d_dlnT"]["lnPgas"])
print(full["d_dxa"]["lnPgas"]["h1"])
```

### `mesa.eos_dt_profile(...)` and `mesa.Eos().dt_profile(...)`

Signature:

```python
mesa.eos_dt_profile(
    T: Iterable[float],
    Rho: Iterable[float],
    chem_id_values: Iterable[int],
    xa: object,
    *,
    input_mode: str = "value",
    output: str = "raw",
) -> dict[str, object]
```

Inputs:

| argument | units | shape | meaning |
| --- | --- | --- | --- |
| `T` | K | `(nzones,)` | temperature profile |
| `Rho` | `g cm^-3` | `(nzones,)` | density profile |
| `chem_id_values` | MESA id | `(species,)` | isotope ids in `xa` row order |
| `xa` | mass fraction | `(species,)` or `(species, nzones)` | fixed composition or zone mass fractions, Fortran-ordered preferred |
| `input_mode` | selector | scalar | `"value"` for physical inputs, `"log"` for natural logs, `"log10"` for base-10 logs |
| `output` | selector | scalar | `"raw"` returns result arrays; `"dict"` returns named result arrays |

Returns:

| key | shape | meaning |
| --- | --- | --- |
| `T` | `(nzones,)` | temperature used by the wrapper |
| `Rho` | `(nzones,)` | density used by the wrapper |
| `results` | `(n_eos_results, nzones)` | raw EOS result matrix when `output="raw"` |
| `result_names` | `(n_eos_results,)` | row names for raw `results`; equal to `mesa.EOS_RESULT_NAMES` |

With `output="dict"`, `results[name]` is a copied `(nzones,)` array for each
EOS result name. Use raw output for throughput loops.

Fixed-composition example:

```python
log_T = np.linspace(3.0, 8.0, 1000)
log_rho = np.linspace(-2.0, 8.0, 1000)

profile = mesa.Eos().dt_profile(log_T, log_rho, mix.chem_id, mix.xa, input_mode="log10")
i_gamma1 = mesa.EOS_RESULT_NAMES.index("gamma1")
gamma1 = profile["results"][i_gamma1, :]
```

### `mesa.eos_dt_profile_from_logs(...)` and `mesa.Eos().dt_profile_from_logs(...)`

Signature:

```python
mesa.eos_dt_profile_from_logs(
    lnT: Iterable[float],
    lnd: Iterable[float],
    chem_id_values: Iterable[int],
    xa: object,
) -> dict[str, object]
```

Compatibility alias for `eos_dt_profile(..., input_mode="log")`. Use this when
a saved model or caller already stores natural-log columns.

```python
lnT = np.log(T)
lnd = np.log(rho)
profile = mesa.Eos().dt_profile_from_logs(lnT, lnd, mix.chem_id, mix.xa)
```

If the caller has base-10 `logT` and `logRho`, call the main profile function:

```python
profile = mesa.Eos().dt_profile(logT, logRho, mix.chem_id, mix.xa, input_mode="log10")
```

### `mesa.eos_solve_rho(...)` and `mesa.Eos().solve_rho(...)`

Signature:

```python
mesa.eos_solve_rho(
    T: float,
    other: str | int,
    other_value: float,
    Rho_guess: float,
    comp: Composition | Mapping[str, float] | Iterable[float] | None = None,
    *,
    logRho_tol: float = 1.0e-10,
    other_tol: float = 1.0e-10,
    max_iter: int = 100,
) -> dict[str, object]
```

Solves for density using MESA `eosDT_get_Rho`.

Inputs:

| argument | units | shape | meaning |
| --- | --- | --- | --- |
| `T` | K | scalar | fixed temperature |
| `other` | result name or index | scalar | EOS result to match |
| `other_value` | MESA result units | scalar | target value for `other` |
| `Rho_guess` | `g cm^-3` | scalar | initial density guess |
| `logRho_tol` | `log10(g cm^-3)` | scalar | density tolerance |
| `other_tol` | result units | scalar | target-result tolerance |
| `max_iter` | count | scalar | maximum solver iterations |

Returns `Rho`, `logRho`, `eos_calls`, and the full EOS output dictionaries.

Example:

```python
target = mesa.Eos().dt(T=1.0e7, Rho=1.0e2, comp=mix)
rho_solve = mesa.Eos().solve_rho(
    T=1.0e7,
    other="lnPgas",
    other_value=target["lnPgas"],
    Rho_guess=80.0,
    comp=mix,
)
```

For `lnPgas`, pass the natural log of gas pressure, not total pressure.

### `mesa.eos_solve_t(...)`, `mesa.eos_solve_T(...)`, and `mesa.Eos().solve_t(...)`

Signature:

```python
mesa.eos_solve_t(
    Rho: float,
    other: str | int,
    other_value: float,
    T_guess: float,
    comp: Composition | Mapping[str, float] | Iterable[float] | None = None,
    *,
    logT_tol: float = 1.0e-10,
    other_tol: float = 1.0e-10,
    max_iter: int = 100,
) -> dict[str, object]
```

Solves for temperature using MESA `eosDT_get_T`. `eos_solve_T` and
`Eos().solve_T` are aliases for the lower-case spelling.

Inputs:

| argument | units | shape | meaning |
| --- | --- | --- | --- |
| `Rho` | `g cm^-3` | scalar | fixed density |
| `other` | result name or index | scalar | EOS result to match |
| `other_value` | MESA result units | scalar | target value for `other` |
| `T_guess` | K | scalar | initial temperature guess |
| `logT_tol` | `log10(K)` | scalar | temperature tolerance |
| `other_tol` | result units | scalar | target-result tolerance |
| `max_iter` | count | scalar | maximum solver iterations |

Returns `T`, `logT`, `eos_calls`, and the full EOS output dictionaries.

### `mesa.eos_solve_rho_profile(...)` and `mesa.Eos().solve_rho_profile(...)`

Signature:

```python
mesa.eos_solve_rho_profile(
    T: Iterable[float],
    other: str | int,
    other_value: Iterable[float] | float,
    Rho_guess: Iterable[float] | float,
    chem_id_values: Iterable[int],
    xa: object,
    *,
    input_mode: str = "value",
    logRho_tol: float = 1.0e-10,
    other_tol: float = 1.0e-10,
    max_iter: int = 100,
) -> dict[str, object]
```

OpenMP-batched profile version of `eos_solve_rho(...)`. `input_mode` applies
to the known `T` profile. `Rho_guess` is always physical `g cm^-3` and may be
scalar or `(nzones,)`. Raw outputs include `Rho`, `logRho`, `eos_calls`,
`results`, `d_dlnRho`, `d_dlnT`, and `d_dxa`.

### `mesa.eos_solve_t_profile(...)`, `mesa.eos_solve_T_profile(...)`, and `mesa.Eos().solve_t_profile(...)`

Signature:

```python
mesa.eos_solve_t_profile(
    Rho: Iterable[float],
    other: str | int,
    other_value: Iterable[float] | float,
    T_guess: Iterable[float] | float,
    chem_id_values: Iterable[int],
    xa: object,
    *,
    input_mode: str = "value",
    logT_tol: float = 1.0e-10,
    other_tol: float = 1.0e-10,
    max_iter: int = 100,
) -> dict[str, object]
```

OpenMP-batched profile version of `eos_solve_t(...)`. `input_mode` applies to
the known `Rho` profile. `T_guess` is always physical K and may be scalar or
`(nzones,)`. `eos_solve_T_profile` and `Eos().solve_T_profile` are aliases for
the lower-case spelling.

## Output schemas

Use schema helpers to inspect expected field names, units, and shapes without
calling MESA:

```python
print(mesa.format_output_schema("eos_dt_full", species=mix.names))
print(mesa.format_output_schema("eos_dt_profile"))
```

Supported EOS schema names are listed by:

```python
mesa.output_schema_names()
```

## Source mapping

```text
$MESA_DIR/eos/public/eos_lib.f90
$MESA_DIR/eos/public/eos_def.f90
src/pyfortmesa/fortran/eos/mesa_eos_public.f90
src/pyfortmesa/mesa.py
src/pyfortmesa/mesa_support.py
```

Fortran wrappers:

```text
mesa_eos_composition -> eosDT_get
mesa_eos_composition_full -> eosDT_get
mesa_eos_profile -> eosDT_get once per profile zone
mesa_eos_profile_from_logs -> compatibility wrapper for natural-log inputs
mesa_eos_solve_rho -> eosDT_get_Rho
mesa_eos_solve_rho_profile -> eosDT_get_Rho once per profile zone
mesa_eos_solve_t -> eosDT_get_T
mesa_eos_solve_t_profile -> eosDT_get_T once per profile zone
mesa_eos_shutdown -> free handle, optionally eos_shutdown
```

`mesa_eos_sample_composition` still exists as a legacy/sample Fortran wrapper,
but the public Python API uses named `Composition` objects instead.

## Common mistakes

- `lnPgas` is gas pressure, not total pressure.
- `input_mode="log"` means natural log; use `input_mode="log10"` for base-10
  arrays.
- Scalar helpers accept `comp=mix`; profile helpers require
  `chem_id_values` and `xa(species,)` or `xa(species, nzones)`.
- `mesa.shutdown()` belongs at the end of a driver, not inside a profile loop.

## Not included

| MESA item | Reason |
| --- | --- |
| `eos_init`, `alloc_eos_handle`, `free_eos_handle` | Managed internally by pyfortmesa handles and `mesa.shutdown(...)`. |
| `eos_ptr` | Exposes MESA pointer state; not safe or useful for normal Python calls. |
| `eos_get_control_namelist`, `eos_set_control_namelist` | Current control path is `mesa.set_inlist(...)`; exposing raw namelist buffers is a larger API. |
| `eosPT_get` and related `eosPT_*` routines | Potentially useful, but not needed while `eosDT_get_Rho/T` cover the current inverse workflows. Add only with examples and tests. |
| gamma-law EOS helper family | Specialized analytic EOS path; not the same workflow as MESA table EOS/KAP calls. |
| HELM component/conversion helpers | Lower-level diagnostics; current API exposes the final MESA result vector. |
| Fermi-Dirac integral helper | Standalone numerical helper, not a pyfortmesa microphysics workflow yet. |
| `num_eos_files_loaded` | Debug/diagnostic only; can be added later if needed for table-loading diagnostics. |
| `mesa_eos_sample_composition` | Legacy/sample Fortran wrapper; prefer named `Composition` path for user code. |
