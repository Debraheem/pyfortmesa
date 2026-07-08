# kap

Status: active in the `./mk mesa` build.

Purpose: call MESA `kap` for known density, temperature, and static composition.
The wrapper calls eos first so kap receives the MESA electron quantities required
by `kap_get`.

## Fast start

```python
from pyfortmesa import mesa

mesa.set_inlist("inlist_eos_and_kap")

mix = mesa.composition({"h1": 0.70, "he4": 0.28, "c12": 0.02})
kap = mesa.Kap()

out = kap.opacity_full(T=1.0e6, Rho=1.0e-7, comp=mix)

print(out["kappa"])
print(out["kap_fracs"])
```

## kap controls

`mesa.Kap(...)` stores Python-side controls that are applied before each opacity
call. The underlying MESA handle is process-persistent.

```python
kap = mesa.Kap(
    use_type2=True,
    zbase=0.02,
    use_zbase_for_type1=True,
)
```

Control precedence:

```text
MESA kap.defaults
  -> optional shared inlist from mesa.set_inlist(...)
  -> optional Python overrides from mesa.Kap(...)
```

| control | units | meaning |
| --- | --- | --- |
| `use_type2` | bool | enable MESA Type2 opacity controls |
| `zbase` | mass fraction | base metallicity used by Type2 controls |
| `use_zbase_for_type1` | bool | use `zbase` for Type1 controls |
| `type2_full_off_X` | mass fraction | Type2 full-off hydrogen threshold |
| `type2_full_on_X` | mass fraction | Type2 full-on hydrogen threshold |
| `type2_full_off_dZ` | mass fraction | Type2 full-off composition threshold |
| `type2_full_on_dZ` | mass fraction | Type2 full-on composition threshold |

`None` means leave the corresponding MESA value unchanged. If no inlist is set
and no Python override is given, pyfortmesa keeps Type2 off so ordinary kap
calls do not require `zbase`.

## Public API

### `mesa.kap_opacity(...)` and `mesa.Kap().opacity(...)`

Signature:

```python
mesa.kap_opacity(
    T: float,
    Rho: float,
    comp: Composition | Mapping[str, float] | Iterable[float] | None = None,
    *,
    use_type2: bool | None = None,
    zbase: float | None = None,
    use_zbase_for_type1: bool | None = None,
    type2_full_off_X: float | None = None,
    type2_full_on_X: float | None = None,
    type2_full_off_dZ: float | None = None,
    type2_full_on_dZ: float | None = None,
) -> dict[str, float]
```

Inputs:

| argument | units | shape | meaning |
| --- | --- | --- | --- |
| `T` | K | scalar | temperature |
| `Rho` | `g cm^-3` | scalar | density |
| `comp` | mass fraction | scalar composition | `Composition`, isotope mapping, legacy vector, or `None` |
| kap controls | mixed | scalar | optional Python overrides listed above |

Returns:

| key | units | meaning |
| --- | --- | --- |
| `kappa` | `cm^2 g^-1` | Rosseland mean opacity |
| `dlnkap_dlnRho` | dimensionless | derivative at constant `T` |
| `dlnkap_dlnT` | dimensionless | derivative at constant `Rho` |

Example:

```python
small = mesa.Kap().opacity(T=1.0e6, Rho=1.0e-7, comp=mix)
print(small["kappa"])
```

### `mesa.kap_opacity_raw(...)` and `mesa.Kap().opacity_raw(...)`

Signature:

```python
mesa.kap_opacity_raw(
    T: float,
    Rho: float,
    chem_id_values: Iterable[int],
    xa: Iterable[float],
    *,
    validate: bool = False,
    use_type2: bool | None = None,
    zbase: float | None = None,
    use_zbase_for_type1: bool | None = None,
    type2_full_off_X: float | None = None,
    type2_full_on_X: float | None = None,
    type2_full_off_dZ: float | None = None,
    type2_full_on_dZ: float | None = None,
) -> tuple[float, float, float]
```

