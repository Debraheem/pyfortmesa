# Testing

The repository-level test command is:

```bash
./test
```

That default mode runs the checks that do not call MESA and compares the
generated output against the committed baseline:

```text
tests/test_output/golden/quick_test_output.txt
```

Generated logs, summaries, and temporary golden output are written under:

```text
tests/test_output/
```

To run the optional MESA integration and profile timing checks after
installing a build for MESA calls:

```bash
./test mesa
```

The MESA timing suite can also be run directly:

```bash
tests/mesa/run_profile_timing_suite.sh
```

If a behavior change intentionally changes the output from checks that do
not call MESA, inspect:

```text
tests/test_output/golden_compare.log
```

If the new output is correct, replace the committed baseline with:

```text
tests/test_output/tmp_golden_output.txt
```

MESA timing output is not part of the golden baseline because timings and
local MESA paths are machine-dependent.
