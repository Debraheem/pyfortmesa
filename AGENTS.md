# AGENTS.md

This file gives project-local guidance to Codex when working in this repository.

## Project Overview

pyfortmesa is a Python package that wraps a curated part of MESA's `const`,
`chem`, `eos`, and `kap` modules. It is not meant to mirror every MESA public
routine. The package should expose Python workflows that are useful for
microphysics calls, profile batches, and documentation-backed examples.

The compiled wrapper path depends on a MESA build with shared module libraries
and `pkg-config` metadata. The plain package path should remain pure Python and
uploadable as a normal wheel.

## Execution Boundaries

- Do not compile MESA or run MESA models unless the user explicitly gives
  permission.
- Non-MESA package checks, Python unit tests, docs builds, JSON validation, and
  static checks are allowed.
- If a task needs the user's Anaconda setup, assume `conda activate base` is the
  baseline environment instruction unless a more specific env is requested.
- Public install docs should not over-prescribe a conda environment. Use conda
  only where it is actually part of the local workflow or an example context.

## Useful Non-MESA Checks

Run focused checks instead of broad commands when possible:

```bash
python -m py_compile src/pyfortmesa/mesa.py src/pyfortmesa/mesa_support.py
PYTHONPATH=src python tests/unit/test_public_api_docs.py
PYTHONPATH=src python tests/unit/test_output_schema.py
PYTHONPATH=src python tests/unit/test_mesa_profile_helpers.py
conda run -n pyfortmesa python -m mkdocs build --clean --strict \
  --site-dir /private/tmp/pyfortmesa-site-check
PYFORTMESA_TEST_OUTPUT_DIR=/private/tmp/pyfortmesa-test-output ./test quick
git diff --check
```

Do not treat these checks as permission to compile MESA. They are package-side
checks only.

## Development Notes

- If a markdown development note or refactor plan is created, keep it updated as
  the implementation changes.
- Development notes should include equations where they verify implementation
  behavior, plus concrete code references when the note is about code changes.
- Keep notes tied to the actual code paths, not general intent.

## Source-First Answers

- Start from the actual code, docs, logs, or local environment before answering
  implementation questions.
- If the user asks how something works, explain the actual mechanism and name the
  files/functions involved.
- Avoid theory-first answers when a source inspection can answer the question.
- Keep distinctions explicit: branch vs tag vs GitHub Release, OpenMP threads vs
  Python processes, physical values vs natural logs vs base-10 logs, gas
  pressure vs radiation pressure.

## API Scope

- Keep the Python API curated. Add wrappers when they enable a concrete workflow,
  remove a slow Python loop, expose a stable result shape, or manage lifecycle
  state.
- Do not mirror all of MESA `const_def`, `chem_lib`, `eos_lib`, or `kap_lib`.
- When a public MESA routine is intentionally not wrapped, document the reason in
  the module docs rather than leaving the omission mysterious.
- Constants exposed through Python should have units and meanings documented.
- `OUTPUT_SCHEMA_NAMES` is for output-layout schema helpers, not a list of every
  public Python function. Aliases are accepted names, not separate output shapes.

## pyfortmesa Concepts

- `mix` is a `Composition` object. `chem_id` or `chem_id_values` is the isotope
  id array. They are related but not interchangeable.
- Scalar helpers can accept `comp=mix`. Profile helpers take split composition
  data: `chem_id_values` plus `xa`.
- Profile helpers should accept fixed `xa(species)` when the composition is
  constant across zones, and `xa(species, nzones)` when it varies by zone.
- Do not recommend scalar EOS/KAP calls inside a Python zone loop. Move profile
  work into Fortran batch wrappers.
- High-throughput profile APIs should favor raw arrays. Named dictionaries are
  useful for interactive/user-facing paths, but raw arrays avoid unnecessary
  allocation and copying.
- Prefer a single `input_mode="value"|"log"|"log10"` option over adding parallel
  `*_from_log10` function names. Existing `*_from_logs` helpers are
  compatibility aliases for natural-log inputs.
- Keep OpenMP at top-level batched wrapper loops. Do not call a new OpenMP batch
  routine from inside another OpenMP profile routine.
- `OMP_NUM_THREADS` controls Fortran OpenMP threading. Python process count or
  `--nproc` is a different mechanism.
- Timing support should be opt-in and package-owned where possible. Do not make
  timing tests spray persistent JSON/log files by default; keep raw timing
  artifacts temporary unless the user explicitly asks to preserve them.
- Prefer high-level public-call timing labels in production paths. Add internal
  phase timers only when there is a concrete profiling question that needs them.

## EOS/KAP Conventions

- MESA EOS `lnPgas` is gas pressure, not total pressure.
- Radiation pressure is reconstructed from temperature:

```text
Prad = crad*T**4/3
Ptot = exp(lnPgas) + Prad
```

- For energy, make the convention explicit:

```text
Erad = crad*T**4/Rho
Egas = exp(lnE) - Erad
```

- KAP table exploration commonly uses the base-10 coordinate:

```text
logR = logRho - 3*logT + 18
```

This is not the same as natural-log `*_from_logs` input.

## Lifecycle and Handles

- pyfortmesa owns persistent Fortran-side MESA handles for process reuse.
- `mesa.shutdown()` frees pyfortmesa's handles but normally leaves loaded MESA
  tables available for reuse in the process.
- `mesa.shutdown(release_tables=True)` additionally asks MESA modules to release
  loaded table/module state. Document this as a stronger cleanup path.
- Do not expose raw MESA init/alloc/free/pointer routines as normal Python API
  unless there is a concrete lifecycle design.

## Build and Packaging

- The plain build should remain pure Python. The MESA build is local and
  compiled.
- Keep optional compiled wrapper declarations in `meson.build` data-driven
  through `mesa_wrapper_specs`; add symbols to existing entries before adding
  new build blocks.
- If a MESA shared-library build is missing, error messages should point users
  toward rebuilding MESA with shared libraries enabled rather than implying a
  generic Python dependency issue.
- For release wording, keep branch, tag, and GitHub Release distinct:
  branch = editable maintenance line, tag = frozen release point, GitHub Release
  = optional public page attached to a tag.

## Style and Diff Hygiene

- Prefer MESA style when modifying Fortran or MESA-facing wrappers.
- Keep diffs clean and minimally invasive. Do not move functions into new
  wrappers unless the move clearly reduces duplication or matches the local
  design.
- Do not rewrite unrelated code while working on a focused task.
- Use structured APIs or existing local helpers instead of ad hoc parsing when
  possible.

## Line Wrapping

- Do not split arguments or clauses vertically just because a formatter might.
- Keep related short arguments on one line when the line remains readable.
- Use compact two-line wrapping before using one-argument-per-line wrapping.
- Wrap only when the line would otherwise become too long or hard to scan.
- Avoid padded documentation examples where a short function call is spread
  across many lines. Prefer the same compact style used in code.
- For long public signatures, wrap enough to keep the signature readable, but
  avoid mechanical one-argument-per-line formatting unless the signature is
  genuinely long.
- Fortran subroutine headers can use MESA-style continuation sooner than Python
  calls. Do not collapse a Fortran header into one long line just because it
  fits under a Python-oriented width limit.
