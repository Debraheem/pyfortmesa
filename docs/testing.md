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
installing the `./mk mesa` build:

```bash
./test mesa
```

The MESA timing suite can also be run directly:

```bash
tests/mesa/run_profile_timing_suite.sh
```

For an apples-to-apples scalar/profile comparison on the same saved-model
`T/Rho` arrays and compositions:

```bash
tests/mesa/run_scalar_profile_timing_compare.sh
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

## Local timing reference

The numbers below are one local reference run, not a golden baseline. They are
useful for order-of-magnitude checks after changing wrappers or timing code.

Environment:

```text
MESA_DIR=/Users/owner/Documents/Software/dev/mesa_release/mesa
pyfortmesa-0.5.0-cp311-cp311-macosx_26_0_arm64.whl
```

The scalar/profile comparison uses 884 zones from:

```text
$MESA_DIR/star/test_suite/20M_pre_ms_to_core_collapse/standard_after_core_he_burn.mod
```

It compares two composition cases:

```text
fixed_3  -> h1/he4/c12 = 0.70/0.28/0.02 at every zone
saved_22 -> the saved model's 22-isotope composition at each zone
```

The table reports hot-call time after MESA table/cache/handle setup. A
`scalar/profile` ratio greater than 1 means the profile wrapper is faster. The
`eos-kap` scalar row uses `Kap.eos_kap_raw(...)`, so eos is evaluated once per
scalar point before kap. That is the scalar analogue of the profile
`Kap.eos_kap_profile(...)` path.

| case | physics | species | threads | scalar | profile | scalar/profile |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `fixed_3` | eos | 3 | 1 | 16.313 us/zone | 13.816 us/zone | 1.181 |
| `fixed_3` | kap | 3 | 1 | 19.837 us/zone | 16.055 us/zone | 1.236 |
| `fixed_3` | eos-kap | 3 | 1 | 19.824 us/zone | 16.897 us/zone | 1.173 |
| `saved_22` | eos | 22 | 1 | 24.469 us/zone | 21.708 us/zone | 1.127 |
| `saved_22` | kap | 22 | 1 | 27.885 us/zone | 23.696 us/zone | 1.177 |
| `saved_22` | eos-kap | 22 | 1 | 27.926 us/zone | 24.167 us/zone | 1.156 |
| `fixed_3` | eos | 3 | 10 | 16.541 us/zone | 1.989 us/zone | 8.317 |
| `fixed_3` | kap | 3 | 10 | 20.039 us/zone | 2.166 us/zone | 9.251 |
| `fixed_3` | eos-kap | 3 | 10 | 20.093 us/zone | 2.181 us/zone | 9.214 |
| `saved_22` | eos | 22 | 10 | 24.910 us/zone | 2.878 us/zone | 8.654 |
| `saved_22` | kap | 22 | 10 | 27.866 us/zone | 3.088 us/zone | 9.023 |
| `saved_22` | eos-kap | 22 | 10 | 28.052 us/zone | 3.193 us/zone | 8.784 |
