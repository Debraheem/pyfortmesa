# Testing

The repository-level test command is:

```bash
./test
```

That default mode runs the non-MESA checks and compares the generated output
against the committed baseline:

```text
tests/test_output/golden/quick_test_output.txt
```

Generated logs, summaries, and temporary golden output are written under:

```text
tests/test_output/
```

To run the optional MESA-backed integration and profile timing checks after
installing a MESA-enabled build:

```bash
./test mesa
```

The MESA timing suite can also be run directly:

```bash
tests/mesa/run_profile_timing_suite.sh
```

If a behavior change intentionally changes the non-MESA output, inspect:

```text
tests/test_output/golden_compare.log
```

If the new output is correct, replace the committed baseline with:

```text
tests/test_output/tmp_golden_output.txt
```

MESA-backed timing output is not part of the golden baseline because timings and
local MESA paths are machine-dependent.