This is the scalar fast path for callers with precomputed `chem_id_values` and
`xa`. It returns:

```text
kappa, dlnkap_dlnRho, dlnkap_dlnT
```

Example:

```python
kap = mesa.Kap()
kap.opacity_raw(T=1.0e6, Rho=1.0e-7, chem_id_values=mix.chem_id, xa=mix.xa)

for T, rho in scalar_points:
    kappa, dkap_dlnrho, dkap_dlnt = kap.opacity_raw(T, rho, mix.chem_id, mix.xa)
```

Use `validate=True` when accepting untrusted arrays. Keep it `False` for hot
loops where `chem_id_values` and `xa` were prepared once by `mesa.composition`.

### `mesa.eos_kap_raw(...)` and `mesa.Kap().eos_kap_raw(...)`

Signature:

```python
mesa.eos_kap_raw(
    T: float,
    Rho: float,
    chem_id_values: Iterable[int],
    xa: Iterable[float],
    *,
    validate: bool = False,
    use_type2: bool | None = None,
    zbase: float | None = None,
    use_zbase_for_type1: bool | None = None,
    type2_full_off_X: float | None = None,
    type2_full_on_X: float | None = None,
    type2_full_off_dZ: float | None = None,
    type2_full_on_dZ: float | None = None,
) -> tuple[np.ndarray, float, float, float]
```

This is the scalar fused eos+kap fast path. It calls eos once, returns the eos
result vector, and passes the electron state from that eos call to kap.

Returns:

```text
results, kappa, dlnkap_dlnRho, dlnkap_dlnT
```

`results` uses `mesa.EOS_RESULT_NAMES` order.

Example:

```python
kap = mesa.Kap()
results, kappa, dkap_dlnrho, dkap_dlnt = kap.eos_kap_raw(
    T=1.0e6, Rho=1.0e-7, chem_id_values=mix.chem_id, xa=mix.xa
)

i_gamma1 = mesa.EOS_RESULT_NAMES.index("gamma1")
gamma1 = results[i_gamma1]
```

Use this instead of calling `eos.dt_raw(...)` and `kap.opacity_raw(...)` when a
scalar loop needs both eos and kap outputs for the same state.

### `mesa.kap_opacity_full(...)` and `mesa.Kap().opacity_full(...)`

Signature:

```python
mesa.kap_opacity_full(
    T: float,
    Rho: float,
    comp: Composition | Mapping[str, float] | Iterable[float] | None = None,
    *,
    use_type2: bool | None = None,
    zbase: float | None = None,
    use_zbase_for_type1: bool | None = None,
    type2_full_off_X: float | None = None,
    type2_full_on_X: float | None = None,
    type2_full_off_dZ: float | None = None,
    type2_full_on_dZ: float | None = None,
) -> dict[str, float | dict[str, float]]
```

Inputs are the same as `kap_opacity(...)`.

Returns:

| key | shape | meaning |
| --- | --- | --- |
| `kappa` | scalar | Rosseland mean opacity |
| `dlnkap_dlnRho` | scalar | derivative at constant `T` |
| `dlnkap_dlnT` | scalar | derivative at constant `Rho` |
| `kap_fracs` | dict | opacity-source fractions |
| `dlnkap_dxa` | dict by isotope name | composition derivatives |

`kap_fracs` keys:

```text
lowT, highT, Type2, Compton
```

Example:

```python
kap_type2 = mesa.Kap(use_type2=True, zbase=0.02)
full = kap_type2.opacity_full(T=1.0e6, Rho=1.0e-7, comp=mix)
print(full["kap_fracs"]["Type2"])
print(full["dlnkap_dxa"]["h1"])
```

### `mesa.kap_opacity_full_raw(...)` and `mesa.Kap().opacity_full_raw(...)`

Signature:

