# API helpers

Status: active in the base package. Helpers that call compiled MESA wrappers
still require the `./mk mesa` build at runtime.

Purpose: document setup, shutdown, and output-schema helpers shared by the
`const`, `chem`, `eos`, and `kap` pages.

## Setup helpers

### `mesa.set_cache_root(...)`

Signature:

```python
mesa.set_cache_root(cache_root: str | os.PathLike[str] | None = ".") -> None
```

Sets the cache root used by pyfortmesa before MESA tables are initialized.

Inputs:

| argument | units | shape | meaning |
| --- | --- | --- | --- |
| `cache_root` | path | scalar | runtime cache root; `None` clears it |

Example:

```python
from pyfortmesa import mesa

mesa.set_cache_root(".")
```

Call this before the first EOS/KAP call in a Python process.

### `mesa.set_inlist(...)`

Signature:

```python
mesa.set_inlist(inlist: str | os.PathLike[str] | None) -> None
```

Sets the optional MESA-style inlist used by the EOS/KAP wrappers. The file can
contain both `&eos` and `&kap` namelists.

Inputs:

| argument | units | shape | meaning |
| --- | --- | --- | --- |
| `inlist` | path | scalar | controls file; `None` clears it for future handles |

Example:

```python
mesa.set_inlist("inlist_eos_and_kap")
```

Call this before the first EOS/KAP call in a Python process. Existing MESA
handles keep the controls they already read.

## Shutdown helper

### `mesa.shutdown(...)`

Signature:

```python
mesa.shutdown(*, release_tables: bool = False) -> None
```

Releases persistent pyfortmesa EOS/KAP handles.

Inputs:

| argument | units | shape | meaning |
| --- | --- | --- | --- |
| `release_tables` | bool | scalar | also call MESA module shutdown routines |

Normal cleanup:

```python
try:
    out = mesa.Eos().dt(T=1.0e7, Rho=1.0e2, comp=mix)
finally:
    mesa.shutdown()
```

Use `release_tables=True` only when no other code in the Python process is using
MESA:

```python
mesa.shutdown(release_tables=True)
```

Default `mesa.shutdown()` frees handles but leaves loaded table state available
for reuse in the process. The heavier `release_tables=True` path also calls the
MESA `kap`, `eos`, and `chem` shutdown routines.

## Output schema helpers

The schema helpers are metadata-only. They do not import or call the compiled
MESA wrappers.

### `mesa.output_schema(...)`

Signature:

```python
mesa.output_schema(
    name: str,
    *,
    species: mesa.Composition | Iterable[str] | None = None,
) -> tuple[dict[str, str], ...]
```

Returns rows with these keys:

| key | meaning |
| --- | --- |
| `column` | flat DataFrame-style column name |
| `path` | nested dictionary path |
| `units` | output units |
| `shape` | scalar or profile shape |
| `comment` | short description |

Example:

```python
for row in mesa.output_schema("eos_kap_profile"):
    print(row["column"], row["units"], row["shape"])
```

### `mesa.output_columns(...)`

Signature:

```python
mesa.output_columns(
    name: str,
    *,
    species: mesa.Composition | Iterable[str] | None = None,
) -> tuple[str, ...]
```

Returns only the flat column names from `output_schema(...)`.

Example:

```python
columns = mesa.output_columns("kap_opacity_full", species=("h1", "he4", "c12"))
```

### `mesa.format_output_schema(...)`

Signature:

```python
mesa.format_output_schema(
    name: str,
    *,
    species: mesa.Composition | Iterable[str] | None = None,
) -> str
```

Returns comment-style lines for interactive notebooks or quick inspection.

Example:

```python
print(mesa.format_output_schema("eos_dt_full", species=mix.names))
```

### `mesa.print_output_schema(...)`

Signature:

```python
mesa.print_output_schema(
    name: str,
    *,
    species: mesa.Composition | Iterable[str] | None = None,
) -> None
```

Prints `format_output_schema(...)`.

### `mesa.output_schema_names(...)`

Signature:

```python
mesa.output_schema_names(*, include_aliases: bool = False) -> tuple[str, ...]
```

Returns accepted names for `output_schema(...)`. With `include_aliases=True`, it
also lists convenience names such as `eos`, `kap`, and `eos_kap`.

Canonical names:

```text
eos_dt
eos_dt_full
eos_dt_profile
eos_dt_profile_from_logs
eos_solve_rho
eos_solve_rho_profile
eos_solve_t
eos_solve_t_profile
kap_opacity
kap_opacity_full
kap_opacity_profile
kap_opacity_profile_from_logs
eos_kap_profile
eos_kap_profile_from_logs
```

## Common mistakes

- Schema names describe pyfortmesa output layouts, not all public functions.
- `input_mode="value"`, `"log"`, and `"log10"` change inputs only, so they do
  not create separate schema names.
- `include_aliases=True` lists additional accepted strings. Use the default
  canonical list in documentation and examples.
- The schema helpers do not validate a live MESA installation.

## Timing helpers

Timing is disabled by default. When enabled, pyfortmesa records process-local
wall-clock time for high-level public calls such as `eos.dt_profile` and
`kap.eos_kap_profile`. It does not write files unless caller code writes the
summary.

### `mesa.timing(...)`

Signature:

```python
mesa.timing(*, reset: bool = True)
```

Context manager that enables timing and restores the previous timing state on
exit.

Example:

```python
with mesa.timing():
    output = mesa.Kap().eos_kap_profile(T, rho, chem_id, xa)

print(mesa.format_timing_summary(sort_by="seconds"))
```

### `mesa.enable_timing(...)`, `mesa.disable_timing(...)`, and `mesa.reset_timing(...)`

Signatures:

```python
mesa.enable_timing(*, reset: bool = True) -> None
mesa.disable_timing() -> None
mesa.reset_timing() -> None
```

Use these for long scripts where a context manager is not convenient:

```python
mesa.enable_timing()
for T, rho, xa in profiles:
    kap.eos_kap_profile(T, rho, chem_id, xa)
mesa.disable_timing()
mesa.print_timing_summary(sort_by="seconds")
```

### `mesa.timing_summary(...)`

Signature:

```python
mesa.timing_summary(*, sort_by: str = "order") -> tuple[dict[str, float | int | str], ...]
```

Returns rows with these keys:

| key | meaning |
| --- | --- |
| `name` | timed public-call name |
| `calls` | number of times the call ran |
| `seconds` | accumulated wall-clock seconds |
| `seconds_per_call` | accumulated seconds divided by calls |
| `fraction` | fraction of recorded pyfortmesa time |

Use `sort_by="seconds"` to put the most expensive public calls first.

### `mesa.format_timing_summary(...)` and `mesa.print_timing_summary(...)`

Signatures:

```python
mesa.format_timing_summary(*, sort_by: str = "order") -> str
mesa.print_timing_summary(*, sort_by: str = "order") -> None
```

These are display helpers for notebooks and scripts. They report high-level
pyfortmesa public calls only; total script time, parsing, plotting, and caller
code remain the caller's responsibility.
