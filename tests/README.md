# Test Runner

From the repository root, run the normal source tree checks with:

```bash
./test
```

That default mode does not call MESA. It runs import/unit checks, syntax
checks for the MESA shell runners, a dry summary suite path that does not
call MESA, and a golden-output comparison. Every command writes stdout and stderr to
`tests/test_output/`, with a command/status index at:

```text
tests/test_output/test_summary.txt
```

The committed golden baseline is:

```text
tests/test_output/golden/quick_test_output.txt
```

Each run writes the candidate output and diff log to:

```text
tests/test_output/tmp_golden_output.txt
tests/test_output/golden_compare.log
```

Use `PYFORTMESA_TEST_OUTPUT_DIR=/path/to/output ./test` to choose a different
output directory. The default `tests/test_output/` directory is ignored by git
except for `tests/test_output/golden/`, which stores the committed baseline.

## Developing

When a behavior change intentionally changes the test output from checks
that do not call MESA, inspect
`tests/test_output/golden_compare.log`. If the new output is correct, replace:

```text
tests/test_output/golden/quick_test_output.txt
```

with:

```text
tests/test_output/tmp_golden_output.txt
```

There is no update script on purpose; replacing the baseline should be an
explicit development action. MESA timing output is not part of this
golden file because timing values and local MESA paths are machine-dependent.

After installing with `./mk mesa` and setting `MESA_DIR`, run:

```bash
./test mesa
```

That runs the quick checks first, then the optional MESA eos/kap,
hydrostatic, and saved model profile timing runners. `./test all` is currently
an alias for `./test mesa`.

The standard saved model profile timing report is part of `./test mesa` through:

```bash
tests/mesa/run_profile_timing_suite.sh
```

## Simple work example

For a small example meant to be copied into project code, see:

```bash
tests/work/run_simple_chem_eos_kap.sh
```

That example calls `chem`, scalar `eos`, scalar `kap`, and the combined
profile eos+kap wrapper.