```python
mesa.kap_opacity_full_raw(
    T: float,
    Rho: float,
    chem_id_values: Iterable[int],
    xa: Iterable[float],
    *,
    validate: bool = False,
    use_type2: bool | None = None,
    zbase: float | None = None,
    use_zbase_for_type1: bool | None = None,
    type2_full_off_X: float | None = None,
    type2_full_on_X: float | None = None,
    type2_full_off_dZ: float | None = None,
    type2_full_on_dZ: float | None = None,
) -> tuple[float, float, float, np.ndarray, np.ndarray]
```

Returns:

```text
kappa, dlnkap_dlnRho, dlnkap_dlnT, kap_fracs, dlnkap_dxa
```

`kap_fracs` uses `mesa.KAP_FRAC_NAMES` order. `dlnkap_dxa` follows the input
`chem_id_values`/`xa` species order.

Example:

```python
kappa, dkap_dlnrho, dkap_dlnt, kap_fracs, dkap_dxa = mesa.Kap(
    use_type2=True, zbase=0.02
).opacity_full_raw(1.0e6, 1.0e-7, mix.chem_id, mix.xa)
```

### `mesa.kap_opacity_profile(...)` and `mesa.Kap().opacity_profile(...)`

Signature:

```python
mesa.kap_opacity_profile(
    T: Iterable[float],
    Rho: Iterable[float],
    chem_id_values: Iterable[int],
    xa: object,
    *,
    input_mode: str = "value",
    use_type2: bool | None = None,
    zbase: float | None = None,
    use_zbase_for_type1: bool | None = None,
    type2_full_off_X: float | None = None,
    type2_full_on_X: float | None = None,
    type2_full_off_dZ: float | None = None,
    type2_full_on_dZ: float | None = None,
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

Returns profile arrays:

```text
T
Rho
kappa
dlnkap_dlnRho
dlnkap_dlnT
```

Fixed-composition profile example with physical `T` and `Rho` arrays:

```python
T = np.linspace(6.0e5, 2.5e6, 1000)
rho = np.full_like(T, 1.0e-7)

profile = mesa.Kap().opacity_profile(T, rho, mix.chem_id, mix.xa)
opacity = profile["kappa"]
```

If the caller already stores base-10 `logT` and `logRho`, pass those arrays
directly:

```python
log_T = np.linspace(5.8, 6.4, 1000)
log_rho = np.full_like(log_T, -7.0)

profile = mesa.Kap().opacity_profile(log_T, log_rho, mix.chem_id, mix.xa, input_mode="log10")
```

### `mesa.kap_opacity_profile_from_logs(...)`

Signature:

```python
mesa.kap_opacity_profile_from_logs(
    lnT: Iterable[float],
    lnd: Iterable[float],
    chem_id_values: Iterable[int],
    xa: object,
    *,
    use_type2: bool | None = None,
    zbase: float | None = None,
    use_zbase_for_type1: bool | None = None,
    type2_full_off_X: float | None = None,
    type2_full_on_X: float | None = None,
    type2_full_off_dZ: float | None = None,
    type2_full_on_dZ: float | None = None,
) -> dict[str, object]
```

Inputs are the same profile layout as `kap_opacity_profile(...)`, except `lnT`
and `lnd` are natural logs. Use this when the caller already has natural-log
columns.

### `mesa.eos_kap_profile(...)` and `mesa.Kap().eos_kap_profile(...)`

Signature:

```python
mesa.eos_kap_profile(
    T: Iterable[float],
    Rho: Iterable[float],
    chem_id_values: Iterable[int],
    xa: object,
    *,
    input_mode: str = "value",
    output: str = "raw",
    use_type2: bool | None = None,
    zbase: float | None = None,
    use_zbase_for_type1: bool | None = None,
    type2_full_off_X: float | None = None,
    type2_full_on_X: float | None = None,
    type2_full_off_dZ: float | None = None,
    type2_full_on_dZ: float | None = None,
) -> dict[str, object]
```

This is the preferred profile path when both eos and kap outputs are needed. It
computes the eos state once per zone and passes that state to kap.

Returns:

```text
T
Rho
results             # raw eos matrix, shape (n_eos_results, nzones)
result_names        # row names for results
kappa
dlnkap_dlnRho
dlnkap_dlnT
```

Example:

```python
combined = mesa.Kap().eos_kap_profile(T, rho, mix.chem_id, mix.xa, output="dict")
gamma1 = combined["results"]["gamma1"]
kappa = combined["kappa"]
```

Pass `output="dict"` when interactive code needs `combined["results"]["gamma1"]`.

### `mesa.eos_kap_profile_from_logs(...)`

Signature:

```python
mesa.eos_kap_profile_from_logs(
    lnT: Iterable[float],
    lnd: Iterable[float],
    chem_id_values: Iterable[int],
    xa: object,
    *,
    use_type2: bool | None = None,
    zbase: float | None = None,
    use_zbase_for_type1: bool | None = None,
    type2_full_off_X: float | None = None,
    type2_full_on_X: float | None = None,
    type2_full_off_dZ: float | None = None,
    type2_full_on_dZ: float | None = None,
) -> dict[str, object]
```

Compatibility alias for `eos_kap_profile(..., input_mode="log")`.

## Output schemas

Use schema helpers to inspect expected field names, units, and shapes without
calling MESA:

```python
print(mesa.format_output_schema("kap_opacity_full", species=mix.names))
print(mesa.format_output_schema("eos_kap_profile"))
```

## Source mapping

```text
$MESA_DIR/kap/public/kap_lib.f90
$MESA_DIR/kap/public/kap_def.f90
src/pyfortmesa/fortran/kap/mesa_kap_public.f90
src/pyfortmesa/mesa.py
src/pyfortmesa/mesa_support.py
```

Fortran wrappers:

```text
mesa_kap_composition_with_controls -> kap_get
mesa_kap_composition_full_with_controls -> kap_get
mesa_eos_kap_composition_with_controls -> eos and kap_get once per scalar point
mesa_kap_profile -> eos state then kap_get once per profile zone
mesa_kap_profile_from_logs -> compatibility wrapper for natural-log inputs
mesa_eos_kap_profile -> eos and kap_get once per profile zone
mesa_eos_kap_profile_from_logs -> compatibility wrapper for natural-log inputs
mesa_kap_shutdown -> free handle, optionally kap_shutdown
```

`mesa_kap_composition` and `mesa_kap_composition_full` still exist as lower
level no-control Fortran wrappers, but the public Python API uses the
`_with_controls` wrappers because they cover both default and override cases.

## Common mistakes

- `input_mode="log"` means natural log; use `input_mode="log10"` for base-10
  `logT` and `logRho`.
- Pass log-space inputs with `input_mode`; do not exponentiate them in Python
  just to call the physical-value path.
- Scalar helpers accept `comp=mix`; profile helpers require
  `chem_id_values` and `xa(species,)` or `xa(species, nzones)`.
- `mesa.Kap(...)` creates a Python control object, not an independent MESA
  handle per object.

## Not included

| MESA item | Reason |
| --- | --- |
| `kap_init`, `alloc_kap_handle`, `free_kap_handle` | Managed internally by pyfortmesa handles and `mesa.shutdown(...)`. |
| `kap_ptr` | Exposes MESA pointer state; not safe or useful for normal Python calls. |
| `kap_setup_tables`, `call_load_op_master` | Table-loading internals; normal use goes through `kap_get`. |
| `kap_setup_hooks` | Requires callback/hook design; not part of the current pure microphysics API. |
| mono-opacity routines | Specialized workflow; add only with a concrete mono-opacity example and tests. |
| conductive, Compton, and radiative sub-opacity routines | The current public call exposes total `kap_get` plus fractions. Sub-opacity APIs need a separate design. |
| Mombarg routines | Specialized grid/table workflow; not current scope. |
| `kap_get_control_namelist`, `kap_set_control_namelist` | Current control path is `mesa.set_inlist(...)` plus Python `Kap(...)` overrides. |
| `mesa_kap_sample_composition` | Legacy/sample Fortran wrapper; prefer named `Composition` path for user code. |
